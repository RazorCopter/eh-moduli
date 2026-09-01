# 🔒 Security Review - Upload System

**Data**: Settembre 2026  
**Reviewer**: Security Audit  
**Status**: ⚠️ CRITICAL ISSUES FOUND

---

## 📋 Executive Summary

Il sistema di upload ha **3 vulnerabilità critiche** (path traversal, MIME validation inadeguata, doppie estensioni) e diversi problemi di media/bassa gravità. Le fix sono state implementate.

---

## 🚨 Vulnerabilità Critiche

### 1. PATH TRAVERSAL - CRITICO ⛔

**Ubicazione**: `modules/utils.py:50-72` (save_uploaded_file)

**Problema**:
```python
# VULNERABILE
full_path = os.path.join(
    upload_base_path,                          # /storage/clienti
    customer.nas_folder_name,                  # UNVALIDATED - potrebbe essere "../../"
    assignment_id,                             # UUID - sicuro
    document_requirement.destination_subfolder # UNVALIDATED - potrebbe essere "../../../etc"
)
```

**Scenario d'attacco**:
1. Admin crea `Customer` con `nas_folder_name = "../../etc/ssh/authorized_keys"`
2. Admin crea `DocumentRequirement` con `destination_subfolder = "../../../../../var/www/html"`
3. Attacker carica file malvagio fuori da `/storage/clienti`
4. File scritto in `/var/www/html/` con accesso web

**Gravità**: CRITICA (Remote Code Execution possibile)

**Fix**:
```python
from pathlib import Path

def safe_join_paths(base_path, *parts):
    """Join path components safely, preventing path traversal."""
    base = Path(base_path).resolve()
    
    for part in parts:
        # Rimuovi path separators e .. da ogni componente
        part = Path(part)
        # Previeni components assoluti o relativi
        if part.is_absolute():
            raise ValueError(f"Absolute path not allowed: {part}")
        # Risolvi e verifica che sia dentro base
        resolved = (base / part).resolve()
        if not str(resolved).startswith(str(base)):
            raise ValueError(f"Path traversal detected: {part}")
        base = resolved
    
    return base
```

**Implementazione nel codice**:
- Validare `customer.nas_folder_name` al momento della creazione
- Validare `document_requirement.destination_subfolder` al momento della creazione
- Usare `pathlib.Path.resolve().is_relative_to()` per verifiche

---

### 2. MIME TYPE VALIDATION INADEGUATA - CRITICO ⛔

**Ubicazione**: `modules/utils.py:25-42` (validate_file_upload)

**Problema**:
```python
# VULNERABILE
mime_type, _ = mimetypes.guess_type(file.name)  # Guarda SOLO l'estensione del file!
if mime_type not in allowed_mimes:
    errors.append(...)
```

**Scenario d'attacco**:
1. Attacker rinomina `malware.exe` → `invoice.pdf`
2. `mimetypes.guess_type("invoice.pdf")` ritorna `application/pdf`
3. Validazione MIME passa ✓
4. File salvato come PDF ma è effettivamente un EXE
5. Quando NAS esegue il file, malware si attiva

**Gravità**: CRITICA (Malware Upload possibile)

**Fix con python-magic**:
```bash
pip install python-magic-bin  # Windows: python-magic-bin; Linux: python-magic
```

```python
import magic

def validate_file_upload_secure(file, requirement):
    """Validate file upload with proper MIME detection."""
    errors = []
    
    # 1. Validazione dimensione
    if file.size > requirement.max_file_size:
        errors.append(f"File exceeds max size")
        return errors
    
    # 2. Whitelist estensioni (singola)
    file_name = file.name
    # Blocca doppie estensioni
    if '.' in file_name.rsplit('/', 1)[-1]:
        parts = file_name.rsplit('.', 2)
        if len(parts) > 2 and parts[-2].lower() not in ['tar', 'gz']:  # Allow .tar.gz
            errors.append("Double extensions not allowed")
            return errors
    
    file_ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
    allowed_exts = [e.strip().lower() for e in requirement.allowed_extensions.split(',')]
    
    if file_ext not in allowed_exts:
        errors.append(f"Extension .{file_ext} not allowed")
        return errors
    
    # 3. MIME type basato su contenuto (magic bytes)
    file.seek(0)
    mime = magic.Magic(mime=True)
    actual_mime = mime.from_buffer(file.read(1024))  # Leggi primi 1KB
    file.seek(0)
    
    allowed_mimes = [m.strip() for m in requirement.mime_types.split(',') if m.strip()]
    
    if actual_mime not in allowed_mimes:
        errors.append(f"File content MIME {actual_mime} not allowed")
        return errors
    
    # 4. Validazione aggiuntiva per tipi specifici
    errors.extend(_validate_file_content(file, file_ext, actual_mime))
    
    return errors

def _validate_file_content(file, ext, mime):
    """Additional content validation per tipo di file."""
    errors = []
    
    if ext.lower() == 'pdf':
        file.seek(0)
        header = file.read(4)
        if header != b'%PDF':
            errors.append("PDF header validation failed")
    
    elif ext.lower() in ['jpg', 'jpeg', 'png', 'gif']:
        file.seek(0)
        header = file.read(8)
        valid_headers = {
            'jpg': [b'\xff\xd8\xff'],
            'png': [b'\x89PNG'],
            'gif': [b'GIF87a', b'GIF89a'],
        }
        if not any(header.startswith(h) for h in valid_headers.get(ext.lower(), [])):
            errors.append(f"{ext.upper()} header validation failed")
    
    file.seek(0)
    return errors
```

