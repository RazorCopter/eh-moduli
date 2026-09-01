from django.urls import path
from . import views

urlpatterns = [
    # Admin panel
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/templates/', views.form_template_list, name='form_template_list'),
    path('admin/templates/create/', views.form_template_create, name='form_template_create'),
    path('admin/templates/<uuid:pk>/edit/', views.form_template_edit, name='form_template_edit'),
    path('admin/templates/<uuid:pk>/duplicate/', views.form_template_duplicate, name='form_template_duplicate'),
    path('admin/customers/', views.customer_list, name='customer_list'),
    path('admin/customers/create/', views.customer_create, name='customer_create'),
    path('admin/assign-form/', views.assign_form_to_customer, name='assign_form_to_customer'),
    path('admin/assignments/<uuid:pk>/', views.assignment_detail, name='assignment_detail'),

    # Public form views
    path('form/<str:token>/', views.get_form_by_token, name='get_form_by_token'),
    path('form/<uuid:assignment_id>/step/<int:step_order>/', views.form_step_view, name='form_step_view'),
    path('form/<uuid:assignment_id>/upload/', views.upload_document_view, name='upload_document_view'),
    path('form/<uuid:assignment_id>/skip-document/<uuid:requirement_id>/', views.skip_optional_document, name='skip_optional_document'),
    path('form/<uuid:assignment_id>/summary/', views.form_summary_view, name='form_summary_view'),
    path('form/<uuid:assignment_id>/submit/', views.form_submission_view, name='form_submission_view'),
]
