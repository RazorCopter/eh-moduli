"""
Views for customer form access, token verification, step navigation, and summaries.
"""

import json
import logging
from itertools import chain

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch
from django.conf import settings

from .models import FormTemplate, FormStep, FormElement, DocumentRequirement, FormAssignment
from .permissions import validate_assignment_access
from .client_i18n import get_translation_context
from .utils import get_client_ip, get_user_agent, log_action, safe_get_form_data

logger = logging.getLogger('modules')


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

        if form.check_access_password(password):
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
            steps = form.formstep_set.all().prefetch_related(
                Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
                Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
            ).order_by('order')

            # Combine FormElement and DocumentRequirement for each step, ordered by order field
            for step in steps:
                elements = step.formelement_set.all()
                documents = step.documentrequirement_set.all()
                step.combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

            context = {
                'form': form,
                'steps': steps,
                'is_published_form': True,
                **get_translation_context(request),
            }
            return render(request, 'modules/published_form.html', context)
        else:
            return render(request, 'modules/form_password.html', {
                'form_id': form_id,
                'error': 'Invalid password'
            })

    # GET request
    if is_authenticated:
        steps = form.formstep_set.all().prefetch_related(
            Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
            Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
        ).order_by('order')

        for step in steps:
            elements = step.formelement_set.all()
            documents = step.documentrequirement_set.all()
            step.combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

        context = {
            'form': form,
            'steps': steps,
            'is_published_form': True,
            **get_translation_context(request),
        }
        return render(request, 'modules/published_form.html', context)

    # Show password prompt
    return render(request, 'modules/form_password.html', {'form_id': form_id})


@require_http_methods(["GET"])
def form_success_view(request):
    """Show success message after form submission or partial draft saving."""
    form_id = request.GET.get('form_id')
    assignment_id = request.GET.get('assignment_id')
    mode = request.GET.get('mode', 'complete')
    customer_name = None
    project_name = None
    expiry_date_str = None

    if assignment_id:
        try:
            assignment = FormAssignment.objects.get(id=assignment_id)
            form_id = str(assignment.form_template_id)
            if assignment.customer:
                customer_name = f"{assignment.customer.first_name} {assignment.customer.last_name}"
            project_name = safe_get_form_data(assignment.form_data, 'project_name', '')
            if assignment.expiry_date:
                expiry_date_str = assignment.expiry_date.strftime('%d/%m/%Y')
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

    trans_ctx = get_translation_context(request)
    context = {
        'timestamp': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
        'form_id': form_id,
        'assignment_id': assignment_id,
        'mode': mode,
        'expiry_date': expiry_date_str,
        'customer': customer_name,
        'project': project_name,
        'is_public_form': True,
        **trans_ctx,
    }
    return render(request, 'modules/form_success.html', context)


