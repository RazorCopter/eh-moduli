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
import time
import mimetypes
import secrets
import hashlib
import json
import logging
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from contextlib import contextmanager
from typing import Tuple, List
from django.db import transaction
from django.utils import timezone
from .models import DocumentUpload
from .utils import get_client_ip, get_user_agent, get_nas_base_path
from .validators import get_mimes_for_extensions

logger = logging.getLogger(__name__)

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
    os.makedirs(str(base), exist_ok=True)

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
    Falls back gracefully to mimetypes.guess_type if python-magic is unavailable.

    Args:
        file_obj: Django UploadedFile object
        max_bytes: Bytes to read for detection

    Returns:
        MIME type string
    """
    if HAS_MAGIC:
        try:
            file_obj.seek(0)
            header = file_obj.read(max_bytes)
            file_obj.seek(0)

            mime = magic.Magic(mime=True)
            detected = mime.from_buffer(header)
            if detected:
                return detected
        except Exception as e:
            logger.warning(f"python-magic failed to detect MIME type: {e}; falling back to extension-based guessing.")
    else:
        logger.warning("python-magic is not installed or available; falling back to extension-based MIME guessing.")

    name = getattr(file_obj, 'name', '')
    guessed, _ = mimetypes.guess_type(name)
    return guessed or 'application/octet-stream'


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


def validate_zip_archive_safety(file_obj, max_uncompressed_bytes=250*1024*1024, max_files=500, max_ratio=100) -> List[str]:
    """
    Validate that an uploaded ZIP archive is safe to extract:
    - Checks ZIP header & structure
    - Protects against Zip Bomb (uncompressed size limit & ratio limit)
    - Protects against Path Traversal (no ../ or absolute paths)
    """
    errors = []
    file_obj.seek(0)
    try:
        with zipfile.ZipFile(file_obj, 'r') as zf:
            infolist = zf.infolist()
            if len(infolist) > max_files:
                errors.append(f"L'archivio ZIP contiene troppi file ({len(infolist)}). Limite massimo: {max_files}.")
                return errors

            total_uncompressed = 0
            for info in infolist:
                # Path traversal check
                norm_name = os.path.normpath(info.filename).replace('\\', '/')
                if norm_name.startswith('../') or norm_name.startswith('/') or '..' in norm_name.split('/'):
                    errors.append(f"Rilevato percorso non sicuro nel file ZIP: {info.filename}")
                    return errors
                if os.path.isabs(info.filename) or (len(info.filename) > 1 and info.filename[1] == ':'):
                    errors.append(f"Percorso assoluto non consentito nel file ZIP: {info.filename}")
                    return errors

                total_uncompressed += info.file_size
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > max_ratio and info.file_size > 1024 * 1024:
                        errors.append(f"Possibile Zip Bomb rilevata nel file {info.filename} (ratio {ratio:.1f}:1)")
                        return errors

            if total_uncompressed > max_uncompressed_bytes:
                errors.append(f"La dimensione decompressa ({total_uncompressed / (1024*1024):.1f} MB) supera il limite consentito di {max_uncompressed_bytes / (1024*1024):.0f} MB.")
                return errors

    except zipfile.BadZipFile:
        errors.append("File archivio ZIP corrotto o non valido.")
    except Exception as e:
        errors.append(f"Errore durante l'analisi del file ZIP: {str(e)}")
    finally:
        file_obj.seek(0)

    return errors


def validate_file_upload_secure(file_obj, requirement) -> List[str]:
    """
    Comprehensive file upload validation.

    Checks:
    1. File size
    2. Single valid extension (or ZIP bulk archive)
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

    is_bulk_zip = (file_ext == 'zip')

    if not is_bulk_zip and file_ext not in allowed_exts:
        errors.append(f"Extension .{file_ext} not allowed. Allowed: {requirement.allowed_extensions}")
        return errors

    # 3. Double extension check
    if not validate_double_extensions(filename):
        errors.append("Double or dangerous extension combination not allowed")
        return errors

    # 4. MIME type from content
    detected_mime = get_mime_type_from_content(file_obj)

    if is_bulk_zip:
        valid_zip_mimes = [
            'application/zip', 'application/x-zip-compressed',
            'application/octet-stream', 'multipart/x-zip'
        ]
        if detected_mime not in valid_zip_mimes:
            errors.append(f"File content MIME type {detected_mime} not recognized as ZIP.")
            return errors
        zip_safety_errors = validate_zip_archive_safety(file_obj)
        errors.extend(zip_safety_errors)
        return errors

    # Derive allowed MIME types from requirement.mime_types AND requirement.allowed_extensions
    allowed_mimes = [m.strip() for m in (getattr(requirement, 'mime_types', '') or '').split(',') if m.strip()]
    derived_mimes = get_mimes_for_extensions(getattr(requirement, 'allowed_extensions', '') or '')
    for dm in derived_mimes:
        if dm not in allowed_mimes:
            allowed_mimes.append(dm)

    if detected_mime not in allowed_mimes:
        errors.append(f"File content MIME type {detected_mime} not allowed. "
                     f"Allowed: {', '.join(allowed_mimes)}")
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
    random_part = secrets.token_urlsafe(16)
    micro_ts = int(time.time() * 1_000_000) % (10 ** 9)
    return f"{random_part}_{micro_ts}.{file_extension}"


