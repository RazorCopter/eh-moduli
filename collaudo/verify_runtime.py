"""Black-box multi-process checks against Gunicorn, PostgreSQL and Redis."""
import io
import multiprocessing
import os
import sys
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django

django.setup()

import requests
from django.core.cache import caches
from django.db import close_old_connections, connection
from reportlab.pdfgen.canvas import Canvas

from modules.models import DocumentUpload, FormAssignment


BASE_URL = os.environ.get("BASE_URL", "http://app:8000").rstrip("/")
ASSIGNMENT_ID = "50000000-0000-0000-0000-000000000001"
CUSTOMER_CODE = "COLLAUDO-UI"
CUSTOMER_PASSWORD = "Collaudo-Cliente-Only-2026!"


def csrf(session, path):
    response = session.get(BASE_URL + path, timeout=20)
    response.raise_for_status()
    return session.cookies["csrftoken"]


def login_customer(session):
    token = csrf(session, "/modules/client/login/")
    response = session.post(
        BASE_URL + "/modules/client/login/",
        data={"code": CUSTOMER_CODE, "password": CUSTOMER_PASSWORD},
        headers={"X-CSRFToken": token, "Referer": BASE_URL + "/modules/client/login/"},
        allow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    if "/modules/client/dashboard/" not in response.url:
        raise AssertionError(f"customer login did not reach dashboard: {response.status_code} {response.url}")
    response = session.get(BASE_URL + f"/modules/client/product/{ASSIGNMENT_ID}/", timeout=30)
    response.raise_for_status()


def pdf_bytes(label):
    buffer = io.BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(50, 750, f"Synthetic collaudo document {label}")
    canvas.save()
    return buffer.getvalue()


def upload_worker(index):
    close_old_connections()
    with requests.Session() as session:
        login_customer(session)
        token = session.cookies["csrftoken"]
        response = session.post(
            BASE_URL + f"/modules/form/{ASSIGNMENT_ID}/upload/",
            data={"requirement_id": "40000000-0000-0000-0000-000000000001"},
            files={"file": (f"concurrent-{index}.pdf", pdf_bytes(index), "application/pdf")},
            headers={"X-CSRFToken": token, "Referer": BASE_URL + f"/modules/form/{ASSIGNMENT_ID}/step/0/"},
            timeout=60,
        )
        return response.status_code, response.text[:300]


def login_attempt(_):
    with requests.Session() as session:
        token = csrf(session, "/modules/client/login/")
        response = session.post(
            BASE_URL + "/modules/client/login/",
            data={"code": "INESISTENTE", "password": "errata"},
            headers={"X-CSRFToken": token, "Referer": BASE_URL + "/modules/client/login/"},
            timeout=30,
        )
        return response.status_code


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    close_old_connections()
    print(f"database_vendor={connection.vendor}")
    print(f"database_name={connection.settings_dict['NAME']}")
    print(f"ratelimit_cache={caches['ratelimit'].__class__.__module__}.{caches['ratelimit'].__class__.__name__}")
    assert connection.vendor == "postgresql"
    assert "redis" in caches["ratelimit"].__class__.__module__.lower()

    DocumentUpload.objects.filter(form_assignment_id=ASSIGNMENT_ID).delete()
    caches["ratelimit"].clear()
    close_old_connections()
    with ProcessPoolExecutor(max_workers=4) as pool:
        upload_results = list(pool.map(upload_worker, range(4)))
    close_old_connections()
    successful = sum(status == 200 for status, _ in upload_results)
    limited_by_capacity = sum(status == 400 for status, _ in upload_results)
    valid_count = DocumentUpload.objects.filter(
        form_assignment_id=ASSIGNMENT_ID,
        status="valid",
    ).count()
    print(f"concurrent_upload_statuses={[status for status, _ in upload_results]}")
    print(f"concurrent_upload_success={successful} capacity_rejections={limited_by_capacity} valid_rows={valid_count}")
    assert successful == 2 and limited_by_capacity == 2 and valid_count == 2, upload_results

    caches["ratelimit"].clear()
    close_old_connections()
    with ProcessPoolExecutor(max_workers=12) as pool:
        rate_statuses = list(pool.map(login_attempt, range(12)))
    print(f"concurrent_login_statuses={rate_statuses}")
    print(f"rate_limit_200={rate_statuses.count(200)} rate_limit_429={rate_statuses.count(429)}")
    assert rate_statuses.count(200) == 10
    assert rate_statuses.count(429) == 2
    print("runtime_probe=PASS")
