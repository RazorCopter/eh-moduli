import logging
import traceback
from itertools import chain

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Prefetch
from django.conf import settings

from .models import FormTemplate, FormStep, FormElement, DocumentRequirement
from .utils import log_action, get_client_ip, get_user_agent
from .client_i18n import get_translation_context

logger = logging.getLogger('modules')


def is_backoffice_user(user):
    """Backoffice operators and administrators"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))


is_admin = is_backoffice_user


@login_required
@user_passes_test(is_admin)
def form_template_list(request):
    """List all form templates."""
    templates = FormTemplate.objects.annotate(
        steps_count=Count('formstep')
    ).order_by('-created_at')

    context = {'templates': templates}
    return render(request, 'modules/admin/form_template_list.html', context)


@login_required
@user_passes_test(is_admin)
def form_template_create(request):
    """Create a new form template (traditional form)."""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        intro_text = request.POST.get('intro_text')
        privacy_text = request.POST.get('privacy_text')
        raw_expiry = request.POST.get('default_expiry_days')
        try:
            default_days = int(raw_expiry) if raw_expiry else getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
            if default_days <= 0:
                default_days = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
        except (ValueError, TypeError):
            default_days = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)

        template = FormTemplate.objects.create(
            name=name,
            description=description,
            intro_text=intro_text,
            privacy_text=privacy_text,
            default_expiry_days=default_days,
            author=request.user,
            status='draft'
        )

        log_action(
            request.user,
            'create',
            'FormTemplate',
            str(template.id),
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect('form_template_edit', pk=template.id)

    return render(request, 'modules/admin/form_template_form.html')


@login_required
@user_passes_test(is_admin)
def form_template_edit(request, pk):
    """Edit existing form template."""
    template = get_object_or_404(FormTemplate, id=pk)

    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.description = request.POST.get('description', template.description)
        template.intro_text = request.POST.get('intro_text', template.intro_text)
        template.privacy_text = request.POST.get('privacy_text', template.privacy_text)
        template.status = request.POST.get('status', template.status)
        if 'default_expiry_days' in request.POST:
            try:
                val = int(request.POST.get('default_expiry_days'))
                if val > 0:
                    template.default_expiry_days = val
            except (ValueError, TypeError):
                pass
        template.save()

        log_action(
            request.user,
            'update',
            'FormTemplate',
            str(template.id),
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect('form_template_list')

    # Prefetch steps with their elements and requirements to avoid N+1 queries
    steps = template.formstep_set.all().prefetch_related(
        Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
        Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
    ).order_by('order')
    context = {'template': template, 'steps': steps}
    return render(request, 'modules/admin/form_template_edit.html', context)


@login_required
@user_passes_test(is_admin)
def form_template_duplicate(request, pk):
    """Duplicate an existing form template and all its steps/requirements."""
    template = get_object_or_404(FormTemplate, id=pk)
    is_new_version = request.GET.get('new_version') == '1'
    new_template = template.duplicate(is_new_version=is_new_version)

    log_action(
        request.user,
        'create',
        'FormTemplate',
        str(new_template.id),
        {'duplicated_from': str(template.id)},
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return redirect('form_template_edit', pk=new_template.id)


@login_required
@user_passes_test(is_admin)
def builder_list(request):
    """List all forms in the builder."""
    logger.info(f"builder_list called by {request.user}")
    try:
        logger.debug("Querying FormTemplate objects...")
        forms = FormTemplate.objects.annotate(
            steps_count=Count('formstep')
        ).order_by('-created_at')

        logger.debug(f"Converting queryset to list (count: {forms.count()})...")
        forms_list = list(forms)
        logger.info(f"Successfully loaded {len(forms_list)} forms")

        context = {'forms': forms_list}
        return render(request, 'modules/admin/builder_list.html', context)
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"BUILDER_LIST ERROR: {str(e)}\n{error_detail}")
        log_action(
            request.user,
            'error',
            'builder_list',
            'dashboard',
            {'error': str(e)},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        return render(request, 'modules/admin/builder_list.html', {'forms': [], 'error': str(e)})


@login_required
@user_passes_test(is_admin)
def builder_create(request):
    """Create new form template (opens builder). Customer and Project are assigned in Phase 2."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        intro_text = request.POST.get('intro_text', '').strip()
        privacy_text = request.POST.get('privacy_text', '').strip()

        errors = []
        if not name:
            errors.append('Nome modulo è obbligatorio')

        if errors:
            return render(request, 'modules/admin/builder_create.html', {
                'errors': errors,
                'form_data': {
                    'name': name,
                    'description': description,
                    'intro_text': intro_text,
                    'privacy_text': privacy_text,
                }
            })

        default_intro = (
            intro_text or 
            'Benvenuto. Ti chiediamo di verificare e caricare i documenti richiesti seguendo i passaggi indicati.'
        )

        template = FormTemplate.objects.create(
            name=name,
            description=description,
            intro_text=default_intro,
            privacy_text=privacy_text,
            author=request.user,
            status='draft'
        )

        log_action(
            request.user,
            'create',
            'FormTemplate',
            str(template.id),
            {'name': name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect('builder_edit', pk=template.id)

    return render(request, 'modules/admin/builder_create.html')


@login_required
@user_passes_test(is_admin)
def builder_edit(request, pk):
    """Edit form in builder."""
    template = get_object_or_404(FormTemplate, id=pk)
    context = {'template': template}
    return render(request, 'modules/admin/builder.html', context)


@login_required
@user_passes_test(is_admin)
def builder_preview(request, pk):
    """Preview form as client would see it (read-only)."""
    template = get_object_or_404(FormTemplate, id=pk)
    steps = template.formstep_set.all().prefetch_related(
        Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
        Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
    ).order_by('order')

    for step in steps:
        step.combined_items = sorted(
            chain(step.formelement_set.all(), step.documentrequirement_set.all()),
            key=lambda x: x.order
        )

    context = {
        'form': template,
        'template': template,
        'steps': steps,
        'is_preview': True,
        **get_translation_context(request),
    }
    return render(request, 'modules/published_form.html', context)
