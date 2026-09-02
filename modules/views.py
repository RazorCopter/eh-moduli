from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import FormAssignment, DocumentRequirement, DocumentUpload, AwarenessDeclaration, FormTemplate
from .utils import get_client_ip, get_user_agent, log_action
from .upload_security import (
    validate_file_upload_secure,
    save_uploaded_file_secure,
    delete_document_secure,
)
from .views_admin import (
    admin_dashboard, form_template_list, form_template_create,
    form_template_edit, form_template_duplicate, customer_list,
    customer_create, assignment_detail, assign_form_to_customer,
    builder_list, builder_create, builder_edit, builder_preview
)
import os
import hashlib
from datetime import datetime

@require_http_methods(["GET", "POST"])
def published_form_access(request, form_id):
    """Password-protected access to published forms."""
    try:
        form = FormTemplate.objects.get(id=form_id, status='published')
    except FormTemplate.DoesNotExist:
        return render(request, 'modules/form_not_found.html', status=404)

    # Check if already authenticated for this form
    session_key = f'form_access_{form_id}'
    is_authenticated = request.session.get(session_key, False)

    if request.method == 'POST':
        password = request.POST.get('password', '')

        if password == form.access_password:
            request.session[session_key] = True
            request.session.modified = True

            log_action(
                None,
                'view',
                'PublishedForm',
                str(form.id),
                {'customer': form.customer.code if form.customer else 'unknown', 'project': form.project_name},
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )

            # Render the form directly (not in assignment context)
            steps = form.formstep_set.all().order_by('order')
            context = {
                'form': form,
                'steps': steps,
                'is_published_form': True
            }
            return render(request, 'modules/published_form.html', context)
        else:
            return render(request, 'modules/form_password.html', {
                'form_id': form_id,
                'error': 'Invalid password'
            })

    # GET request
    if is_authenticated:
        steps = form.formstep_set.all().order_by('order')
        context = {
            'form': form,
            'steps': steps,
            'is_published_form': True
        }
        return render(request, 'modules/published_form.html', context)

    # Show password prompt
    return render(request, 'modules/form_password.html', {'form_id': form_id})