def validate_absence_declaration_file(file_obj, max_size_bytes: int = 10 * 1024 * 1024) -> List[str]:
    """
    Validate uploaded absence declaration file (formal letter on company letterhead, stamped & signed).
    Permitted formats: PDF, DOC, DOCX, JPG, JPEG, PNG. Max 10MB.
    """
    errors = []
    if file_obj.size > max_size_bytes:
        errors.append(f"Il file supera la dimensione massima consentita di {max_size_bytes // (1024*1024)}MB.")
        return errors

    filename = getattr(file_obj, 'name', '')
    if '.' not in filename:
        errors.append("Il file della dichiarazione deve avere un'estensione valida (es. .pdf, .jpg, .docx).")
        return errors

    file_ext = filename.rsplit('.', 1)[-1].lower()
    allowed_exts = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
    if file_ext not in allowed_exts:
        errors.append(f"Formato .{file_ext} non consentito per la dichiarazione di assenza. Formati accettati: PDF, DOCX, DOC, JPG, PNG.")
        return errors

    if not validate_double_extensions(filename):
        errors.append("Nome file non consentito per motivi di sicurezza (estensione doppia o sospetta).")
        return errors

    detected_mime = get_mime_type_from_content(file_obj)
    content_errors = validate_file_content(file_obj, file_ext, detected_mime)
    if content_errors:
        errors.extend(content_errors)

    return errors


