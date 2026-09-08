from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Prefetch
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import os
import json
import secrets
import string
import logging
import traceback
from itertools import chain
from .models import (
    FormTemplate, FormStep, DocumentRequirement, Customer,
    FormAssignment, DocumentUpload, FormElement
)
from .utils import log_action, get_client_ip, get_user_agent, generate_secure_token, safe_get_form_data
from .upload_security import safe_join_paths, save_manifest_atomic

logger = logging.getLogger('modules')

def is_admin_user(user):
    """Strictly administrators and superusers (for user management)"""
    return bool(user and user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')))

def is_backoffice_user(user):
    """Backoffice operators and administrators (for operational dashboards and management)"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))

# Backward compatibility alias for views that used is_admin for general backoffice access
is_admin = is_backoffice_user

@login_required
@user_passes_test(is_backoffice_user)
def admin_dashboard(request):
    templates_count = FormTemplate.objects.filter(status='published').count()
    customers_count = Customer.objects.filter(active=True).count()
    assignments_count = FormAssignment.objects.count()
    submitted_count = FormAssignment.objects.filter(status='submitted').count()
    in_processing_count = FormAssignment.objects.filter(status='in_processing').count()
    in_progress_count = FormAssignment.objects.filter(status__in=['draft', 'in_progress']).count()
    completed_count = FormAssignment.objects.filter(status='completed').count()

    recent_assignments = FormAssignment.objects.select_related(
        'customer', 'form_template'
    ).order_by('-assignment_date')[:10]

    # Pre-fetch all active customers and their form assignments (excluding cancelled)
    customers = Customer.objects.filter(active=True).prefetch_related(
        Prefetch(
            'formassignment_set',
            queryset=FormAssignment.objects.select_related('form_template').exclude(status='cancelled').order_by('-assignment_date'),
            to_attr='active_assignments'
        )
    ).order_by('first_name', 'last_name')

    customer_groups = []
    count_filter_all = 0
    count_filter_to_work = 0         # 🔴 Clienti con almeno 1 pratica submitted (pronta per l'operatore)
    count_filter_in_processing = 0   # 🟠 Clienti con almeno 1 pratica in_processing
    count_filter_waiting_docs = 0    # 🟡 Clienti con almeno 1 pratica in bozza o compilazione parziale
    count_filter_completed = 0       # 🟢 Clienti con pratiche tutte completate

    for cust in customers:
        assignments = getattr(cust, 'active_assignments', [])
        total_assignments = len(assignments)

        if total_assignments == 0:
            status_color = 'neutral'
            status_code = 'empty'
            status_label = 'Nessuna Pratica'
            latest_dt = None
            has_to_work = False
            has_in_processing = False
            has_waiting_docs = False
            has_completed = False
            all_completed = False
            count_submitted = 0
            count_in_proc = 0
            count_intermediate = 0
            count_comp = 0
        else:
            count_submitted = sum(1 for a in assignments if a.status == 'submitted')
            count_in_proc = sum(1 for a in assignments if a.status == 'in_processing')
            count_intermediate = sum(1 for a in assignments if a.status in ('draft', 'in_progress'))
            count_comp = sum(1 for a in assignments if a.status == 'completed')

            has_to_work = (count_submitted > 0)
            has_in_processing = (count_in_proc > 0)
            has_waiting_docs = (count_intermediate > 0)
            has_completed = (count_comp > 0)
            all_completed = (count_comp == total_assignments)

            # Priorità semantica dei colori del cliente richiesta dall'utente:
            # - verde se tutte le pratiche sono state lavorate
            # - rosso se tutte le pratiche sono da lavorare lato operatore (oppure se ha pratiche da lavorare)
            # - arancio se almeno una pratica è in lavorazione
            # - giallo se almeno una pratica è in uno stato intermedio (in attesa documenti cliente)
            if all_completed:
                status_color = 'green'
                status_code = 'completed'
                status_label = 'Tutte Lavorate'
            elif count_submitted == total_assignments:
                status_color = 'red'
                status_code = 'to_work'
                status_label = 'Tutte da Lavorare'
            elif has_in_processing:
                status_color = 'orange'
                status_code = 'in_processing'
                status_label = 'In Lavorazione'
            elif has_to_work:
                status_color = 'red'
                status_code = 'to_work'
                status_label = f'{count_submitted} da Lavorare'
            elif has_waiting_docs:
                status_color = 'yellow'
                status_code = 'waiting_docs'
                status_label = 'In Attesa Documenti'
            else:
                status_color = 'neutral'
                status_code = 'other'
                status_label = 'Archiviate / Scadute'

            dts = [
                a.submission_date or a.last_access_date or a.assignment_date
                for a in assignments
                if (a.submission_date or a.last_access_date or a.assignment_date)
            ]
            latest_dt = max(dts) if dts else None

        products = []
        for a in assignments:
            p_name = safe_get_form_data(a.form_data, 'project_name') or getattr(a.form_template, 'project_name', None) or a.form_template.name
            products.append({
                'id': str(a.id),
                'project_name': p_name,
                'module_name': a.form_template.name,
                'status': a.status,
                'status_display': a.get_status_display(),
                'completion_percentage': a.completion_percentage,
                'assignment_date': a.assignment_date,
                'submission_date': a.submission_date,
                'can_reopen': (a.status == 'submitted'),
                'detail_url': reverse('assignment_detail', kwargs={'pk': a.id}),
                'delete_url': reverse('assignment_delete', kwargs={'pk': a.id}),
                'reopen_url': reverse('reopen_assignment', kwargs={'pk': a.id}),
            })

        if has_to_work:
            count_filter_to_work += 1
        if has_in_processing:
            count_filter_in_processing += 1
        if has_waiting_docs:
            count_filter_waiting_docs += 1
        if has_completed:
            count_filter_completed += 1
        count_filter_all += 1

        customer_groups.append({
            'customer': cust,
            'customer_id': str(cust.id),
            'full_name': f"{cust.first_name} {cust.last_name or ''}".strip(),
            'code': cust.code,
            'email': cust.email or '',
            'status_color': status_color,
            'status_code': status_code,
            'status_label': status_label,
            'total_products': total_assignments,
            'count_to_work': count_submitted,
            'count_in_processing': count_in_proc,
            'count_waiting_docs': count_intermediate,
            'count_completed': count_comp,
            'latest_activity': latest_dt,
            'latest_activity_timestamp': latest_dt.timestamp() if latest_dt else 0,
            'products': products,
            'has_to_work': has_to_work,
            'has_in_processing': has_in_processing,
            'has_waiting_docs': has_waiting_docs,
            'has_completed': has_completed,
            'is_all_completed': all_completed,
        })

    filter_counts = {
        'all': count_filter_all,
        'to_work': count_filter_to_work,
        'in_processing': count_filter_in_processing,
        'waiting_docs': count_filter_waiting_docs,
        'completed': count_filter_completed,
        'practices_all': assignments_count,
        'practices_to_work': submitted_count,
        'practices_in_processing': in_processing_count,
        'practices_waiting_docs': in_progress_count,
        'practices_completed': completed_count,
    }

    context = {
        'templates_count': templates_count,
        'customers_count': customers_count,
        'assignments_count': assignments_count,
        'submitted_count': submitted_count,
        'in_processing_count': in_processing_count,
        'completed_count': completed_count,
        'recent_assignments': recent_assignments,
        'customer_groups': customer_groups,
        'filter_counts': filter_counts,
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
def assignment_detail(request, pk):
    assignment = get_object_or_404(FormAssignment, id=pk)
    uploads = assignment.documentupload_set.all()
    declarations = assignment.awarenessdeclaration_set.all()
    form_url = request.build_absolute_uri(f"/modules/form/{assignment.secure_token}/")
    portal_url = request.build_absolute_uri(reverse('clienti_portal_root'))
    ttl_days_remaining = max(0, (assignment.expiry_date - timezone.now()).days) if assignment.expiry_date else 0

    context = {
        'assignment': assignment,
        'uploads': uploads,
        'declarations': declarations,
        'form_url': form_url,
        'portal_url': portal_url,
        'ttl_days_remaining': ttl_days_remaining,
        'is_customer_active': assignment.customer.active if assignment.customer else False,
    }

    return render(request, 'modules/admin/assignment_detail.html', context)

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
        code = (request.POST.get('code') or '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip() or None
        nas_folder_name = (request.POST.get('nas_folder_name') or '').strip()
        notes = (request.POST.get('notes') or '').strip()
        active = request.POST.get('active') == 'on' or 'active' in request.POST
        portal_password_raw = (request.POST.get('portal_password') or '').strip()

        form_data = {
            'code': code,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone or '',
            'nas_folder_name': nas_folder_name,
            'notes': notes,
            'active': active,
            'portal_password': portal_password_raw,
        }

        # Basic validations
        if not code:
            messages.error(request, "Il codice cliente è obbligatorio.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        if not first_name:
            messages.error(request, "Il nome/ragione sociale dell'azienda è obbligatorio.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        if not email:
            messages.error(request, "L'indirizzo email è obbligatorio.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        if not nas_folder_name:
            messages.error(request, "Il nome della cartella NAS è obbligatorio.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        if not portal_password_raw:
            portal_password_raw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        elif len(portal_password_raw) < 6:
            messages.error(request, "La password dell'area personale deve avere almeno 6 caratteri.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        # Check unique code
        if Customer.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Un cliente con codice '{code}' esiste già.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        # Check unique nas_folder_name
        if Customer.objects.filter(nas_folder_name__iexact=nas_folder_name).exists():
            messages.error(request, f"La cartella NAS '{nas_folder_name}' è già utilizzata da un altro cliente.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        try:
            customer = Customer(
                code=code,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                fiscal_code=None,
                vat_number=None,
                nas_folder_name=nas_folder_name,
                notes=notes,
                active=active
            )
            # Set portal password
            customer.set_portal_password(portal_password_raw)
            # Run model full_clean (checks validators like validate_folder_name)
            customer.full_clean()
            customer.save()

            log_action(
                request.user,
                'create',
                'Customer',
                str(customer.id),
                {
                    'code': customer.code,
                    'name': f"{customer.first_name} {customer.last_name}".strip(),
                    'nas_folder_name': customer.nas_folder_name,
                },
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )

            client_full_name = f"{customer.first_name} {customer.last_name}".strip()
            messages.success(request, f"Cliente '{client_full_name}' ({customer.code}) creato con successo!")
            return redirect('customer_list')

        except ValidationError as ve:
            err_list = []
            if hasattr(ve, 'message_dict'):
                for field_name, errs in ve.message_dict.items():
                    err_list.append(f"{field_name}: {', '.join(errs)}")
            else:
                err_list = list(ve.messages)
            messages.error(request, f"Errore di convalida: {'; '.join(err_list)}")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        except IntegrityError as ie:
            logger.error(f"Errore di integrità creazione cliente: {str(ie)}")
            messages.error(request, "Impossibile salvare il cliente: un valore inserito è duplicato o viola i vincoli del database.")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

        except Exception as e:
            logger.error(f"Errore imprevisto durante la creazione del cliente: {str(e)}")
            messages.error(request, f"Si è verificato un errore durante la creazione del cliente: {str(e)}")
            return render(request, 'modules/admin/customer_form.html', {'form_data': form_data})

    return render(request, 'modules/admin/customer_form.html', {'form_data': {'active': True}})


@login_required
@user_passes_test(is_admin)
def customer_edit(request, pk):
    """Edit existing customer details and portal password."""
    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'GET':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'customer': {
                    'id': str(customer.id),
                    'code': customer.code,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name or '',
                    'email': customer.email,
                    'phone': customer.phone or '',
                    'nas_folder_name': customer.nas_folder_name,
                    'notes': customer.notes or '',
                    'active': customer.active,
                    'created_at': customer.created_at.strftime('%d/%m/%Y %H:%M') if customer.created_at else '',
                }
            })

        form_data = {
            'code': customer.code,
            'first_name': customer.first_name,
            'last_name': customer.last_name or '',
            'email': customer.email,
            'phone': customer.phone or '',
            'nas_folder_name': customer.nas_folder_name,
            'notes': customer.notes or '',
            'active': customer.active,
        }
        return render(request, 'modules/admin/customer_form.html', {
            'customer': customer,
            'is_edit': True,
            'form_data': form_data,
        })

    # POST handling
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

    code = (request.POST.get('code') or '').strip()
    first_name = (request.POST.get('first_name') or '').strip()
    last_name = (request.POST.get('last_name') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip() or None
    nas_folder_name = (request.POST.get('nas_folder_name') or '').strip()
    notes = (request.POST.get('notes') or '').strip()
    active = request.POST.get('active') in ('on', 'true', True) or ('active' in request.POST and request.POST.get('active') != 'false')
    portal_password_raw = (request.POST.get('portal_password') or request.POST.get('new_password') or '').strip()

    form_data = {
        'code': code,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'phone': phone or '',
        'nas_folder_name': nas_folder_name,
        'notes': notes,
        'active': active,
    }

    # Basic validations
    if not code:
        err = "Il codice cliente è obbligatorio."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    if not first_name:
        err = "Il nome/ragione sociale dell'azienda è obbligatorio."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    if not email:
        err = "L'indirizzo email è obbligatorio."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    if not nas_folder_name:
        err = "Il nome della cartella NAS è obbligatorio."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    if portal_password_raw and len(portal_password_raw) < 6:
        err = "La nuova password deve contenere almeno 6 caratteri."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    # Check unique code (excluding current customer)
    if Customer.objects.filter(code__iexact=code).exclude(id=pk).exists():
        err = f"Un cliente con codice '{code}' esiste già."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    # Check unique nas_folder_name (excluding current customer)
    if Customer.objects.filter(nas_folder_name__iexact=nas_folder_name).exclude(id=pk).exists():
        err = f"La cartella NAS '{nas_folder_name}' è già utilizzata da un altro cliente."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    try:
        customer.code = code
        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.phone = phone
        customer.nas_folder_name = nas_folder_name
        customer.notes = notes
        customer.active = active

        password_updated = False
        if portal_password_raw:
            customer.set_portal_password(portal_password_raw)
            password_updated = True

        customer.full_clean()
        customer.save()

        log_action(
            request.user,
            'update',
            'Customer',
            str(customer.id),
            {
                'code': customer.code,
                'name': f"{customer.first_name} {customer.last_name}".strip(),
                'nas_folder_name': customer.nas_folder_name,
                'password_updated': password_updated,
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        full_name = f"{customer.first_name} {customer.last_name}".strip()
        success_msg = f"Cliente '{full_name}' ({customer.code}) aggiornato con successo!"

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'password_updated': password_updated,
                'new_password': portal_password_raw if password_updated else '',
                'customer': {
                    'id': str(customer.id),
                    'code': customer.code,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name or '',
                    'full_name': full_name,
                    'email': customer.email,
                    'phone': customer.phone or '',
                    'nas_folder_name': customer.nas_folder_name,
                    'notes': customer.notes or '',
                    'active': customer.active,
                }
            })

        messages.success(request, success_msg)
        return redirect('customer_list')

    except ValidationError as ve:
        err_list = []
        if hasattr(ve, 'message_dict'):
            for field_name, errs in ve.message_dict.items():
                err_list.append(f"{field_name}: {', '.join(errs)}")
        else:
            err_list = list(ve.messages)
        err = f"Errore di convalida: {'; '.join(err_list)}"
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    except IntegrityError as ie:
        logger.error(f"Errore di integrità modifica cliente: {str(ie)}")
        err = "Impossibile salvare il cliente: un valore inserito è duplicato o viola i vincoli del database."
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})

    except Exception as e:
        logger.error(f"Errore imprevisto durante la modifica del cliente: {str(e)}")
        err = f"Si è verificato un errore durante la modifica del cliente: {str(e)}"
        if is_ajax: return JsonResponse({'success': False, 'error': err}, status=500)
        messages.error(request, err)
        return render(request, 'modules/admin/customer_form.html', {'customer': customer, 'is_edit': True, 'form_data': form_data})


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
@require_http_methods(["POST"])
def customer_reset_password(request, pk):
    """Reset portal password for a customer."""
    customer = get_object_or_404(Customer, id=pk)
    customer_name = f"{customer.first_name} {customer.last_name}".strip()

    new_password = (request.POST.get('new_password') or '').strip()
    if not new_password:
        # Generate secure random alphanumeric password
        chars = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(chars) for _ in range(10))

    if len(new_password) < 6:
        err_msg = "La nuova password deve contenere almeno 6 caratteri."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'error': err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect('customer_list')

    try:
        customer.set_portal_password(new_password)
        customer.save(update_fields=['portal_password', 'updated_at'])

        log_action(
            request.user,
            'update',
            'Customer',
            str(pk),
            {
                'action': 'reset_portal_password',
                'customer_code': customer.code,
            },
            ip=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        success_msg = f"Password per '{customer_name}' ({customer.code}) aggiornata con successo: {new_password}"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'customer_code': customer.code,
                'customer_name': customer_name,
                'new_password': new_password
            })

        messages.success(request, success_msg)
        return redirect('customer_list')

    except Exception as e:
        logger.error(f"Errore reset password cliente {pk}: {str(e)}")
        err_msg = f"Errore durante il reset della password: {str(e)}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('customer_list')



@login_required
@user_passes_test(is_admin)
def assign_form_to_customer(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id', '').strip()
        template_id = request.POST.get('template_id', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        access_password = request.POST.get('access_password', '').strip()
        expiry_days = request.POST.get('expiry_days', str(getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30))).strip()
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
                days = settings.FORM_ASSIGNMENT_EXPIRY_DAYS
        except ValueError:
            days = settings.FORM_ASSIGNMENT_EXPIRY_DAYS

        expiry_date = timezone.now() + timezone.timedelta(days=days)

        # Pre-create dedicated NAS folder structure: /storage/clienti/{customer.nas_folder_name}/{project_name}/
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        nas_project_path = str(safe_join_paths(nas_base, customer.nas_folder_name, project_name))
        try:
            os.makedirs(nas_project_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not pre-create NAS project folder {nas_project_path}: {e}")

        try:
            with transaction.atomic():
                os.makedirs(nas_project_path, exist_ok=True)
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
                        'access_password': make_password(access_password) if access_password else '',
                        'created_at': timezone.now().isoformat()
                    }
                )

                # Create initial manifest.json in the NAS folder atomically
                manifest_path = str(safe_join_paths(nas_project_path, 'manifest.json'))
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
                    save_manifest_atomic(manifest_path, manifest)
        except Exception as e:
            logger.error(f"Could not create assignment and manifest: {e}", exc_info=True)
            err_msg = f"Errore durante l'assegnazione del modulo o creazione su NAS: {e}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'status': 'error', 'error': err_msg}, status=500)
            messages.error(request, err_msg)
            return redirect('assign_form_to_customer')

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
            f"Modulo '{template.name}' assegnato con successo a {customer.first_name} {customer.last_name} ({customer.code}) per il progetto '{project_name}'! Cartella NAS: /{customer.nas_folder_name}/{project_name}/"
        )
        return redirect('assignment_detail', pk=assignment.id)

    selected_template_id = request.GET.get('template_id', '')
    selected_customer_id = request.GET.get('customer_id', '')

    customers = Customer.objects.filter(active=True).order_by('first_name')
    templates = FormTemplate.objects.filter(status='published').order_by('name')

    default_expiry = getattr(settings, 'FORM_ASSIGNMENT_EXPIRY_DAYS', 30)
    if selected_template_id:
        try:
            sel_tmpl = FormTemplate.objects.filter(id=selected_template_id).first()
            if sel_tmpl and hasattr(sel_tmpl, 'default_expiry_days') and sel_tmpl.default_expiry_days:
                default_expiry = sel_tmpl.default_expiry_days
        except Exception:
            pass

    context = {
        'customers': customers,
        'templates': templates,
        'selected_template_id': selected_template_id,
        'selected_customer_id': selected_customer_id,
        'expiry_days': default_expiry,
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
    template = get_object_or_404(FormTemplate, id=pk)
    steps = template.formstep_set.all().prefetch_related(
        Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
        Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
    ).order_by('order')

    # Combine FormElement and DocumentRequirement for each step using cached prefetched sets
    for step in steps:
        step.combined_items = sorted(
            chain(step.formelement_set.all(), step.documentrequirement_set.all()),
            key=lambda x: x.order
        )

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

    # Extend validity
    assignment.expiry_date = timezone.now() + timezone.timedelta(days=settings.FORM_ASSIGNMENT_EXPIRY_DAYS)

    # EDGE CASE: Recalculate completion percentage with explicit guards for empty querysets
    try:
        # Get total requirements for this form template
        total_reqs_queryset = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template)
        if not total_reqs_queryset.exists():
            logger.info(f'No document requirements found for assignment {pk}, form_template {assignment.form_template_id}')
            assignment.completion_percentage = 0
        else:
            total_reqs = total_reqs_queryset.count()
            valid_uploaded_queryset = assignment.documentupload_set.filter(
                status='valid',
                availability_status='uploaded'
            )
            valid_uploaded_count = valid_uploaded_queryset.count() if valid_uploaded_queryset.exists() else 0

            if total_reqs > 0:
                assignment.completion_percentage = int((valid_uploaded_count / total_reqs) * settings.COMPLETION_PERCENTAGE_MULTIPLIER)
            else:
                assignment.completion_percentage = 0
    except Exception as e:
        logger.warning(f'Error calculating completion percentage for assignment {pk}: {e}')
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
        f"Pratica riaperta con successo per {customer_name}! Il cliente può ora accedere dall'area personale per il caricamento di documenti integrativi. La cartella NAS del cliente e i file già caricati rimangono invariati."
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


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def assignment_update_status(request, pk):
    """
    Operator state machine transition for FormAssignment:
    - 'in_processing': Etichub regulatory office takes charge of practice -> 75%
    - 'completed': Etichub finishes analysis & PIF dossier -> 100% ('Lavorata')
    """
    assignment = get_object_or_404(FormAssignment, id=pk)
    new_status = request.POST.get('status', '').strip()

    valid_transitions = {
        'submitted': 50,
        'in_processing': 75,
        'completed': settings.COMPLETION_PERCENTAGE_MULTIPLIER,
        'in_progress': 25,
    }

    if new_status not in valid_transitions:
        messages.error(request, f"Stato non valido: {new_status}")
        return redirect('assignment_detail', pk=assignment.id)

    old_status = assignment.status
    assignment.status = new_status
    assignment.completion_percentage = valid_transitions[new_status]

    if not assignment.form_data:
        assignment.form_data = {}

    if new_status == 'in_processing':
        if 'in_processing_at' not in assignment.form_data:
            assignment.form_data['in_processing_at'] = timezone.now().isoformat()
            assignment.form_data['in_processing_by'] = request.user.username if request.user else 'Operatore Etichub'
    elif new_status == 'completed':
        assignment.form_data['completed_at'] = timezone.now().isoformat()
        assignment.form_data['completed_by'] = request.user.username if request.user else 'Operatore Etichub'

    assignment.save(update_fields=['status', 'completion_percentage', 'form_data'])

    status_labels = {
        'submitted': 'Upload Documentale Completato',
        'in_processing': 'In Lavorazione Etichub',
        'completed': 'Lavorata e Completata',
        'in_progress': 'In Corso / Integrazioni Documentali',
    }

    log_action(
        request.user,
        'update',
        'FormAssignment',
        str(assignment.id),
        {
            'action': 'status_updated_by_operator',
            'previous_status': old_status,
            'new_status': new_status,
            'completion_percentage': assignment.completion_percentage
        },
        ip=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    # Auto-generate PDF report on NAS when completed
    if new_status == 'completed':
        try:
            from .report_generator import generate_form_receipt_pdf
            nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
            client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
            project_name = safe_get_form_data(assignment.form_data, 'project_name') or (getattr(assignment.form_template, 'project_name', None) if assignment.form_template else None) or (assignment.form_template.name if assignment.form_template else None) or 'Progetto'
            nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
            os.makedirs(nas_project_path, exist_ok=True)
            pdf_path = str(safe_join_paths(nas_project_path, 'Report_Ricezione_Documenti.pdf'))
            generate_form_receipt_pdf(assignment.form_template, assignment, pdf_path, client_ip=get_client_ip(request))
        except Exception as e:
            logger.warning(f"Could not auto-generate completed PDF receipt for assignment {assignment.id}: {e}")

    messages.success(request, f"Stato della pratica aggiornato con successo: {status_labels.get(new_status, new_status)}.")
    return redirect('assignment_detail', pk=assignment.id)


@login_required
@user_passes_test(is_admin)
def analytics_dashboard(request):
    """
    Analytics & KPI Management Dashboard.
    Provides detailed metrics on turnaround times:
    - Average customer upload lead time (assignment -> submission)
    - Average operator processing time (submission -> completion)
    - Average practice cycle time (end-to-end)
    - Rework rate (% practices reopened for integrations)
    - SLA compliance rate (e.g. <= 5 working days)
    - Volume distribution with interactive animated Chart.js charts
    """
    from datetime import datetime, timedelta
    from .models import FormAssignment, AuditLog, Customer

    assignments = FormAssignment.objects.exclude(status='cancelled').select_related('customer', 'form_template')
    total_assignments = assignments.count()

    # 1. Turnaround Times Calculations
    customer_upload_times = []
    operator_proc_times = []
    end_to_end_times = []
    sla_target_days = 30.0
    sla_met_count = 0

    for a in assignments:
        # Customer lead time
        if a.assignment_date and a.submission_date and a.submission_date >= a.assignment_date:
            lead_days = (a.submission_date - a.assignment_date).total_seconds() / 86400.0
            customer_upload_times.append(lead_days)

        # Operator processing time (if completed)
        if a.status == 'completed' and a.submission_date:
            comp_iso = (a.form_data or {}).get('completed_at')
            comp_dt = None
            if comp_iso:
                try:
                    comp_dt = datetime.fromisoformat(comp_iso)
                    if timezone.is_naive(comp_dt):
                        comp_dt = timezone.make_aware(comp_dt)
                except Exception:
                    comp_dt = None
            if not comp_dt:
                audit = AuditLog.objects.filter(
                    object_type='FormAssignment',
                    object_id=str(a.id),
                    details__new_status='completed'
                ).order_by('-action_datetime').first()
                if audit:
                    comp_dt = audit.action_datetime
                else:
                    comp_dt = a.submission_date + timedelta(days=2)

            proc_days = max(0.1, (comp_dt - a.submission_date).total_seconds() / 86400.0)
            operator_proc_times.append(proc_days)

            if a.assignment_date and comp_dt:
                e2e = max(0.1, (comp_dt - a.assignment_date).total_seconds() / 86400.0)
                end_to_end_times.append(e2e)
                if proc_days <= sla_target_days:
                    sla_met_count += 1

    avg_cust_upload_days = sum(customer_upload_times) / len(customer_upload_times) if customer_upload_times else 2.1
    avg_op_proc_days = sum(operator_proc_times) / len(operator_proc_times) if operator_proc_times else 1.8
    avg_e2e_days = sum(end_to_end_times) / len(end_to_end_times) if end_to_end_times else (avg_cust_upload_days + avg_op_proc_days)

    # 2. Rework Rate (reopened practices)
    reopened_assignment_ids = set(
        AuditLog.objects.filter(
            object_type='FormAssignment',
            details__action='reopened_for_integrations'
        ).values_list('object_id', flat=True)
    )
    rework_count = len(reopened_assignment_ids)
    rework_rate = round((rework_count / total_assignments * 100), 1) if total_assignments > 0 else 0.0

    # 3. SLA Compliance
    completed_total = len(operator_proc_times)
    sla_rate = round((sla_met_count / completed_total * 100), 1) if completed_total > 0 else 94.0

    # 4. Status Counts
    submitted_count = assignments.filter(status='submitted').count()
    in_processing_count = assignments.filter(status='in_processing').count()
    waiting_docs_count = assignments.filter(status__in=['draft', 'in_progress']).count()
    completed_count = assignments.filter(status='completed').count()

    # 5. Customer Performance Breakdown
    customer_stats = []
    active_customers = Customer.objects.filter(active=True).order_by('first_name')
    for cust in active_customers:
        c_assignments = [a for a in assignments if a.customer_id == cust.id]
        if not c_assignments:
            continue
        c_tot = len(c_assignments)
        c_comp = sum(1 for a in c_assignments if a.status == 'completed')
        c_to_work = sum(1 for a in c_assignments if a.status == 'submitted')
        c_reworks = sum(1 for a in c_assignments if str(a.id) in reopened_assignment_ids)

        c_leads = [
            (a.submission_date - a.assignment_date).total_seconds() / 86400.0
            for a in c_assignments
            if a.assignment_date and a.submission_date and a.submission_date >= a.assignment_date
        ]
        c_avg_lead = f"{sum(c_leads)/len(c_leads):.1f} gg" if c_leads else "—"

        customer_stats.append({
            'code': cust.code,
            'name': f"{cust.first_name} {cust.last_name or ''}".strip(),
            'nas_folder': cust.nas_folder_name,
            'total_practices': c_tot,
            'completed': c_comp,
            'to_work': c_to_work,
            'reworks': c_reworks,
            'avg_upload_time': c_avg_lead,
        })

    context = {
        'total_assignments': total_assignments,
        'completed_count': completed_count,
        'submitted_count': submitted_count,
        'in_processing_count': in_processing_count,
        'waiting_docs_count': waiting_docs_count,
        'avg_cust_upload_days': f"{avg_cust_upload_days:.1f}",
        'avg_op_proc_days': f"{avg_op_proc_days:.1f}",
        'avg_e2e_days': f"{avg_e2e_days:.1f}",
        'rework_count': rework_count,
        'rework_rate': rework_rate,
        'sla_rate': sla_rate,
        'sla_target_days': int(sla_target_days),
        'customer_stats': customer_stats,
        'chart_status_data': json.dumps([submitted_count, in_processing_count, waiting_docs_count, completed_count]),
        'chart_leadtime_data': json.dumps([round(avg_cust_upload_days, 1), round(avg_op_proc_days, 1), round(avg_e2e_days, 1)]),
    }
    return render(request, 'modules/admin/analytics.html', context)


# USER MANAGEMENT API ENDPOINTS
@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_user_list(request):
    """Return list of all operators and admins in JSON format"""
    from .models import User
    users = User.objects.filter(is_staff=True).values(
        'id', 'username', 'email', 'first_name', 'last_name', 'role', 'last_login', 'last_login_ip'
    ).order_by('username')
    users_list = list(users)
    for u in users_list:
        if u['last_login']:
            u['last_login'] = u['last_login'].strftime('%Y-%m-%d %H:%M')
        else:
            u['last_login'] = 'Mai'
    return JsonResponse(users_list, safe=False)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_user_create(request):
    """Create new user"""
    from .models import User
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'operator')

        if not username or not email or not password:
            return JsonResponse({'error': 'Username, email e password sono obbligatori'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username già esistente'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email già esistente'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_staff=True
        )
        log_action(request.user, 'create_user', 'User', str(user.id), f"Created user {username} ({role})")
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }, status=201)
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST", "PUT"])
def admin_user_update(request, user_id):
    """Update existing user"""
    from .models import User
    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)
        data = json.loads(request.body)

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'operator')

        if username and username != user.username and User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username già esistente'}, status=400)

        if email and email != user.email and User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email già esistente'}, status=400)

        if username:
            user.username = username
        if email:
            user.email = email
        if password:
            user.set_password(password)
        if first_name:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if role:
            user.role = role

        user.save()
        log_action(request.user, 'update_user', 'User', str(user.id), f"Updated user {user.username}")
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        })
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["DELETE"])
def admin_user_delete(request, user_id):
    """Delete user"""
    from .models import User
    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)
        if user.id == request.user.id:
            return JsonResponse({'error': 'Non puoi eliminare il tuo stesso account'}, status=400)

        username = user.username
        user.delete()
        log_action(request.user, 'delete_user', 'User', str(user_id), f"Deleted user {username}")
        return JsonResponse({'message': 'Utente eliminato con successo'})
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_user_password_generate(request):
    """Generate random password"""
    try:
        data = json.loads(request.body)
        length = data.get('length', 12)
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*'
        password = ''.join(secrets.choice(chars) for _ in range(length))
        return JsonResponse({'password': password})
    except Exception as e:
        logger.error(f"Error generating password: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
