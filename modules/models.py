from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import uuid
import secrets
import string
import json
from .validators import (
    validate_folder_name,
    validate_subfolder_name,
    validate_allowed_extensions,
    validate_mime_types,
    get_mimes_for_extensions,
)

def generate_secure_token():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(40))

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('operator', 'Operator'),
    ]

    id = models.BigAutoField(primary_key=True)
    email_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator')

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    fiscal_code = models.CharField(max_length=16, blank=True, null=True, unique=True)
    vat_number = models.CharField(max_length=11, blank=True, null=True, unique=True)
    nas_folder_name = models.CharField(
        max_length=100,
        unique=True,
        validators=[validate_folder_name],
        help_text="NAS folder name (alphanumeric, hyphens, underscores only). No path traversal."
    )
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    # Client Portal credentials
    portal_password = models.CharField(
        max_length=128, blank=True, default='',
        help_text="Hashed password for client portal login"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['email']),
            models.Index(fields=['active']),
        ]

    def set_portal_password(self, raw_password):
        """Hash and store a raw password for the client portal."""
        self.portal_password = make_password(raw_password)

    def check_portal_password(self, raw_password):
        """Verify a raw password against the stored hash."""
        if not self.portal_password:
            return False
        return check_password(raw_password, self.portal_password)

    def save(self, *args, **kwargs):
        if self.fiscal_code:
            self.fiscal_code = self.fiscal_code.strip() or None
        else:
            self.fiscal_code = None

        if self.vat_number:
            self.vat_number = self.vat_number.strip() or None
        else:
            self.vat_number = None

        if self.phone:
            self.phone = self.phone.strip() or None
        else:
            self.phone = None

        if self.code:
            self.code = self.code.strip()

        if self.nas_folder_name:
            self.nas_folder_name = self.nas_folder_name.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.first_name} {self.last_name}"


class FormTemplate(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text="Groups all versions of the same logical form")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    intro_text = models.TextField()
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    validity_start_date = models.DateTimeField(null=True, blank=True)
    validity_end_date = models.DateTimeField(null=True, blank=True)
    privacy_text = models.TextField(blank=True)

    # NEW: Form-specific customer + project + password
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, help_text="Specific customer this form is for (optional)")
    project_name = models.CharField(max_length=255, blank=True, help_text="Project name for NAS folder structure")
    access_password = models.CharField(max_length=255, blank=True, help_text="Password to access this form (auto-generated if empty)")
    default_expiry_days = models.PositiveIntegerField(default=30, help_text="Default validity duration in days when assigning this form to a customer")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['family_id']),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def set_access_password(self, raw_password):
        """Hash and store access password for the form template."""
        if raw_password:
            self.access_password = make_password(raw_password)
        else:
            self.access_password = ''

    def check_access_password(self, raw_password):
        """Verify raw password against stored hash or legacy plain text."""
        if not self.access_password or not raw_password:
            return False
        if self.access_password.startswith(('pbkdf2_', 'argon2', 'bcrypt')):
            return check_password(raw_password, self.access_password)
        return secrets.compare_digest(raw_password, self.access_password)

    def has_access_password(self):
        """Check if this template has an access password configured."""
        return bool(self.access_password)

    def duplicate(self, is_new_version=True):
        from django.db.models import Max
        import uuid
        from django.db import transaction

        with transaction.atomic():
            if is_new_version:
                new_family_id = self.family_id
                max_version = FormTemplate.objects.filter(family_id=self.family_id).select_for_update().aggregate(Max('version'))['version__max']
                new_version = (max_version if max_version is not None else self.version) + 1
                new_customer = self.customer
                new_project_name = self.project_name
            else:
                new_family_id = uuid.uuid4()
                new_version = 1
                new_customer = None
                new_project_name = ''

            new_form = FormTemplate.objects.create(
                family_id=new_family_id,
                name=f"{self.name} (copy)",
                description=self.description,
                intro_text=self.intro_text,
                version=new_version,
                status='draft',
                author=self.author,
                privacy_text=self.privacy_text,
                customer=new_customer,
                project_name=new_project_name,
                access_password=self.access_password,
                default_expiry_days=self.default_expiry_days
            )
        # Prefetch all steps with their related elements and requirements to avoid N+1 queries
        from django.db.models import Prefetch
        steps = self.formstep_set.all().prefetch_related(
            Prefetch('documentrequirement_set'),
            Prefetch('formelement_set')
        ).order_by('order')

        for step in steps:
            new_step = FormStep.objects.create(
                form_template=new_form,
                title=step.title,
                description=step.description,
                order=step.order,
                required=step.required,
                active=step.active
            )
            for requirement in step.documentrequirement_set.all():
                DocumentRequirement.objects.create(
                    form_step=new_step,
                    name=requirement.name,
                    description=requirement.description,
                    required=requirement.required,
                    allowed_extensions=requirement.allowed_extensions,
                    mime_types=requirement.mime_types,
                    max_file_size=requirement.max_file_size,
                    max_files=requirement.max_files,
                    destination_subfolder=requirement.destination_subfolder,
                    order=requirement.order,
                    awareness_text=requirement.awareness_text,
                    awareness_required_when_empty=requirement.awareness_required_when_empty
                )
            for element in step.formelement_set.all():
                FormElement.objects.create(
                    form_step=new_step,
                    element_type=element.element_type,
                    order=element.order,
                    config=element.config
                )
        return new_form

class FormStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField()
    required = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['form_template', 'order']),
        ]

    def __str__(self):
        return f"{self.form_template.name} - {self.title}"

class DocumentRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_step = models.ForeignKey(FormStep, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    allowed_extensions = models.CharField(
        max_length=255,
        validators=[validate_allowed_extensions],
        help_text="Comma-separated extensions, e.g. pdf,doc,docx"
    )
    mime_types = models.TextField(
        validators=[validate_mime_types],
        help_text="Comma-separated MIME types, e.g. application/pdf,application/msword"
    )
    max_file_size = models.IntegerField(default=10485760, help_text="Max size in bytes")
    max_files = models.IntegerField(default=200, help_text="Max files allowed (default 200 for batch uploads)")
    example_file = models.FileField(upload_to='examples/', null=True, blank=True)
    destination_subfolder = models.CharField(
        max_length=255,
        validators=[validate_subfolder_name],
        help_text="Subdirectory for uploads. No path traversal allowed."
    )
    order = models.IntegerField()
    awareness_text = models.TextField(blank=True)
    awareness_required_when_empty = models.BooleanField(default=False)

    # NEW: Allow customer to provide description for each file
    allow_file_description = models.BooleanField(default=True, help_text="Allow customer to add description for each file")

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['form_step', 'order']),
        ]

    def __str__(self):
        return f"{self.form_step.form_template.name} - {self.name}"

    def get_effective_mime_types(self):
        """Return all allowed MIME types derived from mime_types and allowed_extensions."""
        explicit = [m.strip() for m in (self.mime_types or '').split(',') if m.strip()]
        derived = get_mimes_for_extensions(self.allowed_extensions or '')
        combined = []
        for m in explicit + derived:
            if m not in combined:
                combined.append(m)
        return combined

    @property
    def file_accept_attribute(self) -> str:
        """
        Build an HTML accept attribute string combining extensions (e.g. .pdf, .docx, .xlsx)
        and MIME types for robust browser file dialog filtering.
        """
        parts = []
        if self.allowed_extensions:
            for ext in self.allowed_extensions.split(','):
                ext = ext.strip().lower().lstrip('.')
                if ext:
                    parts.append(f".{ext}")
        if '.zip' not in parts:
            parts.append('.zip')
        parts.append('application/zip')
        for m in self.get_effective_mime_types():
            if m not in parts:
                parts.append(m)
        return ','.join(parts)

    def save(self, *args, **kwargs):
        # Automatically ensure mime_types includes all valid MIME types for allowed_extensions
        if self.allowed_extensions:
            derived = get_mimes_for_extensions(self.allowed_extensions)
            current = [m.strip() for m in (self.mime_types or '').split(',') if m.strip()]
            combined = []
            for m in current + derived:
                if m not in combined:
                    combined.append(m)
            if combined:
                self.mime_types = ','.join(combined)
        super().save(*args, **kwargs)


