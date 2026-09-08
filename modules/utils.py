import os
import hashlib
import secrets
import string
import logging
from datetime import datetime
from django.utils import timezone
from .models import AuditLog, generate_secure_token

logger = logging.getLogger(__name__)

def safe_get_form_data(form_data, key, default=None):
    """
    Safely access form_data dictionary with defensive fallback.

    Standardized pattern for all form_data access to prevent KeyError and ensure
    consistent None-safe behavior throughout the codebase.

    Args:
        form_data: The form_data dict (may be None, empty, or valid dict)
        key: The key to retrieve from form_data
        default: Default value if key not found or form_data is None

    Returns:
        Value from form_data[key] or default if not found/None

    Schema of common form_data keys:
        - 'client_name': str | None (NAS folder name or customer code)
        - 'project_name': str | None (Project identifier for NAS structure)
        - 'access_password': str | None (Hashed password for form access)
        - 'form_id': str | None (Form template ID)
        - 'transaction_id': str | None (Transaction/assignment ID)
        - 'submission_datetime': str | None (ISO datetime of submission)
        - 'client_ip': str | None (IP address of submitter)
        - 'name': str | None (Form template name)
        - 'user_agent': str | None (User agent of submitter)
        - 'email': str | None (Customer email)
        - 'phone': str | None (Customer phone)
        - 'vat': str | None (VAT/fiscal code)
        - 'id': str | None (Generic ID field)
        - 'assignment_id': str | None (FormAssignment UUID)
        - 'submission_time': str | None (Alternative datetime field)
        - 'ip': str | None (Alternative IP field)
        - 'ip_address': str | None (Alternative IP field)
        - 'vat_number': str | None (Alternative VAT field)
        - 'fiscal_code': str | None (Alternative fiscal code field)

    Examples:
        >>> safe_get_form_data(None, 'project_name', 'Progetto')
        'Progetto'

        >>> safe_get_form_data({'project_name': 'MyProject'}, 'project_name', 'Progetto')
        'MyProject'

        >>> safe_get_form_data({'client_name': 'test'}, 'project_name', 'N/A')
        'N/A'
    """
    if not form_data:
        return default
    return form_data.get(key, default)

def get_client_ip(request):
    if not request or not hasattr(request, 'META'):
        return '127.0.0.1'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip or '127.0.0.1'

def get_user_agent(request):
    if not request or not hasattr(request, 'META'):
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:500]

def calculate_checksum(file_obj):
    sha256_hash = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def is_ajax_request(request) -> bool:
    """
    Standardized check to determine if an HTTP request is an AJAX or JSON-expecting request.
    """
    if not request:
        return False
    return bool(
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
        or request.GET.get('format') == 'json'
    )

def get_nas_base_path() -> str:
    """Return the configured base NAS path for customer documents."""
    return os.getenv(
        'CUSTOMER_DOCUMENTS_CONTAINER_PATH',
        os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti')
    )

def log_action(user, action, object_type, object_id, details=None, ip='', user_agent='', success=True):
    try:
        # Standardize and validate details payload for JSONField
        if details is None:
            details_payload = {}
        elif isinstance(details, dict):
            details_payload = details
        else:
            details_payload = {'message': str(details)}

        # Canonical action mapping to comply with AuditLog.ACTION_CHOICES and max_length=20
        action_str = str(action).strip() if action else 'view'
        canonical_actions = {'create', 'update', 'delete', 'submit', 'view', 'upload', 'login'}

        if action_str not in canonical_actions:
            # Map common variants to canonical choices while preserving original action in details
            action_lower = action_str.lower()
            if 'create' in action_lower:
                canonical = 'create'
            elif 'delete' in action_lower or 'remove' in action_lower:
                canonical = 'delete'
            elif 'upload' in action_lower:
                canonical = 'upload'
            elif 'submit' in action_lower:
                canonical = 'submit'
            elif 'login' in action_lower or 'logout' in action_lower:
                canonical = 'login'
            else:
                canonical = 'update'

            if 'original_action' not in details_payload:
                details_payload['original_action'] = action_str
            action_str = canonical

        AuditLog.objects.create(
            actor_user=user,
            action=action_str[:20],
            object_type=str(object_type)[:100],
            object_id=str(object_id)[:100],
            details=details_payload,
            actor_ip=ip or '127.0.0.1',
            actor_user_agent=(user_agent or '')[:500],
            success=bool(success)
        )
    except Exception as e:
        logger.error(f"Failed to log action: {e}", exc_info=True)

def delete_document(upload_obj, storage_path):
    try:
        file_path = os.path.join(storage_path, upload_obj.relative_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        upload_obj.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        return False

def generate_storage_path(customer, assignment, requirement):
    return os.path.join(
        customer.nas_folder_name,
        str(assignment.id),
        requirement.destination_subfolder
    )
