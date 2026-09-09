from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
import os
import json
import secrets
import string
from .models import FormTemplate, FormStep, FormElement, DocumentRequirement, FormAssignment, Customer
from .utils import log_action, get_client_ip, get_user_agent, get_nas_base_path
from .validators import validate_folder_name, get_mimes_for_extensions
from .upload_security import safe_join_paths, save_manifest_atomic


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

        default_days = data.get('default_expiry_days')
        try:
            default_days = int(default_days) if default_days is not None else getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
            if default_days <= 0:
                default_days = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
        except (ValueError, TypeError):
            default_days = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)

        form = FormTemplate.objects.create(
            name=data.get('name', 'Untitled Form'),
            description=data.get('description', ''),
            intro_text=data.get('intro_text', ''),
            privacy_text=data.get('privacy_text', ''),
            default_expiry_days=default_days,
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
    steps = form.formstep_set.all().prefetch_related(
        Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
        Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
    ).order_by('order')

    for step in steps:
        elements_data = []

        # Combine FormElement and DocumentRequirement in unified order
        combined_items = []

        # Add FormElements using cached prefetched set
        for elem in step.formelement_set.all():
            combined_items.append({
                'id': str(elem.id),
                'type': 'element',
                'element_type': elem.element_type,
                'order': elem.order,
                'config': elem.config
            })

        # Add DocumentRequirements using cached prefetched set
        for doc_req in step.documentrequirement_set.all():
            combined_items.append({
                'id': str(doc_req.id),
                'type': 'document',
                'name': doc_req.name,
                'description': doc_req.description,
                'required': doc_req.required,
                'allowed_extensions': doc_req.allowed_extensions,
                'mime_types': doc_req.mime_types,
                'max_file_size': round(doc_req.max_file_size / (1024 * 1024)) if (doc_req.max_file_size and doc_req.max_file_size >= 1024 * 1024) else (doc_req.max_file_size or 10),
                'max_files': doc_req.max_files,
                'destination_subfolder': doc_req.destination_subfolder,
                'order': doc_req.order,
                'awareness_text': doc_req.awareness_text,
                'awareness_required_when_empty': doc_req.awareness_required_when_empty,
                'allow_file_description': doc_req.allow_file_description
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
            'default_expiry_days': form.default_expiry_days,
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

    # Immutable versioning check (DATA-01): protect assigned templates from destructive modification
    if form.formassignment_set.exists():
        return JsonResponse({
            'success': False,
            'error': 'Impossibile modificare la struttura di un modulo già assegnato a pratiche clienti. Crea una nuova versione esplicita.',
            'is_immutable': True
        }, status=400)

    try:
        data = json.loads(request.body)

        with transaction.atomic():
            # Update form metadata
            form.name = data.get('name', form.name)
            form.description = data.get('description', form.description)
            form.intro_text = data.get('intro_text', form.intro_text)
            form.privacy_text = data.get('privacy_text', form.privacy_text)
            if 'default_expiry_days' in data:
                try:
                    val = int(data['default_expiry_days'])
                    if val > 0:
                        form.default_expiry_days = val
                except (ValueError, TypeError):
                    pass
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
                        # Parse max_file_size: convert MB to bytes if necessary, default to 10MB
                        raw_max_size = item.get('max_file_size')
                        try:
                            if raw_max_size is not None and str(raw_max_size).strip():
                                size_val = int(raw_max_size)
                                if size_val <= 0:
                                    file_size_bytes = 10485760  # default 10MB
                                elif size_val <= 1024:
                                    # User entered MB in builder UI
                                    file_size_bytes = size_val * 1024 * 1024
                                else:
                                    # Already in bytes (e.g. 10485760)
                                    file_size_bytes = size_val
                            else:
                                file_size_bytes = 10485760  # default 10MB
                        except (ValueError, TypeError):
                            file_size_bytes = 10485760

                        allowed_ext = item.get('allowed_extensions', 'pdf,docx')
                        if not allowed_ext or not str(allowed_ext).strip():
                            allowed_ext = 'pdf,docx'

                        # Derive full MIME types matching the allowed extensions
                        derived_mimes = get_mimes_for_extensions(allowed_ext)
                        raw_mimes = item.get('mime_types', '')
                        explicit_mimes = [m.strip() for m in str(raw_mimes).split(',') if m.strip()]
                        combined_mimes = []
                        for m in explicit_mimes + derived_mimes:
                            if m not in combined_mimes:
                                combined_mimes.append(m)
                        m_types = ','.join(combined_mimes) if combined_mimes else 'application/pdf,application/msword'

                        subfolder = item.get('destination_subfolder', '')
                        subfolder = str(subfolder).strip() if subfolder is not None else ''

                        DocumentRequirement.objects.create(
                            form_step=step,
                            name=item.get('name', 'Document'),
                            description=item.get('description', ''),
                            required=item.get('required', True),
                            allowed_extensions=allowed_ext,
                            mime_types=m_types,
                            max_file_size=file_size_bytes,
                            max_files=item.get('max_files') if (item.get('max_files') is not None and int(item.get('max_files', 0)) > 0) else 200,
                            destination_subfolder=subfolder,
                            order=item_order,
                            awareness_text=item.get('awareness_text', ''),
                            awareness_required_when_empty=item.get('awareness_required_when_empty', False),
                            allow_file_description=item.get('allow_file_description', True)
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
    form = get_object_or_404(FormTemplate, id=form_id)

    try:
        with transaction.atomic():
            nas_path = None
            if form.customer and form.project_name:
                # If specific customer and project are defined, create NAS folder structure
                nas_base = get_nas_base_path()
                nas_path = str(safe_join_paths(nas_base, form.customer.nas_folder_name, form.project_name))
                os.makedirs(nas_path, exist_ok=True)

                # Create initial manifest.json atomically
                manifest = {
                    'form_id': str(form.id),
                    'form_name': form.name,
                    'customer': f"{form.customer.first_name} {form.customer.last_name or ''}".strip(),
                    'customer_code': form.customer.code,
                    'project': form.project_name,
                    'created_at': timezone.now().isoformat(),
                    'uploads': []
                }
                manifest_path = str(safe_join_paths(nas_path, 'manifest.json'))
                save_manifest_atomic(manifest_path, manifest)

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
                'customer': form.customer.code if form.customer else 'Multi-cliente',
                'project': form.project_name or 'Definito in fase di assegnazione',
                'has_password': form.has_access_password(),
                'public_url': f'/modules/form/published/{form.id}/',
                'assign_url': f'/modules/admin/assign-form/?template_id={form.id}',
                'note': 'Modulo pubblicato e pronto per essere assegnato ai clienti'
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
@require_http_methods(['POST'])
def api_form_revert_to_draft(request, form_id):
    """Revert a published form back to draft status."""
    form = get_object_or_404(FormTemplate, id=form_id)

    if form.status != 'published':
        return JsonResponse({'success': False, 'error': 'Only published forms can be reverted'}, status=400)

    # Immutable versioning check (DATA-01): protect assigned templates
    if form.formassignment_set.exists():
        return JsonResponse({
            'success': False,
            'error': 'Questo modulo è già stato assegnato a pratiche clienti ed è immutabile per proteggere i documenti storici. Per modificarlo, crea una nuova bozza / versione.',
            'is_immutable': True
        }, status=400)

    try:
        form.status = 'draft'
        form.save()

        log_action(
            request.user,
            'update',
            'FormTemplate',
            str(form.id),
            {'action': 'revert_to_draft', 'version': form.version},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'success': True,
            'data': {
                'id': str(form.id),
                'status': 'draft',
                'message': f'Form "{form.name}" reverted to draft'
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['DELETE'])
def api_form_delete(request, form_id):
    """Delete form (draft or published)."""
    form = get_object_or_404(FormTemplate, id=form_id)

    try:
        form_name = form.name
        form_status = form.status

        # Protect against cascading delete: archive if assignments exist (M2)
        has_assignments = form.formassignment_set.exists()
        if has_assignments:
            form.status = 'archived'
            form.save(update_fields=['status', 'updated_at'])
            action_name = 'archive'
            message = f'Modulo "{form_name}" archiviato con successo (le pratiche e i file dei clienti sono stati protetti).'
        else:
            form.delete()
            action_name = 'delete'
            message = f'Modulo "{form_name}" eliminato'

        log_action(
            request.user,
            action_name,
            'FormTemplate',
            form_id,
            {'name': form_name, 'status': form_status, 'via': 'api', 'archived': has_assignments},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({'success': True, 'message': message, 'archived': has_assignments})
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

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'error': f'Indirizzo email non valido: "{email}"'
            }, status=400)

        # Validate NAS folder name format and path safety
        try:
            validate_folder_name(nas_folder_name)
        except ValidationError as e:
            err_msg = e.message if hasattr(e, 'message') else str(e)
            return JsonResponse({
                'success': False,
                'error': f'Nome cartella NAS non valido: {err_msg}'
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

        portal_password = request.POST.get('portal_password', '').strip()
        if not portal_password:
            portal_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

        customer = Customer(
            code=code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            nas_folder_name=nas_folder_name,
            active=True
        )
        try:
            customer.full_clean()
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': f'Dati cliente non validi: {e.message_dict if hasattr(e, "message_dict") else str(e)}'
            }, status=400)

        customer.set_portal_password(portal_password)
        customer.save()

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
                'nas_folder_name': customer.nas_folder_name,
                'portal_password': portal_password
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(['POST', 'DELETE'])
def api_customer_delete(request, customer_id):
    """Delete customer from database via API (preserves files on NAS)."""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        customer_code = customer.code
        customer_name = f"{customer.first_name} {customer.last_name}".strip()
        nas_folder = customer.nas_folder_name

        # Delete database record only
        # Physical files and directories on NAS remain untouched
        customer.delete()

        log_action(
            request.user,
            'delete',
            'Customer',
            str(customer_id),
            {
                'code': customer_code,
                'name': customer_name,
                'nas_folder_name': nas_folder,
                'physical_files_kept': True,
                'via': 'api',
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return JsonResponse({
            'success': True,
            'message': f"Cliente '{customer_name}' ({customer_code}) eliminato con successo dal database. File sul NAS preservati."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

