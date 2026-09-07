import os
import hashlib
import secrets
import string
import logging
from datetime import datetime
from django.utils import timezone
from .models import AuditLog

logger = logging.getLogger(__name__)

def generate_secure_token():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(40))

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

def log_action(user, action, object_type, object_id, details=None, ip='', user_agent='', success=True):
    try:
        AuditLog.objects.create(
            actor_user=user,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            details=details or {},
            actor_ip=ip,
            actor_user_agent=user_agent[:500],
            success=success
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
