"""
Client Personal Area Views
Handles authentication, dashboard, and product navigation for customers.
"""
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q
from .models import Customer, FormAssignment, DocumentRequirement, DocumentUpload
from .utils import get_client_ip, get_user_agent, log_action
from .client_i18n import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_LANGUAGE_CODES,
    get_client_language,
    get_translation_context,
)
import logging

logger = logging.getLogger('modules')


# ---------------------------------------------------------------------------
# Decorator: customer session authentication
# ---------------------------------------------------------------------------
def customer_login_required(view_func):
    """Decorator that restricts a view to authenticated portal customers."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        customer_id = request.session.get('customer_id')
        if not customer_id:
            return redirect('client_login')
        # Verify the customer still exists and is active
        try:
            customer = Customer.objects.get(id=customer_id, active=True)
        except Customer.DoesNotExist:
            # Session refers to a deleted or deactivated customer
            request.session.flush()
            return redirect('client_login')
        request.portal_customer = customer
        return view_func(request, *args, **kwargs)
    return _wrapped


# ---------------------------------------------------------------------------
# Language Switcher
# ---------------------------------------------------------------------------
@require_http_methods(["GET", "POST"])
def set_client_language(request, lang_code=None):
    """
    Switch active language for the client personal area without losing session.
    Accepts lang_code in URL path or ?lang=<code> or POST data.
    Redirects back to referrer or ?next=<url>.
    """
    code = lang_code or request.POST.get('lang') or request.GET.get('lang') or 'it'
    code = code.lower().strip()
    if code in SUPPORTED_LANGUAGE_CODES:
        request.session['client_language'] = code
        request.session.modified = True

    # Determine safe redirect target
    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER')
    # Fallback if no referrer or external url
    if not next_url or not next_url.startswith('/'):
        if next_url and ('/modules/client/' in next_url or '/modules/form/' in next_url):
            pass
        else:
            if request.session.get('customer_id'):
                next_url = redirect('client_dashboard').url
            else:
                next_url = redirect('client_login').url

    response = redirect(next_url)
    if code in SUPPORTED_LANGUAGE_CODES:
        response.set_cookie('client_language', code, max_age=365*24*3600, samesite='Lax')
    return response


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@require_http_methods(["GET", "POST"])
def client_login(request):
    """Customer portal login — code + password."""
    # If already logged in, redirect to dashboard
    if request.session.get('customer_id'):
        return redirect('client_dashboard')

    trans_ctx = get_translation_context(request)
    t = trans_ctx['t']
    error = None
    code_value = ''

    if request.method == 'POST':
        code_value = (request.POST.get('code') or '').strip()
        password = (request.POST.get('password') or '').strip()

        if not code_value or not password:
            error = t['error_missing_fields']
        else:
            try:
                customer = Customer.objects.get(code__iexact=code_value)
                if not customer.active:
                    error = t['error_account_inactive']
                elif not customer.portal_password:
                    error = t['error_not_configured']
                elif customer.check_portal_password(password):
                    # Success — create session
                    request.session['customer_id'] = str(customer.id)
                    request.session['customer_code'] = customer.code
                    request.session['customer_name'] = f"{customer.first_name} {customer.last_name}".strip()
                    # Ensure current language preference remains saved
                    request.session['client_language'] = trans_ctx['client_lang']
                    request.session.modified = True

                    log_action(
                        None,
                        'login',
                        'CustomerPortal',
                        str(customer.id),
                        {'code': customer.code, 'lang': trans_ctx['client_lang']},
                        ip=get_client_ip(request),
                        user_agent=get_user_agent(request)
                    )

                    return redirect('client_dashboard')
                else:
                    error = t['error_invalid_credentials']
            except Customer.DoesNotExist:
                error = t['error_invalid_credentials']

        log_action(
            None,
            'login',
            'CustomerPortal',
            code_value or 'UNKNOWN',
            {'error': error, 'success': False, 'lang': trans_ctx['client_lang']},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        )

    context = {
        'error': error,
        'code_value': code_value,
        **trans_ctx,
    }

    response = render(request, 'modules/client/login.html', context)
    response.set_cookie('client_language', trans_ctx['client_lang'], max_age=365*24*3600, samesite='Lax')
    return response


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@require_http_methods(["POST"])
def client_logout(request):
    """Customer portal logout — flush customer session data while preserving language preference."""
    customer_id = request.session.get('customer_id')
    current_lang = request.session.get('client_language', 'it')
    if customer_id:
        log_action(
            None,
            'login',  # Using 'login' action type since there's no 'logout' in ACTION_CHOICES
            'CustomerPortal',
            customer_id,
            {'action': 'logout'},
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    # Clear only customer-related session keys (don't destroy language or admin session)
    for key in ['customer_id', 'customer_code', 'customer_name']:
        request.session.pop(key, None)
    request.session['client_language'] = current_lang
    request.session.modified = True
    return redirect('client_login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@require_http_methods(["GET"])
@customer_login_required
def client_dashboard(request):
    """Customer dashboard — list all products (assignments) for this customer."""
    customer = request.portal_customer
    trans_ctx = get_translation_context(request)
    t = trans_ctx['t']

    now = timezone.now()
    # Batch update expired assignments before querying
    FormAssignment.objects.filter(
        customer=customer,
        expiry_date__lt=now
    ).exclude(
        status__in=('submitted', 'in_processing', 'completed', 'expired', 'cancelled')
    ).update(status='expired')

    assignments = FormAssignment.objects.filter(
        customer=customer
    ).exclude(
        status='cancelled'
    ).select_related(
        'form_template'
    ).annotate(
        valid_uploads_count=Count(
            'documentupload',
            filter=Q(documentupload__status='valid')
        )
    ).order_by('-assignment_date')

    # Batch query total requirements per form_template to avoid N+1 queries
    template_ids = {a.form_template_id for a in assignments if a.form_template_id}
    req_counts = dict(
        DocumentRequirement.objects.filter(
            form_step__form_template_id__in=template_ids
        ).values('form_step__form_template_id').annotate(
            total=Count('id')
        ).values_list('form_step__form_template_id', 'total')
    ) if template_ids else {}

    # Enrich each assignment with computed properties for the template
    products = []
    for assignment in assignments:
        project_name = ''
        if assignment.form_data:
            project_name = assignment.form_data.get('project_name', '')

        is_expired = assignment.is_expired()
        total_reqs = req_counts.get(assignment.form_template_id, 0)
        uploaded_count = getattr(assignment, 'valid_uploads_count', 0)

        status_label = t.get(f'status_{assignment.status}', assignment.status)
        badge_label = t.get(f'badge_{assignment.status}', status_label)

        # Build timeline history milestones for this assignment
        is_submitted_or_beyond = assignment.status in ('submitted', 'in_processing', 'completed')
        is_processing_or_beyond = assignment.status in ('in_processing', 'completed')
        is_completed = assignment.status == 'completed'

        timeline_steps = [
            {
                'id': 1,
                'title': t.get('timeline_step_assigned', 'Pratica Creata e Assegnata'),
                'desc': t.get('timeline_step_assigned_desc', 'Modulo predisposto per l\'upload documentale.'),
                'status': 'completed',
                'date': assignment.assignment_date,
                'icon': 'bi-folder-plus',
            },
            {
                'id': 2,
                'title': t.get('timeline_step_submitted', 'Invio Documentale Concluso'),
                'desc': t.get('timeline_step_submitted_desc', 'Tutti i documenti richiesti trasmessi dal cliente.'),
                'status': 'completed' if is_submitted_or_beyond else ('active' if assignment.status in ('draft', 'in_progress') else 'pending'),
                'date': assignment.submission_date if is_submitted_or_beyond else None,
                'icon': 'bi-cloud-check',
            },
            {
                'id': 3,
                'title': t.get('timeline_step_processing', 'Presa in Carico Ufficio Regolatorio'),
                'desc': t.get('timeline_step_processing_desc', 'Verifica tecnica e redazione PIF in corso presso Etichub.'),
                'status': 'completed' if is_completed else ('active' if assignment.status == 'in_processing' else 'pending'),
                'date': None,
                'icon': 'bi-gear-wide-connected',
            },
            {
                'id': 4,
                'title': t.get('timeline_step_completed', 'Lavorazione Regolatoria Completata'),
                'desc': t.get('timeline_step_completed_desc', 'Dossier regolatorio validato con successo.'),
                'status': 'completed' if is_completed else 'pending',
                'date': None,
                'icon': 'bi-patch-check-fill',
            },
        ]

        products.append({
            'assignment': assignment,
            'project_name': project_name or (assignment.form_template.name if assignment.form_template else 'N/A'),
            'module_name': assignment.form_template.name if assignment.form_template else 'N/A',
            'status': assignment.status,
            'status_label': status_label,
            'badge_label': badge_label,
            'is_expired': is_expired,
            'completion_pct': assignment.completion_percentage,
            'total_requirements': total_reqs,
            'uploaded_count': uploaded_count,
            'assignment_date': assignment.assignment_date,
            'expiry_date': assignment.expiry_date,
            'can_upload': assignment.status in ('draft', 'in_progress') and not is_expired,
            'timeline_steps': timeline_steps,
        })

    welcome_msg = t['hello_user'].format(name=customer.first_name) if customer.first_name else t['welcome_back']

    context = {
        'customer': customer,
        'products': products,
        'products_count': len(products),
        'show_navbar': True,
        'customer_initial': (customer.first_name[0] if customer.first_name else '?').upper(),
        'welcome_msg': welcome_msg,
        **trans_ctx,
    }

    response = render(request, 'modules/client/dashboard.html', context)
    response.set_cookie('client_language', trans_ctx['client_lang'], max_age=365*24*3600, samesite='Lax')
    return response


# ---------------------------------------------------------------------------
# Product Detail → redirect to upload flow
# ---------------------------------------------------------------------------
@require_http_methods(["GET"])
@customer_login_required
def client_product_detail(request, assignment_id):
    """
    Entry point from the client dashboard to the upload flow.
    Verifies ownership, sets session access, and redirects to the
    existing step-by-step upload flow.
    """
    customer = request.portal_customer
    assignment = get_object_or_404(FormAssignment, id=assignment_id)
    trans_ctx = get_translation_context(request)
    t = trans_ctx['t']

    # Ownership check
    if assignment.customer_id != customer.id:
        return HttpResponseForbidden(t['error_forbidden_product'])

    # Check status
    if assignment.is_expired() and assignment.status not in ('submitted', 'expired'):
        assignment.status = 'expired'
        assignment.save(update_fields=['status'])

    if assignment.status in ('submitted', 'in_processing', 'completed'):
        return render(request, 'modules/form_already_submitted.html', {
            'assignment': assignment,
            'is_public_form': True,
            **trans_ctx,
        })

    if assignment.status == 'expired':
        return render(request, 'modules/form_expired.html', {
            'assignment': assignment,
            'is_public_form': True,
            **trans_ctx,
        })

    # Grant session access for the existing upload flow (same mechanism as token access)
    session_key = f'assignment_access_{assignment.id}_{assignment.secure_token}'
    request.session[session_key] = True
    request.session[f'assignment_access_{assignment.id}'] = True
    request.session.modified = True

    # Update last access
    assignment.last_access_date = timezone.now()
    if assignment.status == 'draft':
        assignment.status = 'in_progress'
    assignment.save()

    log_action(
        None,
        'view',
        'CustomerPortal',
        str(assignment.id),
        {'action': 'product_access', 'customer': customer.code},
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    # Redirect to the existing form detail (token-based entry point)
    return redirect('get_form_by_token', token=assignment.secure_token)
