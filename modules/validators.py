"""
Validators for model fields to prevent security issues.
"""

import re
import mimetypes
from typing import List
from django.core.exceptions import ValidationError


def validate_folder_name(value):
    """
    Validate folder name to prevent path traversal.

    Rejects:
    - Parent directory references (..)
    - Absolute paths
    - Special characters and spaces
    - Control characters
    """
    if not value:
        raise ValidationError("Folder name cannot be empty")

    if len(value) > 100:
        raise ValidationError("Folder name too long (max 100 characters)")

    # Reject parent directory references
    if '..' in value:
        raise ValidationError("Folder name cannot contain '..'")

    # Reject absolute paths
    if value.startswith('/') or value.startswith('\\'):
        raise ValidationError("Folder name cannot be absolute path")

    # Reject drive letters (Windows)
    if ':' in value:
        raise ValidationError("Folder name cannot contain drive letters")

    # Allow only alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9._\-]+$', value):
        raise ValidationError(
            "Folder name can only contain letters, numbers, dots, hyphens, and underscores"
        )

    # Reject special cases
    if value in ['.', '..', 'etc', 'sys', 'bin', 'boot', 'root']:
        raise ValidationError(f"Folder name '{value}' is reserved")

    return value


def validate_subfolder_name(value):
    """
    Validate subfolder destination to prevent path traversal.

    Similar to folder name but slightly less restrictive (allows more nesting).
    """
    if not value:
        raise ValidationError("Subfolder name cannot be empty")

    if len(value) > 255:
        raise ValidationError("Subfolder name too long (max 255 characters)")

    # Reject parent directory references
    if '..' in value:
        raise ValidationError("Subfolder cannot contain '..'")

    # Reject absolute paths
    if value.startswith('/') or value.startswith('\\'):
        raise ValidationError("Subfolder cannot be absolute path")

    # Reject drive letters (Windows)
    if ':' in value:
        raise ValidationError("Subfolder cannot contain drive letters")

    # Allow nested folders with slashes, but validate each component
    components = value.replace('\\', '/').split('/')
    for component in components:
        if not component:
            raise ValidationError("Subfolder cannot have empty components (e.g., 'foo//bar')")

        if not re.match(r'^[a-zA-Z0-9._\-]+$', component):
            raise ValidationError(
                f"Subfolder component '{component}' can only contain "
                "letters, numbers, dots, hyphens, and underscores"
            )

    return value


def validate_allowed_extensions(value):
    """
    Validate allowed extensions list.

    Examples:
    - Valid: "pdf,doc,docx" or "jpg,png,gif"
    - Invalid: ".pdf,.doc" or "pdf, doc" (with spaces)
    """
    if not value:
        raise ValidationError("At least one extension must be allowed")

    extensions = [ext.strip().lower() for ext in value.split(',')]

    if not extensions:
        raise ValidationError("Invalid extension list format")

    dangerous_extensions = [
        'exe', 'bat', 'cmd', 'com', 'scr', 'vbs', 'js', 'jar',
        'zip', 'rar', '7z', 'cab', 'msi', 'dll', 'sys', 'drv',
        'asp', 'aspx', 'jsp', 'php', 'phtml', 'shtml', 'cgi', 'pl',
        'sh', 'bash', 'py', 'rb', 'pl'
    ]

    for ext in extensions:
        # Check format
        if not ext:
            raise ValidationError("Empty extension in list")

        if len(ext) > 20:
            raise ValidationError(f"Extension '{ext}' too long")

        # Allow only alphanumeric
        if not re.match(r'^[a-z0-9]+$', ext):
            raise ValidationError(f"Invalid characters in extension: {ext}")

        # Warn about executable extensions (but don't block - admin might need them)
        if ext in dangerous_extensions:
            pass  # You might want to log this warning

    return value


