"""
Views for file uploads, absence declarations, and document requirements processing.
"""

import os
import json
import hashlib
import secrets
import tempfile
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from .models import FormTemplate, DocumentRequirement, FormAssignment, DocumentUpload, AwarenessDeclaration
from .utils import get_client_ip, get_user_agent, log_action, safe_get_form_data, get_nas_base_path
from .permissions import validate_assignment_access
from .upload_security import (
    validate_file_upload_secure,
    validate_absence_declaration_file,
    save_uploaded_file_secure,
    safe_join_paths,
    save_manifest_atomic,
)

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

logger = logging.getLogger('modules')


@require_http_methods(["POST"])
@ratelimit(key='ip', rate='30/m', method='POST', block=False)
def published_form_upload(request, form_id):
    """Upload document to published form (no FormAssignment)."""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Limite di upload superato per questo minuto. Riprova a breve.'}, status=429)

    try:
        form = FormTemplate.objects.exclude(status='archived').get(id=form_id)
    except FormTemplate.DoesNotExist:
        return JsonResponse({'error': 'Form not found'}, status=404)

    # Check session authentication
    session_key = f'form_access_{form_id}'
    if not request.session.get(session_key, False):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    file = request.FILES.get('file')
    requirement_id = request.POST.get('requirement_id')
    file_description = request.POST.get('description', '')

    if not file or not requirement_id:
        return JsonResponse({'error': 'Missing file or requirement'}, status=400)

    try:
        requirement = DocumentRequirement.objects.select_related('form_step').get(
            id=requirement_id,
            form_step__form_template=form
        )
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Requirement not found or does not belong to this form'}, status=404)

    # Validate file
    errors = validate_file_upload_secure(file, requirement)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    try:
        nas_base = get_nas_base_path()
        if form.customer:
            nas_path = os.path.join(
                nas_base,
                form.customer.nas_folder_name,
                form.project_name,
                requirement.destination_subfolder
            )
        else:
            return JsonResponse({'error': 'Form must have a customer'}, status=400)

        os.makedirs(nas_path, exist_ok=True)

        # Generate safe filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = file.name.split('.')[-1] if '.' in file.name else ''
        safe_filename = f"{secrets.token_hex(4)}_{timestamp}.{ext}"
        file_path = os.path.join(nas_path, safe_filename)

        # Write file atomically
        with tempfile.NamedTemporaryFile(delete=False, dir=nas_path) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        os.replace(tmp_path, file_path)

        # Calculate SHA256
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        sha256_hex = sha256.hexdigest()

        # Update manifest.json
        manifest_path = os.path.join(nas_base, form.customer.nas_folder_name, form.project_name, 'manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            manifest = {
                'form_id': str(form.id),
                'form_name': form.name,
                'customer': f"{form.customer.first_name} {form.customer.last_name or ''}".strip(),
                'customer_code': form.customer.code,
                'project': form.project_name,
                'created_at': timezone.now().isoformat(),
                'uploads': []
            }

        manifest['uploads'].append({
            'requirement_name': requirement.name,
            'requirement_id': str(requirement.id),
            'original_filename': file.name,
            'stored_filename': safe_filename,
            'file_size': file.size,
            'sha256': sha256_hex,
            'mime_type': file.content_type,
            'description': file_description,
            'upload_datetime': timezone.now().isoformat(),
            'uploaded_from_ip': get_client_ip(request)
        })

        save_manifest_atomic(manifest_path, manifest)

        log_action(
            None,
            'upload',
            'PublishedFormDocument',
            str(form.id),
            {
                'customer': form.customer.code,
                'project': form.project_name,
                'original_filename': file.name,
                'size': file.size,
                'checksum': sha256_hex
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'status': 'success',
            'filename': file.name,
            'size': file.size
        })

    except Exception as e:
        log_action(
            None,
            'upload',
            'PublishedFormDocument',
            'ERROR',
            {'error': str(e), 'form_id': str(form.id)},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )
        return JsonResponse({'error': 'Upload failed'}, status=500)


