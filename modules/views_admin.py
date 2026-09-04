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
from .utils import log_action, get_client_ip, get_user_agent

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
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        template_id = request.POST.get('template_id')

        customer = get_object_or_404(Customer, id=customer_id)
        template = get_object_or_404(FormTemplate, id=template_id)

        assignment = FormAssignment.objects.create(
            customer=customer,
            form_template=template,
            expiry_date=timezone.now() + timezone.timedelta(days=30),
            operator=request.user,
            status='draft'
        )

        log_action(
            request.user,
            'create',
            'FormAssignment',
            str(assignment.id),
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'status': 'success',
                'token': assignment.secure_token,
                'form_url': f"/modules/form/{assignment.secure_token}/",
                'assignment_id': str(assignment.id)
            })

        messages.success(
            request, 
            f"Modulo '{template.name}' assegnato con successo a {customer.first_name} {customer.last_name}! Di seguito trovi il link riservato generato per il cliente."
        )
        return redirect('assignment_detail', pk=assignment.id)

    customers = Customer.objects.filter(active=True)
    templates = FormTemplate.objects.filter(status='published')

    context = {
        'customers': customers,
        'templates': templates,
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
        return render(request, 'modules/admin/builder_list.html', {
            'forms': [],
            'error': f'Errore caricamento form: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
def builder_create(request):
    """Create new form (opens builder)."""
    if request.method == 'POST':
        import secrets
        import string

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        intro_text = request.POST.get('intro_text', '').strip()
        privacy_text = request.POST.get('privacy_text', '').strip()
        customer_id = request.POST.get('customer_id', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        access_password = request.POST.get('access_password', '').strip()

        # Validate required fields
        errors = []
        if not name:
            errors.append('Nome modulo è obbligatorio')
        if not customer_id:
            errors.append('Devi selezionare un cliente')
        if not project_name:
            errors.append('Nome progetto è obbligatorio')

        if errors:
            return render(request, 'modules/admin/builder_create.html', {
                'customers': Customer.objects.filter(active=True).order_by('first_name'),
                'errors': errors,
                'form_data': {
                    'name': name,
                    'description': description,
                    'intro_text': intro_text,
                    'privacy_text': privacy_text,
                }
            })

        # Auto-generate password if empty
        if not access_password:
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
            access_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        # Fetch customer
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return render(request, 'modules/admin/builder_create.html', {
                'customers': Customer.objects.filter(active=True).order_by('first_name'),
                'errors': ['Cliente selezionato non trovato']
            })

        template = FormTemplate.objects.create(
            name=name,
            description=description,
            intro_text=intro_text,
            privacy_text=privacy_text,
            customer=customer,
            project_name=project_name,
            access_password=access_password,
            author=request.user,
            status='draft'
        )

        log_action(
            request.user,
            'create',
            'FormTemplate',
            str(template.id),
            {'customer': str(customer.id) if customer else None, 'project': project_name},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return redirect('builder_edit', pk=template.id)

    customers = Customer.objects.filter(active=True).order_by('first_name')
    return render(request, 'modules/admin/builder_create.html', {'customers': customers})


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
