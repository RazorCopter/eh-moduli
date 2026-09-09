from django.urls import path
from . import views
from . import forms_api
from . import views_client
from . import views_admin

urlpatterns = [
    # Admin panel
    path('admin/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin/templates/', views_admin.form_template_list, name='form_template_list'),
    path('admin/templates/create/', views_admin.form_template_create, name='form_template_create'),
    path('admin/templates/<uuid:pk>/edit/', views_admin.form_template_edit, name='form_template_edit'),
    path('admin/templates/<uuid:pk>/duplicate/', views_admin.form_template_duplicate, name='form_template_duplicate'),
    path('admin/builder/', views_admin.builder_list, name='builder_list'),
    path('admin/builder/new/', views_admin.builder_create, name='builder_create'),
    path('admin/builder/<uuid:pk>/edit/', views_admin.builder_edit, name='builder_edit'),
    path('admin/builder/<uuid:pk>/preview/', views_admin.builder_preview, name='builder_preview'),
    path('admin/customers/', views_admin.customer_list, name='customer_list'),
    path('admin/customers/create/', views_admin.customer_create, name='customer_create'),
    path('admin/customers/<uuid:pk>/edit/', views_admin.customer_edit, name='customer_edit'),
    path('admin/customers/<uuid:pk>/delete/', views_admin.customer_delete, name='customer_delete'),
    path('admin/customers/<uuid:pk>/reset-password/', views_admin.customer_reset_password, name='customer_reset_password'),
    path('admin/assign-form/', views_admin.assign_form_to_customer, name='assign_form_to_customer'),
    path('admin/assignments/<uuid:pk>/', views_admin.assignment_detail, name='assignment_detail'),
    path('admin/assignments/<uuid:pk>/update-status/', views_admin.assignment_update_status, name='assignment_update_status'),
    path('admin/assignments/<uuid:pk>/reopen/', views_admin.reopen_assignment_for_upload, name='reopen_assignment'),
    path('admin/assignments/<uuid:pk>/delete/', views_admin.assignment_delete, name='assignment_delete'),
    path('admin/guide/', views_admin.operational_guide, name='operational_guide'),
    path('admin/analytics/', views_admin.analytics_dashboard, name='analytics_dashboard'),

    # Admin System Maintenance & Database Backup
    path('admin/maintenance/', views_admin.admin_maintenance, name='admin_maintenance'),
    path('admin/maintenance/settings/update/', views_admin.admin_update_settings, name='admin_update_settings'),
    path('admin/maintenance/reset-stats/', views_admin.admin_reset_statistics, name='admin_reset_statistics'),
    path('admin/maintenance/backup/create/', views_admin.admin_backup_create, name='admin_backup_create'),
    path('admin/maintenance/backup/<str:filename>/download/', views_admin.admin_backup_download, name='admin_backup_download'),
    path('admin/maintenance/backup/restore/', views_admin.admin_backup_restore, name='admin_backup_restore'),
    path('admin/maintenance/backup/<str:filename>/delete/', views_admin.admin_backup_delete, name='admin_backup_delete'),

    # Admin User Management API
    path('admin/api/users/', views_admin.admin_user_list, name='admin_user_list'),
    path('admin/api/users/create/', views_admin.admin_user_create, name='admin_user_create'),
    path('admin/api/users/<int:user_id>/update/', views_admin.admin_user_update, name='admin_user_update'),
    path('admin/api/users/<int:user_id>/delete/', views_admin.admin_user_delete, name='admin_user_delete'),
    path('admin/api/password/generate/', views_admin.admin_user_password_generate, name='admin_password_generate'),

    # API v1 endpoints
    path('api/v1/forms/', forms_api.api_forms_list, name='api_forms_list'),
    path('api/v1/forms/create/', forms_api.api_form_create, name='api_form_create'),
    path('api/v1/forms/<uuid:form_id>/', forms_api.api_form_detail, name='api_form_detail'),
    path('api/v1/forms/<uuid:form_id>/save/', forms_api.api_form_save, name='api_form_save'),
    path('api/v1/forms/<uuid:form_id>/publish/', forms_api.api_form_publish, name='api_form_publish'),
    path('api/v1/forms/<uuid:form_id>/revert-to-draft/', forms_api.api_form_revert_to_draft, name='api_form_revert_to_draft'),
    path('api/v1/forms/<uuid:form_id>/duplicate/', forms_api.api_form_duplicate, name='api_form_duplicate'),
    path('api/v1/forms/<uuid:form_id>/delete/', forms_api.api_form_delete, name='api_form_delete'),
    path('api/v1/customers/create/', forms_api.api_customer_create, name='api_customer_create'),
    path('api/v1/customers/<uuid:customer_id>/delete/', forms_api.api_customer_delete, name='api_customer_delete'),

    # Client Personal Area
    path('clienti/', views_client.client_login, name='clienti_login'),
    path('client/login/', views_client.client_login, name='client_login'),
    path('client/logout/', views_client.client_logout, name='client_logout'),
    path('client/dashboard/', views_client.client_dashboard, name='client_dashboard'),
    path('client/product/<uuid:assignment_id>/', views_client.client_product_detail, name='client_product_detail'),
    path('client/set-language/<str:lang_code>/', views_client.set_client_language, name='set_client_language'),
    path('client/set-language/', views_client.set_client_language, name='set_client_language_query'),

    # Public form views
    path('form/published/<uuid:form_id>/', views.published_form_access, name='published_form_access'),
    path('form/published/<uuid:form_id>/submit/', views.published_form_submit, name='published_form_submit'),
    path('form/published/<uuid:form_id>/upload/', views.published_form_upload, name='published_form_upload'),
    path('form/published/<uuid:form_id>/receipt/', views.published_form_receipt, name='published_form_receipt'),
    path('form/assignment/<uuid:assignment_id>/receipt/', views.assignment_receipt, name='assignment_receipt'),
    path('form/success/', views.form_success_view, name='form_success_view'),
    path('form/<str:token>/', views.get_form_by_token, name='get_form_by_token'),
    path('form/<uuid:assignment_id>/step/<int:step_order>/', views.form_step_view, name='form_step_view'),
    path('form/<uuid:assignment_id>/upload/', views.upload_document_view, name='upload_document_view'),
    path('form/<uuid:assignment_id>/upload/<uuid:upload_id>/delete/', views.delete_upload_view, name='delete_upload_view'),
    path('form/<uuid:assignment_id>/skip-document/<uuid:requirement_id>/', views.skip_optional_document, name='skip_optional_document'),
    path('form/<uuid:assignment_id>/summary/', views.form_summary_view, name='form_summary_view'),
    path('form/<uuid:assignment_id>/submit/', views.form_submission_view, name='form_submission_view'),
]
