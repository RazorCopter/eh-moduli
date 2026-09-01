# 📐 Document Collector - System Architecture

**Version**: 1.0  
**Last Updated**: September 2026  
**Environment**: Django 4.2 + PostgreSQL + Docker + NAS Synology

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Model](#data-model)
4. [Storage Architecture](#storage-architecture)
5. [Request Flow](#request-flow)
6. [Document Lifecycle](#document-lifecycle)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Scalability](#scalability)

---

## System Overview

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENT COLLECTOR SYSTEM                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │   CLIENT LAYER   │              │   ADMIN PANEL    │         │
│  ├──────────────────┤              ├──────────────────┤         │
│  │ Public Form View │              │ Dashboard        │         │
│  │ (no auth)        │              │ Template CRUD    │         │
│  │ Token-based      │              │ Customer Mgmt    │         │
│  │ Security        │              │ (login required) │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
│           │                                  │                   │
│           │ HTTPS/HTTP                       │ HTTPS/HTTP       │
│           └──────────────────┬───────────────┘                   │
│                              │                                    │
│  ┌──────────────────────────▼────────────────────────────┐      │
│  │         APPLICATION LAYER (Django)                   │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ ┌────────────────────────────────────────────────┐  │      │
│  │ │ Views (Public + Admin)                         │  │      │
│  │ │ - form_step_view, upload_document_view         │  │      │
│  │ │ - admin_dashboard, form_template_*             │  │      │
│  │ └────────────────────────────────────────────────┘  │      │
│  │ ┌────────────────────────────────────────────────┐  │      │
│  │ │ Security Layer (upload_security.py)            │  │      │
│  │ │ - Path validation, MIME detection              │  │      │
│  │ │ - Atomic file operations, audit logging        │  │      │
│  │ └────────────────────────────────────────────────┘  │      │
│  │ ┌────────────────────────────────────────────────┐  │      │
│  │ │ ORM (Django Models)                            │  │      │
│  │ │ - 10 models: User, Customer, FormTemplate, ... │  │      │
│  │ └────────────────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────────────────┘      │
│           │                           │                         │
│           │ SQL                       │ File ops               │
│           │                           │                         │
│  ┌────────▼──────────┐   ┌───────────▼──────────┐              │
│  │  DATABASE LAYER   │   │   STORAGE LAYER      │              │
│  ├───────────────────┤   ├──────────────────────┤              │
│  │ PostgreSQL 15     │   │ /storage/clienti     │              │
│  │ (Persisted)       │   │ (NAS - Synology)     │              │
│  └───────────────────┘   └──────────────────────┘              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### System Components

```
DOCUMENT COLLECTOR
│
├─ 🌐 PRESENTATION LAYER
│  ├─ Public Form Interface (HTTP/HTTPS)
│  │  └─ Token-based access (no login)
│  │     ├─ Form display
│  │     ├─ Step navigation
│  │     ├─ File upload widget
│  │     └─ Progress tracking
│  │
│  └─ Admin Panel (HTTP/HTTPS)
│     └─ Authenticated access (login required)
│        ├─ Dashboard (KPIs)
│        ├─ Form template builder
│        ├─ Customer management
│        ├─ Assignment tracking
│        └─ Audit log viewer
│
├─ 🔧 APPLICATION LAYER (Django)
│  ├─ Request Handler
│  │  ├─ URL routing (app/urls.py)
│  │  ├─ Middleware stack
│  │  │  ├─ Security middleware
│  │  │  ├─ Session middleware
│  │  │  ├─ CSRF middleware
│  │  │  └─ Authentication middleware
│  │  └─ Request context
│  │
│  ├─ Views & Controllers
│  │  ├─ modules/views.py (Public)
│  │  │  ├─ get_form_by_token
│  │  │  ├─ form_step_view
│  │  │  ├─ upload_document_view ← CRITICAL SECURITY
│  │  │  ├─ form_summary_view
│  │  │  └─ form_submission_view
│  │  │
│  │  └─ modules/views_admin.py (Admin)
│  │     ├─ admin_dashboard
│  │     ├─ form_template_* (CRUD)
│  │     ├─ customer_* (CRUD)
│  │     └─ assignment_detail
│  │
│  ├─ Security & Validation Layer
│  │  ├─ modules/upload_security.py ⭐
│  │  │  ├─ safe_join_paths (path traversal prevention)
│  │  │  ├─ validate_file_upload_secure (comprehensive checks)
│  │  │  ├─ save_uploaded_file_secure (atomic operations)
│  │  │  └─ delete_document_secure (secure deletion)
│  │  │
│  │  └─ modules/validators.py
│  │     ├─ validate_folder_name
│  │     ├─ validate_subfolder_name
│  │     ├─ validate_allowed_extensions
│  │     └─ validate_mime_types
│  │
│  ├─ Business Logic (utils/models)
│  │  ├─ modules/models.py (10 ORM models)
│  │  ├─ modules/utils.py (helpers)
│  │  │  ├─ log_action (audit logging)
│  │  │  ├─ get_client_ip
│  │  │  └─ get_user_agent
│  │  │
│  │  └─ modules/admin.py (Django admin registration)
│  │
│  └─ Template Rendering
│     ├─ accounts/templates/
│     │  ├─ base.html (base layout)
│     │  └─ login.html
│     │
│     └─ modules/templates/
│        ├─ modules/ (public forms)
│        └─ admin/ (admin panel)
│
├─ 💾 DATA PERSISTENCE LAYER
│  ├─ PostgreSQL Database
│  │  ├─ User table (auth)
│  │  ├─ Customer table (clients)
│  │  ├─ FormTemplate table (forms)
│  │  ├─ FormStep table (steps)
│  │  ├─ DocumentRequirement table (requirements)
│  │  ├─ FormAssignment table (assignments)
│  │  ├─ DocumentUpload table (files metadata)
│  │  ├─ AwarenessDeclaration table (declarations)
│  │  ├─ AuditLog table (audit trail)
│  │  └─ NotificationLog table (email tracking)
│  │
│  └─ Indexes & Queries
│     ├─ secure_token (fast assignment lookup)
│     ├─ customer (fast client lookup)
│     ├─ status (filtering)
│     └─ created_at (temporal queries)
│
└─ 📁 FILE STORAGE LAYER
   ├─ NAS Synology (/storage/clienti)
   │  ├─ /customer_code_1/
   │  │  ├─ /assignment-uuid-1/
   │  │  │  ├─ /documento_identita/
   │  │  │  │  ├─ 20260901_a7f3.pdf
   │  │  │  │  └─ 20260902_b2e4.pdf (superseded)
   │  │  │  │
   │  │  │  └─ /buste_paga/
   │  │  │     ├─ 20260901_c9d1.pdf
   │  │  │     └─ 20260902_e3f5.pdf
   │  │  │
   │  │  └─ /assignment-uuid-2/
   │  │
   │  └─ /customer_code_2/
   │
   └─ Application Data (/app/data)
      ├─ /media/ (temp uploads)
      ├─ /logs/ (application logs)
      └─ /staticfiles/ (CSS, JS)
```

---

## Data Model

### Entity Relationship Diagram

```
┌──────────────┐
│    USER      │
├──────────────┤
│ id (PK)      │
│ username     │◄──────────────┐
│ email        │               │
│ role         │               │
│ is_staff     │               │
│ is_active    │               │
└──────────────┘               │
       ▲                        │ author (FK)
       │                        │
       │                   ┌────┴─────────────────┐
       │                   │                      │
       │              ┌────▼───────────┐   ┌─────▼──────────────┐
       │              │ FORMTEMPLATE   │   │ FORMASSIGNMENT     │
       │              ├────────────────┤   ├────────────────────┤
       │              │ id (UUID)      │   │ id (UUID)          │
       │              │ name           │   │ customer_id (FK)◄──┼────┐
       │              │ version        │   │ form_template_id◄──┼────┤
       │              │ status         │   │ secure_token       │    │
       │              │ intro_text     │   │ assignment_date    │    │
       │              │ privacy_text   │   │ expiry_date        │    │
       │              │ created_at     │   │ status             │    │
       │              └────┬───────────┘   │ completion_%       │    │
       │                   │               │ last_access_date   │    │
       │                   │               │ submission_date    │    │
       │                   │               └────┬───────────────┘    │
       │                   │                    │                    │
       │              ┌────▼─────────────┐      │                    │
       │              │  FORMSTEP        │      │                    │
       │              ├──────────────────┤      │                    │
       │              │ id (UUID)        │      │                    │
       │              │ form_template_id│◄─────┘                    │
       │              │ (FK)            │                            │
       │              │ title           │                            │
       │              │ order           │                            │
       │              │ required        │                            │
       │              │ active          │                            │
       │              └────┬────────────┘                            │
       │                   │                                         │
       │              ┌────▼──────────────────┐                      │
       │              │ DOCUMENTREQUIREMENT   │                      │
       │              ├───────────────────────┤                      │
       │              │ id (UUID)             │                      │
       │              │ form_step_id (FK)     │                      │
       │              │ name                  │                      │
       │              │ required              │                      │
       │              │ allowed_extensions    │                      │
       │              │ mime_types            │                      │
       │              │ max_file_size         │                      │
       │              │ max_files             │                      │
       │              │ destination_subfolder │                      │
       │              │ awareness_text        │                      │
       │              └────┬──────────────────┘                      │
       │                   │                                         │
       │              ┌────▼─────────────────────┐                   │
       │              │ DOCUMENTUPLOAD          │                   │
       │              ├────────────────────────┤                   │
       │              │ id (UUID)              │                   │
       │              │ form_assignment_id (FK)├──────────────────┘
       │              │ document_requirement_id│
       │              │ (FK)                   │
       │              │ original_filename      │
       │              │ stored_filename        │
       │              │ relative_path          │
       │              │ sha256_checksum        │
       │              │ upload_datetime        │
       │              │ uploaded_by_ip         │
       │              │ uploaded_by_user_agent │
       │              │ status                 │
       │              │ version                │
       │              │ previous_version_id    │
       │              │ (FK self)              │
       │              └────────────────────────┘
       │
       │ (audit)
       │
       └───────────┬──────────────┐
                   │              │
              ┌────▼──────────┐  ┌┴─────────────────┐
              │ AUDITLOG      │  │ CUSTOMER         │
              ├───────────────┤  ├──────────────────┤
              │ id (UUID)     │  │ id (UUID)        │
              │ actor_user_id │  │ code (unique)    │
              │ (FK)          │  │ first_name       │
              │ action_date   │  │ last_name        │
              │ action        │  │ email            │
              │ object_type   │  │ phone            │
              │ object_id     │  │ fiscal_code      │
              │ actor_ip      │  │ vat_number       │
              │ actor_user_ag │  │ nas_folder_name  │
              │ details (JSON)│  │ active           │
              │ success       │  │ created_at       │
              └───────────────┘  └──────────────────┘
                                  │
                                  │ (1:N)
                                  ▼
                         FORMASSIGNMENT
                         (see above)
```

### Model Relationships

```
Customer (1) ──── (N) FormAssignment
  │
  └─ Multiple assignments over time
  └─ Folder on NAS per customer

FormTemplate (1) ──── (N) FormStep
  │
  └─ Version control (v1, v2, ...)

FormStep (1) ──── (N) DocumentRequirement
  │
  └─ Sequential steps

DocumentRequirement (1) ──── (N) DocumentUpload
  │
  └─ Multiple file uploads per requirement

FormAssignment (1) ──── (N) DocumentUpload
  │
  └─ Tracks all uploads for assignment

DocumentUpload (self-referential)
  └─ previous_version (tracks file versioning)

FormAssignment (1) ──── (N) AwarenessDeclaration
  │
  └─ When customer skips optional documents

User (1) ──── (N) FormAssignment
  │
  └─ Operator who assigned form

User (1) ──── (N) AuditLog
  │
  └─ Actor in audit trail
```

---

## Storage Architecture

### NAS Synology Directory Structure

```
/volume1/
│
├─ Clienti/                          ← CUSTOMER_DOCUMENTS_PATH
│  │
│  ├─ cliente_001/                   ← customer.nas_folder_name (validated)
│  │  │
│  │  ├─ 550e8400-e29b-41d4-a716-446655440001/  ← FormAssignment UUID
│  │  │  │
│  │  │  ├─ documento_identita/      ← DocumentRequirement.destination_subfolder
│  │  │  │  │
│  │  │  │  ├─ 20260901_143022_a7f3.pdf       ← file (safe random name)
│  │  │  │  │  └─ DB: stored_filename = "20260901_143022_a7f3.pdf"
│  │  │  │  │  └─ DB: original_filename = "ID_cartaIdentita_Cliente.pdf" (sanitized)
│  │  │  │  │  └─ DB: sha256_checksum = "abc123..."
│  │  │  │  │  └─ DB: relative_path = "cliente_001/.../documento_identita/20260901_143022_a7f3.pdf"
│  │  │  │  │
│  │  │  │  └─ 20260902_152530_b2e4.pdf       ← newer version
│  │  │  │     └─ DB: version = 2, previous_version = {first upload}
│  │  │  │
│  │  │  ├─ buste_paga/
│  │  │  │  ├─ 20260901_165940_c9d1.pdf
│  │  │  │  └─ 20260901_171205_e3f5.pdf
│  │  │  │
│  │  │  ├─ dichiarazioni/
│  │  │  │  └─ (empty if all documents required)
│  │  │  │  └─ (no files: AwarenessDeclaration stored in DB instead)
│  │  │  │
│  │  │  └─ .metadata.json (optional)
│  │  │     └─ assignment metadata (for NAS-side inspection)
│  │  │
│  │  ├─ 550e8400-e29b-41d4-a716-446655440002/  ← Another assignment
│  │  │  └─ (similar structure)
│  │  │
│  │  └─ .access_log                  ← Optional: access audit on NAS
│  │
│  ├─ cliente_002/
│  │  └─ (same structure)
│  │
│  └─ cliente_N/
│     └─ (same structure)
│
├─ docker/
│  ├─ document-collector/
│  │  │
│  │  ├─ appdata/                     ← APP_DATA_PATH
│  │  │  ├─ staticfiles/              ← Django collectstatic output
│  │  │  │  ├─ css/
│  │  │  │  ├─ js/
│  │  │  │  └─ admin/
│  │  │  │
│  │  │  ├─ media/                    ← Temp uploads (during processing)
│  │  │  │  └─ examples/              ← Example documents for download
│  │  │  │
│  │  │  └─ logs/
│  │  │     ├─ django.log
│  │  │     ├─ access.log
│  │  │     └─ error.log
│  │  │
│  │  └─ postgres/                    ← POSTGRES_DATA_PATH
│  │     ├─ global/
│  │     ├─ pg_stat_tmp/
│  │     ├─ pg_wal/                   ← Write-ahead logs
│  │     ├─ base/
│  │     └─ (PostgreSQL internal structure)
│  │
│  └─ (other services if needed)
```

### Storage Characteristics

| Aspect | Value | Notes |
|--------|-------|-------|
| **Base Path** | `/storage/clienti` | Mounted from host |
| **Permission Mode** | `0o750` (rwxr-x---) | Owner + group readable |
| **File Mode** | `0o600` (rw-------)  | Owner only |
| **Filename Format** | `{timestamp}_{random}.{ext}` | No traversal risk |
| **Max File Size** | Per DocumentRequirement | Typically 50-500MB |
| **Directory Depth** | 3 levels max | Customer → Assignment → Subfolder |
| **Atomic Save** | Yes | Temp file + atomic rename |
| **Versioning** | Via `DocumentUpload.version` | DB tracks versions |
| **Deletion** | Secure (overwrite) | OS-level file delete |

### Storage Path Construction (SAFE)

```
# VULNERABLE (before)
path = os.path.join(base, customer.nas_folder, assignment_id, subfolder)
# ❌ If customer.nas_folder = "../../etc/ssh" → ESCAPES base

# SECURE (after)
from modules.upload_security import safe_join_paths

path = safe_join_paths(
    base_path="/storage/clienti",
    "cliente_001",                  # Validated via validator
    "550e8400-...",                 # UUID (safe)
    "documento_identita"            # Validated via validator
)
# ✅ Each component verified, traversal impossible
```

---

## Request Flow

### 1. Public Form Access Flow

```
CLIENT
  │
  ├─ 1. GET /modules/form/{secure_token}/
  │   └─ Query: FormAssignment.objects.get(secure_token=token)
  │
  │   ↓ SECURITY CHECKS
  │   • Token exists?
  │   • Not expired?
  │   • Not already submitted?
  │
  ├─ 2. Render form_detail.html
  │   └─ Display: form title, intro text, privacy
  │   └─ Button: "Inizia" → next step
  │
  ├─ 3. GET /modules/form/{assignment_id}/step/1/
  │   └─ Query: FormStep.objects.get(order=1)
  │   └─ Query: DocumentRequirement.objects.filter(form_step=step)
  │
  ├─ 4. Render form_step.html
  │   └─ Display: step title, document requirements
  │   └─ File input for each requirement
  │   └─ HTMX triggers upload on file select
  │
  ├─ 5. POST /modules/form/{assignment_id}/upload/
  │   │
  │   ├─ FILE RECEIVED
  │   │
  │   ├─ VALIDATION (upload_security.py)
  │   │  ├─ Size check
  │   │  ├─ Extension validation
  │   │  ├─ Double extension check
  │   │  ├─ MIME type from content
  │   │  └─ Content header validation
  │   │  └─ (can fail here → 400 response)
  │   │
  │   ├─ SAVE (atomic)
  │   │  ├─ Temp file created
  │   │  ├─ File written chunk-by-chunk
  │   │  ├─ Checksum calculated
  │   │  ├─ Atomic rename to final location
  │   │  └─ (can fail here → 500 response)
  │   │
  │   ├─ DB RECORD
  │   │  └─ DocumentUpload created with:
  │   │     ├─ stored_filename (safe random)
  │   │     ├─ original_filename (sanitized)
  │   │     ├─ relative_path
  │   │     ├─ sha256_checksum
  │   │     ├─ mime_type_detected
  │   │     └─ status = 'valid'
  │   │
  │   ├─ AUDIT LOG
  │   │  └─ AuditLog.create(action='upload', success=True, ...)
  │   │
  │   └─ JSON RESPONSE
  │      └─ {"status": "success", "upload_id": "...", "filename": "..."}
  │
  ├─ 6. Repeat for remaining requirements/steps
  │   └─ Update FormAssignment.completion_percentage
  │   └─ Update FormAssignment.last_access_date
  │
  ├─ 7. GET /modules/form/{assignment_id}/summary/
  │   └─ Display: all uploaded files
  │   └─ Display: all acceptance declarations
  │   └─ Button: "Conferma e Invia"
  │
  └─ 8. POST /modules/form/{assignment_id}/submit/
      │
      ├─ FINAL VALIDATION
      │  └─ All required documents present?
      │
      ├─ UPDATE DB
      │  ├─ FormAssignment.status = 'submitted'
      │  ├─ FormAssignment.submission_date = now()
      │  └─ FormAssignment.completion_percentage = 100
      │
      ├─ AUDIT LOG
      │  └─ AuditLog.create(action='submit', success=True, ...)
      │
      ├─ NOTIFICATION
      │  └─ NotificationLog.create(type='form_submitted', ...)
      │  └─ (email queue for async send)
      │
      └─ JSON RESPONSE + REDIRECT
         └─ {"status": "success", "redirect": "/modules/form/success/"}
```

### 2. Admin Form Creation Flow

```
ADMIN (logged in)
  │
  ├─ 1. GET /modules/admin/templates/create/
  │   └─ Render: form_template_form.html
  │
  ├─ 2. POST /modules/admin/templates/create/
  │   ├─ Form data: {name, description, intro_text, privacy_text}
  │   │
  │   ├─ CREATE FormTemplate
  │   │  ├─ status = 'draft'
  │   │  ├─ version = 1
  │   │  ├─ author = request.user
  │   │  └─ created_at = now()
  │   │
  │   ├─ AUDIT LOG
  │   │  └─ AuditLog.create(action='create', object_type='FormTemplate', ...)
  │   │
  │   └─ REDIRECT to: /modules/admin/templates/{template_id}/edit/
  │
  ├─ 3. GET /modules/admin/templates/{template_id}/edit/
  │   └─ Render: form_template_edit.html
  │   └─ Display: form details, list of steps
  │   └─ Button: "Aggiungi Step"
  │
  ├─ 4. [STEP CREATION] (in form builder UI)
  │   ├─ Admin adds step: "Documento di Identità"
  │   │  └─ FormStep.create(form_template_id, title, order=1)
  │   │
  │   ├─ Admin adds requirement: "Copia Fronte"
  │   │  └─ DocumentRequirement.create(
  │   │     form_step_id,
  │   │     name="Copia Fronte",
  │   │     required=True,
  │   │     allowed_extensions="pdf,jpg,png",
  │   │     mime_types="application/pdf,image/jpeg,image/png",
  │   │     max_file_size=5242880,  # 5MB
  │   │     destination_subfolder="documento_identita",
  │   │     awareness_text="",
  │   │     awareness_required_when_empty=False
  │   │  )
  │   │
  │   └─ (Validators run: validate_subfolder_name, validate_extensions, ...)
  │
  ├─ 5. Admin finalizes template
  │   ├─ Update FormTemplate.status = 'published'
  │   ├─ AUDIT LOG
  │   └─ REDIRECT to template list
  │
  ├─ 6. Admin creates customer
  │   ├─ POST /modules/admin/customers/create/
  │   ├─ Form data: {code, first_name, email, nas_folder_name}
  │   │
  │   ├─ CREATE Customer
  │   │  ├─ id = UUID
  │   │  ├─ nas_folder_name validated (validator rejects ../etc)
  │   │  └─ created_at = now()
  │   │
  │   └─ Validator: validate_folder_name
  │      └─ Rejects: .., /, :, spaces, special chars
  │
  └─ 7. Admin assigns form to customer
     ├─ POST /modules/admin/assign-form/
     ├─ Form data: {customer_id, template_id}
     │
     ├─ CREATE FormAssignment
     │  ├─ id = UUID
     │  ├─ secure_token = generate_secure_token()  # 40 char random
     │  ├─ status = 'draft'
     │  ├─ expiry_date = now() + 30 days
     │  ├─ operator = request.user
     │  └─ created_at = now()
     │
     ├─ AUDIT LOG
     │  └─ AuditLog.create(action='create', object_type='FormAssignment', ...)
     │
     ├─ SEND EMAIL
     │  └─ Customer receives link: /modules/form/{secure_token}/
     │
     └─ RESPONSE
        └─ JSON: {token, form_url}
```

---

## Document Lifecycle

### Complete Lifecycle Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                    DOCUMENT LIFECYCLE STATE MACHINE               │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [1] CREATION (Admin)                                       │ │
│  │                                                             │ │
│  │ Action: Admin creates FormTemplate                         │ │
│  │ State: FormTemplate.status = 'draft'                       │ │
│  │ DB Changes:                                                │ │
│  │   CREATE FormTemplate (status=draft)                       │ │
│  │   CREATE FormStep[1..N] (required, active)                 │ │
│  │   CREATE DocumentRequirement[1..M] (required/optional)     │ │
│  │                                                             │ │
│  │ Permissions: Admin only                                    │ │
│  │ Audit: ✓ Logged                                            │ │
│  │                                                             │ │
│  │                     ↓ publish()                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [2] PUBLICATION (Admin)                                    │ │
│  │                                                             │ │
│  │ Action: Admin marks template as published                  │ │
│  │ State: FormTemplate.status = 'published'                   │ │
│  │ DB Changes:                                                │ │
│  │   UPDATE FormTemplate SET status='published'               │ │
│  │                                                             │ │
│  │ Permissions: Admin only                                    │ │
│  │ Audit: ✓ Logged                                            │ │
│  │                                                             │ │
│  │                   ↓ assign_to_customer()                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [3] ASSIGNMENT (Operator)                                  │ │
│  │                                                             │ │
│  │ Action: Operator assigns form to customer                  │ │
│  │ State: FormAssignment.status = 'draft'                     │ │
│  │ DB Changes:                                                │ │
│  │   CREATE FormAssignment                                    │ │
│  │     - secure_token = random(40 chars)                      │ │
│  │     - expiry_date = now() + 30 days                        │ │
│  │     - status = 'draft'                                     │ │
│  │     - completion_percentage = 0                            │ │
│  │                                                             │ │
│  │ Storage: No files yet (/storage/clienti/... empty)         │ │
│  │ Email: Customer receives public link                       │ │
│  │ Permissions: Operator/Admin only                           │ │
│  │ Audit: ✓ Logged (action='create', object_type=FormAsgn)    │ │
│  │                                                             │ │
│  │           ↓ customer_accesses_link()                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [4] ACCESS / FORM INITIATION (Customer)                    │ │
│  │                                                             │ │
│  │ Action: Customer clicks public link                        │ │
│  │ State: FormAssignment.status = 'in_progress'               │ │
│  │ DB Changes:                                                │ │
│  │   UPDATE FormAssignment SET                                │ │
│  │     status='in_progress',                                  │ │
│  │     last_access_date=now()                                 │ │
│  │                                                             │ │
│  │ Checks:                                                    │ │
│  │   ✓ Token valid?                                           │ │
│  │   ✓ Not expired?  (expiry_date > now)                      │ │
│  │   ✓ Not already submitted?  (status ≠ 'submitted')         │ │
│  │                                                             │ │
│  │ Permissions: Public (token-based)                          │ │
│  │ Audit: ✓ Logged (action='view')                            │ │
│  │                                                             │ │
│  │              ↓ navigate_steps() / upload()                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [5] DOCUMENT UPLOAD (Customer)                             │ │
│  │                                                             │ │
│  │ Repeat for each document requirement:                      │ │
│  │                                                             │ │
│  │ Action: Customer uploads file                              │ │
│  │ Security:                                                  │ │
│  │   ✓ File size within limit?                                │ │
│  │   ✓ Extension allowed?                                     │ │
│  │   ✓ No double extensions (.php.jpg)?                       │ │
│  │   ✓ MIME type matches content (magic bytes)?               │ │
│  │   ✓ Content header valid (PDF, JPG, etc)?                  │ │
│  │   ✓ Filename sanitized (no null bytes)?                    │ │
│  │   ✓ Path safe (no traversal)?                              │ │
│  │   └─ Any failure → 400 response, file rejected             │ │
│  │                                                             │ │
│  │ File Save (ATOMIC):                                        │ │
│  │   1. Create temp file in /storage/clienti/...              │ │
│  │   2. Write file content (chunk-by-chunk)                   │ │
│  │   3. Calculate SHA-256 checksum                            │ │
│  │   4. Atomic rename to final location                       │ │
│  │   5. Set permissions 0o600 (owner-only)                    │ │
│  │                                                             │ │
│  │ DB Changes:                                                │ │
│  │   CREATE DocumentUpload                                    │ │
│  │     - stored_filename = safe_random_name.pdf               │ │
│  │     - original_filename = sanitized_user_name.pdf          │ │
│  │     - relative_path = clienti/cust1/assg-id/subfolder/...  │ │
│  │     - sha256_checksum = calculated                         │ │
│  │     - mime_type_detected = from magic                      │ │
│  │     - status = 'valid'                                     │ │
│  │                                                             │ │
│  │ For OPTIONAL documents (not uploaded):                     │ │
│  │   CREATE AwarenessDeclaration                              │ │
│  │     - accepted = True                                      │ │
│  │     - customer_name_declared = filled by customer          │ │
│  │     - acceptance_ip = client IP                            │ │
│  │                                                             │ │
│  │ DB Updates:                                                │ │
│  │   UPDATE FormAssignment SET                                │ │
│  │     completion_percentage = (docs_complete / docs_total)*100 │
│  │     last_access_date = now()                               │ │
│  │                                                             │ │
│  │ File Location on NAS:                                      │ │
│  │   /storage/clienti/cliente_001/assg-uuid/subfolder/        │ │
│  │   20260901_a7f3.pdf                                        │ │
│  │                                                             │ │
│  │ Permissions: Public (token-based)                          │ │
│  │ Audit: ✓ Logged (action='upload', size, checksum)          │ │
│  │                                                             │ │
│  │              ↓ continue_to_next_step()                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [6] REVIEW / SUMMARY (Customer)                            │ │
│  │                                                             │ │
│  │ Action: Customer reviews all uploaded documents            │ │
│  │ Display:                                                   │ │
│  │   - All uploaded files (with original names)               │ │
│  │   - All acceptance declarations                            │ │
│  │   - Completion status                                      │ │
│  │                                                             │ │
│  │ DB Access: Read-only                                       │ │
│  │   - SELECT * FROM DocumentUpload                           │ │
│  │   - SELECT * FROM AwarenessDeclaration                     │ │
│  │                                                             │ │
│  │ Permissions: Public (token-based)                          │ │
│  │ Audit: ✓ Logged (action='view', object=FormAssignment)    │ │
│  │                                                             │ │
│  │               ↓ submit()                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [7] SUBMISSION (Customer)                                  │ │
│  │                                                             │ │
│  │ Action: Customer clicks "Conferma e Invia"                 │ │
│  │ Validation:                                                │ │
│  │   ✓ All REQUIRED documents present?                        │ │
│  │   ✓ For OPTIONAL: declaration provided?                    │ │
│  │   ✓ FormAssignment not already submitted?                  │ │
│  │   └─ Any failure → 400, form stays open                    │ │
│  │                                                             │ │
│  │ DB Changes:                                                │ │
│  │   UPDATE FormAssignment SET                                │ │
│  │     status = 'submitted',                                  │ │
│  │     completion_percentage = 100,                           │ │
│  │     submission_date = now(),                               │ │
│  │     last_completed_step = final_step                       │ │
│  │                                                             │ │
│  │ Notifications:                                             │ │
│  │   CREATE NotificationLog                                   │ │
│  │     - notification_type = 'form_submitted'                 │ │
│  │     - recipient_email = customer.email                     │ │
│  │     - status = 'pending'                                   │ │
│  │   QUEUE: Email to customer + operator                      │ │
│  │                                                             │ │
│  │ Immutable:                                                 │ │
│  │   ✓ status = 'submitted' is terminal                       │ │
│  │   ✓ No further uploads allowed                             │ │
│  │   ✓ No edits possible                                      │ │
│  │                                                             │ │
│  │ Permissions: Public (token-based, one-time)                │ │
│  │ Audit: ✓ Logged (action='submit', FormAssignment)          │ │
│  │                                                             │ │
│  │              ↓ admin_review()                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [8] COMPLETION / ARCHIVAL (Admin)                          │ │
│  │                                                             │ │
│  │ Action: Operator reviews submitted documents               │ │
│  │ Access:                                                    │ │
│  │   - /modules/admin/assignments/{assignment_id}/            │ │
│  │   - View all uploaded files                                │ │
│  │   - Download ZIP with all documents                        │ │
│  │   - Move to external storage / archive                     │ │
│  │   - Export for compliance                                  │ │
│  │                                                             │ │
│  │ File Access:                                               │ │
│  │   - Files remain on NAS indefinitely                       │ │
│  │   - Organized by customer → assignment → type              │ │
│  │   - Can be mounted via SMB/NFS on client machines          │ │
│  │                                                             │ │
│  │ Permissions: Operator/Admin only                           │ │
│  │ Audit: ✓ Logged (action='view', object=FormAssignment)    │ │
│  │                                                             │ │
│  │              (end of lifecycle)                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

ALTERNATIVE PATHS:
  • [Expiration] If now() > expiry_date: FormAssignment.status='expired'
  • [Cancellation] Operator can cancel: FormAssignment.status='cancelled'
  • [Document Rejection] If uploaded doc invalid: DocumentUpload.status='rejected'
  • [Document Replacement] Customer can re-upload: Creates new version
```

### State Transition Matrix

| Current State | Transition | New State | Triggered By | Immutable? |
|---|---|---|---|---|
| draft | publish | published | Admin UI | ❌ Can unpublish |
| published | archive | archived | Admin UI | ❌ Can re-publish |
| draft (assignment) | customer_access | in_progress | Public link | ❌ Can expire |
| in_progress | customer_upload | in_progress | File upload | ❌ Can expire |
| in_progress | customer_submit | submitted | Submit button | ✅ TERMINAL |
| any | admin_expire | expired | Scheduler / manual | ✅ TERMINAL |
| any | admin_cancel | cancelled | Admin UI | ✅ TERMINAL |
| submitted | none | none | | ✅ IMMUTABLE |

---

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 0: NETWORK SECURITY (Synology / Reverse Proxy)    │
├─────────────────────────────────────────────────────────┤
│ • TLS/SSL for HTTPS (Reverse Proxy handles)             │
│ • HTTP → HTTPS redirect                                 │
│ • Security headers (X-Frame-Options, CSP, etc.)         │
│ • Rate limiting (optional, at proxy level)              │
│ • DDoS protection (optional, at proxy level)            │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: DJANGO SECURITY (Middleware)                   │
├─────────────────────────────────────────────────────────┤
│ • CSRF protection (form token)                          │
│ • X-Frame-Options (clickjacking prevention)             │
│ • X-Content-Type-Options (MIME sniffing prevention)     │
│ • Session cookie security (Secure, HttpOnly flags)      │
│ • User authentication (login required for admin)        │
│ • Permission checks (staff_required decorators)         │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: APPLICATION LOGIC SECURITY                     │
├─────────────────────────────────────────────────────────┤
│ • Token-based access control (public forms)             │
│ • User authorization checks (admin vs public)           │
│ • Rate limiting (per IP / per user - optional)          │
│ • Input validation (form validators)                    │
│ • Output encoding (template escaping)                   │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 3: FILE UPLOAD SECURITY ⭐ CRITICAL              │
├─────────────────────────────────────────────────────────┤
│ 3.1 PRE-VALIDATION                                      │
│     • File size limit check                             │
│     • Extension whitelist                               │
│     • Double extension detection                        │
│                                                         │
│ 3.2 CONTENT VALIDATION                                  │
│     • MIME type from magic bytes (not extension!)       │
│     • Content header validation (PDF, JPG, PNG, etc.)   │
│     • Suspicious pattern detection                      │
│                                                         │
│ 3.3 PATH SAFETY                                         │
│     • Database validators reject "../" and "/"          │
│     • safe_join_paths() prevents traversal              │
│     • Absolute path rejection                           │
│                                                         │
│ 3.4 FILENAME SAFETY                                     │
│     • Null byte removal                                 │
│     • Control character removal                         │
│     • Unicode normalization                             │
│     • Leading/trailing dot removal                      │
│                                                         │
│ 3.5 SECURE FILE OPERATIONS                              │
│     • Atomic temp file + rename (prevents partial)      │
│     • Secure random filename generation (collision-free)│
│     • Restrictive file permissions (0o600)              │
│     • Secure deletion (overwrite + delete)              │
│                                                         │
│ 3.6 STORAGE SECURITY                                    │
│     • Organized by customer → no cross-contamination    │
│     • NAS folder access control (OS level)              │
│     • Audit trail in database                           │
│ ⭐ See SECURITY_REVIEW_UPLOAD.md for details            │
│ ⭐ See upload_security.py source for implementation      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 4: DATABASE SECURITY                              │
├─────────────────────────────────────────────────────────┤
│ • SQL injection protection (ORM parameterized queries)  │
│ • Field-level validators (regex, range checks)          │
│ • Unique constraints (secure_token, customer.code)      │
│ • Foreign key constraints (referential integrity)       │
│ • Row-level audit logging (all changes tracked)         │
│ • Connection pooling with timeout                       │
│ • Connection requires password (from .env)              │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 5: AUDIT & LOGGING                                │
├─────────────────────────────────────────────────────────┤
│ • All actions logged: action, user, IP, user-agent      │
│ • File checksums stored (detect tampering)              │
│ • Timestamps (action_datetime, upload_datetime)         │
│ • JSON details field (rich structured data)             │
│ • Success/failure tracking                              │
│ • Sensitive data masked in logs                         │
└─────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Docker Compose Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   DOCKER COMPOSE SETUP                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Network: collector-network (internal bridge)        │   │
│  └─────────────────────────────────────────────────────┘   │
│         ▲                              ▲                    │
│         │                              │                    │
│  ┌──────┴────────────────┐    ┌───────┴──────────────┐    │
│  │   SERVICE: app        │    │  SERVICE: db         │    │
│  ├───────────────────────┤    ├──────────────────────┤    │
│  │ Image: BUILD          │    │ Image: postgres:15   │    │
│  │ (Dockerfile)          │    │ -alpine              │    │
│  │                       │    │                      │    │
│  │ Depends on: db ✓      │    │ Healthcheck: pg_isready
│  │                       │    │                      │    │
│  │ Port Mapping:         │    │ Port (internal only):│    │
│  │ 6000:8000 (HOST:CONT) │    │ 5432 (not exposed)   │    │
│  │                       │    │                      │    │
│  │ Environment:          │    │ Environment:         │    │
│  │ • DEBUG (from .env)   │    │ • POSTGRES_DB        │    │
│  │ • SECRET_KEY          │    │ • POSTGRES_USER      │    │
│  │ • POSTGRES_*          │    │ • POSTGRES_PASSWORD  │    │
│  │ • ALLOWED_HOSTS       │    │                      │    │
│  │ • TZ                  │    │ Environment (from):  │    │
│  │ • ENVIRONMENT         │    │ .env file            │    │
│  │                       │    │                      │    │
│  │ Volumes:              │    │ Volumes:             │    │
│  │ • ${APP_DATA_PATH}:   │    │ • ${POSTGRES_DATA}:  │    │
│  │   /app/data           │    │   /var/lib/postgres  │    │
│  │ • ${CUSTOMER_DOCS}:   │    │                      │    │
│  │   /storage/clienti    │    │ Restart: unless-stop │    │
│  │                       │    │                      │    │
│  │ Healthcheck:          │    │ Networks:            │    │
│  │ curl http://...       │    │ collector-network    │    │
│  │                       │    │                      │    │
│  │ Restart: unless-stop  │    └──────────────────────┘    │
│  │                       │                                  │
│  │ Networks:             │                                  │
│  │ collector-network     │                                  │
│  │                       │                                  │
│  │ Processes:            │                                  │
│  │ • Gunicorn (:8000)    │                                  │
│  │   -  4 workers        │                                  │
│  │   - sync mode         │                                  │
│  │ • Django management   │                                  │
│  │   (entrypoint)        │                                  │
│  └───────────────────────┘                                  │
│         ▲                                                    │
│         │ HTTP/HTTPS                                        │
│         │                                                    │
│  ┌──────┴──────────────────────────────────────────────┐   │
│  │ HOST MACHINE                                        │   │
│  ├───────────────────────────────────────────────────┤   │
│  │ Synology NAS / Server                              │   │
│  │                                                     │   │
│  │ Port 6000 (exposed)  ←─── Client browser (HTTP)    │   │
│  │                      ←─── Reverse proxy (HTTPS)    │   │
│  │                                                     │   │
│  │ Volumes (bind mounts):                             │   │
│  │ • /volume1/docker/document-collector/appdata       │   │
│  │ • /volume1/docker/document-collector/postgres      │   │
│  │ • /volume1/Clienti                                 │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘

SERVICES COMMUNICATION:
  app ──(SQL over TCP:5432)──> db
  app ──(file operations)──> NAS /storage/clienti
  db ──(persists)──> NAS /var/lib/postgresql/data
  client ──(HTTP:6000)──> app (reverse proxy handles HTTPS)
```

### Environment Variables

```ini
# ========== APPLICATION ==========
DEBUG=False                                    # Django debug mode
SECRET_KEY=your-secret-key-here               # Django SECRET_KEY (CHANGE!)
ENVIRONMENT=production                        # development/production
APP_PORT=6000                                 # External port
TZ=Europe/Rome                                # Timezone

# ========== DATABASE ==========
POSTGRES_DB=document_collector                # Database name
POSTGRES_USER=collector_user                  # Database user
POSTGRES_PASSWORD=secure_password             # Database password (CHANGE!)
POSTGRES_HOST=db                              # Hostname (docker service name)
POSTGRES_PORT=5432                            # Internal port

# ========== DJANGO SECURITY ==========
ALLOWED_HOSTS=localhost,127.0.0.1,your-ip    # CSRF origins
CSRF_TRUSTED_ORIGINS=http://localhost:6000   # CORS origin

# ========== STORAGE PATHS ==========
APP_DATA_PATH=/volume1/docker/document-collector/appdata
POSTGRES_DATA_PATH=/volume1/docker/document-collector/postgres
CUSTOMER_DOCUMENTS_PATH=/volume1/Clienti

# ========== OPTIONAL ==========
SENTRY_DSN=                                   # Error tracking (optional)
LOG_LEVEL=INFO                                # Logging level
```

### Health Checks

```yaml
# Service: app
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s

# Service: db
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

---

## Scalability

### Horizontal Scaling Strategy

```
CURRENT: Single container, single database

PHASE 1 (now): Single container, PostgreSQL
  └─ Can handle ~1000 concurrent users
  └─ 4 Gunicorn workers
  └─ Good for small-to-medium deployments

PHASE 2 (future): Multiple containers behind load balancer
  ├─ app-1 (container 1)
  ├─ app-2 (container 2)
  ├─ app-N (container N)
  │   └─ All connected to shared PostgreSQL
  │   └─ All mounting same NAS /storage/clienti
  └─ Load balancer (HAProxy / Nginx / Synology reverse proxy)
     └─ Distributes requests across containers

PHASE 3 (future): Read replicas for database
  ├─ Primary PostgreSQL (writes)
  ├─ Replica-1 (reads)
  └─ Replica-N (reads)
     └─ App containers can query replicas for reporting

PHASE 4 (future): Separate file storage
  └─ Replace NAS mount with S3-compatible storage (MinIO)
  └─ Enables edge replication across datacenters
```

### Bottlenecks & Solutions

| Bottleneck | Current | Solution |
|---|---|---|
| CPU | Single container (4 workers) | Scale Gunicorn workers, add containers |
| Memory | 2GB container | Increase container memory limit |
| Database | Single PostgreSQL | Add read replicas, optimize queries |
| File I/O | Local NAS mount | S3-compatible distributed storage |
| Concurrent uploads | Limited by disk I/O | NAS with SSD + RAID10 |
| Session storage | Database (sessions table) | Move to Redis (optional) |

---

## API Endpoints

### Public Endpoints (No Authentication)

```
GET    /health/
       └─ Health check for load balancer
       └─ Response: {"status": "healthy"}

GET    /modules/form/{secure_token}/
       └─ Initialize form submission
       └─ Response: HTML form (form_detail.html)

GET    /modules/form/{assignment_id}/step/{step_order}/
       └─ Get specific form step
       └─ Response: HTML form (form_step.html)

POST   /modules/form/{assignment_id}/upload/
       └─ Upload document
       └─ Request: multipart/form-data {file, requirement_id}
       └─ Response: {"status": "success", "upload_id": "..."}

POST   /modules/form/{assignment_id}/skip-document/
       └─ Skip optional document with declaration
       └─ Request: {requirement_id, declaration_text}
       └─ Response: {"status": "success"}

GET    /modules/form/{assignment_id}/summary/
       └─ Get submission summary
       └─ Response: HTML summary (form_summary.html)

POST   /modules/form/{assignment_id}/submit/
       └─ Submit form (terminal action)
       └─ Response: {"status": "success", "redirect": "..."}
```

### Admin Endpoints (Authentication Required)

```
GET    /modules/admin/
       └─ Admin dashboard
       └─ Response: HTML dashboard (admin/dashboard.html)

GET    /modules/admin/templates/
       └─ List form templates
       └─ Response: HTML list (admin/form_template_list.html)

POST   /modules/admin/templates/create/
       └─ Create new template
       └─ Request: {name, description, intro_text, privacy_text}
       └─ Response: Redirect to edit

GET    /modules/admin/templates/{template_id}/edit/
       └─ Edit template
       └─ Response: HTML form (admin/form_template_edit.html)

POST   /modules/admin/templates/{template_id}/edit/
       └─ Update template
       └─ Response: Redirect to list

GET    /modules/admin/customers/
       └─ List customers
       └─ Response: HTML list (admin/customer_list.html)

POST   /modules/admin/customers/create/
       └─ Create customer
       └─ Request: {code, first_name, email, nas_folder_name}
       └─ Response: Redirect to list

POST   /modules/admin/assign-form/
       └─ Assign form to customer
       └─ Request: {customer_id, template_id}
       └─ Response: {"status": "success", "token": "..."}

GET    /modules/admin/assignments/{assignment_id}/
       └─ View assignment details
       └─ Response: HTML details (admin/assignment_detail.html)
```

---

## Summary

### Key Architectural Decisions

| Decision | Rationale |
|---|---|
| Django (not React) | Simpler deployment, server-side rendering for public forms |
| PostgreSQL | ACID compliance, UUID support, proven reliability |
| NAS storage (not DB) | Large files, direct client access via SMB/NFS, cost-effective |
| Docker Compose | Simple, fits Synology deployment model |
| Token-based access | Stateless public access, no login required for customers |
| Atomic file operations | Prevents partial uploads, ensures data consistency |
| Magic byte MIME detection | Prevents exe-as-pdf attacks, secure upload validation |
| Audit logging | Complete audit trail, compliance, forensics |

### Deployment Checklist

- [ ] Configure `.env` with production values
- [ ] Set `SECRET_KEY` to strong random value
- [ ] Set `POSTGRES_PASSWORD` to strong random value
- [ ] Create NAS directories (/volume1/Clienti, /volume1/docker/...)
- [ ] Run `docker-compose build`
- [ ] Run `docker-compose up -d`
- [ ] Verify healthchecks: `docker-compose ps`
- [ ] Access http://NAS_IP:6000
- [ ] Test admin login
- [ ] Create test customer and form
- [ ] Test file upload with various file types
- [ ] Monitor audit logs for errors
- [ ] Configure reverse proxy for HTTPS (optional)

---

**Document Status**: ✅ Complete  
**Last Review**: September 2026  
**Next Review**: When adding new features or major changes
