import gzip
import io
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.management import call_command
from django.db import connection, transaction
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import (
    Customer, FormTemplate, FormStep, FormElement, DocumentRequirement,
    FormAssignment, DocumentUpload, AwarenessDeclaration, AuditLog,
    NotificationLog, User, SystemSetting
)
from .utils import log_action, get_client_ip, get_user_agent, get_nas_base_path

logger = logging.getLogger('modules')

BACKUP_DIR = Path(os.getenv('BACKUP_DIR', settings.BASE_DIR / 'data' / 'backups'))


def is_admin_user(user):
    """Only superusers or administrative users have access to system maintenance."""
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == 'admin'))


def is_safe_backup_filename(filename):
    """Validate that filename is strictly alphanumeric and safe against path traversal."""
    return bool(filename and re.match(r'^[A-Za-z0-9_\-]+\.json(\.gz)?$', filename))


def get_available_backups():
    """Retrieve list of existing backups on server storage ordered by date descending."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    try:
        for p in BACKUP_DIR.iterdir():
            if p.is_file() and is_safe_backup_filename(p.name):
                stat = p.stat()
                size_bytes = stat.st_size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

                is_pre_restore = p.name.startswith("pre_restore_")
                backups.append({
                    'filename': p.name,
                    'size_str': size_str,
                    'size_bytes': size_bytes,
                    'created_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
                    'is_pre_restore': is_pre_restore,
                })
        backups.sort(key=lambda x: x['created_at'], reverse=True)
    except Exception as e:
        logger.error(f"Error reading backups directory: {e}")
    return backups


@login_required
@user_passes_test(is_admin_user)
def admin_maintenance(request):
    """Main system maintenance view."""
    # Database metrics
    db_engine = connection.vendor  # 'postgresql' or 'sqlite'
    counts = {
        'customers': Customer.objects.count(),
        'templates': FormTemplate.objects.count(),
        'steps': FormStep.objects.count(),
        'elements': FormElement.objects.count(),
        'requirements': DocumentRequirement.objects.count(),
        'assignments': FormAssignment.objects.count(),
        'uploads': DocumentUpload.objects.count(),
        'declarations': AwarenessDeclaration.objects.count(),
        'audit_logs': AuditLog.objects.count(),
        'notification_logs': NotificationLog.objects.count(),
        'users': User.objects.count(),
    }
    total_records = sum(counts.values())

    backups = get_available_backups()

    context = {
        'db_engine': db_engine.upper(),
        'counts': counts,
        'total_records': total_records,
        'backups': backups,
        'backup_count': len(backups),
        'last_backup': backups[0]['created_at'] if backups else None,
        'app_version': getattr(settings, 'APP_VERSION', '3.0.0'),
        'nas_base_path': get_nas_base_path(),
    }
    return render(request, 'modules/admin/maintenance.html', context)

@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_update_settings(request):
    """Update global system settings (e.g. NAS Base Path)."""
    nas_base_path = request.POST.get('nas_base_path', '').strip()
    
    if not nas_base_path:
        messages.error(request, "Il percorso del Folder NAS non può essere vuoto.")
        return redirect('admin_maintenance')
        
    try:
        setting, created = SystemSetting.objects.get_or_create(key='nas_base_path')
        old_value = setting.value
        setting.value = nas_base_path
        setting.updated_by = request.user
        setting.save()
        
        log_action(
            request.user,
            'update',
            'SystemSetting',
            'nas_base_path',
            {'old_value': old_value, 'new_value': nas_base_path},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        messages.success(request, "Impostazioni di sistema aggiornate con successo.")
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        messages.error(request, f"Errore durante l'aggiornamento delle impostazioni: {str(e)}")
        
    return redirect('admin_maintenance')


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_reset_statistics(request):
    """Reset telemetry statistics and system audit logs."""
    confirm_text = request.POST.get('confirm_text', '').strip().upper()
    if confirm_text != 'RESET':
        messages.error(request, "Operazione annullata: è necessario digitare 'RESET' per confermare l'azzeramento.")
        return redirect('admin_maintenance')

    mode = request.POST.get('reset_mode', 'all')  # 'all' or 'older_30'

    try:
        if mode == 'older_30':
            cutoff = timezone.now() - timezone.timedelta(days=30)
            count_audit, _ = AuditLog.objects.filter(action_datetime__lt=cutoff).delete()
            count_notif, _ = NotificationLog.objects.filter(notification_datetime__lt=cutoff).delete()
            msg = f"Statistiche e log anteriori a 30 giorni eliminati con successo ({count_audit} log audit, {count_notif} notifiche)."
        else:
            count_audit, _ = AuditLog.objects.all().delete()
            count_notif, _ = NotificationLog.objects.all().delete()
            msg = f"Tutte le statistiche e i log telemetrici sono stati azzerati con successo ({count_audit} log audit, {count_notif} notifiche)."

        # Register audit event for the reset action itself
        log_action(
            request.user,
            'delete',
            'AuditLog',
            'telemetry_reset',
            {'mode': mode, 'deleted_audit_logs': count_audit, 'deleted_notifications': count_notif},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        messages.success(request, msg)
    except Exception as e:
        logger.error(f"Error during statistics reset: {e}")
        messages.error(request, f"Errore durante il reset delle statistiche: {str(e)}")

    return redirect('admin_maintenance')


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_backup_create(request):
    """Generate a complete compressed JSON backup of application data."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ehmoduli_backup_{timestamp}.json.gz"
    file_path = BACKUP_DIR / filename

    try:
        buf = io.StringIO()
        call_command(
            'dumpdata',
            'modules',
            'accounts',
            natural_foreign=True,
            natural_primary=True,
            exclude=['contenttypes', 'auth.permission'],
            indent=2,
            stdout=buf
        )
        json_content = buf.getvalue()

        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            f.write(json_content)

        file_size_kb = file_path.stat().st_size / 1024
        logger.info(f"Database backup created: {filename} ({file_size_kb:.1f} KB) by {request.user}")

        log_action(
            request.user,
            'create',
            'DatabaseBackup',
            filename,
            {'size_kb': round(file_size_kb, 1), 'timestamp': timestamp},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        messages.success(request, f"Backup del database creato con successo: {filename} ({file_size_kb:.1f} KB).")
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        messages.error(request, f"Errore durante la creazione del backup: {str(e)}")

    return redirect('admin_maintenance')


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_backup_download(request, filename):
    """Download an existing database backup file."""
    if not is_safe_backup_filename(filename):
        return HttpResponseBadRequest("Nome file di backup non valido o non consentito.")

    file_path = BACKUP_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise Http404("File di backup non trovato.")

    content_type = 'application/gzip' if filename.endswith('.gz') else 'application/json'
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_backup_restore(request):
    """
    Restore database from an existing server backup or an uploaded file.
    Always takes an automatic safety snapshot before restoring.
    """
    confirm_text = request.POST.get('confirm_text', '').strip().upper()
    if confirm_text != 'RIPRISTINA':
        messages.error(request, "Operazione annullata: è necessario digitare 'RIPRISTINA' per confermare il ripristino.")
        return redirect('admin_maintenance')

    source_type = request.POST.get('source_type') or request.POST.get('backup_source', 'existing')
    if source_type == 'server':
        source_type = 'existing'

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    target_path = None
    temp_file_to_clean = None
    temp_decompressed = None

    try:
        if source_type == 'existing':
            filename = (request.POST.get('filename') or request.POST.get('backup_filename', '')).strip()
            if not is_safe_backup_filename(filename):
                messages.error(request, "Nome file di backup non valido.")
                return redirect('admin_maintenance')
            target_path = BACKUP_DIR / filename
            if not target_path.exists():
                messages.error(request, f"File di backup '{filename}' non trovato.")
                return redirect('admin_maintenance')

        elif source_type == 'upload':
            if 'backup_file' not in request.FILES:
                messages.error(request, "Nessun file di backup caricato.")
                return redirect('admin_maintenance')
            uploaded = request.FILES['backup_file']
            if not is_safe_backup_filename(uploaded.name):
                messages.error(request, "Il file caricato deve avere estensione .json o .json.gz.")
                return redirect('admin_maintenance')

            # Save uploaded file into temporary file
            suffix = '.json.gz' if uploaded.name.endswith('.gz') else '.json'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(BACKUP_DIR)) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
                target_path = Path(tmp.name)
                temp_file_to_clean = target_path
        else:
            messages.error(request, "Tipo di sorgente di ripristino non valido.")
            return redirect('admin_maintenance')

        # 1. Automatic Pre-Restore Safety Snapshot
        snap_ts = timezone.now().strftime('%Y%m%d_%H%M%S')
        safety_snapshot_name = f"pre_restore_snapshot_{snap_ts}.json.gz"
        safety_path = BACKUP_DIR / safety_snapshot_name

        buf = io.StringIO()
        call_command(
            'dumpdata',
            'modules',
            'accounts',
            natural_foreign=True,
            natural_primary=True,
            exclude=['contenttypes', 'auth.permission'],
            indent=2,
            stdout=buf
        )
        with gzip.open(safety_path, 'wt', encoding='utf-8') as sf:
            sf.write(buf.getvalue())

        logger.info(f"Created pre-restore safety snapshot: {safety_snapshot_name}")

        # 2. Decompress if needed to run loaddata
        restore_json_file = None
        temp_decompressed = None

        if str(target_path).endswith('.gz'):
            with gzip.open(target_path, 'rt', encoding='utf-8') as gz_in:
                content = gz_in.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8', dir=str(BACKUP_DIR)) as jf:
                jf.write(content)
                restore_json_file = Path(jf.name)
                temp_decompressed = restore_json_file
        else:
            restore_json_file = target_path

        # 3. Execute loaddata inside atomic transaction
        with transaction.atomic():
            call_command('loaddata', str(restore_json_file))

        # Log the restore event
        log_action(
            request.user,
            'update',
            'DatabaseRestore',
            target_path.name,
            {'pre_restore_snapshot': safety_snapshot_name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        messages.success(
            request,
            f"Ripristino completato con successo! È stato creato automaticamente il punto di sicurezza: {safety_snapshot_name}."
        )

    except Exception as e:
        logger.error(f"Database restore failed: {e}")
        messages.error(request, f"Errore durante il ripristino del database: {str(e)}")
    finally:
        # Cleanup temporary files
        if temp_file_to_clean and temp_file_to_clean.exists():
            try:
                temp_file_to_clean.unlink()
            except Exception:
                pass
        if temp_decompressed and temp_decompressed.exists():
            try:
                temp_decompressed.unlink()
            except Exception:
                pass

    return redirect('admin_maintenance')


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_backup_delete(request, filename):
    """Delete an existing backup file from server storage."""
    if not is_safe_backup_filename(filename):
        messages.error(request, "Nome file di backup non valido.")
        return redirect('admin_maintenance')

    file_path = BACKUP_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        messages.error(request, "File di backup non trovato.")
        return redirect('admin_maintenance')

    try:
        file_path.unlink()
        log_action(
            request.user,
            'delete',
            'DatabaseBackup',
            filename,
            {},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        messages.success(request, f"Backup '{filename}' eliminato con successo.")
    except Exception as e:
        logger.error(f"Failed to delete backup file {filename}: {e}")
        messages.error(request, f"Errore durante l'eliminazione del backup: {str(e)}")

    return redirect('admin_maintenance')
