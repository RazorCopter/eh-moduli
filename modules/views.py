from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import FormAssignment, DocumentRequirement, DocumentUpload, AwarenessDeclaration
from .utils import get_client_ip, get_user_agent, log_action
from .upload_security import (
    validate_file_upload_secure,
    save_uploaded_file_secure,
    delete_document_secure,
)
from .views_admin import (
    admin_dashboard, form_template_list, form_template_create,
    form_template_edit, form_template_duplicate, customer_list,
    customer_create, assignment_detail, assign_form_to_customer
)
import os

@require_http_methods(["GET"])
def get_form_by_token(request, token):
    try:
        assignment = FormAssignment.objects.get(secure_token=token)

        if assignment.is_expired():
            assignment.status = 'expired'
            assignment.save()
            return render(request, 'modules/form_expired.html')

        if assignment.status == 'submitted':
            return render(request, 'modules/form_already_submitted.html')

        assignment.last_access_date = timezone.now()
        assignment.save()

        context = {
            'assignment': assignment,
            'form_template': assignment.form_template,
        }

        log_action(
            None,
            'view',
            'FormAssignment',
            str(assignment.id),
            {'token': token[:10] + '...'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return render(request, 'modules/form_detail.html', context)

    except FormAssignment.DoesNotExist:
        return render(request, 'modules/form_not_found.html', status=404)

@require_http_methods(["GET", "POST"])
def form_step_view(request, assignment_id, step_order):
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    try:
        step = assignment.form_template.formstep_set.get(order=step_order)
    except:
        return JsonResponse({'error': 'Step not found'}, status=404)

    requirements = step.documentrequirement_set.all().order_by('order')

    if request.method == 'POST':
        assignment.last_completed_step = step
        assignment.status = 'in_progress'
        assignment.save()
        return JsonResponse({'status': 'ok'})

    context = {
        'assignment': assignment,
        'step': step,
        'requirements': requirements,
        'step_count': assignment.form_template.formstep_set.count(),
    }

    return render(request, 'modules/form_step.html', context)

@require_http_methods(["POST"])
def upload_document_view(request, assignment_id):
    """Upload document with comprehensive security validation."""
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    file = request.FILES.get('file')
    requirement_id = request.POST.get('requirement_id')

    if not file or not requirement_id:
        return JsonResponse({'error': 'Missing file or requirement'}, status=400)

    try:
        requirement = DocumentRequirement.objects.get(id=requirement_id)
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Requirement not found'}, status=404)

    # SECURE VALIDATION: checks path traversal, MIME, double extensions, etc
    errors = validate_file_upload_secure(file, requirement)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    try:
        # SECURE SAVE: atomic write, safe paths, restrictive permissions
        upload = save_uploaded_file_secure(
            file,
            assignment,
            requirement,
            '/storage/clienti'
        )

        # Update tracking info
        upload.uploaded_by_ip = get_client_ip(request)
        upload.uploaded_by_user_agent = get_user_agent(request)
        upload.save()

        # Log action
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

        return JsonResponse({
            'status': 'success',
            'upload_id': str(upload.id),
            'filename': upload.original_filename,
            'size': file.size
        })

    except ValueError as e:
        # Security validation error
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
        # Unexpected error
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
        return JsonResponse({'error': 'Upload failed'}, status=500)

@require_http_methods(["POST"])
def skip_optional_document(request, assignment_id, requirement_id):
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
        requirement = DocumentRequirement.objects.get(id=requirement_id)
    except:
        return JsonResponse({'error': 'Not found'}, status=404)

    if requirement.required:
        return JsonResponse({'error': 'Cannot skip required document'}, status=400)

    declaration_text = request.POST.get('declaration_text', '')

    AwarenessDeclaration.objects.create(
        form_assignment=assignment,
        document_requirement=requirement,
        declaration_text=declaration_text,
        accepted=True,
        acceptance_ip=get_client_ip(request),
        acceptance_user_agent=get_user_agent(request),
        customer_name_declared=request.POST.get('customer_name', '')
    )

    return JsonResponse({'status': 'success'})

@require_http_methods(["GET"])
def form_summary_view(request, assignment_id):
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    uploads = assignment.documentupload_set.filter(status='valid')
    declarations = assignment.awarenessdeclaration_set.filter(accepted=True)

    context = {
        'assignment': assignment,
        'uploads': uploads,
        'declarations': declarations,
    }

    return render(request, 'modules/form_summary.html', context)

@require_http_methods(["POST"])
def form_submission_view(request, assignment_id):
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    assignment.status = 'submitted'
    assignment.submission_date = timezone.now()
    assignment.save()

    log_action(
        None,
        'submit',
        'FormAssignment',
        str(assignment.id),
        {'customer': str(assignment.customer.id)},
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return JsonResponse({'status': 'success', 'redirect': '/modules/form/success/'})
