"""
Views for form submissions (partial and complete), finalization, and PDF receipt downloads.
"""

import os
import json
import hashlib
import secrets
import tempfile
import traceback
import logging
from itertools import chain

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden, Http404, FileResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from django.db.models import Prefetch
from django.conf import settings

from .models import (
    FormTemplate, FormStep, FormElement, DocumentRequirement,
    FormAssignment, AwarenessDeclaration, NotificationLog
)
from .utils import get_client_ip, get_user_agent, log_action, safe_get_form_data, is_ajax_request
from .upload_security import safe_join_paths, save_manifest_atomic
from .report_generator import generate_form_receipt_pdf, generate_submission_pdf

logger = logging.getLogger('modules')


@require_http_methods(["GET"])
def published_form_receipt(request, form_id):
    """Download the official PDF report receipt for a submitted form."""
    try:
        form = FormTemplate.objects.get(id=form_id)
    except (FormTemplate.DoesNotExist, ValueError):
        raise Http404("Modulo non trovato")

    is_staff = request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'role', '') == 'admin')
    has_assignment_access = any(k.startswith('assignment_access_') and v is True for k, v in request.session.items())
    session_key = f'form_access_{form_id}'

    if not request.session.get(session_key, False) and not is_staff and not has_assignment_access:
        return HttpResponseForbidden("Accesso non autorizzato. Effettua prima l'accesso con password.")

    nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
    customer_folder = form.customer.nas_folder_name if form.customer else '_generic'
    project_folder = form.project_name if form.project_name else str(form.id)
    nas_project_path = os.path.join(nas_base, customer_folder, project_folder)
    pdf_path = os.path.join(nas_project_path, 'Report_Ricezione_Documenti.pdf')

    if not os.path.exists(pdf_path):
        raise Http404("Il report PDF non è stato ancora generato per questo modulo.")

    try:
        safe_title = "".join(c for c in form.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"Ricevuta_{safe_title}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=filename)
    except (IOError, OSError) as e:
        logger.error(f'File download error for published_form_receipt {form_id}: {e}')
        raise Http404("Il file PDF non può essere scaricato. Per favore, contatta l'amministratore.")


@require_http_methods(["GET"])
def assignment_receipt(request, assignment_id):
    """Download the official PDF report receipt for a submitted assignment."""
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except (FormAssignment.DoesNotExist, ValueError):
        raise Http404("Pratica non trovata")

    is_staff = request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'role', '') == 'admin')
    token_session_key = f'assignment_access_{assignment.id}_{assignment.secure_token}'
    legacy_session_key = f'assignment_access_{assignment.id}'
    has_access = bool(request.session.get(token_session_key, False) or request.session.get(legacy_session_key, False))

    if assignment.has_access_password() and not has_access and not is_staff:
        return HttpResponseForbidden("Accesso non autorizzato. Effettua prima l'accesso con password.")

    nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
    client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
    project_name = safe_get_form_data(assignment.form_data, 'project_name') or ''
    nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
    pdf_path = str(safe_join_paths(nas_project_path, 'Report_Ricezione_Documenti.pdf'))

    try:
        os.makedirs(nas_project_path, exist_ok=True)
        generate_form_receipt_pdf(assignment.form_template, assignment, pdf_path, client_ip=get_client_ip(request))
    except Exception as e:
        logger.warning(f"Could not generate/update PDF receipt on demand: {e}")

    if not os.path.exists(pdf_path):
        raise Http404("Il report PDF non è stato ancora generato per questa pratica.")

    try:
        template_name = assignment.form_template.name if assignment.form_template else "Modulo"
        safe_title = "".join(c for c in template_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"Ricevuta_{safe_title}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=filename)
    except (IOError, OSError) as e:
        logger.error(f'File download error for assignment_receipt {assignment_id}: {e}')
        raise Http404("Il file PDF non può essere scaricato. Per favore, contatta l'amministratore.")


@require_http_methods(["POST"])
def form_submission_view(request, assignment_id):
    """Complete or partial submission of an assignment by the customer."""
    try:
        assignment = FormAssignment.objects.get(id=assignment_id)
    except FormAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    # Password protection check
    token_key = f'assignment_access_{assignment.id}_{assignment.secure_token}'
    legacy_key = f'assignment_access_{assignment.id}'
    has_access = request.session.get(token_key, False) or request.session.get(legacy_key, False)
    if assignment.has_access_password() and not has_access:
        return redirect('get_form_by_token', token=assignment.secure_token)

    action_type = request.POST.get('action_type', 'complete')

    # Partial / Draft save
    if action_type == 'partial':
        try:
            if assignment.status != 'submitted':
                assignment.status = 'in_progress'
                total_reqs_qs = DocumentRequirement.objects.filter(form_step__form_template=assignment.form_template)
                total_reqs = total_reqs_qs.count() if total_reqs_qs.exists() else 0
                valid_uploads_qs = assignment.documentupload_set.filter(status='valid')
                valid_count = valid_uploads_qs.count() if valid_uploads_qs.exists() else 0

                if total_reqs > 0:
                    assignment.completion_percentage = min(45, max(10, int((valid_count / total_reqs) * 50)))
                else:
                    assignment.completion_percentage = 10
                assignment.save(update_fields=['status', 'completion_percentage'])

            try:
                cust_id_str = str(assignment.customer.id) if assignment.customer else ''
                log_action(
                    None,
                    'save_draft',
                    'FormAssignment',
                    str(assignment.id),
                    {'customer': cust_id_str, 'status': assignment.status, 'completion_percentage': assignment.completion_percentage},
                    ip=get_client_ip(request),
                    user_agent=get_user_agent(request)
                )
            except Exception as log_err:
                logger.warning(f"Could not log save draft action: {log_err}")

            redirect_url = f'/modules/form/success/?assignment_id={assignment.id}&mode=partial'
            if is_ajax_request(request):
                return JsonResponse({'status': 'success', 'redirect': redirect_url})
            return redirect(redirect_url)

        except Exception as e:
            logger.exception(f"Unexpected error in form_submission_view (partial draft): {e}")
            if is_ajax_request(request):
                return JsonResponse({'error': f'Salvataggio bozza fallito: {str(e)}'}, status=500)
            return redirect(f'/modules/form/success/?assignment_id={assignment.id}&mode=partial')

    # Final Complete Submission
    awareness_accepted = request.POST.get('awareness_declaration') in ('true', '1', 'on', True)
    if request.POST.get('action_type') == 'complete' and not awareness_accepted:
        if is_ajax_request(request):
            return JsonResponse({'error': 'La dichiarazione di consapevolezza documentale è obbligatoria per l\'invio definitivo.'}, status=400)
        messages.error(request, 'È necessario confermare la dichiarazione di consapevolezza prima di inviare i documenti.')
        return redirect(f'/modules/form/{assignment.id}/summary/')

    try:
        assignment.status = 'submitted'
        assignment.submission_date = timezone.now()
        assignment.completion_percentage = 50
        assignment.save()

        try:
            AwarenessDeclaration.objects.create(
                form_assignment=assignment,
                declaration_text="Dichiarazione di consapevolezza: avvenuta trasmissione di tutti i documenti e le informazioni in possesso per la lavorazione del prodotto da parte di Etichub",
                accepted=True,
                acceptance_ip=get_client_ip(request),
                acceptance_user_agent=get_user_agent(request),
                customer_name_declared=request.POST.get('customer_name', '')
            )
        except Exception as decl_err:
            logger.warning(f"Could not create awareness declaration on submit: {decl_err}")

        try:
            recipient_email = assignment.customer.email if (assignment.customer and assignment.customer.email) else 'regolatorio@etichub.com'
            NotificationLog.objects.create(
                notification_type='form_submitted',
                recipient_email=recipient_email,
                status='sent'
            )
        except Exception as notif_err:
            logger.warning(f"Could not create notification log on submit: {notif_err}")

        try:
            nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
            client_name = safe_get_form_data(assignment.form_data, 'client_name') or (assignment.customer.nas_folder_name if assignment.customer else '_generic')
            project_name = safe_get_form_data(assignment.form_data, 'project_name') or ''
            nas_project_path = str(safe_join_paths(nas_base, client_name, project_name))
            os.makedirs(nas_project_path, exist_ok=True)
            pdf_path = str(safe_join_paths(nas_project_path, 'Report_Ricezione_Documenti.pdf'))
            generate_form_receipt_pdf(assignment.form_template, assignment, pdf_path, client_ip=get_client_ip(request))
        except Exception as e:
            logger.warning(f"Could not generate PDF receipt on assignment submit: {e}")

        try:
            cust_id_str = str(assignment.customer.id) if assignment.customer else ''
            log_action(
                None,
                'submit',
                'FormAssignment',
                str(assignment.id),
                {'customer': cust_id_str},
                ip=get_client_ip(request),
                user_agent=get_user_agent(request)
            )
        except Exception as log_err:
            logger.warning(f"Could not log submit action: {log_err}")

        if is_ajax_request(request):
            return JsonResponse({'status': 'success', 'redirect': f'/modules/form/success/?assignment_id={assignment.id}&mode=complete'})
        return redirect(f'/modules/form/success/?assignment_id={assignment.id}&mode=complete')

    except Exception as e:
        logger.exception(f"Unexpected error in form_submission_view: {e}")
        if is_ajax_request(request):
            return JsonResponse({'error': f'Invio fallito: {str(e)}'}, status=500)
        return redirect(f'/modules/form/success/?assignment_id={assignment.id}&mode=complete')


@require_http_methods(["POST"])
def published_form_submit(request, form_id):
    """Submit a published form with document availability tracking."""
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
            customer_display = f"{form.customer.first_name} {form.customer.last_name or ''}".strip() if form.customer else 'Generic'
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

        steps = list(form.formstep_set.all().prefetch_related(
            Prefetch('formelement_set', queryset=FormElement.objects.order_by('order')),
            Prefetch('documentrequirement_set', queryset=DocumentRequirement.objects.order_by('order'))
        ).order_by('order'))

        if not steps:
            logger.info(f'No form steps found for form {form_id} in published_form_submit')

        all_requirements = []
        for step in steps:
            for doc in step.documentrequirement_set.all():
                all_requirements.append({
                    'id': str(doc.id),
                    'name': doc.name,
                    'required': doc.required,
                    'destination_subfolder': doc.destination_subfolder or ''
                })
            for elem in step.formelement_set.all():
                if elem.element_type == 'doc_upload':
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

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else ''
                safe_filename = f"{secrets.token_hex(4)}_{timestamp}.{ext}"

                dest_subfolder = requirement['destination_subfolder']
                file_path_dest = os.path.join(nas_project_path, dest_subfolder)
                os.makedirs(file_path_dest, exist_ok=True)

                file_full_path = os.path.join(file_path_dest, safe_filename)

                with tempfile.NamedTemporaryFile(delete=False, dir=file_path_dest) as tmp:
                    for chunk in uploaded_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                os.replace(tmp_path, file_full_path)

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

        form_fields = []
        for step in steps:
            for elem in step.formelement_set.all():
                if elem.element_type not in ('doc_upload', 'separator', 'text_info'):
                    elem_id = str(elem.id)
                    val = request.POST.get(f'element_{elem_id}', '').strip()
                    label = elem.config.get('label') or elem.element_type
                    if val:
                        form_fields.append({
                            'label': label,
                            'value': val,
                            'type': elem.element_type
                        })

        save_manifest_atomic(manifest_path, manifest)

        try:
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
                'name': f"{form.customer.first_name} {form.customer.last_name or ''}".strip() if form.customer else 'Non specificato',
                'code': form.customer.code if form.customer else '—',
                'email': form.customer.email if form.customer else '—',
                'phone': form.customer.phone if form.customer else '—',
                'vat': (getattr(form.customer, 'vat_number', '') or getattr(form.customer, 'fiscal_code', '') or '—') if form.customer else '—'
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
            logger.error(f"Error generating submission PDF: {pdf_err}", exc_info=True)

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
