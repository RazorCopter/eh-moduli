import string
import secrets
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count

from .models import Customer
from .utils import log_action, get_client_ip, get_user_agent, is_ajax_request

logger = logging.getLogger('modules')


def is_admin_user(user):
    """Strictly administrators and superusers (for user management and customer deletion)"""
    return bool(user and user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')))


def is_backoffice_user(user):
    """Backoffice operators and administrators (for operational dashboards and customer management)"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))


is_admin = is_backoffice_user


@login_required
@user_passes_test(is_backoffice_user)
def customer_list(request):
    """List all customers with assignment counts."""
    customers = Customer.objects.annotate(
        assignments_count=Count('formassignment')
    ).order_by('-created_at')

    context = {'customers': customers}
    return render(request, 'modules/admin/customer_list.html', context)


@login_required
@user_passes_test(is_backoffice_user)
def customer_create(request):
    """Create a new customer."""
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
            customer.set_portal_password(portal_password_raw)
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
@user_passes_test(is_backoffice_user)
def customer_edit(request, pk):
    """Edit existing customer details and portal password."""
    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'GET':
        if is_ajax_request(request):
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
    is_ajax = is_ajax_request(request)

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
@user_passes_test(is_admin_user)
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

        if is_ajax_request(request):
            return JsonResponse({'success': True, 'message': msg})

        messages.success(request, msg)
        return redirect('customer_list')
    except Exception as e:
        logger.error(f"Errore durante l'eliminazione del cliente {pk}: {str(e)}")
        err_msg = f"Errore durante l'eliminazione del cliente: {str(e)}"
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('customer_list')


@login_required
@user_passes_test(is_backoffice_user)
@require_http_methods(["POST"])
def customer_reset_password(request, pk):
    """Reset portal password for a customer."""
    customer = get_object_or_404(Customer, id=pk)
    customer_name = f"{customer.first_name} {customer.last_name}".strip()

    new_password = (request.POST.get('new_password') or '').strip()
    if not new_password:
        chars = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(chars) for _ in range(10))

    if len(new_password) < 6:
        err_msg = "La nuova password deve contenere almeno 6 caratteri."
        if is_ajax_request(request):
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

        success_msg = f"Password per '{customer_name}' ({customer.code}) aggiornata con successo."

        if is_ajax_request(request):
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'customer_code': customer.code,
                'customer_name': customer_name,
                'password_updated': True,
            })

        messages.success(request, f"Password per '{customer_name}' ({customer.code}) aggiornata con successo: {new_password}")
        return redirect('customer_list')

    except Exception as e:
        logger.error(f"Errore reset password cliente {pk}: {str(e)}")
        err_msg = f"Errore durante il reset della password: {str(e)}"
        if is_ajax_request(request):
            return JsonResponse({'success': False, 'error': err_msg}, status=500)
        messages.error(request, err_msg)
        return redirect('customer_list')