@require_http_methods(["GET", "POST"])
def get_form_by_token(request, token):
    """Access form through unique secure token generated for an assignment."""
    try:
        assignment = FormAssignment.objects.get(secure_token=token)

        if assignment.customer and not assignment.customer.active:
            is_staff = request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'role', '') in ('admin', 'operator'))
            if not is_staff:
                return render(request, 'modules/form_not_found.html', {'error': "L'anagrafica cliente associata a questa pratica è disattivata.", 'is_public_form': True}, status=403)

        if assignment.is_expired():
            assignment.status = 'expired'
            assignment.save()
            return render(request, 'modules/form_expired.html', {'is_public_form': True})

        if assignment.status in ('submitted', 'in_processing', 'completed'):
            trans_ctx = get_translation_context(request)
            return render(request, 'modules/form_already_submitted.html', {
                'assignment': assignment,
                'is_public_form': True,
                **trans_ctx,
            })

        session_key = f'assignment_access_{assignment.id}_{assignment.secure_token}'

        if assignment.has_access_password():
            if request.method == 'POST':
                entered_pwd = request.POST.get('password', '').strip()
                if assignment.check_access_password(entered_pwd):
                    request.session[session_key] = True
                    request.session[f'assignment_access_{assignment.id}'] = True
                    request.session.modified = True
                    return redirect('get_form_by_token', token=token)
                else:
                    return render(request, 'modules/form_password.html', {
                        'error': 'Password errata. Riprova.',
                        'assignment': assignment,
                        'form_title': assignment.form_template.name,
                    })

            if not request.session.get(session_key, False):
                portal_cust_id = request.session.get('customer_id')
                if portal_cust_id and assignment.customer and str(assignment.customer.id) == str(portal_cust_id):
                    request.session[session_key] = True
                    request.session[f'assignment_access_{assignment.id}'] = True
                    request.session.modified = True
                else:
                    return render(request, 'modules/form_password.html', {
                        'assignment': assignment,
                        'form_title': assignment.form_template.name,
                    })

        assignment.last_access_date = timezone.now()
        assignment.save(update_fields=['last_access_date'])

        steps = list(assignment.form_template.formstep_set.all().order_by('order'))
        first_step_order = steps[0].order if steps else 0
        project_name = safe_get_form_data(assignment.form_data, 'project_name', '')

        # The animation is only for initial login or direct external landing page access
        is_client_portal = bool(request.session.get('customer_id')) or (request.GET.get('from') == 'portal')
        show_intro = not is_client_portal

        context = {
            'assignment': assignment,
            'form_template': assignment.form_template,
            'first_step_order': first_step_order,
            'project_name': project_name,
            'is_public_form': True,
            'show_intro': show_intro,
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
    """View and navigate specific step of an assigned form."""
    assignment, err_resp = validate_assignment_access(request, assignment_id, require_writable=(request.method == 'POST'), allow_password_redirect=(request.method == 'GET'))
    if err_resp:
        return err_resp

    if request.method == 'GET' and assignment.status in ('submitted', 'in_processing', 'completed'):
        return redirect('form_summary_view', assignment_id=assignment.id)

    steps = list(assignment.form_template.formstep_set.all().prefetch_related(
        Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
        Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
    ).order_by('order'))
    if not steps:
        logger.warning(f'Empty form steps for assignment {assignment_id}, form_template {assignment.form_template_id}')
        return render(request, 'modules/form_empty.html', {'assignment': assignment, 'is_public_form': True})

    # Resilient step lookup: match order, fallback to index with defensive guard
    step = next((s for s in steps if s.order == step_order), None)
    if not step:
        if not steps:
            logger.error(f'Empty steps list despite earlier check for assignment {assignment_id}')
            return render(request, 'modules/form_empty.html', {'assignment': assignment, 'is_public_form': True})

        if 1 <= step_order <= len(steps):
            step = steps[step_order - 1]
        elif 0 <= step_order < len(steps):
            step = steps[step_order]
        else:
            step = steps[0]

    elements = list(step.formelement_set.all())
    for elem in elements:
        elem.is_form_element = True

    documents = list(step.documentrequirement_set.all())
    for doc in documents:
        doc.is_document_requirement = True

    combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

    if request.method == 'POST':
        with transaction.atomic():
            locked_assignment = FormAssignment.objects.select_for_update().get(id=assignment.id)
            form_data = locked_assignment.form_data or {}
            answers = form_data.setdefault('answers', {})
            for key, val in request.POST.items():
                if key.startswith('element_'):
                    elem_id = key.replace('element_', '')
                    answers[elem_id] = val
                elif key == 'answers':
                    try:
                        parsed = json.loads(val) if isinstance(val, str) else val
                        if isinstance(parsed, dict):
                            answers.update(parsed)
                    except Exception:
                        pass
                elif key not in ('csrfmiddlewaretoken', 'action_type'):
                    answers[key] = val
            locked_assignment.form_data = form_data
            locked_assignment.last_completed_step = step
            if locked_assignment.status == 'draft':
                locked_assignment.status = 'in_progress'
            locked_assignment.save(update_fields=['form_data', 'last_completed_step', 'status'])
            return JsonResponse({'status': 'ok', 'saved_answers': answers})

    # GET: Prepare context
    try:
        current_index = steps.index(step) + 1
    except ValueError:
        logger.error(f'Step {step.id} not found in steps list for assignment {assignment_id}. Using fallback index 1.')
        current_index = 1

    step_count = len(steps)
    progress_pct = int((current_index / max(step_count, 1)) * settings.COMPLETION_PERCENTAGE_MULTIPLIER)
    prev_step = steps[current_index - 2] if current_index > 1 else None
    next_step = steps[current_index] if current_index < step_count else None

    # Load existing valid uploads for this assignment (both latest-mapped and grouped list)
    existing_uploads = {}
    existing_uploads_grouped = {}
    for upload in assignment.documentupload_set.filter(status='valid').order_by('upload_datetime'):
        req_id_str = str(upload.document_requirement_id)
        existing_uploads[req_id_str] = upload
        existing_uploads[upload.document_requirement_id] = upload
        if req_id_str not in existing_uploads_grouped:
            existing_uploads_grouped[req_id_str] = []
            existing_uploads_grouped[upload.document_requirement_id] = existing_uploads_grouped[req_id_str]
        existing_uploads_grouped[req_id_str].append(upload)

    trans_ctx = get_translation_context(request)
    saved_answers = (assignment.form_data or {}).get('answers', {})
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
        'existing_uploads_grouped': existing_uploads_grouped,
        'saved_answers': saved_answers,
        'is_public_form': True,
        **trans_ctx,
    }

    return render(request, 'modules/form_step.html', context)


@require_http_methods(["GET"])
def form_summary_view(request, assignment_id):
    """Review all uploaded documents and absence declarations before final submission."""
    assignment, err_resp = validate_assignment_access(request, assignment_id, require_writable=False, allow_password_redirect=True)
    if err_resp:
        return err_resp

    uploads = assignment.documentupload_set.filter(status='valid')
    declarations = assignment.awarenessdeclaration_set.filter(accepted=True)
    trans_ctx = get_translation_context(request)

    context = {
        'assignment': assignment,
        'uploads': uploads,
        'declarations': declarations,
        'is_public_form': True,
        **trans_ctx,
    }

    return render(request, 'modules/form_summary.html', context)
