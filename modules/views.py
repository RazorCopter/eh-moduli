from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse, Http404, HttpResponseForbidden
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
    customer_create, customer_delete, assignment_detail, assign_form_to_customer,
    builder_list, builder_create, builder_edit, builder_preview, operational_guide
)
import os
import hashlib
from datetime import datetime

@require_http_methods(["GET", "POST"])
def published_form_access(request, form_id):
    """Password-protected access to published forms.
    URL is permanent: works regardless of form status (draft/published).
    Only archived forms are excluded.
    """
    try:
        form = FormTemplate.objects.exclude(status='archived').get(id=form_id)
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
            from itertools import chain
            steps = form.formstep_set.all().order_by('order')

            # Combine FormElement and DocumentRequirement for each step, ordered by order field
            for step in steps:
                elements = step.formelement_set.all().order_by('order')
                documents = step.documentrequirement_set.all().order_by('order')
                step.combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

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
        from itertools import chain
        steps = form.formstep_set.all().order_by('order')

        # Combine FormElement and DocumentRequirement for each step, ordered by order field
        for step in steps:
            elements = step.formelement_set.all().order_by('order')
            documents = step.documentrequirement_set.all().order_by('order')
            step.combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

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
    form_id = request.GET.get('form_id')
    assignment_id = request.GET.get('assignment_id')
    customer_name = None
    project_name = None

    if assignment_id:
        try:
            assignment = FormAssignment.objects.get(id=assignment_id)
            form_id = str(assignment.form_template_id)
            if assignment.customer:
                customer_name = f"{assignment.customer.first_name} {assignment.customer.last_name}"
            project_name = assignment.form_data.get('project_name', '')
        except (FormAssignment.DoesNotExist, ValueError):
            pass
    elif form_id:
        try:
            form = FormTemplate.objects.get(id=form_id)
            if form.customer:
                customer_name = f"{form.customer.first_name} {form.customer.last_name}"
            project_name = form.project_name
        except (FormTemplate.DoesNotExist, ValueError):
            pass

    context = {
        'timestamp': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
        'form_id': form_id,
        'assignment_id': assignment_id,
        'customer': customer_name,
        'project': project_name,
        'is_public_form': True,
    }
    return render(request, 'modules/form_success.html', context)



@require_http_methods(["GET"])
def published_form_receipt(request, form_id):
    """Download the official PDF report receipt for a submitted form."""
    try:
        form = FormTemplate.objects.get(id=form_id)
    except (FormTemplate.DoesNotExist, ValueError):
        raise Http404("Modulo non trovato")

    session_key = f'form_access_{form_id}'
    if not request.session.get(session_key, False):
        return HttpResponseForbidden("Accesso non autorizzato. Effettua prima l'accesso con password.")

    nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
    customer_folder = form.customer.nas_folder_name if form.customer else '_generic'
    project_folder = form.project_name if form.project_name else str(form.id)
    nas_project_path = os.path.join(nas_base, customer_folder, project_folder)
    pdf_path = os.path.join(nas_project_path, 'Report_Ricezione_Documenti.pdf')

    if not os.path.exists(pdf_path):
        raise Http404("Il report PDF non è stato ancora generato per questo modulo.")

    safe_title = "".join(c for c in form.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"Ricevuta_{safe_title}.pdf"
    return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=filename)