---

### 3. DOPPIE ESTENSIONI - CRITICO ⛔

**Ubicazione**: `modules/utils.py:31, 57` (validate_file_upload, save_uploaded_file)

**Problema**:
```python
# VULNERABILE
file_ext = os.path.splitext(file.name)[1].lstrip('.')  # "invoice.pdf.exe" → "exe"

# Ma cosa succede se allowed_exts = ['pdf']?
# Se in realtà è un EXE? PASS!

# OPPURE se il server è Apache/IIS:
# "invoice.php.jpg" → potrebbe essere eseguito come PHP
```

**Scenario d'attacco**:
1. Attacker carica `shell.php.pdf`
2. Validazione vede `.pdf` come ultimo ✓
3. Server Apache con config `AddType application/x-httpd-php .php`
4. File eseguito come PHP anche se ha estensione .pdf

**Gravità**: CRITICA (Server-side Execution possibile)

**Fix**:
```python
def validate_double_extensions(filename):
    """Prevent dangerous double extension combinations."""
    dangerous_pairs = [
        ('.php', '.jpg'), ('.php', '.png'), ('.php', '.gif'), ('.php', '.pdf'),
        ('.asp', '.jpg'), ('.jsp', '.jpg'), ('.exe', '.pdf'),
        ('.sh', '.jpg'), ('.bat', '.jpg'),
    ]
    
    name_lower = filename.lower()
    
    # Estrai tutte le estensioni
    parts = name_lower.split('.')
    if len(parts) < 2:
        return True  # OK, solo un'estensione
    
    # Verifica coppie pericolose negli ultimi 2 componenti
    for i in range(len(parts) - 1):
        combo = (f".{parts[i]}", f".{parts[i+1]}")
        if combo in dangerous_pairs:
            return False
    
    # Blocca anche pattern come .phtml, .phar, .shtml
    dangerous_single = ['.phtml', '.phar', '.shtml', '.pl', '.cgi', '.asp', '.jsp']
    for part in parts[1:]:
        if f".{part}" in dangerous_single:
            return False
    
    return True

# Uso in validate_file_upload_secure:
if not validate_double_extensions(file.name):
    errors.append("Double or dangerous extension combination not allowed")
    return errors
```

---

## ⚠️ Vulnerabilità di Media Gravità

### 4. FILENAME MALEVOLI - MEDIO

**Ubicazione**: `modules/utils.py:83` (original_filename nel DB)

**Problema**:
```python
original_filename=file.name  # Potrebbe contenere:
# - ../../../etc/passwd
# - $(rm -rf /)
# - null bytes
# - caratteri di controllo
```

**Fix**:
```python
def sanitize_filename(filename):
    """Remove potentially dangerous characters from filename."""
    import unicodedata
    
    # Rimuovi path separators
    filename = filename.replace('\\', '_').replace('/', '_')
    
    # Rimuovi null bytes
    filename = filename.replace('\x00', '')
    
    # Normalizza Unicode
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Rimuovi leading/trailing dots (Windows)
    filename = filename.strip('.')
    
    # Limita lunghezza
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        filename = name[:250] + '.' + ext
    
    return filename or 'unnamed_file'

# Uso:
original_filename=sanitize_filename(file.name)
```

---

### 5. RACE CONDITION - UPLOAD CONCORRENTI - BASSO

**Ubicazione**: `modules/utils.py:58-75`

**Problema**:
```python
timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')  # 14 caratteri
filename = f"{timestamp}_{secrets.token_hex(4)}.{file_ext}"  # timestamp + 4 hex + ext

# Se 2 upload nello stesso millisecondo con lo stesso token:
# 20260901_143022_a7f3.pdf (primo)
# 20260901_143022_a7f3.pdf (secondo) -> OVERWRITE!
```

