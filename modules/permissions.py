"""
Centralized permission and state validation helpers for EH-Moduli.
Addresses SEC-01, SEC-02, SEC-03, SEC-04.
"""

import logging
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from .models import FormAssignment

logger = logging.getLogger('modules')


def is_staff_or_operator(user) -> bool:
    """Return True if user is authenticated staff, superuser, or backoffice operator/admin."""
    return bool(
        user and user.is_authenticated and (
            user.is_staff or user.is_superuser or
            getattr(user, 'role', '') in ('admin', 'operator')
        )
    )


def is_ajax_request(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')
    )


def validate_assignment_access(request, assignment_id, require_writable=False, allow_password_redirect=False):
    """
    Centralized validation for assignment operations.
    Verifies:
      1. Assignment exists
      2. If assignment has an access password, verifies session grant or staff/operator status
      3. Customer active status (deactivated customers block client access)
      4. Expiry date and state mutability (only draft and in_progress are writable)

    Returns (assignment, error_response). If error_response is not None, return it immediately.
    """
    is_ajax = is_ajax_request(request)

    def error(msg, status_code=403):
        if is_ajax:
            return None, JsonResponse({'error': msg}, status=status_code)
        return None, HttpResponseForbidden(msg)

    try:
        assignment = FormAssignment.objects.select_related('customer', 'form_template').get(id=assignment_id)
    except (FormAssignment.DoesNotExist, ValueError):
        if is_ajax:
            return None, JsonResponse({'error': 'Pratica non trovata.'}, status=404)
        from django.http import Http404
        raise Http404("Pratica non trovata.")

    is_staff = is_staff_or_operator(request.user)

    # Check password/token grant
    token_key = f'assignment_access_{assignment.id}_{assignment.secure_token}'
    legacy_key = f'assignment_access_{assignment.id}'
    has_grant = request.session.get(token_key, False) or request.session.get(legacy_key, False)

    if assignment.has_access_password():
        if not is_staff and not has_grant:
            if allow_password_redirect and not is_ajax and request.method == 'GET':
                from django.shortcuts import redirect
                return None, redirect('get_form_by_token', token=assignment.secure_token)
            logger.warning(
                f"Unauthorized access attempt to password-protected assignment {assignment_id} from IP {request.META.get('REMOTE_ADDR')}"
            )
            return error("Accesso non autorizzato. È richiesta l'autenticazione con password.", 403)
    else:
        # For forms without password, access via token or session or staff is permitted
        pass

    # Customer active check
    if assignment.customer and not assignment.customer.active and not is_staff:
        return error("L'anagrafica cliente associata a questa pratica è disattivata.", 403)

    # State & Writable check
    if require_writable:
        # Expiry check
        if assignment.is_expired():
            return error("Questa pratica è scaduta e non accetta ulteriori modifiche.", 403)

        # Status transition check
        # Only 'draft' and 'in_progress' are writable
        writable_statuses = ('draft', 'in_progress')
        if assignment.status not in writable_statuses:
            return error(
                f"La pratica è in stato '{assignment.get_status_display()}' e non può essere modificata.",
                403
            )

    return assignment, None