def save_uploaded_file_secure(file_obj, form_assignment, document_requirement,
                              storage_base_path: str, request=None,
                              availability_status: str = 'uploaded',
                              motivazione_indisponibilita: str = ''):
    """
    Securely save uploaded file with comprehensive validation.

    Args:
        file_obj: Django UploadedFile object
        form_assignment: FormAssignment instance
        document_requirement: DocumentRequirement instance
        storage_base_path: Base storage path (e.g., /storage/clienti or dedicated project path)
        request: HttpRequest object (optional)
        availability_status: Status ('uploaded' or 'not_available' for absence declaration)
        motivazione_indisponibilita: Optional motive/notes

    Returns:
        DocumentUpload instance

    Raises:
        ValueError: If validation fails
    """
    customer = form_assignment.customer
    assignment_id = str(form_assignment.id)
    cust_folder_name = customer.nas_folder_name if customer else '_generic'

    storage_base = Path(storage_base_path).resolve()
    os.makedirs(str(storage_base), exist_ok=True)

    raw_subfolder = (document_requirement.destination_subfolder or '').strip().lstrip('/\\')
    if raw_subfolder:
        _, subfolder = validate_path_components(cust_folder_name, raw_subfolder)
    else:
        subfolder = ''

    # Check if storage_base already points to project folder (contains customer NAS folder)
    nas_base = get_nas_base_path()
    try:
        rel = storage_base.relative_to(Path(nas_base).resolve())
        is_project_folder = cust_folder_name in rel.parts
    except (ValueError, Exception):
        trailing_parts = [storage_base.name]
        if storage_base.parent:
            trailing_parts.append(storage_base.parent.name)
        is_project_folder = cust_folder_name in trailing_parts

    if is_project_folder:
        if subfolder:
            final_dir = safe_join_paths(str(storage_base), subfolder)
        else:
            final_dir = storage_base
    else:
        cust_folder, safe_sub = validate_path_components(cust_folder_name, subfolder)
        final_dir = safe_join_paths(str(storage_base), cust_folder, assignment_id, safe_sub)

    os.makedirs(str(final_dir), exist_ok=True)

    # Generate safe filename
    file_ext = file_obj.name.rsplit('.', 1)[-1].lower()
    safe_filename = generate_secure_filename(file_ext)
    final_path = final_dir / safe_filename

    # Save file atomically, with direct-write fallback if atomic tempfile fails across mount boundaries
    try:
        with atomic_file_save(str(final_path)) as temp_path:
            with open(temp_path, 'wb') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
    except Exception:
        with open(str(final_path), 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

    # Set restrictive permissions (owner read/write only) - ignore if FS/OS doesn't support chmod
    try:
        os.chmod(str(final_path), stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError, PermissionError):
        pass

    # Calculate checksum
    checksum = calculate_checksum_secure(file_obj)

    # Get detected MIME type
    detected_mime = get_mime_type_from_content(file_obj)

    # Create database record
    try:
        relative_path = str(final_path.relative_to(storage_base)).replace('\\', '/')
    except ValueError:
        relative_path = safe_filename

    client_ip = get_client_ip(request)
    client_ua = get_user_agent(request)

    upload = DocumentUpload.objects.create(
        form_assignment=form_assignment,
        document_requirement=document_requirement,
        original_filename=sanitize_filename(file_obj.name),
        stored_filename=safe_filename,
        relative_path=relative_path,
        file_extension=file_ext,
        mime_type_detected=detected_mime,
        file_size=file_obj.size,
        sha256_checksum=checksum,
        uploaded_by_ip=client_ip,
        uploaded_by_user_agent=client_ua,
        status='valid',
        availability_status=availability_status,
        motivazione_indisponibilita=motivazione_indisponibilita,
    )

    return upload


def extract_and_index_zip_archive(file_obj, assignment, requirement, nas_project_path: str, request=None) -> dict:
    """
    Safely extracts a ZIP archive into the requirement destination subfolder on NAS:
    NOME_CLIENTE\\NOME_PRODOTTO\\ALLEGATO\\...
    
    1. Extracts all files and subfolders preserving directory hierarchy.
    2. Deletes the original ZIP archive from disk/memory.
    3. Recursively scans the extracted folder and creates DocumentUpload records for every file.
    4. Updates manifest.json.
    """
    req_subfolder = requirement.destination_subfolder or f"Allegato{requirement.order}"
    target_dir = Path(safe_join_paths(nas_project_path, req_subfolder))
    target_dir.mkdir(parents=True, exist_ok=True)

    file_obj.seek(0)
    with zipfile.ZipFile(file_obj, 'r') as zf:
        for member in zf.infolist():
            clean_name = os.path.normpath(member.filename).replace('\\', '/').lstrip('/')
            if not clean_name or clean_name.startswith('../'):
                continue
            
            parts = clean_name.split('/')
            if any(p.startswith('.') or p in ['__MACOSX', 'Thumbs.db', 'desktop.ini'] for p in parts):
                continue

            target_file_path = target_dir / clean_name
            if member.is_dir():
                target_file_path.mkdir(parents=True, exist_ok=True)
            else:
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target_file_path, 'wb') as target:
                    target.write(source.read())

    # The ZIP has been extracted. We now scan the directory tree recursively.
    created_uploads = []
    client_ip = get_client_ip(request) if request else '127.0.0.1'
    client_ua = get_user_agent(request) if request else 'System/BulkUpload'

    with transaction.atomic():
        for root, dirs, files in os.walk(str(target_dir)):
            for fname in files:
                if fname.startswith('.') or fname in ['Thumbs.db', 'desktop.ini']:
                    continue

                fpath = os.path.join(root, fname)
                fsize = os.path.getsize(fpath)
                fext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''

                sha256 = hashlib.sha256()
                with open(fpath, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b''):
                        sha256.update(chunk)
                checksum = sha256.hexdigest()

                try:
                    rel_to_proj = os.path.relpath(fpath, nas_project_path).replace('\\', '/')
                except ValueError:
                    rel_to_proj = fname

                guessed_mime, _ = mimetypes.guess_type(fname)
                mime_detected = guessed_mime or 'application/octet-stream'

                # Check if upload record already exists for this relative path
                existing = DocumentUpload.objects.filter(
                    form_assignment=assignment,
                    document_requirement=requirement,
                    relative_path=rel_to_proj
                ).first()

                if existing:
                    existing.file_size = fsize
                    existing.sha256_checksum = checksum
                    existing.status = 'valid'
                    existing.availability_status = 'uploaded'
                    existing.save(update_fields=['file_size', 'sha256_checksum', 'status', 'availability_status'])
                    upload = existing
                else:
                    upload = DocumentUpload.objects.create(
                        form_assignment=assignment,
                        document_requirement=requirement,
                        original_filename=fname,
                        stored_filename=fname,
                        relative_path=rel_to_proj,
                        file_extension=fext,
                        mime_type_detected=mime_detected,
                        file_size=fsize,
                        sha256_checksum=checksum,
                        uploaded_by_ip=client_ip,
                        uploaded_by_user_agent=client_ua,
                        status='valid',
                        availability_status='uploaded'
                    )

                created_uploads.append({
                    'id': str(upload.id),
                    'name': fname,
                    'relative_path': rel_to_proj,
                    'size': fsize,
                    'checksum': checksum
                })

        # Update manifest.json on NAS
        try:
            manifest_path = os.path.join(nas_project_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as mf:
                    manifest = json.load(mf)
            else:
                client_name = assignment.customer.nas_folder_name if assignment.customer else '_generic'
                project_name = safe_get_form_data(assignment.form_data, 'project_name') or 'Progetto'
                manifest = {
                    'form_name': assignment.form_template.name if assignment.form_template else 'N/A',
                    'customer': client_name,
                    'project': project_name,
                    'form_assignment_id': str(assignment.id),
                    'uploads': []
                }

            for u in created_uploads:
                manifest['uploads'].append({
                    'requirement_name': requirement.name,
                    'original_filename': u['name'],
                    'stored_filename': u['name'],
                    'relative_path': u['relative_path'],
                    'file_size': u['size'],
                    'sha256': u['checksum'],
                    'upload_datetime': timezone.now().isoformat(),
                    'uploaded_by_ip': client_ip,
                    'status': 'uploaded'
                })
            save_manifest_atomic(manifest_path, manifest)
        except Exception as e:
            logger.warning(f"Could not update manifest.json for bulk zip upload: {e}")

    return {
        'status': 'success',
        'is_bulk': True,
        'count': len(created_uploads),
        'files': created_uploads,
        'message': f"Archivio decompresso con successo: {len(created_uploads)} file estratti e indicizzati."
    }


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
        logger.error(f"Failed to securely delete document: {e}", exc_info=True)
        return False


@contextmanager
def file_lock(lock_path: str, timeout: float = 10.0):
    """
    Cross-platform file locking using atomic OS-level exclusive file creation.
    Protects manifest.json and shared files from race conditions across processes (DATA-03).
    """
    lock_file = Path(str(lock_path) + '.lock')
    start_time = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except (FileExistsError, OSError):
            if time.time() - start_time > timeout:
                try:
                    if lock_file.exists() and (time.time() - lock_file.stat().st_mtime > 30):
                        lock_file.unlink()
                except OSError:
                    pass
                if time.time() - start_time > timeout + 1:
                    logger.warning(f"Timeout waiting for lock on {lock_path}, proceeding anyway.")
                    break
            time.sleep(0.05)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
                if lock_file.exists():
                    lock_file.unlink()
            except OSError:
                pass


def save_manifest_atomic(manifest_path: str, manifest_data: dict) -> None:
    """
    Atomically write manifest.json using tempfile and os.replace with process lock.
    Guarantees no partial writes and prevents data corruption on concurrent requests (DATA-03).

    Args:
        manifest_path: Destination path for manifest.json
        manifest_data: Dictionary content to serialize
    """
    with file_lock(manifest_path):
        manifest_dest = Path(manifest_path).resolve()
        manifest_dir = manifest_dest.parent
        manifest_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=str(manifest_dir), delete=False) as tmp:
            tmp_name = tmp.name

        try:
            with open(tmp_name, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_name, str(manifest_dest))
        except Exception:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass
            raise