@require_http_methods(["GET"])
def form_success_view(request):
    """Show success message after form submission."""
    context = {
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return render(request, 'modules/form_success.html', context)


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
        # STEP 0: Handle client_name and project_name
        if step_order == 0:
            client_name = request.POST.get('client_name', '').strip()
            project_name = request.POST.get('project_name', '').strip()

            if not client_name or not project_name:
                return JsonResponse({'error': 'Client and Project names are required'}, status=400)

            # Save to form_data
            assignment.form_data = {
                'client_name': client_name,
                'project_name': project_name,
                'created_at': timezone.now().isoformat()
            }
            assignment.save()

            # Create NAS folder structure: /storage/clienti/{client}/{project}/
            try:
                nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
                nas_path = os.path.join(nas_base, client_name, project_name)
                os.makedirs(nas_path, exist_ok=True)
                log_action(
                    request.user if request.user.is_authenticated else None,
                    'create',
                    'NASFolder',
                    nas_path,
                    {'client': client_name, 'project': project_name},
                    ip=get_client_ip(request),
                    user_agent=get_user_agent(request)
                )
            except Exception as e:
                log_action(
                    request.user if request.user.is_authenticated else None,
                    'create',
                    'NASFolder',
                    nas_path,
                    {'error': str(e)},
                    ip=get_client_ip(request),
                    user_agent=get_user_agent(request)
                )

        assignment.last_completed_step = step
        assignment.status = 'in_progress'
        assignment.save()
        return JsonResponse({'status': 'ok'})

    # GET: Prepare context
    context = {
        'assignment': assignment,
        'step': step,
        'requirements': requirements,
        'step_count': assignment.form_template.formstep_set.count(),
    }

    # Fetch available clients from NAS folder
    try:
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        if os.path.exists(nas_base):
            available_clients = [d for d in os.listdir(nas_base)
                                if os.path.isdir(os.path.join(nas_base, d)) and not d.startswith('.')]
            available_clients.sort()
        else:
            available_clients = []
    except:
        available_clients = []

    context['available_clients'] = available_clients

    return render(request, 'modules/form_step.html', context)

@require_http_methods(["POST"])
def published_form_upload(request, form_id):
    """Upload document to published form (no FormAssignment)."""
    import hashlib
    from datetime import datetime

    try:
        form = FormTemplate.objects.get(id=form_id, status='published')
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
        requirement = DocumentRequirement.objects.get(id=requirement_id)
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Requirement not found'}, status=404)

    # Validate file
    errors = validate_file_upload_secure(file, requirement)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    try:
        # Build NAS path: /storage/clienti/{customer.nas_folder_name}/{project_name}/{destination_subfolder}/
        # Use container path for Docker deployments, fall back to host path
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
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
        import secrets
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = file.name.split('.')[-1] if '.' in file.name else ''
        safe_filename = f"{secrets.token_hex(4)}_{timestamp}.{ext}"
        file_path = os.path.join(nas_path, safe_filename)

        # Write file atomically
        import tempfile
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
        import json
        manifest_path = os.path.join(nas_base, form.customer.nas_folder_name, form.project_name, 'manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            manifest = {
                'form_id': str(form.id),
                'form_name': form.name,
                'customer': form.customer.first_name + ' ' + form.customer.last_name,
                'customer_code': form.customer.code,
                'project': form.project_name,
                'created_at': timezone.now().isoformat(),
                'uploads': []
            }

        # Add upload record
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

        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

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

    # Verify form_data has client and project (Step 0 must be completed)
    if not assignment.form_data or 'client_name' not in assignment.form_data:
        return JsonResponse({'error': 'Please complete Step 0 (Client & Project info) first'}, status=400)

    try:
        requirement = DocumentRequirement.objects.get(id=requirement_id)
    except DocumentRequirement.DoesNotExist:
        return JsonResponse({'error': 'Requirement not found'}, status=404)

    # SECURE VALIDATION: checks path traversal, MIME, double extensions, etc
    errors = validate_file_upload_secure(file, requirement)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    try:
        # Get NAS path from form_data (Step 0)
        client_name = assignment.form_data.get('client_name')
        project_name = assignment.form_data.get('project_name')
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        nas_project_path = os.path.join(nas_base, client_name, project_name)

        # SECURE SAVE: atomic write, safe paths, restrictive permissions
        upload = save_uploaded_file_secure(
            file,
            assignment,
            requirement,
            nas_project_path  # Use Step 0 path instead of /storage/clienti
        )

        # Update tracking info
        upload.uploaded_by_ip = get_client_ip(request)
        upload.uploaded_by_user_agent = get_user_agent(request)
        upload.save()

        # CREATE MANIFEST.JSON with document metadata
        try:
            import json
            manifest_path = os.path.join(nas_project_path, 'manifest.json')

            # Load existing manifest or create new
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    'form_name': assignment.form_template.name,
                    'customer': client_name,
                    'project': project_name,
                    'form_assignment_id': str(assignment.id),
                    'uploads': []
                }

            # Add this upload to manifest
            manifest['uploads'].append({
                'requirement_name': requirement.name,
                'requirement_description': requirement.description,
                'original_filename': upload.original_filename,
                'stored_filename': upload.stored_filename,
                'file_size': upload.file_size,
                'sha256': upload.sha256_checksum,
                'mime_type': upload.mime_type_detected,
                'upload_datetime': upload.upload_datetime.isoformat(),
                'uploaded_by_ip': upload.uploaded_by_ip
            })

            # Save manifest
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        except Exception as manifest_error:
            # Log but don't fail the upload
            log_action(
                None,
                'create',
                'Manifest',
                manifest_path,
                {'error': str(manifest_error)},
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )

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
