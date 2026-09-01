"""
Secure file upload utilities with comprehensive security checks.

Addresses:
- Path traversal (CVE-class vulnerabilities)
- MIME type spoofing
- Double extensions
- Malicious filenames
- Race conditions
- Permission issues
"""

import os
import re
import stat
import secrets
import hashlib
import tempfile
import unicodedata
from pathlib import Path
from contextlib import contextmanager
from typing import Tuple, List

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


# ============================================================================
# SAFE PATH HANDLING
# ============================================================================

def safe_join_paths(base_path: str, *parts: str) -> Path:
    """
    Safely join path components, preventing path traversal attacks.

    Raises ValueError if any part tries to escape base_path.

    Args:
        base_path: Base directory (must exist and be trusted)
        *parts: Path components to join

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path traversal detected
    """
    base = Path(base_path).resolve()

    if not base.exists():
        raise ValueError(f"Base path does not exist: {base}")

    current = base

    for part in parts:
        if not part:
            continue

        part_str = str(part).strip()

        # Reject absolute paths
        if part_str.startswith('/') or part_str.startswith('\\'):
            raise ValueError(f"Absolute path component not allowed: {part_str}")

        # Reject drive letters (Windows)
        if ':' in part_str:
            raise ValueError(f"Drive letter in path component: {part_str}")

        # Join and resolve
        candidate = (current / part_str).resolve()

        # Verify it's still within base
        try:
            candidate.relative_to(base)
        except ValueError:
            raise ValueError(f"Path traversal detected: {part_str} -> {candidate}")

        current = candidate

    return current


def validate_path_components(customer_folder: str, subfolder: str) -> Tuple[str, str]:
    """
    Validate path components for safety before use.

    Args:
        customer_folder: Customer's NAS folder name
        subfolder: Document requirement subfolder

    Returns:
        Tuple of validated (customer_folder, subfolder)

    Raises:
        ValueError: If components contain dangerous patterns
    """
    danger_patterns = [
        r'\.\.',          # Parent directory
        r'^/',            # Absolute path
        r'[\\]',          # Backslash (Windows path escape)
        r'[:\*\?"<>\|]',  # Invalid filename chars
        r'\x00',          # Null byte
        r'[\r\n]',        # Line breaks
    ]

    for component in [customer_folder, subfolder]:
        for pattern in danger_patterns:
            if re.search(pattern, component):
                raise ValueError(f"Unsafe characters in path component: {component}")

    return customer_folder.strip(), subfolder.strip()


