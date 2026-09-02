from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from modules.views_health import health_live, health_ready

urlpatterns = [
    # Root redirect → builder (modern form admin panel)
    path('', RedirectView.as_view(url='/modules/admin/builder/', permanent=False), name='home'),

    # Health check endpoints (for Docker, Kubernetes, monitoring)
    path('health/', health_live, name='health_live'),  # Liveness probe (simple)
    path('health/live/', health_live, name='health_live_v2'),  # Liveness probe (explicit)
    path('health/ready/', health_ready, name='health_ready'),  # Readiness probe (checks DB + storage)

    # Admin and application URLs
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('modules/', include('modules.urls')),
]
