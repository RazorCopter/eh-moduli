import os
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.urls import reverse

from .models import (
    FormTemplate, DocumentRequirement, Customer,
    FormAssignment
)
from .utils import (
    log_action, get_client_ip, get_user_agent,
    generate_secure_token, safe_get_form_data, is_ajax_request,
    get_nas_base_path
)
from .upload_security import safe_join_paths, save_manifest_atomic

logger = logging.getLogger('modules')


def is_backoffice_user(user):
    """Backoffice operators and administrators (for operational dashboards and assignment management)"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))


is_admin = is_backoffice_user


@login_required
@user_passes_test(is_backoffice_user)
def assignment_detail(request, pk):
    """Detailed view of an assignment with all uploads, declarations, and status."""
    assignment = get_object_or_404(FormAssignment, id=pk)
    uploads = assignment.documentupload_set.all()
    declarations = assignment.awarenessdeclaration_set.all()
    form_url = request.build_absolute_uri(f"/modules/form/{assignment.secure_token}/")
    portal_url = request.build_absolute_uri(reverse('clienti_portal_root'))
    ttl_days_remaining = max(0, (assignment.expiry_date - timezone.now()).days) if assignment.expiry_date else 0

    context = {
        'assignment': assignment,
        'uploads': uploads,
        'declarations': declarations,
        'form_url': form_url,
        'portal_url': portal_url,
        'ttl_days_remaining': ttl_days_remaining,
        'is_customer_active': assignment.customer.active if assignment.customer else False,
    }

    return render(request, 'modules/admin/assignment_detail.html', context)


@login_required
@user_passes_test(is_backoffice_user)
def assign_form_to_customer(request):
    """Assign a published form template to a customer, creating dedicated NAS folder and initial manifest."""
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id', '').strip()
        template_id = request.POST.get('template_id', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        access_password = request.POST.get('access_password', '').strip()
        expiry_days = request.POST.get('expiry_days', str(getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30))).strip()
        internal_notes = request.POST.get('internal_notes', '').strip()

        errors = []
        if not customer_id:
            errors.append('Devi selezionare un cliente destinatario.')
        if not template_id:
            errors.append('Devi selezionare un modulo di raccolta.')
        if not project_name:
            errors.append('Nome Progetto è obbligatorio (definisce la cartella dedicata sul NAS).')

        customer = None
        template = None
        if customer_id:
            customer = get_object_or_404(Customer, id=customer_id)
        if template_id:
            template = get_object_or_404(FormTemplate, id=template_id)

        if errors:
            customers = Customer.objects.filter(active=True).order_by('first_name')
            templates = FormTemplate.objects.filter(status='published').order_by('name')
            return render(request, 'modules/admin/assign_form.html', {
                'customers': customers,
                'templates': templates,
                'errors': errors,
                'selected_customer_id': customer_id,
                'selected_template_id': template_id,
                'project_name': project_name,
                'access_password': access_password,
                'expiry_days': expiry_days,
                'internal_notes': internal_notes,
            })

        try:
            days = int(expiry_days)
            if days <= 0:
                days = settings.FORM_ASSIGNMENT_EXPIRY_DAYS
        except ValueError:
            days = settings.FORM_ASSIGNMENT_EXPIRY_DAYS

        expiry_date = timezone.now() + timezone.timedelta(days=days)

        nas_base = get_nas_base_path()
        nas_project_path = str(safe_join_paths(nas_base, customer.nas_folder_name, project_name))
        try:
            os.makedirs(nas_project_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not pre-create NAS project folder {nas_project_path}: {e}")

        try:
            with transaction.atomic():
                os.makedirs(nas_project_path, exist_ok=True)
                assignment = FormAssignment.objects.create(
                    customer=customer,
                    form_template=template,
                    expiry_date=expiry_date,
                    operator=request.user,
                    status='draft',
                    internal_notes=internal_notes,
                    form_data={
                        'client_name': customer.nas_folder_name,
                        'project_name': project_name,
                        'access_password': make_password(access_password) if access_password else '',
                        'created_at': timezone.now().isoformat()
                    }
                )

                # Create initial manifest.json in the NAS folder atomically
                manifest_path = str(safe_join_paths(nas_project_path, 'manifest.json'))
                if not os.path.exists(manifest_path):
                    manifest = {
                        'assignment_id': str(assignment.id),
                        'form_name': template.name,
                        'customer': f"{customer.first_name} {customer.last_name}",
                        'customer_code': customer.code,
                        'nas_client_folder': customer.nas_folder_name,
                        'project': project_name,
                        'created_at': timezone.now().isoformat(),
                        'uploads': []
                    }
                    import modules.views_admin as va
                    save_func = getattr(va, 'save_manifest_atomic', save_manifest_atomic)
                    save_func(manifest_path, manifest)
        except Exception as e:
            logger.error(f"Could not create assignment and manifest: {e}", exc_info=True)
            err_msg = f"Errore durante l'assegnazione del modulo o creazione su NAS: {e}"
            if is_ajax_request(request):
                return JsonResponse({'status': 'error', 'error': err_msg}, status=500)
            messages.error(request, err_msg)
            return redirect('assign_form_to_customer')

        log_action(
            request.user,
            'create',
            'FormAssignment',
            str(assignment.id),
            {'customer': customer.code, 'template': template.name, 'project': project_name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        if is_ajax_request(request):
            return JsonResponse({
                'status': 'success',
                'token': assignment.secure_token,
                'form_url': f"/modules/form/{assignment.secure_token}/",
                'assignment_id': str(assignment.id),
                'project_name': project_name,
                'has_access_password': bool(access_password),
                'nas_path': nas_project_path
            })

        messages.success(
            request, 
            f"Modulo '{template.name}' assegnato con successo a {customer.first_name} {customer.last_name} ({customer.code}) per il progetto '{project_name}'! Cartella NAS: /{customer.nas_folder_name}/{project_name}/"
        )
        return redirect('assignment_detail', pk=assignment.id)

    selected_template_id = request.GET.get('template_id', '')
    selected_customer_id = request.GET.get('customer_id', '')

    customers = Customer.objects.filter(active=True).order_by('first_name')
    templates = FormTemplate.objects.filter(status='published').order_by('name')

    default_expiry = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
    if selected_template_id:
        try:
            sel_tmpl = FormTemplate.objects.filter(id=selected_template_id).first()
            if sel_tmpl and hasattr(sel_tmpl, 'default_expiry_days') and sel_tmpl.default_expiry_days:
                default_expiry = sel_tmpl.default_expiry_days
        except Exception:
            pass

    context = {
        'customers': customers,
        'templates': templates,
        'selected_template_id': selected_template_id,
        'selected_customer_id': selected_customer_id,
        'expiry_days': default_expiry,
    }

    return render(request, 'modules/admin/assign_form.html', context)


@login_required
@user_passes_test(is_backoffice_user)
@require_http_methods(["POST"])
def reopen_assignment_for_upload(request, pk):
    """
    Reopens a FormAssignment to allow customer to upload additional/integrative files.
    - Generates a new secure token for customer access.
    - Resets status to 'in_progress' and clears submission_date.
    - Extends validity date (+30 days).
    """
    assignment = get_object_or_404(FormAssignment, id=pk)
    old_status = assignment.status
    old_token = assignment.secure_token

    # Generate brand new unique secure token
    assignment.secure_token = generate_secure_token()

    # Reopen status and clear submission timestamp
    assignment.status = 'in_progress'
    assignment.submission_date = None

    # Extend validity
    assignment.expiry_date = timezone.now() + timezone.timedelta(days=settings.FORM_ASSIGNMENT_EXPIRY_DAYS)

    # Recalculate completion percentage with explicit guards for empty querysets
    try:
        total_reqs_queryset = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template)
        if not total_reqs_queryset.exists():
            assignment.completion_percentage = 0
        else:
            total_reqs = total_reqs_queryset.count()
            valid_uploaded_queryset = assignment.documentupload_set.filter(
                status='valid',
                availability_status='uploaded'
            )
            valid_uploaded_count = valid_uploaded_queryset.count() if valid_uploaded_queryset.exists() else 0

            if total_reqs > 0:
                assignment.completion_percentage = int((valid_uploaded_count / total_reqs) * settings.COMPLETION_PERCENTAGE_MULTIPLIER)
            else:
                assignment.completion_percentage = 0
    except Exception as e:
        logger.warning(f'Error calculating completion percentage for assignment {pk}: {e}')
        assignment.completion_percentage = 0

    assignment.save()

    # Invalidate existing session credentials for this assignment
    request.session.pop(f'assignment_access_{assignment.id}', None)
    request.session.pop(f'assignment_access_{assignment.id}_{old_token}', None)
    request.session.modified = True

    # Audit log
    log_action(
        request.user,
        'update',
        'FormAssignment',
        str(assignment.id),
        {
            'action': 'reopened_for_integrations',
            'previous_status': old_status,
            'old_token_prefix': old_token[:8] + '...',
            'new_token_prefix': assignment.secure_token[:8] + '...',
            'customer': assignment.customer.code if assignment.customer else '',
            'nas_folder': assignment.customer.nas_folder_name if assignment.customer else ''
        },
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    customer_name = f"{assignment.customer.first_name} {assignment.customer.last_name}" if assignment.customer else "Cliente"
    messages.success(
        request,
        f"Pratica riaperta con successo per {customer_name}! Il cliente può ora accedere dall'area personale per il caricamento di documenti integrativi. La cartella NAS del cliente e i file già caricati rimangono invariati."
    )

    if is_ajax_request(request):
        new_url = request.build_absolute_uri(f"/modules/form/{assignment.secure_token}/")
        return JsonResponse({
            'status': 'success',
            'token': assignment.secure_token,
            'form_url': new_url,
            'message': 'Link rigenerato con successo'
        })

    return redirect('assignment_detail', pk=assignment.id)


@login_required
@user_passes_test(is_backoffice_user)
@require_http_methods(["POST"])
def assignment_delete(request, pk):
    """
    Deletes / disassociates a FormAssignment from a customer.
    - Removes assignment record and cascades related uploads/declarations.
    - Customer, FormTemplate and physical files on NAS remain intact.
    """
    assignment = get_object_or_404(FormAssignment, id=pk)
    customer_name = f"{assignment.customer.first_name} {assignment.customer.last_name}" if assignment.customer else "Cliente"
    customer_code = assignment.customer.code if assignment.customer else ""
    template_name = assignment.form_template.name if assignment.form_template else "Modulo"
    assignment_id_str = str(assignment.id)

    # Invalidate any session credentials
    request.session.pop(f'assignment_access_{assignment.id}', None)
    request.session.pop(f'assignment_access_{assignment.id}_{assignment.secure_token}', None)
    request.session.modified = True

    try:
        uploads_count = assignment.documentupload_set.count()
        declarations_count = assignment.awarenessdeclaration_set.count()

        assignment.delete()

        log_action(
            request.user,
            'delete',
            'FormAssignment',
            assignment_id_str,
            {
                'customer': customer_code,
                'customer_name': customer_name,
                'template': template_name,
                'deleted_uploads_count': uploads_count,
                'deleted_declarations_count': declarations_count,
                'database_records_purged': True,
                'physical_files_kept': True,
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        msg = f"Pratica '{template_name}' disassociata ed eliminata con successo dal cliente {customer_name}. Tutti i record di caricamento ({uploads_count}) e dichiarazioni ({declarations_count}) sul database sono stati eliminati."

        if is_ajax_request(request):
            return JsonResponse({'status': 'success', 'message': msg})

        messages.success(request, msg)
        return redirect('admin_dashboard')

    except Exception as e:
        logger.error(f"Errore durante l'eliminazione dell'assegnazione {pk}: {e}")
        err_msg = f"Errore durante l'eliminazione dell'assegnazione: {str(e)}"
        if is_ajax_request(request):
            return JsonResponse({'status': 'error', 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('admin_dashboard')


@login_required
@user_passes_test(is_backoffice_user)
@require_http_methods(["POST"])
def assignment_update_status(request, pk):
    """
    Operator state machine transition for FormAssignment:
    - 'in_processing': Etichub regulatory office takes charge of practice -> 75%
    - 'completed': Etichub finishes analysis & PIF dossier -> 100% ('Lavorata')
    """
    assignment = get_object_or_404(FormAssignment, id=pk)
    new_status = request.POST.get('status', '').strip()

    valid_transitions = {
        'submitted': 50,
        'in_processing': 75,
        'completed': settings.COMPLETION_PERCENTAGE_MULTIPLIER,
        'in_progress': 25,
    }

    if new_status not in valid_transitions:
        messages.error(request, f"Stato non valido: {new_status}")
        return redirect('assignment_detail', pk=assignment.id)

    old_status = assignment.status
    assignment.status = new_status
    assignment.completion_percentage = valid_transitions[new_status]

    if not assignment.form_data:
        assignment.form_data = {}

    if new_status == 'in_processing':
        if 'in_processing_at' not in assignment.form_data:
            assignment.form_data['in_processing_at'] = timezone.now().isoformat()
            assignment.form_data['in_processing_by'] = request.user.username if request.user else 'Operatore Etichub'
    elif new_status == 'completed':
        assignment.form_data['completed_at'] = timezone.now().isoformat()
        assignment.form_data['completed_by'] = request.user.username if request.user else 'Operatore Etichub'

    assignment.save(update_fields=['status', 'completion_percentage', 'form_data'])

    log_action(
        request.user,
        'update',
        'FormAssignment',
        str(assignment.id),
        {
            'action': 'status_updated_by_operator',
            'previous_status': old_status,
            'new_status': new_status,
            'completion_percentage': assignment.completion_percentage
        },
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    # Auto-generate PDF report on NAS when completed
    if new_status == 'completed':
        try:
            from .report_generator import generate_form_receipt_pdf
            nas_base = get_nas_base_path()
            client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
            project_name = safe_get_form_data(assignment.form_data, 'project_name') or (getattr(assignment.form_template, 'project_name', None) if assignment.form_template else None) or (assignment.form_template.name if assignment.form_template else None) or 'Progetto'
            nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
            os.makedirs(nas_project_path, exist_ok=True)
            pdf_path = str(safe_join_paths(nas_project_path, f'Report_Ricezione_Documenti_{assignment.id}.pdf'))
            generate_form_receipt_pdf(assignment.form_template, assignment, pdf_path, client_ip=get_client_ip(request))
        except Exception as e:
            logger.warning(f"Could not auto-generate completed PDF receipt for assignment {assignment.id}: {e}")

    messages.success(request, f"Stato pratica aggiornato a: {new_status}")
    return redirect('assignment_detail', pk=assignment.id)
