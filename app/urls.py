from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy'})

urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('modules/', include('modules.urls')),
]
