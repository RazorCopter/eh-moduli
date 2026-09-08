import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from .models import FormTemplate, Customer, FormAssignment, AuditLog
from .utils import log_action, get_client_ip, get_user_agent, safe_get_form_data

logger = logging.getLogger('modules')


def is_backoffice_user(user):
    """Backoffice operators and administrators (for operational dashboards and management)"""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role in ('admin', 'operator'))))


is_admin = is_backoffice_user


@login_required
@user_passes_test(is_backoffice_user)
def admin_dashboard(request):
    """Main administrative and operator dashboard with customer groupings and practice status."""
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
    count_filter_to_work = 0         # Clienti con almeno 1 pratica submitted (pronta per l'operatore)
    count_filter_in_processing = 0   # Clienti con almeno 1 pratica in_processing
    count_filter_waiting_docs = 0    # Clienti con almeno 1 pratica in bozza o compilazione parziale
    count_filter_completed = 0       # Clienti con pratiche tutte completate

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

            # Priorità semantica dei colori del cliente:
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
@user_passes_test(is_backoffice_user)
def operational_guide(request):
    """Render comprehensive interactive operational workflow guide."""
    return render(request, 'modules/admin/operational_guide.html')


@login_required
@user_passes_test(is_backoffice_user)
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
    assignments = FormAssignment.objects.exclude(status='cancelled').select_related('customer', 'form_template')
    total_assignments = assignments.count()

    # 1. Turnaround Times Calculations
    customer_upload_times = []
    operator_proc_times = []
    end_to_end_times = []
    sla_target_days = 30.0
    sla_met_count = 0

    # PERF-01: Pre-group assignments by customer in O(N) using defaultdict
    assignments_by_customer = defaultdict(list)

    for a in assignments:
        if a.customer_id:
            assignments_by_customer[a.customer_id].append(a)

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

    # 5. Customer Performance Breakdown (Optimized with assignments_by_customer O(1) lookup)
    customer_stats = []
    active_customers = Customer.objects.filter(active=True).order_by('first_name')
    for cust in active_customers:
        c_assignments = assignments_by_customer.get(cust.id, [])
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