# ============================================================================
# FILENAME SANITIZATION
# ============================================================================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Remove potentially dangerous characters from filename.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Safe filename
    """
    if not filename:
        return 'unnamed_file'

    # Remove directory separators
    filename = filename.replace('\\', '_').replace('/', '_')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove control characters
    filename = ''.join(char for char in filename if not unicodedata.category(char).startswith('C'))

    # Normalize Unicode
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Remove leading/trailing dots and spaces (Windows)
    filename = filename.strip('. ')

    # Enforce max length (preserve extension)
    if len(filename) > max_length:
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            max_name_len = max_length - len(ext) - 1
            filename = name[:max_name_len] + '.' + ext
        else:
            filename = filename[:max_length]

    # Ensure not empty after sanitization
    return filename or 'unnamed_file'


def validate_double_extensions(filename: str) -> bool:
    """
    Prevent dangerous double extension combinations.

    Examples of blocked patterns:
    - .php.jpg (executed as PHP on Apache)
    - .asp.pdf (executed as ASP on IIS)
    - .exe.pdf (executable)

    Args:
        filename: Filename to check

    Returns:
        True if safe, False if dangerous
    """
    dangerous_pairs = [
        ('.php', '.jpg'), ('.php', '.png'), ('.php', '.gif'), ('.php', '.pdf'),
        ('.php', '.txt'), ('.phtml', '.jpg'), ('.shtml', '.jpg'),
        ('.asp', '.jpg'), ('.asp', '.pdf'),
        ('.jsp', '.jpg'), ('.jsp', '.pdf'),
        ('.exe', '.pdf'), ('.exe', '.jpg'),
        ('.sh', '.pdf'), ('.bat', '.pdf'),
    ]

    dangerous_single = [
        '.phtml', '.phar', '.shtml', '.pl', '.cgi', '.asp', '.jsp',
        '.jspx', '.jsw', '.jsv', '.jspf', '.woa', '.wst'
    ]

    name_lower = filename.lower()
    parts = name_lower.split('.')

    if len(parts) < 2:
        return True  # Single extension OK

    # Check dangerous pairs in last 2 components
    if len(parts) >= 2:
        pair = (f".{parts[-2]}", f".{parts[-1]}")
        if pair in dangerous_pairs:
            return False

    # Check dangerous single extensions
    for part in parts[1:]:
        if f".{part}" in dangerous_single:
            return False

    return True


# ============================================================================
# MIME TYPE VALIDATION
# ============================================================================

def get_mime_type_from_content(file_obj, max_bytes: int = 8192) -> str:
    """
    Detect MIME type from file content (magic bytes), not extension.

    Requires: pip install python-magic-bin (Windows) or python-magic (Linux)

    Args:
        file_obj: Django UploadedFile object
        max_bytes: Bytes to read for detection

    Returns:
        MIME type string
    """
    if not HAS_MAGIC:
        return 'application/octet-stream'

    try:
        file_obj.seek(0)
        header = file_obj.read(max_bytes)
        file_obj.seek(0)

        mime = magic.Magic(mime=True)
        return mime.from_buffer(header) or 'application/octet-stream'
    except Exception:
        return 'application/octet-stream'


def validate_file_content(file_obj, file_extension: str, detected_mime: str) -> List[str]:
    """
    Validate file content matches extension and MIME type.

    Args:
        file_obj: Django UploadedFile object
        file_extension: File extension (e.g., 'pdf')
        detected_mime: MIME type detected from content

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    file_obj.seek(0)
    header = file_obj.read(512)
    file_obj.seek(0)

    ext = file_extension.lower()

    # PDF validation
    if ext == 'pdf':
        if not header.startswith(b'%PDF'):
            errors.append("Invalid PDF header")
        if detected_mime != 'application/pdf':
            errors.append(f"MIME mismatch: expected application/pdf, got {detected_mime}")

    # Image validation
    elif ext in ['jpg', 'jpeg']:
        if not header.startswith(b'\xff\xd8\xff'):
            errors.append("Invalid JPEG header")
        if 'image/jpeg' not in detected_mime:
            errors.append(f"MIME mismatch: expected image/jpeg, got {detected_mime}")

    elif ext == 'png':
        if not header.startswith(b'\x89PNG\r\n\x1a\n'):
            errors.append("Invalid PNG header")
        if detected_mime != 'image/png':
            errors.append(f"MIME mismatch: expected image/png, got {detected_mime}")

    elif ext == 'gif':
        if not header.startswith((b'GIF87a', b'GIF89a')):
            errors.append("Invalid GIF header")
        if detected_mime not in ['image/gif', 'image/x-gif']:
            errors.append(f"MIME mismatch: expected image/gif, got {detected_mime}")

    # ZIP-based formats
    elif ext in ['docx', 'xlsx', 'pptx']:
        if not header.startswith(b'PK\x03\x04'):
            errors.append(f"Invalid {ext.upper()} header (not ZIP)")

    return errors