@require_http_methods(["POST"])
@ratelimit(key='ip', rate='30/m', method='POST', block=False)
def upload_document_view(request, assignment_id):
    """Upload document with comprehensive security validation and NAS storage."""
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Limite di upload superato per questo minuto. Riprova a breve.'}, status=429)

    assignment, err_resp = validate_assignment_access(request, assignment_id, require_writable=True)
    if err_resp:
        return err_resp

    file = request.FILES.get('file')
    requirement_id = request.POST.get('requirement_id')

    if not requirement_id:
        for k in request.POST.keys():
            if k.startswith('availability_') or k.startswith('file_'):
                requirement_id = k.split('_', 1)[1]
                break

    if not file and requirement_id:
        file = request.FILES.get(f'file_{requirement_id}')

    if not file or not requirement_id:
        return JsonResponse({'error': 'Missing file or requirement'}, status=400)

    # Verify form_data has client and project (Step 0 must be completed)
    if not assignment.form_data or 'client_name' not in assignment.form_data:
        if assignment.customer:
            if not assignment.form_data:
                assignment.form_data = {}
            assignment.form_data['client_name'] = assignment.customer.nas_folder_name or f"cliente_{assignment.customer.code}"
            assignment.form_data['project_name'] = (getattr(assignment.form_template, 'project_name', None) if assignment.form_template else None) or (assignment.form_template.name if assignment.form_template else None) or 'Progetto'
            assignment.save(update_fields=['form_data'])
        else:
            return JsonResponse({'error': 'Please complete Step 0 (Client & Project info) first'}, status=400)

    try:
        requirement = DocumentRequirement.objects.select_related('form_step').get(
            id=requirement_id,
            form_step__form_template_id=assignment.form_template_id
        )
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Requirement not found or does not belong to this form'}, status=404)

    # Check max_files limit for multi-file additions
    if requirement.max_files > 1:
        current_valid_count = DocumentUpload.objects.filter(
            form_assignment=assignment,
            document_requirement=requirement,
            status='valid'
        ).count()
        if current_valid_count >= requirement.max_files:
            return JsonResponse({
                'error': f'Limite massimo di {requirement.max_files} file già raggiunto per questo documento. Elimina un file prima di aggiungerne un altro.'
            }, status=400)

    # SECURE VALIDATION: checks path traversal, MIME, double extensions, etc
    errors = validate_file_upload_secure(file, requirement)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    try:
        client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
        project_name = safe_get_form_data(assignment.form_data, 'project_name') or (getattr(assignment.form_template, 'project_name', None) if assignment.form_template else None) or (assignment.form_template.name if assignment.form_template else None) or 'Progetto'
        nas_base = get_nas_base_path()
        nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
        os.makedirs(nas_project_path, exist_ok=True)

        # Check if bulk ZIP archive
        if file.name.lower().endswith('.zip'):
            from .upload_security import extract_and_index_zip_archive
            bulk_res = extract_and_index_zip_archive(
                file,
                assignment,
                requirement,
                nas_project_path,
                request=request
            )
            assignment.status = 'in_progress'
            assignment.last_access_date = timezone.now()
            assignment.save(update_fields=['status', 'last_access_date'])

            return JsonResponse({
                'status': 'success',
                'is_bulk': True,
                'extracted_count': bulk_res['count'],
                'message': bulk_res['message'],
                'files': bulk_res['files']
            })

        # If max_files is 1, replace previous file; if max_files > 1, allow multiple files up to limit
        with transaction.atomic():
            locked_assignment = FormAssignment.objects.select_for_update().get(id=assignment.id)

            if requirement.max_files > 1:
                current_valid_count = DocumentUpload.objects.filter(
                    form_assignment=locked_assignment,
                    document_requirement=requirement,
                    status='valid'
                ).count()
                if current_valid_count >= requirement.max_files:
                    return JsonResponse({
                        'error': f'Limite massimo di {requirement.max_files} file già raggiunto per questo documento. Elimina un file prima di aggiungerne un altro.'
                    }, status=400)

            # SECURE SAVE: atomic write, safe paths, restrictive permissions
            upload = save_uploaded_file_secure(
                file,
                locked_assignment,
                requirement,
                nas_project_path,
                request=request
            )

            # Always supersede any previous 'not_available' justification records for this requirement
            DocumentUpload.objects.filter(
                form_assignment=locked_assignment,
                document_requirement=requirement,
                availability_status='not_available'
            ).exclude(id=upload.id).update(status='superseded')

            if requirement.max_files == 1:
                DocumentUpload.objects.filter(
                    form_assignment=locked_assignment,
                    document_requirement=requirement,
                    status='valid'
                ).exclude(id=upload.id).update(status='superseded')

            upload.uploaded_by_ip = get_client_ip(request)
            upload.uploaded_by_user_agent = get_user_agent(request)
            upload.save(update_fields=['uploaded_by_ip', 'uploaded_by_user_agent'])

            manifest_path = os.path.join(nas_project_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    'form_name': locked_assignment.form_template.name if locked_assignment.form_template else 'N/A',
                    'customer': client_name,
                    'project': project_name,
                    'form_assignment_id': str(locked_assignment.id),
                    'uploads': []
                }

            file_description = request.POST.get('file_description') or request.POST.get('description', '') or requirement.description or ''
            manifest['uploads'].append({
                'requirement_name': requirement.name,
                'requirement_description': requirement.description,
                'original_filename': upload.original_filename,
                'stored_filename': upload.stored_filename,
                'file_size': upload.file_size,
                'sha256': upload.sha256_checksum,
                'mime_type': upload.mime_type_detected,
                'description': file_description,
                'status': 'uploaded',
                'availability_status': 'uploaded',
                'is_absence_declaration': False,
                'upload_datetime': timezone.now().isoformat(),
                'uploaded_by_ip': get_client_ip(request)
            })
            save_manifest_atomic(manifest_path, manifest)

        log_action(
            None,
            'upload',
            'DocumentUpload',
            str(upload.id),
            {
                'original_filename': upload.original_filename,
                'size': file.size,
                'checksum': upload.sha256_checksum,
                'mime': upload.mime_type_detected
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        try:
            total_reqs_qs = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template)
            total_reqs = total_reqs_qs.count() if total_reqs_qs.exists() else 0

            valid_uploads_qs = assignment.documentupload_set.filter(status='valid')
            valid_count = valid_uploads_qs.count() if valid_uploads_qs.exists() else 0

            if assignment.status == 'draft':
                assignment.status = 'in_progress'
            if assignment.status == 'in_progress':
                if total_reqs > 0:
                    assignment.completion_percentage = min(45, max(10, int((valid_count / total_reqs) * 50)))
                else:
                    assignment.completion_percentage = 10
            assignment.save(update_fields=['status', 'completion_percentage'])
        except Exception as st_err:
            logger.warning(f"Could not update assignment progress: {st_err}")

        return JsonResponse({
            'status': 'success',
            'upload_id': str(upload.id),
            'filename': upload.original_filename,
            'size': file.size
        })

    except ValueError as e:
        log_action(
            None,
            'upload',
            'DocumentUpload',
            'FAILED',
            {'error': str(e), 'filename': file.name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        logger.exception(f"Unexpected upload error: {e}")
        log_action(
            None,
            'upload',
            'DocumentUpload',
            'ERROR',
            {'error': str(e)},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )
        return JsonResponse({'error': f'Caricamento fallito: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def skip_optional_document(request, assignment_id, requirement_id):
    """Mark a document requirement as not available with reason or formal declaration letter."""
    assignment, err_resp = validate_assignment_access(request, assignment_id, require_writable=True)
    if err_resp:
        return err_resp

    try:
        requirement = DocumentRequirement.objects.select_related('form_step').get(
            id=requirement_id,
            form_step__form_template_id=assignment.form_template_id
        )
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Documento o pratica non trovata.'}, status=404)

    file_obj = request.FILES.get('file') or request.FILES.get('declaration_file')
    justification = (request.POST.get('justification') or request.POST.get('declaration_text') or '').strip()

    if requirement.required and not file_obj and not justification:
        return JsonResponse({
            'error': 'Per i documenti obbligatori non disponibili è necessario allegare il giustificativo o una formale dichiarazione su carta intestata timbrata e firmata.'
        }, status=400)

    final_motive = justification or ('Dichiarazione formale su carta intestata timbrata e firmata' if file_obj else 'Documento non disponibile')

    # Case 1: Uploaded formal signed/stamped declaration file
    if file_obj:
        validation_errors = validate_absence_declaration_file(file_obj)
        if validation_errors:
            return JsonResponse({'error': ' '.join(validation_errors), 'errors': validation_errors}, status=400)

        client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
        project_name = safe_get_form_data(assignment.form_data, 'project_name') or (getattr(assignment.form_template, 'project_name', None) if assignment.form_template else None) or (assignment.form_template.name if assignment.form_template else None) or 'Progetto'
        nas_base = get_nas_base_path()
        nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
        os.makedirs(nas_project_path, exist_ok=True)

        with transaction.atomic():
            # Mark existing valid uploads as superseded ONLY after successful validation
            DocumentUpload.objects.filter(
                form_assignment=assignment,
                document_requirement=requirement,
                status='valid'
            ).update(status='superseded')
            upload = save_uploaded_file_secure(
                file_obj,
                assignment,
                requirement,
                nas_project_path,
                request=request,
                availability_status='not_available',
                motivazione_indisponibilita=final_motive
            )

            AwarenessDeclaration.objects.create(
                form_assignment=assignment,
                document_requirement=requirement,
                declaration_text=final_motive,
                accepted=True,
                acceptance_ip=get_client_ip(request),
                acceptance_user_agent=get_user_agent(request),
                customer_name_declared=request.POST.get('customer_name', '')
            )

            manifest_path = os.path.join(nas_project_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    'form_name': assignment.form_template.name if assignment.form_template else 'N/A',
                    'customer': client_name,
                    'project': project_name,
                    'form_assignment_id': str(assignment.id),
                    'uploads': []
                }
            manifest.setdefault('uploads', []).append({
                'requirement_name': requirement.name,
                'requirement_description': requirement.description,
                'original_filename': upload.original_filename,
                'stored_filename': upload.stored_filename,
                'file_size': upload.file_size,
                'sha256': upload.sha256_checksum,
                'mime_type': upload.mime_type_detected,
                'status': 'not_available',
                'availability_status': 'not_available',
                'is_absence_declaration': True,
                'motivazione_indisponibilita': final_motive,
                'upload_datetime': timezone.now().isoformat(),
                'uploaded_by_ip': get_client_ip(request)
            })
            save_manifest_atomic(manifest_path, manifest)

        log_action(
            None,
            'upload_absence_declaration',
            'DocumentUpload',
            str(upload.id),
            {
                'original_filename': upload.original_filename,
                'size': upload.file_size,
                'checksum': upload.sha256_checksum,
                'motive': final_motive
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'status': 'success',
            'availability_status': 'not_available',
            'filename': upload.original_filename,
            'file_size': upload.file_size,
            'justification': final_motive,
            'is_declaration_file': True
        })

    # Case 2: Only justification text
    with transaction.atomic():
        DocumentUpload.objects.filter(
            form_assignment=assignment,
            document_requirement=requirement,
            status='valid'
        ).update(status='superseded')
        DocumentUpload.objects.create(
            form_assignment=assignment,
            document_requirement=requirement,
            original_filename="NON_DISPONIBILE",
            stored_filename="",
            relative_path="",
            file_extension="",
            mime_type_detected="text/plain",
            file_size=0,
            sha256_checksum="",
            status='valid',
            availability_status='not_available',
            motivazione_indisponibilita=final_motive,
            uploaded_by_ip=get_client_ip(request),
            uploaded_by_user_agent=get_user_agent(request),
        )

        AwarenessDeclaration.objects.create(
            form_assignment=assignment,
            document_requirement=requirement,
            declaration_text=final_motive,
            accepted=True,
            acceptance_ip=get_client_ip(request),
            acceptance_user_agent=get_user_agent(request),
            customer_name_declared=request.POST.get('customer_name', '')
        )

        client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
        project_name = safe_get_form_data(assignment.form_data, 'project_name') or ''
        nas_base = get_nas_base_path()
        manifest_path = os.path.join(nas_base, client_name, project_name, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            manifest.setdefault('uploads', []).append({
                'requirement_name': requirement.name,
                'requirement_description': requirement.description,
                'original_filename': 'NON_DISPONIBILE',
                'stored_filename': '',
                'file_size': 0,
                'sha256': '',
                'mime_type': 'text/plain',
                'status': 'not_available',
                'availability_status': 'not_available',
                'is_absence_declaration': False,
                'motivazione_indisponibilita': final_motive,
                'upload_datetime': timezone.now().isoformat(),
                'uploaded_by_ip': get_client_ip(request)
            })
            save_manifest_atomic(manifest_path, manifest)

    return JsonResponse({
        'status': 'success',
        'availability_status': 'not_available',
        'filename': 'NON_DISPONIBILE',
        'file_size': 0,
        'justification': final_motive,
        'is_declaration_file': False
    })


@require_http_methods(["POST"])
def delete_upload_view(request, assignment_id, upload_id):
    """Delete or mark superseded an uploaded file from an assignment."""
    assignment, err_resp = validate_assignment_access(request, assignment_id, require_writable=True)
    if err_resp:
        return err_resp

    try:
        upload = DocumentUpload.objects.get(id=upload_id, form_assignment=assignment)
    except DocumentUpload.DoesNotExist:
        return JsonResponse({'error': 'File o pratica non trovata.'}, status=404)

    req_id = upload.document_requirement_id
    filename = upload.original_filename
    upload.status = 'superseded'
    upload.save(update_fields=['status'])

    # Count remaining valid uploads for this requirement
    remaining_count = DocumentUpload.objects.filter(
        form_assignment=assignment,
        document_requirement_id=req_id,
        status='valid'
    ).count()

    # Recalculate completion percentage
    try:
        total_reqs_qs = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template)
        total_reqs = total_reqs_qs.count() if total_reqs_qs.exists() else 0
        valid_count = DocumentUpload.objects.filter(form_assignment=assignment, status='valid').count()
        if assignment.status == 'in_progress':
            if total_reqs > 0:
                assignment.completion_percentage = min(45, max(10, int((valid_count / total_reqs) * 50)))
            else:
                assignment.completion_percentage = 10
            assignment.save(update_fields=['completion_percentage'])
    except Exception as e:
        logger.warning(f"Could not update assignment progress: {e}")

    log_action(
        None,
        'delete',
        'DocumentUpload',
        str(upload.id),
        {'original_filename': filename},
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return JsonResponse({
        'status': 'success',
        'remaining_count': remaining_count,
        'requirement_id': str(req_id) if req_id else None,
        'filename': filename
    })

