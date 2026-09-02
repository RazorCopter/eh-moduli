from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
from .models import FormTemplate, FormStep, FormElement, DocumentRequirement, FormAssignment, Customer
from .utils import log_action, get_client_ip, get_user_agent


def is_admin(user):
    return user.is_staff or (hasattr(user, 'role') and user.role == 'admin')


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['GET'])
def api_forms_list(request):
    """List all forms (drafts and published) grouped by family_id."""
    forms = FormTemplate.objects.all().values(
        'family_id', 'id', 'name', 'status', 'version', 'created_at'
    ).order_by('-created_at')

    return JsonResponse({
        'success': True,
        'data': list(forms)
    })


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['POST'])
def api_form_create(request):
    """Create new form (draft)."""
    try:
        data = json.loads(request.body)

        form = FormTemplate.objects.create(
            name=data.get('name', 'Untitled Form'),
            description=data.get('description', ''),
            intro_text=data.get('intro_text', ''),
            privacy_text=data.get('privacy_text', ''),
            author=request.user,
            status='draft'
        )

        log_action(
            request.user,
            'create',
            'FormTemplate',
            str(form.id),
            {'via': 'api'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'success': True,
            'data': {
                'id': str(form.id),
                'family_id': str(form.family_id),
                'name': form.name,
                'version': form.version,
                'status': form.status
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['GET'])
def api_form_detail(request, form_id):
    """Get complete form structure (steps, elements, requirements)."""
    form = get_object_or_404(FormTemplate, id=form_id)

    steps_data = []
    for step in form.formstep_set.all().order_by('order'):
        elements_data = []

        # Combine FormElement and DocumentRequirement in unified order
        combined_items = []

        # Add FormElements
        for elem in step.formelement_set.all().order_by('order'):
            combined_items.append({
                'id': str(elem.id),
                'type': 'element',
                'element_type': elem.element_type,
                'order': elem.order,
                'config': elem.config
            })

        # Add DocumentRequirements
        for doc_req in step.documentrequirement_set.all().order_by('order'):
            combined_items.append({
                'id': str(doc_req.id),
                'type': 'document',
                'name': doc_req.name,
                'description': doc_req.description,
                'required': doc_req.required,
                'allowed_extensions': doc_req.allowed_extensions,
                'mime_types': doc_req.mime_types,
                'max_file_size': doc_req.max_file_size,
                'max_files': doc_req.max_files,
                'destination_subfolder': doc_req.destination_subfolder,
                'order': doc_req.order,
                'awareness_text': doc_req.awareness_text,
                'awareness_required_when_empty': doc_req.awareness_required_when_empty
            })

        # Sort unified list by order
        combined_items.sort(key=lambda x: x['order'])

        steps_data.append({
            'id': str(step.id),
            'title': step.title,
            'description': step.description,
            'order': step.order,
            'required': step.required,
            'active': step.active,
            'elements': combined_items
        })

    return JsonResponse({
        'success': True,
        'data': {
            'id': str(form.id),
            'family_id': str(form.family_id),
            'name': form.name,
            'description': form.description,
            'intro_text': form.intro_text,
            'version': form.version,
            'status': form.status,
            'privacy_text': form.privacy_text,
            'steps': steps_data
        }
    })


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['PUT'])
def api_form_save(request, form_id):
    """Save form structure (steps, elements, requirements). Transactional."""
    form = get_object_or_404(FormTemplate, id=form_id)

    # Only allow editing drafts
    if form.status != 'draft':
        return JsonResponse({'success': False, 'error': 'Only draft forms can be edited'}, status=400)

    try:
        data = json.loads(request.body)

        with transaction.atomic():
            # Update form metadata
            form.name = data.get('name', form.name)
            form.description = data.get('description', form.description)
            form.intro_text = data.get('intro_text', form.intro_text)
            form.privacy_text = data.get('privacy_text', form.privacy_text)
            form.updated_at = timezone.now()
            form.save()

            # Delete existing steps/elements/requirements
            form.formstep_set.all().delete()

            # Create new steps
            steps_data = data.get('steps', [])
            for step_order, step_data in enumerate(steps_data):
                step = FormStep.objects.create(
                    form_template=form,
                    title=step_data.get('title', f'Step {step_order + 1}'),
                    description=step_data.get('description', ''),
                    order=step_order,
                    required=step_data.get('required', True),
                    active=step_data.get('active', True)
                )

                # Create elements and requirements from unified list
                elements = step_data.get('elements', [])
                for item_order, item in enumerate(elements):
                    item_type = item.get('type')

                    if item_type == 'element':
                        FormElement.objects.create(
                            form_step=step,
                            element_type=item.get('element_type'),
                            order=item_order,
                            config=item.get('config', {})
                        )
                    elif item_type == 'document':
                        DocumentRequirement.objects.create(
                            form_step=step,
                            name=item.get('name', 'Document'),
                            description=item.get('description', ''),
                            required=item.get('required', True),
                            allowed_extensions=item.get('allowed_extensions', 'pdf'),
                            mime_types=item.get('mime_types', 'application/pdf'),
                            max_file_size=item.get('max_file_size', 10485760),
                            max_files=item.get('max_files', 1),
                            destination_subfolder=item.get('destination_subfolder', ''),
                            order=item_order,
                            awareness_text=item.get('awareness_text', ''),
                            awareness_required_when_empty=item.get('awareness_required_when_empty', False)
                        )

            log_action(
                request.user,
                'update',
                'FormTemplate',
                str(form.id),
                {'via': 'api'},
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )

        return JsonResponse({'success': True, 'data': {'id': str(form.id)}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['POST'])
def api_form_publish(request, form_id):
    """Publish form and create NAS folder structure."""
    import os
    import json

    form = get_object_or_404(FormTemplate, id=form_id)

    if not form.customer or not form.project_name:
        return JsonResponse({
            'success': False,
            'error': 'Form must have a specific customer and project name before publishing'
        }, status=400)

    try:
        with transaction.atomic():
            # Create NAS folder structure (use container path for Docker deployments)
            nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
            nas_path = os.path.join(nas_base, form.customer.nas_folder_name, form.project_name)
            os.makedirs(nas_path, exist_ok=True)

            # Create initial manifest.json
            manifest = {
                'form_id': str(form.id),
                'form_name': form.name,
                'customer': form.customer.first_name + ' ' + form.customer.last_name,
                'customer_code': form.customer.code,
                'project': form.project_name,
                'created_at': timezone.now().isoformat(),
                'uploads': []
            }
            manifest_path = os.path.join(nas_path, 'manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)

            form.status = 'published'
            form.save()

            log_action(
                request.user,
                'update',
                'FormTemplate',
                str(form.id),
                {
                    'action': 'publish',
                    'version': form.version,
                    'nas_path': nas_path,
                    'via': 'api'
                },
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )

        return JsonResponse({
            'success': True,
            'data': {
                'status': 'published',
                'form_id': str(form.id),
                'form_name': form.name,
                'customer': form.customer.code,
                'project': form.project_name,
                'access_password': form.access_password,
                'public_url': f'/modules/form/published/{form.id}/',
                'note': 'Share this URL and password with the customer'
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['POST'])
def api_form_duplicate(request, form_id):
    """Duplicate form (create new draft with same structure)."""
    form = get_object_or_404(FormTemplate, id=form_id)

    try:
        new_form = form.duplicate()

        log_action(
            request.user,
            'create',
            'FormTemplate',
            str(new_form.id),
            {'duplicated_from': str(form.id), 'via': 'api'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'success': True,
            'data': {
                'id': str(new_form.id),
                'family_id': str(new_form.family_id),
                'name': new_form.name,
                'version': new_form.version
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['DELETE'])
def api_form_delete(request, form_id):
    """Delete form (only drafts)."""
    form = get_object_or_404(FormTemplate, id=form_id)

    if form.status != 'draft':
        return JsonResponse({'success': False, 'error': 'Only draft forms can be deleted'}, status=400)

    try:
        form_name = form.name
        form.delete()

        log_action(
            request.user,
            'delete',
            'FormTemplate',
            form_id,
            {'name': form_name, 'via': 'api'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['POST'])
def api_customer_create(request):
    """Quick create customer from form builder."""
    try:
        code = request.POST.get('code', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        nas_folder_name = request.POST.get('nas_folder_name', '').strip()

        # Validate required fields
        if not code or not first_name or not email or not nas_folder_name:
            return JsonResponse({
                'success': False,
                'error': 'Campi obbligatori: code, first_name, email, nas_folder_name'
            }, status=400)

        # Check if code already exists
        if Customer.objects.filter(code=code).exists():
            return JsonResponse({
                'success': False,
                'error': f'Cliente con codice "{code}" esiste già'
            }, status=400)

        # Check if nas_folder_name already exists
        if Customer.objects.filter(nas_folder_name=nas_folder_name).exists():
            return JsonResponse({
                'success': False,
                'error': f'Cartella NAS "{nas_folder_name}" è già in uso'
            }, status=400)

        customer = Customer.objects.create(
            code=code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            nas_folder_name=nas_folder_name,
            active=True
        )

        log_action(
            request.user,
            'create',
            'Customer',
            str(customer.id),
            {'code': code, 'via': 'api'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'success': True,
            'data': {
                'id': str(customer.id),
                'code': customer.code,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'nas_folder_name': customer.nas_folder_name
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