def validate_file_upload_secure(file_obj, requirement) -> List[str]:
    """
    Comprehensive file upload validation.

    Checks:
    1. File size
    2. Single valid extension
    3. No double extensions
    4. MIME type from content (not extension)
    5. Content validation

    Args:
        file_obj: Django UploadedFile object
        requirement: DocumentRequirement model instance

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # 1. Size check
    if file_obj.size > requirement.max_file_size:
        errors.append(f"File exceeds max size of {requirement.max_file_size} bytes")
        return errors

    # 2. Extension validation
    filename = file_obj.name
    if '.' not in filename:
        errors.append("File must have an extension")
        return errors

    file_ext = filename.rsplit('.', 1)[-1].lower()
    allowed_exts = [e.strip().lower() for e in requirement.allowed_extensions.split(',')]

    if file_ext not in allowed_exts:
        errors.append(f"Extension .{file_ext} not allowed. Allowed: {requirement.allowed_extensions}")
        return errors

    # 3. Double extension check
    if not validate_double_extensions(filename):
        errors.append("Double or dangerous extension combination not allowed")
        return errors

    # 4. MIME type from content
    detected_mime = get_mime_type_from_content(file_obj)
    allowed_mimes = [m.strip() for m in requirement.mime_types.split(',') if m.strip()]

    if detected_mime not in allowed_mimes:
        errors.append(f"File content MIME type {detected_mime} not allowed. "
                     f"Allowed: {requirement.mime_types}")
        return errors

    # 5. Content validation
    content_errors = validate_file_content(file_obj, file_ext, detected_mime)
    errors.extend(content_errors)

    return errors


# ============================================================================
# SECURE FILE SAVING
# ============================================================================

@contextmanager
def atomic_file_save(target_path: str):
    """
    Context manager for atomic file saves using temp files.

    Prevents partial/corrupted uploads from reaching final location.

    Args:
        target_path: Final destination path

    Yields:
        Temporary file path to write to
    """
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, mode=0o750, exist_ok=True)

    # Create temp file in same directory (atomicity across filesystems)
    temp_fd, temp_path = tempfile.mkstemp(dir=target_dir)

    try:
        os.close(temp_fd)
        yield temp_path
        # Atomic rename
        os.replace(temp_path, target_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise


def calculate_checksum_secure(file_obj) -> str:
    """
    Calculate SHA-256 checksum of uploaded file.

    Args:
        file_obj: Django UploadedFile object

    Returns:
        Hex string of SHA-256
    """
    file_obj.seek(0)
    sha256_hash = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256_hash.update(chunk)
    file_obj.seek(0)
    return sha256_hash.hexdigest()


def generate_secure_filename(file_extension: str) -> str:
    """
    Generate unique, collision-resistant filename.

    Format: {urlsafe_random}_{microsecond_timestamp}.{ext}

    Args:
        file_extension: File extension without dot

    Returns:
        Safe filename
    """
    import time
    random_part = secrets.token_urlsafe(16)
    micro_ts = int(time.time() * 1_000_000) % (10 ** 9)
    return f"{random_part}_{micro_ts}.{file_extension}"


def save_uploaded_file_secure(file_obj, form_assignment, document_requirement,
                              storage_base_path: str):
    """
    Securely save uploaded file with comprehensive validation.

    Args:
        file_obj: Django UploadedFile object
        form_assignment: FormAssignment instance
        document_requirement: DocumentRequirement instance
        storage_base_path: Base storage path (e.g., /storage/clienti)

    Returns:
        DocumentUpload instance

    Raises:
        ValueError: If validation fails
    """
    from .models import DocumentUpload
    from .utils import get_client_ip, get_user_agent

    customer = form_assignment.customer
    assignment_id = str(form_assignment.id)

    # Validate path components
    cust_folder, subfolder = validate_path_components(
        customer.nas_folder_name,
        document_requirement.destination_subfolder
    )

    # Construct safe paths
    storage_base = Path(storage_base_path).resolve()
    final_dir = safe_join_paths(
        str(storage_base),
        cust_folder,
        assignment_id,
        subfolder
    )

    # Generate safe filename
    file_ext = file_obj.name.rsplit('.', 1)[-1].lower()
    safe_filename = generate_secure_filename(file_ext)
    final_path = final_dir / safe_filename

    # Save file atomically
    with atomic_file_save(str(final_path)) as temp_path:
        with open(temp_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

    # Set restrictive permissions (owner read/write only)
    os.chmod(str(final_path), stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    # Calculate checksum
    checksum = calculate_checksum_secure(file_obj)

    # Get detected MIME type
    detected_mime = get_mime_type_from_content(file_obj)

    # Create database record
    relative_path = str(final_path.relative_to(storage_base))

    upload = DocumentUpload.objects.create(
        form_assignment=form_assignment,
        document_requirement=document_requirement,
        original_filename=sanitize_filename(file_obj.name),
        stored_filename=safe_filename,
        relative_path=relative_path.replace('\\', '/'),
        file_extension=file_ext,
        mime_type_detected=detected_mime,
        file_size=file_obj.size,
        sha256_checksum=checksum,
        uploaded_by_ip=get_client_ip(None),
        uploaded_by_user_agent='',
    )

    return upload


def delete_document_secure(upload_obj, storage_base_path: str) -> bool:
    """
    Securely delete uploaded file with path validation.

    Args:
        upload_obj: DocumentUpload instance
        storage_base_path: Base storage path

    Returns:
        True if successful, False otherwise
    """
    try:
        storage_base = Path(storage_base_path).resolve()
        file_path = safe_join_paths(str(storage_base), upload_obj.relative_path)

        if file_path.exists():
            # Secure deletion (overwrite before delete)
            with open(file_path, 'rb+') as f:
                length = f.seek(0, 2)
                f.seek(0)
                f.write(b'\x00' * length)  # Overwrite with zeros

            file_path.unlink()

        upload_obj.delete()
        return True
    except Exception as e:
        print(f"Failed to securely delete document: {e}")
        return False