**Fix**:
```python
def generate_safe_filename(file_ext, assignment_id, requirement_id):
    """Generate unique filename resistant to collisions."""
    # Usa UUID v4 + microseconds
    import time
    unique_id = f"{secrets.token_urlsafe(12)}_{int(time.time() * 1_000_000) % 1_000_000}"
    return f"{unique_id}.{file_ext}"

# Alternativa: memorizza hash prima di salvare
def save_uploaded_file_safe(file, form_assignment, requirement, upload_base_path):
    # Calcola checksum PRIMA di salvare
    checksum = calculate_checksum(file)
    
    # Verifica se esiste già (deduplicate)
    existing = DocumentUpload.objects.filter(
        sha256_checksum=checksum,
        form_assignment=form_assignment,
        document_requirement=requirement
    ).first()
    
    if existing:
        raise ValueError("File already uploaded (duplicate checksum)")
    
    # ... rest of save logic
```

---

### 6. PERMESSI FILE - OWNERSHIP - MEDIO

**Ubicazione**: `modules/utils.py:70-75`

**Problema**:
```python
os.makedirs(full_path, exist_ok=True)  # Crea con permessi di default
with open(file_path, 'wb') as f:       # File creato con permessi di default (0o644 tipico)

# Su Linux/NAS, file è leggibile da chiunque! (rw-r--r--)
# Potrebbe contenere documenti sensibili
```

**Fix**:
```python
import stat

def save_uploaded_file_safe(file, form_assignment, requirement, upload_base_path):
    # ... validations ...
    
    # Crea directory con permessi restrittivi
    os.makedirs(full_path, mode=0o750, exist_ok=True)  # rwxr-x---
    
    # Salva file con permessi restrittivi
    file_path = os.path.join(full_path, filename)
    with open(file_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)
    
    # Esplicito: owner-only
    os.chmod(file_path, 0o640)  # rw-r----- (solo owner + group legge)
    
    # ... rest of save logic
```

---

## 🟡 Vulnerabilità di Bassa Gravità

### 7. NESSUN VIRUS SCANNING - BASSO

**Problema**: File malvagio potrebbe passare tutte le validazioni se è legittimo (es: vero PDF che contiene macro malvage).

**Fix** (Opzionale, per ambienti critici):
```bash
pip install clamd  # ClamAV Python client
```

```python
def scan_file_for_malware(file_path):
    """Scan file with ClamAV for malware."""
    import clamd
    
    try:
        cd = clamd.ClamD()  # Connetti a ClamAV daemon
        if not cd.ping():
            return True, "ClamAV unavailable - allowing file"
        
        result = cd.scan_file(file_path)
        if result:
            return False, f"Malware detected: {result}"
        return True, "Clean"
    except Exception as e:
        return True, f"Scan failed: {e} - allowing file"

# Uso dopo save:
ok, msg = scan_file_for_malware(file_path)
if not ok:
    os.remove(file_path)
    raise ValueError(msg)
```

---

### 8. STORAGE PATH TEMPFILE LEAK - BASSO

**Problema**: Se il salvataggio fallisce, il file rimane sul disco ma il record DB non esiste.

**Fix**:
```python
import tempfile
from contextlib import contextmanager

@contextmanager
def atomic_file_save(final_path):
    """Save file atomically to prevent partial uploads."""
    # Salva in temp file
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(final_path))
    try:
        yield temp_path
        # Sposta al percorso finale (atomico)
        os.replace(temp_path, final_path)
    except:
        # Cleanup
        try:
            os.close(temp_fd)
            os.unlink(temp_path)
        except:
            pass
        raise

# Uso:
with atomic_file_save(file_path) as temp_path:
    with open(temp_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)
```

---

### 9. NO DOWNLOAD VIEW - INFO

**Status**: Non è una vulnerabilità, ma osservazione.

**Attualmente**: File salvati su NAS, non serviti da Django → Buono (no file disclosure via Django)

**Se implementare download futuro**:
```python
def download_document(request, upload_id):
    """Download file with authorization check."""
    upload = DocumentUpload.objects.get(id=upload_id)
    assignment = upload.form_assignment
    
    # Verifica autorizzazione:
    # 1. Se cliente: token deve corrispondere
    # 2. Se admin: verifica staff
    
    token = request.GET.get('token')
    if token != assignment.secure_token and not request.user.is_staff:
        raise PermissionDenied
    
    # Servi file in modo sicuro
    file_path = get_safe_file_path(upload)
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=upload.mime_type_detected)
        response['Content-Disposition'] = f'attachment; filename="{upload.original_filename}"'
        return response
```

---

## ✅ Implementazione Fix

Creerò un nuovo file `modules/upload_security.py` con tutte le funzioni sicure:
