from django.urls import path
from . import views
from . import forms_api

urlpatterns = [
    # Admin panel
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/templates/', views.form_template_list, name='form_template_list'),
    path('admin/templates/create/', views.form_template_create, name='form_template_create'),
    path('admin/templates/<uuid:pk>/edit/', views.form_template_edit, name='form_template_edit'),
    path('admin/templates/<uuid:pk>/duplicate/', views.form_template_duplicate, name='form_template_duplicate'),
    path('admin/builder/', views.builder_list, name='builder_list'),
    path('admin/builder/new/', views.builder_create, name='builder_create'),
    path('admin/builder/<uuid:pk>/edit/', views.builder_edit, name='builder_edit'),
    path('admin/builder/<uuid:pk>/preview/', views.builder_preview, name='builder_preview'),
    path('admin/customers/', views.customer_list, name='customer_list'),
    path('admin/customers/create/', views.customer_create, name='customer_create'),
    path('admin/customers/<uuid:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('admin/assign-form/', views.assign_form_to_customer, name='assign_form_to_customer'),
    path('admin/assignments/<uuid:pk>/', views.assignment_detail, name='assignment_detail'),
    path('admin/guide/', views.operational_guide, name='operational_guide'),

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

    # Public form views
    path('form/published/<uuid:form_id>/', views.published_form_access, name='published_form_access'),
    path('form/published/<uuid:form_id>/submit/', views.published_form_submit, name='published_form_submit'),
    path('form/published/<uuid:form_id>/upload/', views.published_form_upload, name='published_form_upload'),
    path('form/published/<uuid:form_id>/receipt/', views.published_form_receipt, name='published_form_receipt'),
    path('form/success/', views.form_success_view, name='form_success_view'),
    path('form/<str:token>/', views.get_form_by_token, name='get_form_by_token'),
    path('form/<uuid:assignment_id>/step/<int:step_order>/', views.form_step_view, name='form_step_view'),
    path('form/<uuid:assignment_id>/upload/', views.upload_document_view, name='upload_document_view'),
    path('form/<uuid:assignment_id>/skip-document/<uuid:requirement_id>/', views.skip_optional_document, name='skip_optional_document'),
    path('form/<uuid:assignment_id>/summary/', views.form_summary_view, name='form_summary_view'),
    path('form/<uuid:assignment_id>/submit/', views.form_submission_view, name='form_submission_view'),
]