class FormElement(models.Model):
    ELEMENT_TYPE_CHOICES = [
        ('text_field', 'Campo di Testo'),
        ('email_field', 'Campo Email'),
        ('phone_field', 'Campo Telefono'),
        ('date_field', 'Campo Data'),
        ('text_info', 'Testo Informativo'),
        ('awareness_declaration', 'Dichiarazione di Consenso'),
        ('separator', 'Separatore'),
        ('client_dropdown', 'Selettore Cliente (da NAS)'),
        ('project_name_field', 'Nome Progetto'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_step = models.ForeignKey(FormStep, on_delete=models.CASCADE)
    element_type = models.CharField(max_length=50, choices=ELEMENT_TYPE_CHOICES)
    order = models.IntegerField(help_text="Display order within the step")
    config = models.JSONField(default=dict, blank=True, help_text="Type-specific configuration (label, placeholder, required, etc.)")

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['form_step', 'order']),
        ]

    def __str__(self):
        return f"{self.form_step.form_template.name} - {self.element_type} (order {self.order})"


class FormAssignment(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Pratica Aperta'),
        ('in_progress', 'Documentazione Parziale'),
        ('submitted', 'Upload Documentale Completato'),
        ('in_processing', 'Lavorazione Etichub in Corso'),
        ('completed', 'Lavorazione Completata'),
        ('expired', 'Scaduto'),
        ('cancelled', 'Annullato'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE)
    secure_token = models.CharField(max_length=40, unique=True, default=generate_secure_token)
    assignment_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    completion_percentage = models.IntegerField(default=0)
    last_completed_step = models.ForeignKey(FormStep, on_delete=models.SET_NULL, null=True, blank=True)
    last_access_date = models.DateTimeField(null=True, blank=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments')
    internal_notes = models.TextField(blank=True)
    form_data = models.JSONField(default=dict, blank=True, help_text="Step 0 data: client_name, project_name, etc.")

    class Meta:
        ordering = ['-assignment_date']
        indexes = [
            models.Index(fields=['secure_token']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.customer.code} - {self.form_template.name}"

    def is_expired(self):
        if self.status in ('submitted', 'in_processing', 'completed', 'cancelled'):
            return False
        return timezone.now() > self.expiry_date

    def set_access_password(self, raw_password):
        """Hash and store access password in assignment form_data."""
        if self.form_data is None:
            self.form_data = {}
        if raw_password:
            self.form_data['access_password'] = make_password(raw_password)
        else:
            self.form_data['access_password'] = ''

    def check_access_password(self, raw_password):
        """Verify raw password against assignment hash, template fallback, or customer portal_password."""
        if not raw_password:
            return False
        pwd = (self.form_data or {}).get('access_password', '')
        if not pwd and self.form_template:
            pwd = self.form_template.access_password or ''
        if pwd:
            if pwd.startswith(('pbkdf2_', 'argon2', 'bcrypt')):
                return check_password(raw_password, pwd)
            return secrets.compare_digest(raw_password, pwd)
        # Fallback to customer's portal_password if set
        if self.customer and self.customer.portal_password:
            return self.customer.check_portal_password(raw_password)
        return False

    def has_access_password(self):
        """Check if this assignment, its template, or its customer has an access password configured."""
        pwd = (self.form_data or {}).get('access_password', '')
        if not pwd and self.form_template:
            pwd = self.form_template.access_password or ''
        if pwd:
            return True
        return bool(self.customer and self.customer.portal_password)

    def get_form_data_value(self, key, default=None):
        """
        Safely retrieve a value from form_data dictionary.

        Standardized defensive method for accessing form_data without KeyError risk.
        Delegates to safe_get_form_data() utility for consistent pattern.

        Args:
            key: The key to retrieve from form_data
            default: Default value if key not found or form_data is None

        Returns:
            Value from form_data[key] or default if not found/None

        Examples:
            >>> assignment.get_form_data_value('project_name', 'N/A')
            'MyProject' or 'N/A' (default)

            >>> assignment.get_form_data_value('client_ip', '')
            '192.168.1.1' or '' (default)
        """
        from .utils import safe_get_form_data
        return safe_get_form_data(self.form_data, key, default)

class DocumentUpload(models.Model):
    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('rejected', 'Rejected'),
        ('superseded', 'Superseded'),
    ]

    AVAILABILITY_CHOICES = [
        ('uploaded', 'File Caricato'),
        ('not_available', 'Non Disponibile'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_assignment = models.ForeignKey(FormAssignment, on_delete=models.CASCADE)
    document_requirement = models.ForeignKey(DocumentRequirement, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    stored_filename = models.CharField(max_length=255, blank=True, null=True)
    relative_path = models.CharField(max_length=500, blank=True, null=True)
    file_extension = models.CharField(max_length=10, blank=True, null=True)
    mime_type_detected = models.CharField(max_length=100, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)
    sha256_checksum = models.CharField(max_length=64, blank=True, null=True)
    upload_datetime = models.DateTimeField(auto_now_add=True)
    uploaded_by_ip = models.GenericIPAddressField()
    uploaded_by_user_agent = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='valid')
    rejection_reason = models.TextField(blank=True, null=True)
    version = models.IntegerField(default=1)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    # NEW: Availability status (uploaded or not_available with reason)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='uploaded')
    motivazione_indisponibilita = models.TextField(blank=True, null=True, help_text="Reason why document is not available")

    class Meta:
        ordering = ['-upload_datetime']
        indexes = [
            models.Index(fields=['form_assignment']),
            models.Index(fields=['document_requirement']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.form_assignment.customer.code})"

class AwarenessDeclaration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_assignment = models.ForeignKey(FormAssignment, on_delete=models.CASCADE)
    document_requirement = models.ForeignKey(DocumentRequirement, on_delete=models.CASCADE, null=True, blank=True)
    declaration_text = models.TextField()
    accepted = models.BooleanField(default=False)
    acceptance_datetime = models.DateTimeField(auto_now_add=True)
    acceptance_ip = models.GenericIPAddressField()
    acceptance_user_agent = models.TextField()
    customer_name_declared = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-acceptance_datetime']
        indexes = [
            models.Index(fields=['form_assignment']),
            models.Index(fields=['document_requirement']),
        ]

    def __str__(self):
        return f"Declaration {self.id} - {self.form_assignment.customer.code}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('submit', 'Submit'),
        ('view', 'View'),
        ('upload', 'Upload'),
        ('login', 'Login'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_datetime = models.DateTimeField(auto_now_add=True)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    actor_ip = models.GenericIPAddressField()
    actor_user_agent = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-action_datetime']
        indexes = [
            models.Index(fields=['actor_user', 'action_datetime']),
            models.Index(fields=['object_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.action} - {self.object_type} - {self.action_datetime}"

class NotificationLog(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('form_assigned', 'Form Assigned'),
        ('form_submitted', 'Form Submitted'),
        ('document_uploaded', 'Document Uploaded'),
        ('form_expired', 'Form Expired'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    recipient_email = models.EmailField()
    notification_datetime = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-notification_datetime']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['notification_datetime']),
        ]


    def __str__(self):
        return f"{self.notification_type} - {self.recipient_email} ({self.status})"

class SystemSetting(models.Model):
    """Stores global system configurations (key-value) accessible by administrators."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, unique=True, help_text="Unique configuration key (e.g., nas_base_path)")
    value = models.TextField(blank=True, help_text="Configuration value")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['key']
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.key
