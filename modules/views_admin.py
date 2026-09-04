from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
import logging
import traceback
from .models import (
    FormTemplate, FormStep, DocumentRequirement, Customer,
    FormAssignment, DocumentUpload, FormElement
)
from .utils import log_action, get_client_ip, get_user_agent, generate_secure_token

logger = logging.getLogger('modules')

def is_admin(user):
    return user.is_staff or (hasattr(user, 'role') and user.role == 'admin')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    templates_count = FormTemplate.objects.filter(status='published').count()
    customers_count = Customer.objects.filter(active=True).count()
    assignments_count = FormAssignment.objects.count()
    submitted_count = FormAssignment.objects.filter(status='submitted').count()

    recent_assignments = FormAssignment.objects.select_related(
        'customer', 'form_template'
    ).order_by('-assignment_date')[:10]

    context = {
        'templates_count': templates_count,
        'customers_count': customers_count,
        'assignments_count': assignments_count,
        'submitted_count': submitted_count,
        'recent_assignments': recent_assignments,
    }

    log_action(
        request.user,
        'view',
        'AdminDashboard',
        'dashboard',
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return render(request, 'modules/admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def form_template_list(request):
    templates = FormTemplate.objects.annotate(
        steps_count=Count('formstep')
    ).order_by('-created_at')

    context = {'templates': templates}
    return render(request, 'modules/admin/form_template_list.html', context)

@login_required
@user_passes_test(is_admin)
def form_template_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        intro_text = request.POST.get('intro_text')
        privacy_text = request.POST.get('privacy_text')

        template = FormTemplate.objects.create(
            name=name,
            description=description,
            intro_text=intro_text,
            privacy_text=privacy_text,
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
    template = get_object_or_404(FormTemplate, id=pk)

    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.description = request.POST.get('description', template.description)
        template.intro_text = request.POST.get('intro_text', template.intro_text)
        template.privacy_text = request.POST.get('privacy_text', template.privacy_text)
        template.status = request.POST.get('status', template.status)
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

    steps = template.formstep_set.all().order_by('order')
    context = {'template': template, 'steps': steps}
    return render(request, 'modules/admin/form_template_edit.html', context)

@login_required
@user_passes_test(is_admin)
def form_template_duplicate(request, pk):
    template = get_object_or_404(FormTemplate, id=pk)
    new_template = template.duplicate()

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
def customer_list(request):
    customers = Customer.objects.annotate(
        assignments_count=Count('formassignment')
    ).order_by('-created_at')

    context = {'customers': customers}
    return render(request, 'modules/admin/customer_list.html', context)

@login_required
@user_passes_test(is_admin)
def customer_create(request):
    if request.method == 'POST':
        customer = Customer.objects.create(
            code=request.POST.get('code'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone', ''),
            fiscal_code=request.POST.get('fiscal_code', ''),
            vat_number=request.POST.get('vat_number', ''),
            nas_folder_name=request.POST.get('nas_folder_name'),
            notes=request.POST.get('notes', ''),
            active=request.POST.get('active') == 'on'
        )

        log_action(
            request.user,
            'create',
            'Customer',
            str(customer.id),
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect('customer_list')

    return render(request, 'modules/admin/customer_form.html')

@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def customer_delete(request, pk):
    """Delete customer from DB only.
    Files and directories on the NAS are preserved.
    """
    customer = get_object_or_404(Customer, id=pk)
    customer_code = customer.code
    customer_name = f"{customer.first_name} {customer.last_name}".strip()
    nas_folder = customer.nas_folder_name

    try:
        # Delete the customer record from DB
        # This will SET_NULL on FormTemplate.customer, and CASCADE related FormAssignment
        # Physical NAS directories and files are untouched
        customer.delete()

        log_action(
            request.user,
            'delete',
            'Customer',
            str(pk),
            {
                'code': customer_code,
                'name': customer_name,
                'nas_folder_name': nas_folder,
                'physical_files_kept': True,
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        msg = f"Cliente '{customer_name}' ({customer_code}) eliminato con successo dal database. La cartella NAS '{nas_folder}' è rimasta intatta."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'message': msg})

        messages.success(request, msg)
        return redirect('customer_list')
    except Exception as e:
        logger.error(f"Errore durante l'eliminazione del cliente {pk}: {str(e)}")
        err_msg = f"Errore durante l'eliminazione del cliente: {str(e)}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('customer_list')


@login_required
@user_passes_test(is_admin)
def assignment_detail(request, pk):
    assignment = get_object_or_404(FormAssignment, id=pk)
    uploads = assignment.documentupload_set.all()
    declarations = assignment.awarenessdeclaration_set.all()
    form_url = request.build_absolute_uri(f"/modules/form/{assignment.secure_token}/")

    context = {
        'assignment': assignment,
        'uploads': uploads,
        'declarations': declarations,
        'form_url': form_url,
    }

    return render(request, 'modules/admin/assignment_detail.html', context)

@login_required
@user_passes_test(is_admin)
def assign_form_to_customer(request):
    import os
    import json
    import secrets
    import string

    if request.method == 'POST':
        customer_id = request.POST.get('customer_id', '').strip()
        template_id = request.POST.get('template_id', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        access_password = request.POST.get('access_password', '').strip()
        expiry_days = request.POST.get('expiry_days', '30').strip()
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
                days = 30
        except ValueError:
            days = 30

        expiry_date = timezone.now() + timezone.timedelta(days=days)

        # Pre-create dedicated NAS folder structure: /storage/clienti/{customer.nas_folder_name}/{project_name}/
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        nas_project_path = os.path.join(nas_base, customer.nas_folder_name, project_name)
        try:
            os.makedirs(nas_project_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not pre-create NAS project folder {nas_project_path}: {e}")

        if not access_password:
            alphabet = string.ascii_letters + string.digits
            access_password = ''.join(secrets.choice(alphabet) for _ in range(8))

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
                'access_password': access_password,
                'created_at': timezone.now().isoformat()
            }
        )

        # Create initial manifest.json in the NAS folder
        try:
            manifest_path = os.path.join(nas_project_path, 'manifest.json')
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
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not create initial manifest.json in {nas_project_path}: {e}")

        log_action(
            request.user,
            'create',
            'FormAssignment',
            str(assignment.id),
            {'customer': customer.code, 'template': template.name, 'project': project_name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'status': 'success',
                'token': assignment.secure_token,
                'form_url': f"/modules/form/{assignment.secure_token}/",
                'assignment_id': str(assignment.id),
                'project_name': project_name,
                'access_password': access_password,
                'nas_path': nas_project_path
            })

        messages.success(
            request, 
            f"Modulo '{template.name}' assegnato con successo a {customer.first_name} {customer.last_name} per il progetto '{project_name}'! Password di accesso: {access_password}. Cartella NAS: /{customer.nas_folder_name}/{project_name}/"
        )
        return redirect('assignment_detail', pk=assignment.id)

    selected_template_id = request.GET.get('template_id', '')
    selected_customer_id = request.GET.get('customer_id', '')

    customers = Customer.objects.filter(active=True).order_by('first_name')
    templates = FormTemplate.objects.filter(status='published').order_by('name')

    context = {
        'customers': customers,
        'templates': templates,
        'selected_template_id': selected_template_id,
        'selected_customer_id': selected_customer_id,
    }

    return render(request, 'modules/admin/assign_form.html', context)


@login_required
@user_passes_test(is_admin)
def builder_list(request):
    """List all forms (drafts and published)."""
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

        # Validate required fields
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
    from itertools import chain
    template = get_object_or_404(FormTemplate, id=pk)
    steps = template.formstep_set.all().order_by('order')

    # Combine FormElement and DocumentRequirement for each step, ordered by order field
    for step in steps:
        elements = step.formelement_set.all().order_by('order')
        documents = step.documentrequirement_set.all().order_by('order')
        step.combined_items = sorted(chain(elements, documents), key=lambda x: x.order)

    context = {
        'form': template,
        'template': template,
        'steps': steps,
        'is_preview': True
    }
    return render(request, 'modules/published_form.html', context)


@login_required
@user_passes_test(is_admin)
def operational_guide(request):
    """Render comprehensive interactive operational workflow guide."""
    return render(request, 'modules/admin/operational_guide.html')


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def reopen_assignment_for_upload(request, pk):
    """
    Reopens a FormAssignment to allow the customer to upload additional/integrative files.
    - Generates a new secure token for customer access.
    - Resets status to 'in_progress' and clears submission_date.
    - Extends validity date (+30 days).
    - Preserves all customer metadata and dedicated NAS folder structure (/storage/clienti/{customer.nas_folder_name}/{project_name}/).
    - Preserves existing uploaded files.
    """
    assignment = get_object_or_404(FormAssignment, id=pk)
    old_status = assignment.status
    old_token = assignment.secure_token

    # Generate brand new unique secure token
    assignment.secure_token = generate_secure_token()

    # Reopen status and clear submission timestamp
    assignment.status = 'in_progress'
    assignment.submission_date = None

    # Extend validity (30 days from now)
    assignment.expiry_date = timezone.now() + timezone.timedelta(days=30)

    # Recalculate completion percentage based on valid uploaded files vs total requirements
    total_reqs = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template).count()
    if total_reqs > 0:
        valid_uploaded_count = assignment.documentupload_set.filter(
            status='valid',
            availability_status='uploaded'
        ).count()
        assignment.completion_percentage = int((valid_uploaded_count / total_reqs) * 100)
    else:
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
        f"Pratica riaperta con successo per {customer_name}! È stato generato un nuovo link di accesso per il caricamento di documenti integrativi. La cartella NAS del cliente e i file già caricati rimangono invariati."
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        new_url = request.build_absolute_uri(f"/modules/form/{assignment.secure_token}/")
        return JsonResponse({
            'status': 'success',
            'token': assignment.secure_token,
            'form_url': new_url,
            'message': 'Link rigenerato con successo'
        })

    return redirect('assignment_detail', pk=assignment.id)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def assignment_delete(request, pk):
    """
    Deletes / disassociates a FormAssignment from a customer.
    - Removes the assignment record and cascades related uploads/declarations metadata.
    - Customer and FormTemplate remain intact.
    - Physical files on NAS are kept intact.
    - Logs the action in audit log.
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

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'success', 'message': msg})

        messages.success(request, msg)
        return redirect('admin_dashboard')

    except Exception as e:
        logger.error(f"Errore durante l'eliminazione dell'assegnazione {pk}: {e}")
        err_msg = f"Errore durante l'eliminazione dell'assegnazione: {str(e)}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('admin_dashboard')

