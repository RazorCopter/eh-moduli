"""Create deterministic, entirely fictitious browser-test data (idempotent)."""
from datetime import timedelta
from uuid import UUID

from django.utils import timezone

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import django

django.setup()

from modules.models import (
    Customer,
    DocumentRequirement,
    FormAssignment,
    FormElement,
    FormStep,
    FormTemplate,
    User,
)


ADMIN_USERNAME = "collaudo_admin"
ADMIN_PASSWORD = "Collaudo-Admin-Only-2026!"
CUSTOMER_CODE = "COLLAUDO-UI"
CUSTOMER_PASSWORD = "Collaudo-Cliente-Only-2026!"
CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
FORM_ID = UUID("20000000-0000-0000-0000-000000000001")
STEP_ID = UUID("30000000-0000-0000-0000-000000000001")
REQUIREMENT_ID = UUID("40000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("50000000-0000-0000-0000-000000000001")


admin, _ = User.objects.update_or_create(
    username=ADMIN_USERNAME,
    defaults={
        "email": "admin-collaudo@example.invalid",
        "first_name": "Ada",
        "last_name": "Collaudo",
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
    },
)
admin.set_password(ADMIN_PASSWORD)
admin.save()

customer, _ = Customer.objects.update_or_create(
    id=CUSTOMER_ID,
    defaults={
        "code": CUSTOMER_CODE,
        "first_name": "Cliente",
        "last_name": "Dimostrativo Con Denominazione Molto Lunga",
        "email": "referente-collaudo-con-indirizzo-lungo@example.invalid",
        "nas_folder_name": "COLLAUDO_UI",
        "active": True,
        "notes": "Dato sintetico riservato al collaudo locale.",
    },
)
customer.set_portal_password(CUSTOMER_PASSWORD)
customer.save()

CUSTOMER_EMPTY_ID = UUID("10000000-0000-0000-0000-000000000002")
CUSTOMER_EMPTY_CODE = "COLLAUDO-EMPTY"
customer_empty, _ = Customer.objects.update_or_create(
    id=CUSTOMER_EMPTY_ID,
    defaults={
        "code": CUSTOMER_EMPTY_CODE,
        "first_name": "Cliente Senza",
        "last_name": "Pratiche Attive",
        "email": "cliente-vuoto@example.invalid",
        "nas_folder_name": "COLLAUDO_EMPTY",
        "active": True,
        "notes": "Dato sintetico per verifica empty state portale cliente.",
    },
)
customer_empty.set_portal_password(CUSTOMER_PASSWORD)
customer_empty.save()

form, _ = FormTemplate.objects.update_or_create(
    id=FORM_ID,
    defaults={
        "name": "Dossier cosmetico dimostrativo con titolo esteso",
        "description": "Modulo sintetico usato esclusivamente per verifiche locali.",
        "intro_text": "Completa i dati e allega i documenti richiesti.",
        "privacy_text": "Informativa sintetica per dati di collaudo.",
        "status": "published",
        "author": admin,
        "customer": customer,
        "project_name": "PROGETTO_COLLAUDO_UI",
    },
)
form.set_access_password(CUSTOMER_PASSWORD)
form.save()

step, _ = FormStep.objects.update_or_create(
    id=STEP_ID,
    defaults={
        "form_template": form,
        "title": "Documentazione tecnica",
        "description": "Inserisci i riferimenti e carica la documentazione disponibile.",
        "order": 0,
        "required": True,
        "active": True,
    },
)

FormElement.objects.update_or_create(
    form_step=step,
    order=0,
    defaults={
        "element_type": "text_field",
        "config": {
            "name": "referente",
            "label": "Referente della pratica",
            "placeholder": "Nome e cognome",
            "required": True,
        },
    },
)

DocumentRequirement.objects.update_or_create(
    id=REQUIREMENT_ID,
    defaults={
        "form_step": step,
        "name": "Scheda tecnica del prodotto con denominazione molto lunga",
        "description": "Documento PDF necessario per completare la pratica.",
        "required": True,
        "allowed_extensions": "pdf",
        "mime_types": "application/pdf",
        "max_file_size": 5 * 1024 * 1024,
        "max_files": 2,
        "destination_subfolder": "Schede",
        "order": 0,
        "awareness_required_when_empty": True,
    },
)

assignment, _ = FormAssignment.objects.update_or_create(
    id=ASSIGNMENT_ID,
    defaults={
        "customer": customer,
        "form_template": form,
        "expiry_date": timezone.now() + timedelta(days=30),
        "status": "in_progress",
        "completion_percentage": 20,
        "operator": admin,
        "form_data": {
            "client_name": "COLLAUDO_UI",
            "project_name": "PROGETTO_COLLAUDO_UI",
            "answers": {},
        },
    },
)
assignment.set_access_password(CUSTOMER_PASSWORD)
assignment.save()

print(f"seeded admin={ADMIN_USERNAME} customer={CUSTOMER_CODE} assignment={ASSIGNMENT_ID} form={FORM_ID}")