def validate_mime_types(value):
    """
    Validate MIME types list format.

    Examples:
    - Valid: "application/pdf,application/msword"
    - Invalid: "pdf,doc" or missing slashes
    """
    if not value:
        raise ValidationError("At least one MIME type must be allowed")

    mimes = [mime.strip() for mime in value.split(',')]

    if not mimes:
        raise ValidationError("Invalid MIME type list format")

    # Standard MIME type format is type/subtype
    mime_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_+\.]*/'
    mime_pattern += r'[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_+\.]*(\+[a-z]+)?$'

    for mime in mimes:
        if not mime:
            raise ValidationError("Empty MIME type in list")

        if not re.match(mime_pattern, mime):
            raise ValidationError(
                f"Invalid MIME type format: '{mime}'. "
                f"Expected format: type/subtype (e.g., 'application/pdf')"
            )

    return value


COMMON_EXTENSION_MIMES = {
    # Documents & Office
    'pdf': ['application/pdf', 'application/x-pdf'],
    'doc': ['application/msword'],
    'docx': [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/zip',
        'application/x-zip-compressed',
    ],
    'xls': [
        'application/vnd.ms-excel',
        'application/msexcel',
        'application/x-msexcel',
        'application/x-ms-excel',
    ],
    'xlsx': [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/zip',
        'application/x-zip-compressed',
    ],
    'ppt': ['application/vnd.ms-powerpoint'],
    'pptx': [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-powerpoint',
        'application/zip',
        'application/x-zip-compressed',
    ],
    'odt': ['application/vnd.oasis.opendocument.text'],
    'ods': ['application/vnd.oasis.opendocument.spreadsheet'],
    'odp': ['application/vnd.oasis.opendocument.presentation'],
    'rtf': ['application/rtf', 'text/rtf'],
    'txt': ['text/plain'],
    'csv': [
        'text/csv',
        'text/plain',
        'application/csv',
        'text/x-csv',
        'application/vnd.ms-excel',
    ],
    'xml': ['application/xml', 'text/xml'],
    'json': ['application/json', 'text/plain'],

    # Images
    'jpg': ['image/jpeg', 'image/pjpeg'],
    'jpeg': ['image/jpeg', 'image/pjpeg'],
    'png': ['image/png'],
    'gif': ['image/gif', 'image/x-gif'],
    'webp': ['image/webp'],
    'svg': ['image/svg+xml', 'text/xml', 'text/plain'],
    'tif': ['image/tiff'],
    'tiff': ['image/tiff'],
    'bmp': ['image/bmp', 'image/x-ms-bmp'],
    'ico': ['image/x-icon', 'image/vnd.microsoft.icon'],

    # Archives
    'zip': [
        'application/zip',
        'application/x-zip-compressed',
        'multipart/x-zip',
        'application/octet-stream',
    ],
    'rar': [
        'application/vnd.rar',
        'application/x-rar-compressed',
        'application/octet-stream',
    ],
    '7z': [
        'application/x-7z-compressed',
        'application/octet-stream',
    ],
    'tar': ['application/x-tar', 'application/tar'],
    'gz': ['application/gzip', 'application/x-gzip'],
}


def get_mimes_for_extensions(extensions_str: str) -> List[str]:
    """
    Given a comma-separated string of extensions (e.g. 'pdf,docx,xlsx'),
    returns a list of matching valid MIME types.
    Uses COMMON_EXTENSION_MIMES and falls back to python's mimetypes module.
    """
    if not extensions_str:
        return []

    mimes: List[str] = []
    for ext in extensions_str.split(','):
        ext = ext.strip().lower().lstrip('.')
        if not ext:
            continue
        if ext in COMMON_EXTENSION_MIMES:
            for m in COMMON_EXTENSION_MIMES[ext]:
                if m not in mimes:
                    mimes.append(m)
        else:
            guessed, _ = mimetypes.guess_type(f"file.{ext}")
            if guessed and guessed not in mimes:
                mimes.append(guessed)
    return mimes

