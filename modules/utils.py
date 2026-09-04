import os
import hashlib
import secrets
import string
import mimetypes
from datetime import datetime
from django.utils import timezone
from .models import AuditLog

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

def validate_file_upload(file, requirement):
    errors = []

    if file.size > requirement.max_file_size:
        errors.append(f"File exceeds max size of {requirement.max_file_size} bytes")

    file_ext = os.path.splitext(file.name)[1].lstrip('.').lower()
    allowed_exts = [e.strip().lower() for e in requirement.allowed_extensions.split(',')]
    if file_ext not in allowed_exts:
        errors.append(f"File extension .{file_ext} not allowed. Allowed: {requirement.allowed_extensions}")

    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type:
        allowed_mimes = [m.strip() for m in requirement.mime_types.split(',') if m.strip()]
        if mime_type not in allowed_mimes:
            errors.append(f"MIME type {mime_type} not allowed")

    return errors

def calculate_checksum(file_obj):
    sha256_hash = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def save_uploaded_file(file, form_assignment, document_requirement, upload_base_path):
    from .models import DocumentUpload

    customer = form_assignment.customer
    assignment_id = str(form_assignment.id)
    requirement_id = str(document_requirement.id)

    file_ext = os.path.splitext(file.name)[1].lstrip('.')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{secrets.token_hex(4)}.{file_ext}"

    rel_path = os.path.join(
        customer.nas_folder_name,
        assignment_id,
        document_requirement.destination_subfolder,
        filename
    ).replace('\\', '/')

    full_path = os.path.join(upload_base_path, customer.nas_folder_name, assignment_id,
                           document_requirement.destination_subfolder)
    os.makedirs(full_path, exist_ok=True)

    file_path = os.path.join(full_path, filename)
    with open(file_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)

    checksum = calculate_checksum(file)
    mime_type, _ = mimetypes.guess_type(file.name)

    upload = DocumentUpload.objects.create(
        form_assignment=form_assignment,
        document_requirement=document_requirement,
        original_filename=file.name,
        stored_filename=filename,
        relative_path=rel_path,
        file_extension=file_ext,
        mime_type_detected=mime_type or 'application/octet-stream',
        file_size=file.size,
        sha256_checksum=checksum,
        uploaded_by_ip=get_client_ip(None),
        uploaded_by_user_agent=''
    )

    return upload

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
        print(f"Failed to log action: {e}")

def delete_document(upload_obj, storage_path):
    try:
        file_path = os.path.join(storage_path, upload_obj.relative_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        upload_obj.delete()
        return True
    except Exception as e:
        print(f"Failed to delete document: {e}")
        return False

def generate_storage_path(customer, assignment, requirement):
    return os.path.join(
        customer.nas_folder_name,
        str(assignment.id),
        requirement.destination_subfolder
    )
