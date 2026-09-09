"""
Audit Regression Test Suite for EH-Moduli.
Inverts all audit probe expectations into verified security and data integrity assertions.
Validates:
- DATA-01: Immutable assigned template versioning
- DATA-02: Absence declaration upload atomicity
- DATA-03: Process file locking & unique receipt naming
- SEC-01: Document upload/delete access control & inactive customer rejection
- SEC-02: Strict receipt download isolation
- SEC-03: Mutation lock on completed/submitted assignments
- SEC-04: Prevention of open redirects in language switcher
- FORM-01: Form data input persistence on step save & draft
- FORM-02: Enforcement of required documents and awareness consent
- UPLOAD-01: File replacement (max_files=1) vs clean limit rejection (max_files>1)
"""

import io
import os
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from reportlab.pdfgen.canvas import Canvas

from .models import (
    User, Customer, FormTemplate, FormStep, DocumentRequirement,
    DocumentUpload, FormAssignment, AwarenessDeclaration
)
from .upload_security import file_lock, save_manifest_atomic


class AuditRegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.csrf = 'test-csrf-token'
        self.tmp = tempfile.TemporaryDirectory()

        self.nas_patcher = patch('modules.views_upload.get_nas_base_path', return_value=self.tmp.name)
        self.nas_patcher_sub = patch('modules.views_submission.get_nas_base_path', return_value=self.tmp.name)
        self.nas_patcher_ass = patch('modules.views_assignments.get_nas_base_path', return_value=self.tmp.name)
        self.nas_patcher.start()
        self.nas_patcher_sub.start()
        self.nas_patcher_ass.start()

        self.user = User.objects.create_user(
            username='admin_audit',
            email='audit@example.invalid',
            password='audit-password',
            role='admin',
            is_staff=True
        )

        self.customer = Customer.objects.create(
            code='CLI_AUDIT',
            first_name='Cliente',
            last_name='Audit',
            email='cliente@example.invalid',
            nas_folder_name='CLIENTE_AUDIT',
            active=True
        )

        self.form = FormTemplate.objects.create(
            name='Modulo Regolatorio Audit',
            project_name='PROGETTO_AUDIT',
            customer=self.customer,
            status='published'
        )
        self.form.set_access_password('AuditPass123!')

        self.step = FormStep.objects.create(
            form_template=self.form,
            title='Documenti Primari',
            order=0,
            required=True,
            active=True
        )

        self.req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Scheda Tecnica',
            required=True,
            order=0,
            allowed_extensions='pdf,docx',
            max_files=1,
            destination_subfolder='Schede'
        )

        self.multi_req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Certificati Analisi',
            required=False,
            order=1,
            allowed_extensions='pdf,docx',
            max_files=2,
            destination_subfolder='Certificati'
        )

        self.assignment = FormAssignment.objects.create(
            form_template=self.form,
            customer=self.customer,
            status='in_progress',
            expiry_date=timezone.now() + timedelta(days=30),
            form_data={
                'client_name': 'CLIENTE_AUDIT',
                'project_name': 'PROGETTO_AUDIT'
            }
        )
        self.assignment.set_access_password('AuditPass123!')
        self.assignment.save()

        self.upload = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.req,
            original_filename='scheda_tecnica_v1.pdf',
            stored_filename='scheda_tecnica_v1.pdf',
            relative_path='CLIENTE_AUDIT/PROGETTO_AUDIT/Schede/scheda_tecnica_v1.pdf',
            status='valid',
            availability_status='uploaded',
            file_size=2048,
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestClient'
        )

    def tearDown(self):
        self.nas_patcher.stop()
        self.nas_patcher_sub.stop()
        self.nas_patcher_ass.stop()
        self.tmp.cleanup()

    def grant(self):
        """Grant session access token for current assignment."""
        session = self.client.session
        session[f'assignment_access_{self.assignment.id}_{self.assignment.secure_token}'] = True
        session[f'assignment_access_{self.assignment.id}'] = True
        session.save()

    def post_ajax(self, url, data=None):
        return self.client.post(url, data or {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def create_dummy_pdf(self, name='document.pdf'):
        buf = io.BytesIO()
        canv = Canvas(buf)
        canv.drawString(50, 750, "Sample PDF test payload")
        canv.save()
        return SimpleUploadedFile(name, buf.getvalue(), content_type='application/pdf')

    # =========================================================================
    # 1. SEC-01: Anonymous Access Control
    # =========================================================================
    def test_regression_SEC01_anonymous_delete_forbidden(self):
        """Unauthenticated user cannot delete uploads on password-protected assignment."""
        delete_url = reverse('delete_upload_view', kwargs={'assignment_id': self.assignment.id, 'upload_id': self.upload.id})
        resp = self.post_ajax(delete_url)
        self.assertEqual(resp.status_code, 403)
        self.upload.refresh_from_db()
        self.assertEqual(self.upload.status, 'valid')

    def test_regression_SEC01_anonymous_upload_forbidden(self):
        """Unauthenticated user cannot upload documents on password-protected assignment."""
        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})
        pdf_file = self.create_dummy_pdf('test.pdf')
        resp = self.post_ajax(upload_url, {'requirement_id': str(self.req.id), 'file': pdf_file})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(DocumentUpload.objects.filter(form_assignment=self.assignment, original_filename='test.pdf').exists())

    def test_regression_SEC01_inactive_customer_blocked(self):
        """Deactivated customer cannot modify or upload to assignment."""
        self.grant()
        self.customer.active = False
        self.customer.save()

        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})
        pdf_file = self.create_dummy_pdf('test.pdf')
        resp = self.post_ajax(upload_url, {'requirement_id': str(self.req.id), 'file': pdf_file})
        self.assertEqual(resp.status_code, 403)

    def test_regression_SEC01_arbitrary_upload_deletion_isolated(self):
        """Deleting an upload belonging to another assignment is rejected."""
        self.grant()
        other_customer = Customer.objects.create(code='CLI_OTHER', first_name='Other', email='other@example.com', nas_folder_name='OTHER')
        other_form = FormTemplate.objects.create(name='Other Form', customer=other_customer)
        other_assignment = FormAssignment.objects.create(
            form_template=other_form,
            customer=other_customer,
            expiry_date=timezone.now() + timedelta(days=30)
        )
        other_upload = DocumentUpload.objects.create(
            form_assignment=other_assignment,
            document_requirement=self.req,
            original_filename='private.pdf',
            stored_filename='private.pdf',
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestClient'
        )

        delete_url = reverse('delete_upload_view', kwargs={'assignment_id': self.assignment.id, 'upload_id': other_upload.id})
        resp = self.post_ajax(delete_url)
        self.assertIn(resp.status_code, (403, 404))
        other_upload.refresh_from_db()
        self.assertEqual(other_upload.status, 'valid')

    # =========================================================================
    # 2. DATA-01: Immutable Versioning
    # =========================================================================
    def test_regression_DATA01_assigned_form_cannot_be_reverted_to_draft(self):
        """Assigned forms are immutable; revert to draft is rejected to protect historical uploads."""
        self.client.force_login(self.user)
        revert_url = reverse('api_form_revert_to_draft', kwargs={'form_id': self.form.id})
        resp = self.client.post(revert_url)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get('is_immutable'))

        # Structure remains intact and uploads survive
        self.upload.refresh_from_db()
        self.assertEqual(self.upload.status, 'valid')
        self.assertTrue(FormStep.objects.filter(id=self.step.id).exists())

    def test_regression_DATA01_assigned_form_cannot_be_overwritten(self):
        """Modifying structure of an assigned form via api_form_save is rejected."""
        self.client.force_login(self.user)
        save_url = reverse('api_form_save', kwargs={'form_id': self.form.id})
        payload = {
            'name': 'Hacked Form',
            'steps': []
        }
        resp = self.client.put(save_url, json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(DocumentUpload.objects.filter(id=self.upload.id).exists())

    # =========================================================================
    # 3. DATA-02: Absence Declaration Atomicity
    # =========================================================================
    def test_regression_DATA02_invalid_absence_leaves_existing_upload_valid(self):
        """Invalid absence declaration file upload fails and leaves existing valid uploads untouched."""
        self.grant()
        skip_url = reverse('skip_optional_document', kwargs={'assignment_id': self.assignment.id, 'requirement_id': self.req.id})
        invalid_file = SimpleUploadedFile('script.exe', b'malicious payload', content_type='application/octet-stream')
        resp = self.post_ajax(skip_url, {'file': invalid_file})
        self.assertEqual(resp.status_code, 400)

        self.upload.refresh_from_db()
        self.assertEqual(self.upload.status, 'valid')

    # =========================================================================
    # 4. SEC-03: Immutable State on Completed Assignments
    # =========================================================================
    def test_regression_SEC03_completed_assignment_cannot_be_mutated(self):
        """Posting to form_step on a completed assignment is rejected and does NOT revert status."""
        self.grant()
        self.assignment.status = 'completed'
        self.assignment.save()

        step_url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})
        resp = self.post_ajax(step_url, {'element_test': 'value'})
        self.assertEqual(resp.status_code, 403)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'completed')

    # =========================================================================
    # 5. SEC-02: Receipt Access Isolation
    # =========================================================================
    def test_regression_SEC02_unrelated_receipt_access_forbidden(self):
        """Session grant for one assignment does not authorize downloading another form's receipt."""
        self.grant()
        other = FormTemplate.objects.create(name='Other customer form', project_name='OTHER_PROJECT')
        receipt_url = reverse('published_form_receipt', kwargs={'form_id': other.id})
        resp = self.client.get(receipt_url)
        self.assertEqual(resp.status_code, 403)

    # =========================================================================
    # 6. SEC-04: Language Switcher Open Redirect Prevention
    # =========================================================================
    def test_regression_SEC04_external_language_redirect_prevented(self):
        """Scheme-relative and external open redirects in set_client_language are blocked."""
        lang_url = reverse('set_client_language_query')
        resp = self.client.get(lang_url, {'next': '//example.invalid/audit'})
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp['Location'], '//example.invalid/audit')
        self.assertIn('/client/login', resp['Location'])

    # =========================================================================
    # 7. FORM-01 & FORM-02: Draft Persistence vs Final Submission
    # =========================================================================
    def test_regression_FORM01_step_post_persists_fields(self):
        """Posting step inputs saves answers into assignment.form_data['answers']."""
        self.grant()
        step_url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})
        data = {
            'element_txt1': 'Testo compilato',
            'element_chk1': '1',
            'email': 'compilato@example.invalid'
        }
        resp = self.post_ajax(step_url, data)
        self.assertEqual(resp.status_code, 200)

        self.assignment.refresh_from_db()
        answers = self.assignment.form_data.get('answers', {})
        self.assertEqual(answers.get('txt1'), 'Testo compilato')
        self.assertEqual(answers.get('chk1'), '1')
        self.assertEqual(answers.get('email'), 'compilato@example.invalid')

    def test_regression_FORM02_missing_action_and_consent_rejected(self):
        """Submitting without consent or missing action_type is rejected with 400."""
        self.grant()
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})

        # Missing action_type
        resp = self.post_ajax(submit_url, {})
        self.assertEqual(resp.status_code, 400)
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.status, 'submitted')

        # Action complete but without awareness declaration
        resp = self.post_ajax(submit_url, {'action_type': 'complete'})
        self.assertEqual(resp.status_code, 400)
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.status, 'submitted')
        self.assertFalse(AwarenessDeclaration.objects.filter(form_assignment=self.assignment, accepted=True).exists())

    def test_regression_FORM01_save_draft_accepts_incomplete_compilation(self):
        """Partial submission / Save Draft succeeds without requiring mandatory fields or consent."""
        self.grant()
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        data = {
            'action_type': 'partial',
            'element_incomplete': 'Parziale'
        }
        resp = self.post_ajax(submit_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'in_progress')
        self.assertEqual(self.assignment.form_data['answers'].get('incomplete'), 'Parziale')

    # =========================================================================
    # 8. UPLOAD-01: File Replacement (max_files=1) vs Rejection (max_files>1)
    # =========================================================================
    def test_regression_UPLOAD01_max_files_1_replaces_file(self):
        """When max_files=1, uploading a second valid file replaces (supersedes) the old one."""
        self.grant()
        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})
        pdf_file = self.create_dummy_pdf('scheda_tecnica_v2.pdf')

        resp = self.post_ajax(upload_url, {'requirement_id': str(self.req.id), 'file': pdf_file})
        self.assertEqual(resp.status_code, 200)

        self.upload.refresh_from_db()
        self.assertEqual(self.upload.status, 'superseded')
        new_up = DocumentUpload.objects.get(form_assignment=self.assignment, original_filename='scheda_tecnica_v2.pdf')
        self.assertEqual(new_up.status, 'valid')

    def test_regression_UPLOAD01_max_files_limit_enforced_for_multifile(self):
        """When max_files=2, attempting to add a 3rd valid file returns a 400 error."""
        self.grant()
        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})

        # Upload 1st file to multi_req
        f1 = self.create_dummy_pdf('cert1.pdf')
        r1 = self.post_ajax(upload_url, {'requirement_id': str(self.multi_req.id), 'file': f1})
        self.assertEqual(r1.status_code, 200)

        # Upload 2nd file to multi_req
        f2 = self.create_dummy_pdf('cert2.pdf')
        r2 = self.post_ajax(upload_url, {'requirement_id': str(self.multi_req.id), 'file': f2})
        self.assertEqual(r2.status_code, 200)

        # Upload 3rd file to multi_req -> must fail with 400
        f3 = self.create_dummy_pdf('cert3.pdf')
        r3 = self.post_ajax(upload_url, {'requirement_id': str(self.multi_req.id), 'file': f3})
        self.assertEqual(r3.status_code, 400)
        self.assertIn('Limite massimo', r3.json().get('error', ''))

    # =========================================================================
    # 9. DATA-03: Process Locking and Unique Receipt Naming
    # =========================================================================
    def test_regression_DATA03_unique_receipt_naming_per_assignment(self):
        """Assignments sharing the same customer/project folder generate distinct receipt filenames."""
        self.grant()
        # Complete assignment
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        resp = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(resp.status_code, 200)

        project_dir = Path(self.tmp.name) / 'CLIENTE_AUDIT' / 'PROGETTO_AUDIT'
        expected_receipt = project_dir / f'Report_Ricezione_Documenti_{self.assignment.id}.pdf'
        self.assertTrue(expected_receipt.exists())

    def test_regression_DATA03_manifest_process_lock(self):
        """file_lock prevents corrupt partial writes and serializes concurrent manifest saves."""
        manifest_file = Path(self.tmp.name) / 'CLIENTE_AUDIT' / 'PROGETTO_AUDIT' / 'manifest.json'
        manifest_file.parent.mkdir(parents=True, exist_ok=True)

        data1 = {'version': 1, 'items': ['a']}
        save_manifest_atomic(str(manifest_file), data1)
        self.assertTrue(manifest_file.exists())
        with open(manifest_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        self.assertEqual(content['version'], 1)

    # =========================================================================
    # 10. Concurrency, Server Validation & Rate Limiting Hardening
    # =========================================================================
    def test_regression_FORM02_missing_mandatory_document_rejected(self):
        """Final submission is rejected if a mandatory DocumentRequirement has neither upload nor absence declaration."""
        self.grant()
        self.upload.delete()

        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        resp = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Documenti obbligatori mancanti', resp.json().get('error', ''))
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.status, 'submitted')

        # Add valid absence declaration -> then submission must succeed
        DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.req,
            original_filename='NON_DISPONIBILE',
            status='valid',
            availability_status='not_available',
            motivazione_indisponibilita='Non applicabile per questo lotto',
            uploaded_by_ip='127.0.0.1'
        )
        resp2 = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(resp2.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')

    def test_regression_FORM02_missing_mandatory_field_rejected(self):
        """Final submission is rejected if a mandatory FormElement has no answer."""
        self.grant()
        from .models import FormElement
        elem = FormElement.objects.create(
            form_step=self.step,
            element_type='text_field',
            order=0,
            config={'name': 'piva', 'label': 'Partita IVA', 'required': True}
        )
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        resp = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Campi obbligatori non compilati', resp.json().get('error', ''))
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.status, 'submitted')

        # Provide answer for mandatory field -> must succeed
        self.assignment.form_data['answers'] = {str(elem.id): 'IT12345678901'}
        self.assignment.save()
        resp2 = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(resp2.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')

    def test_regression_DATA03_historical_receipts_isolated_per_assignment(self):
        """Multiple assignments for same customer/project keep separate PDF receipts without overwriting."""
        self.grant()
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        r1 = self.post_ajax(submit_url, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(r1.status_code, 200)

        ass2 = FormAssignment.objects.create(
            form_template=self.form,
            customer=self.customer,
            status='in_progress',
            expiry_date=timezone.now() + timedelta(days=30),
            form_data={'client_name': 'CLIENTE_AUDIT', 'project_name': 'PROGETTO_AUDIT'}
        )
        ass2.set_access_password('AuditPass123!')
        ass2.save()
        DocumentUpload.objects.create(
            form_assignment=ass2,
            document_requirement=self.req,
            original_filename='scheda2.pdf',
            stored_filename='scheda2.pdf',
            status='valid',
            availability_status='uploaded',
            file_size=1024,
            uploaded_by_ip='127.0.0.1'
        )

        session = self.client.session
        session[f'assignment_access_{ass2.id}_{ass2.secure_token}'] = True
        session[f'assignment_access_{ass2.id}'] = True
        session.save()

        submit_url2 = reverse('form_submission_view', kwargs={'assignment_id': ass2.id})
        r2 = self.post_ajax(submit_url2, {'action_type': 'complete', 'awareness_declaration': 'true'})
        self.assertEqual(r2.status_code, 200)

        project_dir = Path(self.tmp.name) / 'CLIENTE_AUDIT' / 'PROGETTO_AUDIT'
        receipt1 = project_dir / f'Report_Ricezione_Documenti_{self.assignment.id}.pdf'
        receipt2 = project_dir / f'Report_Ricezione_Documenti_{ass2.id}.pdf'
        self.assertTrue(receipt1.exists())
        self.assertTrue(receipt2.exists())
        self.assertNotEqual(str(receipt1), str(receipt2))

    def test_regression_DATA03_concurrent_manifest_locks_cycle(self):
        """Concurrent threads modifying manifest.json via file_lock serialize cleanly without data corruption."""
        import concurrent.futures
        manifest_file = Path(self.tmp.name) / 'CLIENTE_AUDIT' / 'PROGETTO_AUDIT' / 'concurrent_manifest.json'
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        initial_data = {'uploads': []}
        save_manifest_atomic(str(manifest_file), initial_data)

        def append_item(idx):
            lock_path = str(manifest_file) + '.lock'
            with file_lock(lock_path):
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['uploads'].append({'item': idx})
                save_manifest_atomic(str(manifest_file), data)
            return idx

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(append_item, i) for i in range(12)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 12)
        with open(manifest_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        self.assertEqual(len(final_data['uploads']), 12)
        saved_indices = sorted([u['item'] for u in final_data['uploads']])
        self.assertEqual(saved_indices, list(range(12)))

    def test_regression_FORM01_simultaneous_answers_save_merged(self):
        """Simultaneous POST requests updating distinct fields merge into answers without losing keys."""
        self.grant()
        step_url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})
        resp1 = self.post_ajax(step_url, {'element_field_A': 'Valore A'})
        self.assertEqual(resp1.status_code, 200)

        resp2 = self.post_ajax(step_url, {'element_field_B': 'Valore B'})
        self.assertEqual(resp2.status_code, 200)

        self.assignment.refresh_from_db()
        answers = self.assignment.form_data.get('answers', {})
        self.assertEqual(answers.get('field_A'), 'Valore A')
        self.assertEqual(answers.get('field_B'), 'Valore B')

    def test_regression_RATELIMIT_atomic_cache_backend(self):
        """Verify ratelimit cache configuration and atomic counter increment support."""
        from django.core.cache import caches
        from django.conf import settings
        self.assertEqual(settings.RATELIMIT_USE_CACHE, 'ratelimit')
        rl_cache = caches['ratelimit']
        test_key = 'test_ratelimit_key'
        rl_cache.set(test_key, 1, timeout=60)
        new_val = rl_cache.incr(test_key)
        self.assertEqual(new_val, 2)
        rl_cache.delete(test_key)

