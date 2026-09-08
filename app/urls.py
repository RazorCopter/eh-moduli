from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from modules.views_health import health_live, health_ready
from modules import views_admin

urlpatterns = [
    # Root redirect → dashboard (main landing page)
    path('', RedirectView.as_view(url='/modules/admin/', permanent=False), name='home'),

    # Health check endpoints (for Docker, Kubernetes, monitoring)
    path('health/', health_live, name='health_live'),  # Liveness probe (simple)
    path('health/live/', health_live, name='health_live_v2'),  # Liveness probe (explicit)
    path('health/ready/', health_ready, name='health_ready'),  # Readiness probe (checks DB + storage)

    # Client portal direct root aliases (e.g. updoc.etichub.it/clienti/)
    path('clienti/', RedirectView.as_view(url='/modules/client/login/', permanent=False), name='clienti_portal_root'),
    path('client/', RedirectView.as_view(url='/modules/client/login/', permanent=False), name='client_portal_root'),

    # User Management API endpoints (accessible both at /admin/api/ and /modules/admin/api/)
    path('admin/api/users/', include([
        path('', views_admin.admin_user_list, name='admin_user_list_root'),
        path('create/', views_admin.admin_user_create, name='admin_user_create_root'),
        path('<int:user_id>/update/', views_admin.admin_user_update, name='admin_user_update_root'),
        path('<int:user_id>/delete/', views_admin.admin_user_delete, name='admin_user_delete_root'),
    ])),
    path('admin/api/password/generate/', views_admin.admin_user_password_generate, name='admin_password_generate_root'),

    # Admin and application URLs
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('modules/', include('modules.urls')),
]
