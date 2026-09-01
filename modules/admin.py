from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Customer, FormTemplate, FormStep, DocumentRequirement,
    FormAssignment, DocumentUpload, AwarenessDeclaration, AuditLog, NotificationLog
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'email_verified', 'last_login_ip')}),
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('code', 'first_name', 'last_name', 'email', 'active')
    list_filter = ('active', 'created_at')
    search_fields = ('code', 'first_name', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'status', 'author', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(FormStep)
class FormStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'form_template', 'order', 'required', 'active')
    list_filter = ('required', 'active', 'form_template')
    search_fields = ('title', 'description')
    readonly_fields = ('id',)

@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ('name', 'form_step', 'required', 'order')
    list_filter = ('required', 'form_step')
    search_fields = ('name', 'description')
    readonly_fields = ('id',)

@admin.register(FormAssignment)
class FormAssignmentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'form_template', 'status', 'completion_percentage', 'assignment_date')
    list_filter = ('status', 'assignment_date')
    search_fields = ('customer__code', 'secure_token')
    readonly_fields = ('id', 'assignment_date', 'secure_token')

@admin.register(DocumentUpload)
class DocumentUploadAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'form_assignment', 'status', 'upload_datetime')
    list_filter = ('status', 'upload_datetime')
    search_fields = ('original_filename',)
    readonly_fields = ('id', 'sha256_checksum', 'upload_datetime')

@admin.register(AwarenessDeclaration)
class AwarenessDeclarationAdmin(admin.ModelAdmin):
    list_display = ('form_assignment', 'accepted', 'acceptance_datetime')
    list_filter = ('accepted', 'acceptance_datetime')
    readonly_fields = ('id', 'acceptance_datetime')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'object_type', 'actor_user', 'action_datetime', 'success')
    list_filter = ('action', 'success', 'action_datetime')
    search_fields = ('object_id', 'actor_user__username')
    readonly_fields = ('id', 'action_datetime')

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'recipient_email', 'status', 'notification_datetime')
    list_filter = ('notification_type', 'status', 'notification_datetime')
    search_fields = ('recipient_email',)
    readonly_fields = ('id', 'notification_datetime')