@require_http_methods(["GET"])
def get_form_by_token(request, token):
    try:
        assignment = FormAssignment.objects.get(secure_token=token)

        if assignment.is_expired():
            assignment.status = 'expired'
            assignment.save()
            return render(request, 'modules/form_expired.html', {'is_public_form': True})

        if assignment.status == 'submitted':
            return render(request, 'modules/form_already_submitted.html', {'is_public_form': True})

        assignment.last_access_date = timezone.now()
        assignment.save()

        steps = list(assignment.form_template.formstep_set.all().order_by('order'))
        first_step_order = steps[0].order if steps else 0
        project_name = assignment.form_data.get('project_name', '') if assignment.form_data else ''

        context = {
            'assignment': assignment,
            'form_template': assignment.form_template,
            'first_step_order': first_step_order,
            'project_name': project_name,
            'is_public_form': True,
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
        return render(request, 'modules/form_not_found.html', {'is_public_form': True}, status=404)

@require_http_methods(["GET", "POST"])
def form_step_view(request, assignment_id, step_order):
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    steps = list(assignment.form_template.formstep_set.all().order_by('order'))
    if not steps:
        return render(request, 'modules/form_empty.html', {'assignment': assignment, 'is_public_form': True})

    # Resilient step lookup: match order, fallback to index
    step = next((s for s in steps if s.order == step_order), None)
    if not step:
        if 1 <= step_order <= len(steps):
            step = steps[step_order - 1]
        elif 0 <= step_order < len(steps):
            step = steps[step_order]
        else:
            step = steps[0]

    from itertools import chain
    elements = list(step.formelement_set.all().order_by('order'))
    for elem in elements:
        elem.is_form_element = True

    documents = list(step.documentrequirement_set.all().order_by('order'))
    for doc in documents:
        doc.is_document_requirement = True

    combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

    if request.method == 'POST':
        assignment.last_completed_step = step
        assignment.status = 'in_progress'
        assignment.save()
        return JsonResponse({'status': 'ok'})

    # GET: Prepare context
    current_index = steps.index(step) + 1
    step_count = len(steps)
    progress_pct = int((current_index / max(step_count, 1)) * 100)
    prev_step = steps[current_index - 2] if current_index > 1 else None
    next_step = steps[current_index] if current_index < step_count else None

    # Load existing valid uploads for this assignment
    existing_uploads = {}
    for upload in assignment.documentupload_set.filter(status='valid'):
        existing_uploads[str(upload.document_requirement_id)] = upload
        existing_uploads[upload.document_requirement_id] = upload

    context = {
        'assignment': assignment,
        'step': step,
        'combined_items': combined_items,
        'requirements': documents,
        'step_count': step_count,
        'current_index': current_index,
        'progress_pct': progress_pct,
        'prev_step': prev_step,
        'next_step': next_step,
        'existing_uploads': existing_uploads,
        'is_public_form': True,
    }

    return render(request, 'modules/form_step.html', context)


@require_http_methods(["POST"])
def published_form_upload(request, form_id):
    """Upload document to published form (no FormAssignment)."""
    import hashlib
    from datetime import datetime

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
        'is_public_form': True,
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
    assignment.completion_percentage = 100
    assignment.save()

    # Generate official PDF receipt on submission
    try:
        from .report_generator import generate_form_receipt_pdf
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        client_name = assignment.form_data.get('client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
        project_name = assignment.form_data.get('project_name') or ''
        nas_project_path = os.path.join(nas_base, client_name, project_name)
        os.makedirs(nas_project_path, exist_ok=True)
        pdf_path = os.path.join(nas_project_path, 'Report_Ricezione_Documenti.pdf')
        generate_form_receipt_pdf(assignment.form_template, assignment, pdf_path)
    except Exception as e:
        logger.warning(f"Could not generate PDF receipt on assignment submit: {e}")

    log_action(
        None,
        'submit',
        'FormAssignment',
        str(assignment.id),
        {'customer': str(assignment.customer.id)},
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'status': 'success', 'redirect': f'/modules/form/success/?assignment_id={assignment.id}'})
    return redirect(f'/modules/form/success/?assignment_id={assignment.id}')



@require_http_methods(["POST"])
def published_form_submit(request, form_id):
    """Submit a published form with document availability tracking."""
    import os
    import json
    import hashlib
    from datetime import datetime

    try:
        form = FormTemplate.objects.exclude(status='archived').get(id=form_id)
    except FormTemplate.DoesNotExist:
        return render(request, 'modules/form_not_found.html', status=404)

    session_key = f'form_access_{form_id}'
    if not request.session.get(session_key, False):
        return render(request, 'modules/form_password.html', {
            'form_id': form_id,
            'error': 'Session expired. Please enter password again.'
        }, status=401)

    try:
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        customer_folder = form.customer.nas_folder_name if form.customer else '_generic'
        project_folder = form.project_name if form.project_name else str(form.id)
        nas_project_path = os.path.join(nas_base, customer_folder, project_folder)
        os.makedirs(nas_project_path, exist_ok=True)

        manifest_path = os.path.join(nas_project_path, 'manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            customer_display = (form.customer.first_name + ' ' + form.customer.last_name) if form.customer else 'Generic'
            customer_code = form.customer.code if form.customer else 'GEN'
            manifest = {
                'form_id': str(form.id),
                'form_name': form.name,
                'customer': customer_display,
                'customer_code': customer_code,
                'project': form.project_name or '',
                'created_at': timezone.now().isoformat(),
                'uploads': []
            }

        # Process each document requirement and doc_upload FormElement across all steps
        all_requirements = []
        for step in form.formstep_set.all():
            for doc in step.documentrequirement_set.all():
                all_requirements.append({
                    'id': str(doc.id),
                    'name': doc.name,
                    'required': doc.required,
                    'destination_subfolder': doc.destination_subfolder or ''
                })
            for elem in step.formelement_set.filter(element_type='doc_upload'):
                all_requirements.append({
                    'id': str(elem.id),
                    'name': elem.config.get('label') or 'Documento',
                    'required': elem.config.get('required', False),
                    'destination_subfolder': elem.config.get('destination_subfolder', '')
                })

        for requirement in all_requirements:
            requirement_id = requirement['id']
            availability_key = f'availability_{requirement_id}'
            motivation_key = f'motivazione_indisponibilita_{requirement_id}'
            file_key = f'file_{requirement_id}'

            availability_status = request.POST.get(availability_key, 'uploaded')
            motivation = request.POST.get(motivation_key, '')
            uploaded_file = request.FILES.get(file_key)

            doc_record = {
                'document_name': requirement['name'],
                'requirement_id': requirement_id,
                'required': requirement['required'],
                'availability_status': availability_status,
                'upload_datetime': timezone.now().isoformat(),
                'uploaded_from_ip': get_client_ip(request)
            }

            if availability_status == 'not_available':
                doc_record['indisponibile'] = True
                doc_record['motivazione_indisponibilita'] = motivation
            elif availability_status == 'uploaded' and uploaded_file:
                doc_record['indisponibile'] = False
                doc_record['original_filename'] = uploaded_file.name

                # Generate safe filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else ''
                import secrets
                safe_filename = f"{secrets.token_hex(4)}_{timestamp}.{ext}"

                # Save file
                dest_subfolder = requirement['destination_subfolder']
                file_path_dest = os.path.join(nas_project_path, dest_subfolder)
                os.makedirs(file_path_dest, exist_ok=True)

                file_full_path = os.path.join(file_path_dest, safe_filename)

                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, dir=file_path_dest) as tmp:
                    for chunk in uploaded_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                os.replace(tmp_path, file_full_path)

                # Calculate SHA256
                sha256 = hashlib.sha256()
                with open(file_full_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        sha256.update(chunk)

                doc_record['stored_filename'] = safe_filename
                doc_record['file_size'] = uploaded_file.size
                doc_record['sha256'] = sha256.hexdigest()
                doc_record['mime_type'] = uploaded_file.content_type
            else:
                doc_record['indisponibile'] = True

            manifest['uploads'].append(doc_record)

        # Collect submitted form element fields (text, email, phone, date, etc.)
        form_fields = []
        for step in form.formstep_set.all():
            for elem in step.formelement_set.exclude(element_type__in=['doc_upload', 'separator', 'text_info']):
                elem_id = str(elem.id)
                val = request.POST.get(f'element_{elem_id}', '').strip()
                label = elem.config.get('label') or elem.element_type
                if val:
                    form_fields.append({
                        'label': label,
                        'value': val,
                        'type': elem.element_type
                    })

        # Save manifest.json as machine-readable record
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Generate Premium PDF Report with Etichub vector logo
        try:
            from .report_generator import generate_submission_pdf
            from django.conf import settings

            logo_svg = os.path.join(settings.BASE_DIR, 'static', 'images', 'Etichub_Logo_V2_Verticale_Color.svg')
            pdf_report_path = os.path.join(nas_project_path, 'Report_Ricezione_Documenti.pdf')

            form_meta = {
                'form_id': str(form.id),
                'name': form.name,
                'project_name': form.project_name or '',
                'submission_datetime': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
                'client_ip': get_client_ip(request),
                'user_agent': get_user_agent(request)
            }

            customer_info = {
                'name': (form.customer.first_name + ' ' + form.customer.last_name) if form.customer else 'Non specificato',
                'code': form.customer.code if form.customer else '—',
                'email': form.customer.email if form.customer else '—',
                'phone': form.customer.phone if form.customer else '—',
                'vat': getattr(form.customer, 'vat_number', '') or getattr(form.customer, 'fiscal_code', '') or '—'
            }

            generate_submission_pdf(
                output_pdf_path=pdf_report_path,
                form_data=form_meta,
                customer_data=customer_info,
                uploads=manifest['uploads'],
                form_fields=form_fields,
                logo_path=logo_svg
            )
        except Exception as pdf_err:
            import logging
            logger = logging.getLogger('modules')
            logger.error(f"Error generating submission PDF: {pdf_err}\n{traceback.format_exc()}")

        log_action(
            None,
            'submit',
            'PublishedForm',
            str(form.id),
            {
                'customer': form.customer.code if form.customer else 'generic',
                'project': form.project_name or '',
                'document_count': len(manifest['uploads'])
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect(f'/modules/form/success/?form_id={form.id}')

    except Exception as e:
        logger = logging.getLogger('modules')
        logger.error(f"published_form_submit ERROR: {str(e)}\n{traceback.format_exc()}")

        log_action(
            None,
            'submit',
            'PublishedForm',
            'ERROR',
            {'error': str(e), 'form_id': str(form.id)},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )

        return render(request, 'modules/form_not_found.html', {
            'error': f'Submission failed: {str(e)}'
        }, status=500)
