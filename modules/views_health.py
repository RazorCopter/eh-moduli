"""
Health check endpoints for Docker and container orchestration.

Provides two endpoints:
- /health/live/  - Liveness probe (is the app running?)
- /health/ready/ - Readiness probe (is the app ready to serve traffic?)
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.conf import settings
import os
import tempfile


@require_http_methods(["GET"])
def health_live(request):
    """
    Liveness probe for Kubernetes/Docker.

    Simply indicates the Django process is alive and responding.
    Does not verify dependencies.

    Returns:
        HTTP 200: Process is running
        HTTP 503: Process is not responding (unlikely)
    """
    return JsonResponse(
        {
            "status": "live",
            "service": "document-collector",
        },
        status=200
    )


@require_http_methods(["GET"])
def health_ready(request):
    """
    Readiness probe for Kubernetes/Docker.

    Verifies the application is ready to serve traffic:
    1. Database connection is working
    2. Customer documents storage path is writable
    3. Application data path is writable

    Returns:
        HTTP 200: Application is ready
        HTTP 503: Application is not ready (missing dependencies)
    """

    checks = {
        "database": False,
        "storage": False,
        "data_dir": False,
    }

    details = {}

    # Check 1: Database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
        details["database"] = "Connected"
    except Exception as e:
        details["database"] = f"Failed: {str(e)}"

    # Check 2: Customer documents storage is writable
    try:
        storage_path = "/storage/clienti"
        if os.path.exists(storage_path) and os.path.isdir(storage_path):
            # Verify writable by attempting to create temp file
            test_file = os.path.join(storage_path, f".health_{os.getpid()}")
            with open(test_file, 'w') as f:
                f.write("health_check")
            os.remove(test_file)
            checks["storage"] = True
            details["storage"] = "Writable"
        else:
            details["storage"] = f"Path does not exist: {storage_path}"
    except Exception as e:
        details["storage"] = f"Not writable: {str(e)}"

    # Check 3: Application data directory is writable
    try:
        data_dir = os.path.join(settings.BASE_DIR, "data")
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            # Verify writable
            test_file = os.path.join(data_dir, f".health_{os.getpid()}")
            with open(test_file, 'w') as f:
                f.write("health_check")
            os.remove(test_file)
            checks["data_dir"] = True
            details["data_dir"] = "Writable"
        else:
            details["data_dir"] = f"Path does not exist: {data_dir}"
    except Exception as e:
        details["data_dir"] = f"Not writable: {str(e)}"

    # All checks must pass
    all_ready = all(checks.values())

    response_data = {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "details": details,
        "service": "document-collector",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    # Return 200 if ready, 503 if not
    status_code = 200 if all_ready else 503

    return JsonResponse(response_data, status=status_code)
