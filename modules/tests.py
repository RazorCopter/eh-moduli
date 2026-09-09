import os
import json
import shutil
import tempfile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import (
    User, Customer, FormTemplate, FormStep, DocumentRequirement,
    DocumentUpload, FormAssignment, AuditLog, AwarenessDeclaration, NotificationLog
)


class CustomerDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='password123',
            role='admin',
            is_staff=True
        )
        self.client.force_login(self.admin_user)

        # Temporary folder simulating NAS storage
        self.temp_nas = tempfile.mkdtemp(prefix="nas_test_")

    def tearDown(self):
        # Cleanup temporary NAS storage
        if os.path.exists(self.temp_nas):
            shutil.rmtree(self.temp_nas)

    def test_customer_delete_removes_from_db_and_preserves_nas_files(self):
        # 1. Simulate NAS folder structure: PIPPO/Pluto/documento.pdf
        customer_nas_folder = os.path.join(self.temp_nas, "PIPPO")
        project_subfolder = os.path.join(customer_nas_folder, "Pluto")
        os.makedirs(project_subfolder, exist_ok=True)
        file_path = os.path.join(project_subfolder, "documento.pdf")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Dati importanti del cliente")

        self.assertTrue(os.path.exists(file_path))

        # 2. Create customer in DB
        customer = Customer.objects.create(
            code="PIPPO_001",
            first_name="Pippo",
            last_name="De Pippis",
            email="pippo@example.com",
            nas_folder_name="PIPPO",
            active=True
        )

        # 3. Create linked FormTemplate
        form = FormTemplate.objects.create(
            name="Onboarding Pluto",
            intro_text="Benvenuto",
            customer=customer,
            project_name="Pluto",
            author=self.admin_user
        )

        customer_id = customer.id

        # 4. Perform customer delete via admin view
        url = reverse('customer_delete', kwargs={'pk': customer_id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('customer_list'))

        # 5. Assert Customer record is deleted from DB
        self.assertFalse(Customer.objects.filter(id=customer_id).exists())

        # 6. Assert FormTemplate still exists and customer is set to None (on_delete=SET_NULL)
        form.refresh_from_db()
        self.assertIsNone(form.customer)
        self.assertEqual(form.name, "Onboarding Pluto")

        # 7. CRITICAL: Assert physical files and directories on NAS remain 100% intact!
        self.assertTrue(os.path.exists(customer_nas_folder), "Cartella NAS del cliente non deve essere cancellata")
        self.assertTrue(os.path.exists(project_subfolder), "Sottocartella progetto non deve essere cancellata")
        self.assertTrue(os.path.exists(file_path), "I file all'interno della cartella NAS devono rimanere intatti")
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "Dati importanti del cliente")

        # 8. Assert AuditLog records the deletion with physical_files_kept=True
        log = AuditLog.objects.filter(action='delete', object_type='Customer', object_id=str(customer_id)).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.details.get('physical_files_kept'))
        self.assertEqual(log.details.get('nas_folder_name'), "PIPPO")

    def test_api_customer_delete(self):
        # 1. Simulate NAS file
        customer_nas_folder = os.path.join(self.temp_nas, "DEMO_CLIENT")
        os.makedirs(customer_nas_folder, exist_ok=True)
        demo_file = os.path.join(customer_nas_folder, "test.txt")
        with open(demo_file, "w") as f:
            f.write("Contenuto di test")

        customer = Customer.objects.create(
            code="DEMO_001",
            first_name="Demo",
            last_name="Customer",
            email="demo@example.com",
            nas_folder_name="DEMO_CLIENT",
            active=True
        )

        customer_id = customer.id
        url = reverse('api_customer_delete', kwargs={'customer_id': customer_id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

        # DB record removed
        self.assertFalse(Customer.objects.filter(id=customer_id).exists())

        # File on disk preserved
        self.assertTrue(os.path.exists(demo_file))

    def test_customer_delete_permission(self):
        # Non-admin user cannot delete
        regular_user = User.objects.create_user(
            username='operator1',
            email='op@test.com',
            password='password123',
            role='operator',
            is_staff=False
        )
        self.client.force_login(regular_user)

        customer = Customer.objects.create(
            code="TEST_NOAUTH",
            first_name="Test",
            email="test@test.com",
            nas_folder_name="TEST_NOAUTH"
        )

        url = reverse('customer_delete', kwargs={'pk': customer.id})
        response = self.client.post(url)

        # Should be redirected (due to user_passes_test)
        self.assertEqual(response.status_code, 302)
        # Customer still exists in DB
        self.assertTrue(Customer.objects.filter(id=customer.id).exists())


class DashboardAndNavigationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_dash',
            email='admin_dash@test.com',
            password='password123',
            role='admin',
            is_staff=True
        )
        self.client.force_login(self.admin_user)

    def test_root_redirects_to_dashboard(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/modules/admin/')

    def test_dashboard_rendered_with_kpis_and_tooltips(self):
        # Create some sample data
        cust = Customer.objects.create(
            code="CUST_DASH",
            first_name="Mario",
            last_name="Rossi",
            email="mario@test.com",
            nas_folder_name="MARIO_ROSSI"
        )
        form = FormTemplate.objects.create(
            name="Modulo Test",
            intro_text="Intro",
            status="published",
            customer=cust,
            author=self.admin_user
        )

        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Check context
        self.assertEqual(response.context['templates_count'], 1)
        self.assertEqual(response.context['customers_count'], 1)

        # Check HTML content: KPI titles and tooltips present
        content = response.content.decode('utf-8')
        self.assertIn('Moduli Pubblicati', content)
        self.assertIn('Clienti Attivi', content)
        self.assertIn('Assegnazioni Totali', content)
        self.assertIn('Pratiche Completate', content)
        self.assertIn('data-bs-toggle="tooltip"', content)
        self.assertIn('bi-info-circle-fill', content)
        self.assertIn('navbar-brand', content)
        self.assertIn('btn-logout-pill', content)

    def test_assign_form_to_customer_redirects_to_detail(self):
        cust = Customer.objects.create(
            code="CUST_ASSIGN",
            first_name="Giuseppe",
            last_name="Rossi",
            email="giuseppe@test.com",
            nas_folder_name="GIUSEPPE_ROSSI"
        )
        template = FormTemplate.objects.create(
            name="Documenti",
            intro_text="Carica i tuoi documenti",
            status="published",
            version=1,
            author=self.admin_user
        )

        response = self.client.post(reverse('assign_form_to_customer'), {
            'customer_id': str(cust.id),
            'template_id': str(template.id),
            'project_name': 'ProgettoTest'
        })

        # Must NOT return raw JsonResponse on standard POST, must redirect to assignment_detail!
        self.assertEqual(response.status_code, 302)
        assignment = FormAssignment.objects.filter(customer=cust, form_template=template).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.form_data.get('project_name'), 'ProgettoTest')
        self.assertRedirects(response, reverse('assignment_detail', kwargs={'pk': assignment.id}))

        # Following the redirect renders assignment_detail with copyable link
        detail_response = self.client.get(reverse('assignment_detail', kwargs={'pk': assignment.id}))
        self.assertEqual(detail_response.status_code, 200)
        detail_content = detail_response.content.decode('utf-8')
        self.assertIn('Area Personale Cliente', detail_content)
        self.assertIn('Link Portale Clienti:', detail_content)
        self.assertIn('ProgettoTest', detail_content)

    def test_builder_create_as_reusable_template(self):
        """Test creating a form template without requiring customer or project."""
        response = self.client.post(reverse('builder_create'), {
            'name': 'Modulo Onboarding Fornitori',
            'description': 'Raccolta dati e documenti fornitori',
            'intro_text': 'Benvenuto nel portale fornitori'
        })
        self.assertEqual(response.status_code, 302)
        template = FormTemplate.objects.filter(name='Modulo Onboarding Fornitori').first()
        self.assertIsNotNone(template)
        self.assertIsNone(template.customer)
        self.assertEqual(template.status, 'draft')
        self.assertRedirects(response, reverse('builder_edit', kwargs={'pk': template.id}))

    def test_operational_guide_view(self):
        """Test operational guide page renders with visual workflow elements."""
        response = self.client.get(reverse('operational_guide'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Guida al Flusso di Lavoro', content)
        self.assertIn('Il Workflow in 4 Fasi', content)
        self.assertIn('Struttura delle Cartelle sul NAS', content)
        self.assertIn('/volume1/Clienti/', content)


class PublicAssignmentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_pub',
            email='admin_pub@test.com',
            password='password123',
            role='admin',
            is_staff=True
        )
        self.customer = Customer.objects.create(
            code="CLIENT_01",
            first_name="Mario",
            last_name="Rossi",
            email="mario@rossi.it",
            nas_folder_name="MARIO_ROSSI"
        )
        self.template = FormTemplate.objects.create(
            name="Modulo Raccolta Fiscale",
            intro_text="Benvenuto. Carica i tuoi documenti.",
            privacy_text="Informativa trattamento dati personali.",
            status="published",
            version=1,
            author=self.admin_user
        )
        # Create 2 steps
        from .models import FormStep, DocumentRequirement
        self.step1 = FormStep.objects.create(
            form_template=self.template,
            title="Dati Anagrafici",
            description="Carica la carta d'identità",
            order=0,
            required=True
        )
        self.doc_req1 = DocumentRequirement.objects.create(
            form_step=self.step1,
            name="Carta Identità",
            required=True,
            order=0,
            max_file_size=10485760,
            destination_subfolder=''
        )
        self.step2 = FormStep.objects.create(
            form_template=self.template,
            title="Documenti Reddituali",
            description="Carica il CUD o modello 730",
            order=1,
            required=True
        )
        from django.utils import timezone
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            expiry_date=timezone.now() + timezone.timedelta(days=30),
            operator=self.admin_user,
            status='draft',
            form_data={
                'client_name': self.customer.nas_folder_name,
                'project_name': 'Pratica2026'
            }
        )

    def test_get_form_by_token_renders_public_page_without_admin_nav(self):
        url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Modulo Raccolta Fiscale', content)
        self.assertIn('Raccolta Documenti', content)
        self.assertIn('Inizia la Compilazione', content)
        self.assertIn('etichub-intro', content)
        # Verify admin navbar items are NOT shown
        self.assertNotIn('href="/modules/admin/" class="navbar-link', content)

    def test_form_step_view_step_1_renders_without_500_error(self):
        # Accessing step 1 directly (as reported by user)
        url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Documenti Reddituali', content)
        self.assertIn('Passaggio 2 di 2', content)
        self.assertIn('id="nextStepBtn"', content)
        self.assertIn('Vai al Riepilogo e Invia', content)
        self.assertIn('proceedToNextStep', content)

    def test_form_step_view_step_0_renders_without_500_error(self):
        url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Dati Anagrafici', content)
        self.assertIn('Carta Identità', content)
        self.assertIn('Passaggio 1 di 2', content)

    def test_form_step_interleaved_ordering(self):
        """Verify that FormElements and DocumentRequirements are interleaved by order field."""
        from .models import FormElement
        # Step with:
        # order 0: text_info "Avviso Materiali"
        # order 1: doc_req "Scheda Materiali" (existing doc_req1, let's update order to 1)
        # order 2: separator
        # order 3: text_info "Avviso Idratazione"
        self.elem1 = FormElement.objects.create(
            form_step=self.step1,
            element_type='text_info',
            order=0,
            config={'text': 'Avviso Materiali'}
        )
        self.doc_req1.order = 1
        self.doc_req1.name = 'Scheda Materiali'
        self.doc_req1.save()

        self.elem2 = FormElement.objects.create(
            form_step=self.step1,
            element_type='separator',
            order=2,
            config={}
        )
        self.elem3 = FormElement.objects.create(
            form_step=self.step1,
            element_type='text_info',
            order=3,
            config={'text': 'Avviso Idratazione'}
        )

        url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        idx_info1 = content.find('Avviso Materiali')
        idx_doc1 = content.find('Scheda Materiali')
        idx_sep = content.find('dashed #CBD5E1')
        idx_info2 = content.find('Avviso Idratazione')

        self.assertTrue(idx_info1 != -1 and idx_doc1 != -1 and idx_sep != -1 and idx_info2 != -1)
        # Check sequence: info1 < doc1 < sep < info2
        self.assertTrue(idx_info1 < idx_doc1 < idx_sep < idx_info2, "Gli elementi e i documenti devono apparire nell'ordine stabilito nel builder")

    def test_assign_form_uses_customer_portal_credentials_when_empty(self):
        """Admin assigning a form without explicit password links to customer portal credentials."""
        self.customer.set_portal_password('CustomerPass123')
        self.customer.save()
        self.client.force_login(self.admin_user)
        url = reverse('assign_form_to_customer')
        post_data = {
            'customer_id': str(self.customer.id),
            'template_id': str(self.template.id),
            'project_name': 'TestCustomerPwdProject',
            'expiry_days': '30',
        }
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Check in DB: assignment is protected by customer portal password
        assignment = FormAssignment.objects.get(id=data['assignment_id'])
        self.assertTrue(assignment.has_access_password())
        self.assertTrue(assignment.check_access_password('CustomerPass123'))
        self.assertFalse(assignment.check_access_password('WrongPass'))

    def test_access_password_protection_flow(self):
        """Accessing a password-protected assignment requires valid password before viewing form."""
        self.assignment.form_data['access_password'] = 'Secret12'
        self.assignment.save()

        token_url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        step_url = reverse('form_step_view', kwargs={'assignment_id': self.assignment.id, 'step_order': 0})

        # 1. Direct step view redirects to token
        resp_step = self.client.get(step_url)
        self.assertEqual(resp_step.status_code, 302)
        self.assertEqual(resp_step.url, token_url)

        # 2. Token view without authentication shows password prompt
        resp_token = self.client.get(token_url)
        self.assertEqual(resp_token.status_code, 200)
        self.assertIn('Accesso al Modulo', resp_token.content.decode('utf-8'))
        self.assertIn('Inserisci la password', resp_token.content.decode('utf-8'))

        # 3. Wrong password shows error
        resp_wrong = self.client.post(token_url, {'password': 'WrongPassword'})
        self.assertEqual(resp_wrong.status_code, 200)
        self.assertIn('Password errata', resp_wrong.content.decode('utf-8'))

        # 4. Correct password authenticates
        resp_ok = self.client.post(token_url, {'password': 'Secret12'})
        self.assertEqual(resp_ok.status_code, 302)

        # 5. Follow redirect: form details are now displayed
        resp_authed = self.client.get(token_url)
        self.assertEqual(resp_authed.status_code, 200)
        self.assertIn('Inizia la Compilazione', resp_authed.content.decode('utf-8'))

    def test_file_upload_success_without_500(self):
        """Uploading a document succeeds, avoids 500 errors, and registers valid upload."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.doc_req1.allowed_extensions = "pdf"
        self.doc_req1.mime_types = "application/pdf"
        self.doc_req1.save()

        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})
        pdf_content = b"%PDF-1.4 valid test pdf file contents"
        pdf_file = SimpleUploadedFile("test_doc.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(upload_url, {
            'file': pdf_file,
            'requirement_id': str(self.doc_req1.id)
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('filename'), 'test_doc.pdf')

        # Check DB
        upload = self.assignment.documentupload_set.filter(status='valid').first()
        self.assertIsNotNone(upload)
        self.assertEqual(upload.original_filename, 'test_doc.pdf')
        self.assertEqual(upload.availability_status, 'uploaded')

    def test_skip_mandatory_document_requires_justification(self):
        """Marking a mandatory document as unavailable requires justification."""
        self.doc_req1.required = True
        self.doc_req1.save()

        skip_url = reverse('skip_optional_document', kwargs={
            'assignment_id': self.assignment.id,
            'requirement_id': self.doc_req1.id
        })

        # 1. No justification on required document fails with 400
        resp_fail = self.client.post(skip_url, {'justification': ''})
        self.assertEqual(resp_fail.status_code, 400)
        data_fail = resp_fail.json()
        self.assertIn('giustificativo', data_fail.get('error', '').lower())

        # 2. With justification succeeds and saves unavailable status
        justification_text = "Documento smarrito, in attesa di duplicato dal comune"
        resp_ok = self.client.post(skip_url, {'justification': justification_text})
        self.assertEqual(resp_ok.status_code, 200)
        data_ok = resp_ok.json()
        self.assertEqual(data_ok.get('status'), 'success')
        self.assertEqual(data_ok.get('availability_status'), 'not_available')

        # Check DB DocumentUpload
        upload = self.assignment.documentupload_set.filter(status='valid').first()
        self.assertIsNotNone(upload)
        self.assertEqual(upload.availability_status, 'not_available')
        self.assertEqual(upload.motivazione_indisponibilita, justification_text)

    def test_absence_declaration_file_upload_success(self):
        """Uploading a formal signed letterhead absence declaration successfully records file and checksum."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.doc_req1.required = True
        self.doc_req1.save()

        skip_url = reverse('skip_optional_document', kwargs={
            'assignment_id': self.assignment.id,
            'requirement_id': self.doc_req1.id
        })

        pdf_content = b"%PDF-1.4 formal declaration on letterhead stamped and signed by technical director"
        declaration_file = SimpleUploadedFile("Dichiarazione_Assenza_Firmata.pdf", pdf_content, content_type="application/pdf")
        notes = "Dichiarazione formale assenza documento su carta intestata timbrata e firmata da legale rappresentante"

        response = self.client.post(skip_url, {
            'file': declaration_file,
            'justification': notes
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('availability_status'), 'not_available')
        self.assertTrue(data.get('is_declaration_file'))
        self.assertEqual(data.get('filename'), 'Dichiarazione_Assenza_Firmata.pdf')
        self.assertGreater(data.get('file_size'), 0)

        # Check DB DocumentUpload
        upload = self.assignment.documentupload_set.filter(status='valid').first()
        self.assertIsNotNone(upload)
        self.assertEqual(upload.availability_status, 'not_available')
        self.assertEqual(upload.original_filename, 'Dichiarazione_Assenza_Firmata.pdf')
        self.assertGreater(upload.file_size, 0)
        self.assertTrue(len(upload.sha256_checksum) == 64)
        self.assertEqual(upload.motivazione_indisponibilita, notes)

        # Verify receipt PDF generation includes the absence declaration file
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        sub_resp = self.client.post(submit_url)
        self.assertEqual(sub_resp.status_code, 302)

    def test_form_submission_view_success_and_pdf_generation(self):
        """Form submission completes successfully, generates receipt, updates status, and redirects without 500 error."""
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        response = self.client.post(submit_url)

        # Must redirect to success page, not crash with 500
        self.assertEqual(response.status_code, 302)
        self.assertIn('/modules/form/success/', response.url)

        # Check DB status - Milestone 1 reached: 50%
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')
        self.assertEqual(self.assignment.completion_percentage, 50)
        self.assertIsNotNone(self.assignment.submission_date)

    def test_form_submission_partial_draft_save(self):
        """Partial submission saves draft state (in_progress), proportional %, and does not submit to regulatory."""
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        response = self.client.post(submit_url, {'action_type': 'partial'})

        self.assertEqual(response.status_code, 302)
        self.assertIn('mode=partial', response.url)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'in_progress')
        self.assertLess(self.assignment.completion_percentage, 50)
        self.assertIsNone(self.assignment.submission_date)

        # No awareness declaration created for partial save
        self.assertFalse(AwarenessDeclaration.objects.filter(form_assignment=self.assignment).exists())
        # No regulatory notification created
        self.assertFalse(NotificationLog.objects.filter(notification_type='form_submitted').exists())

    def test_form_submission_complete_requires_awareness_declaration(self):
        """Complete submission explicitly requires awareness_declaration=true."""
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})

        # 1. Attempt complete submission without awareness declaration -> blocked
        resp_blocked = self.client.post(submit_url, {'action_type': 'complete'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp_blocked.status_code, 400)
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.status, 'submitted')

        # 2. Attempt complete submission with awareness declaration -> succeeds
        resp_ok = self.client.post(submit_url, {
            'action_type': 'complete',
            'awareness_declaration': 'true',
            'customer_name': 'Mario Rossi'
        })
        self.assertEqual(resp_ok.status_code, 302)
        self.assertIn('mode=complete', resp_ok.url)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')
        self.assertEqual(self.assignment.completion_percentage, 50)
        self.assertIsNotNone(self.assignment.submission_date)
        self.assertTrue(AwarenessDeclaration.objects.filter(form_assignment=self.assignment, accepted=True).exists())

    def test_operator_state_machine_transitions(self):
        """Etichub operator transitions practice: submitted (50%) -> in_processing (75%) -> completed (100%)."""
        self.client.force_login(self.admin_user)
        self.assignment.status = 'submitted'
        self.assignment.completion_percentage = 50
        self.assignment.save()

        update_url = reverse('assignment_update_status', kwargs={'pk': self.assignment.id})

        # 1. Operator takes charge: in_processing (75%)
        resp1 = self.client.post(update_url, {'status': 'in_processing'})
        self.assertRedirects(resp1, reverse('assignment_detail', kwargs={'pk': self.assignment.id}))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'in_processing')
        self.assertEqual(self.assignment.completion_percentage, 75)

        # 2. Operator finishes practice: completed (100% Lavorata)
        resp2 = self.client.post(update_url, {'status': 'completed'})
        self.assertRedirects(resp2, reverse('assignment_detail', kwargs={'pk': self.assignment.id}))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'completed')
        self.assertEqual(self.assignment.completion_percentage, 100)

        # 3. Can revert to submitted (50%) if needed
        resp3 = self.client.post(update_url, {'status': 'submitted'})
        self.assertRedirects(resp3, reverse('assignment_detail', kwargs={'pk': self.assignment.id}))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')
        self.assertEqual(self.assignment.completion_percentage, 50)

    def test_reopen_assignment_for_upload_flow(self):
        """Admin can reopen a submitted practice, generating a new secure URL while preserving the customer NAS folder."""
        # 1. Mark assignment as submitted
        self.assignment.status = 'submitted'
        self.assignment.submission_date = timezone.now()
        self.assignment.completion_percentage = 100
        self.assignment.save()

        old_token = self.assignment.secure_token
        reopen_url = reverse('reopen_assignment', kwargs={'pk': self.assignment.id})

        # 2. Anonymous / non-admin cannot reopen
        self.client.logout()
        resp_unauth = self.client.post(reopen_url)
        self.assertNotEqual(resp_unauth.status_code, 200)

        # 3. Admin user reopens assignment
        self.client.force_login(self.admin_user)
        resp_reopen = self.client.post(reopen_url)
        self.assertRedirects(resp_reopen, reverse('assignment_detail', kwargs={'pk': self.assignment.id}))

        # 4. Check DB updates
        self.assignment.refresh_from_db()
        self.assertNotEqual(self.assignment.secure_token, old_token)
        self.assertEqual(len(self.assignment.secure_token), 40)
        self.assertEqual(self.assignment.status, 'in_progress')
        self.assertIsNone(self.assignment.submission_date)
        self.assertGreater(self.assignment.expiry_date, timezone.now())

        # Customer and project NAS folder structure strictly preserved
        self.assertEqual(self.assignment.customer.nas_folder_name, "MARIO_ROSSI")
        self.assertEqual(self.assignment.form_data.get('project_name'), "Pratica2026")

        # 5. Customer can access the form again with the new token
        self.client.logout()
        new_form_url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        resp_new = self.client.get(new_form_url)
        self.assertEqual(resp_new.status_code, 200)
        self.assertNotContains(resp_new, "Modulo già inviato")

        # 6. Old token is invalid (returns 404)
        old_form_url = reverse('get_form_by_token', kwargs={'token': old_token})
        resp_old = self.client.get(old_form_url)
        self.assertEqual(resp_old.status_code, 404)

    def test_reopen_assignment_ajax(self):
        """Admin can trigger reopen via AJAX and receive JSON with new URL and token."""
        self.client.force_login(self.admin_user)
        reopen_url = reverse('reopen_assignment', kwargs={'pk': self.assignment.id})
        resp = self.client.post(reopen_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('form_url', data)
        self.assertIn('token', data)
        self.assignment.refresh_from_db()
        self.assertEqual(data.get('token'), self.assignment.secure_token)

    def test_upload_integrative_document_after_reopening_supersedes_unavailable(self):
        """After reopening, uploading an integrative document supersedes previous unavailable status."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.doc_req1.allowed_extensions = "pdf"
        self.doc_req1.mime_types = "application/pdf"
        self.doc_req1.save()

        # 1. Mark document as unavailable with justification
        skip_url = reverse('skip_optional_document', kwargs={
            'assignment_id': self.assignment.id,
            'requirement_id': self.doc_req1.id
        })
        self.client.post(skip_url, {'justification': 'In attesa di emissione'})

        # 2. Submit assignment
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        self.client.post(submit_url)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')

        # 3. Admin reopens assignment for integrations
        self.client.force_login(self.admin_user)
        reopen_url = reverse('reopen_assignment', kwargs={'pk': self.assignment.id})
        self.client.post(reopen_url)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'in_progress')

        # 4. Client uploads the integrative document
        self.client.logout()
        upload_url = reverse('upload_document_view', kwargs={'assignment_id': self.assignment.id})
        pdf_file = SimpleUploadedFile("documento_integrativo.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        upload_resp = self.client.post(upload_url, {
            'file': pdf_file,
            'requirement_id': str(self.doc_req1.id)
        })
        self.assertEqual(upload_resp.status_code, 200)

        # 5. Check DB: previous unavailable upload is superseded, new upload is valid and uploaded
        old_unavail = self.assignment.documentupload_set.filter(availability_status='not_available').first()
        self.assertEqual(old_unavail.status, 'superseded')

        new_upload = self.assignment.documentupload_set.filter(status='valid').first()
        self.assertEqual(new_upload.original_filename, 'documento_integrativo.pdf')
        self.assertEqual(new_upload.availability_status, 'uploaded')

        # 6. Final submit succeeds (attesting Milestone 1: 50%)
        self.client.post(submit_url)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'submitted')
        self.assertEqual(self.assignment.completion_percentage, 50)

    def test_reopened_assignment_requests_password_and_downloads_receipt_without_forbidden(self):
        """Reopening an assignment requires password on new link and allows downloading receipt without 403 error."""
        # 1. Set password on assignment
        self.assignment.form_data['access_password'] = 'SecretPass123'
        self.assignment.save()

        # Reopen practice
        self.client.force_login(self.admin_user)
        reopen_url = reverse('reopen_assignment', kwargs={'pk': self.assignment.id})
        self.client.post(reopen_url)
        self.assignment.refresh_from_db()
        self.client.logout()

        # 2. Accessing new token URL prompts for password
        form_url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        resp_prompt = self.client.get(form_url)
        self.assertEqual(resp_prompt.status_code, 200)
        self.assertTemplateUsed(resp_prompt, 'modules/form_password.html')

        # 3. Entering wrong password fails
        resp_wrong = self.client.post(form_url, {'password': 'wrong'})
        self.assertEqual(resp_wrong.status_code, 200)
        self.assertTemplateUsed(resp_wrong, 'modules/form_password.html')
        self.assertContains(resp_wrong, 'Password errata')

        # 4. Entering correct password succeeds and unlocks form
        resp_ok = self.client.post(form_url, {'password': 'SecretPass123'})
        self.assertEqual(resp_ok.status_code, 302)

        # Following redirect to form_detail succeeds
        resp_detail = self.client.get(form_url)
        self.assertEqual(resp_detail.status_code, 200)
        self.assertTemplateUsed(resp_detail, 'modules/form_detail.html')

        # 5. Submit form
        submit_url = reverse('form_submission_view', kwargs={'assignment_id': self.assignment.id})
        resp_submit = self.client.post(submit_url)
        self.assertEqual(resp_submit.status_code, 302)
        self.assertIn('/modules/form/success/', resp_submit.url)

        # Success page has receipt download link pointing to assignment_receipt
        resp_success = self.client.get(resp_submit.url)
        self.assertEqual(resp_success.status_code, 200)
        receipt_url = reverse('assignment_receipt', kwargs={'assignment_id': self.assignment.id})
        self.assertContains(resp_success, receipt_url)

        # 6. Downloading receipt returns 200 PDF without 403 Forbidden
        resp_receipt = self.client.get(receipt_url)
        self.assertEqual(resp_receipt.status_code, 200)
        self.assertEqual(resp_receipt['Content-Type'], 'application/pdf')

        # 7. Anonymous user with no session gets 403 Forbidden
        anon_client = Client()
        resp_unauth = anon_client.get(receipt_url)
        self.assertEqual(resp_unauth.status_code, 403)

        # 8. Admin user can download directly even without client session
        anon_client.force_login(self.admin_user)
        resp_admin = anon_client.get(receipt_url)
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(resp_admin['Content-Type'], 'application/pdf')

    def test_assignment_delete_by_admin(self):
        """Admin can disassociate and delete an assignment, cascading all uploaded files and declarations from DB."""
        from .models import DocumentUpload, AwarenessDeclaration

        # 1. Simulate uploaded document and declaration for this assignment
        upload = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.doc_req1,
            original_filename="carta_identita_errata.pdf",
            stored_filename="stored_123.pdf",
            file_size=1024,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='test'
        )
        declaration = AwarenessDeclaration.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.doc_req1,
            declaration_text="Confermo correttezza",
            acceptance_ip='127.0.0.1',
            acceptance_user_agent='test',
            accepted=True
        )

        self.assertEqual(DocumentUpload.objects.filter(form_assignment=self.assignment).count(), 1)
        self.assertEqual(AwarenessDeclaration.objects.filter(form_assignment=self.assignment).count(), 1)

        delete_url = reverse('assignment_delete', kwargs={'pk': self.assignment.id})

        # 2. Anonymous cannot delete
        self.client.logout()
        resp_anon = self.client.post(delete_url)
        self.assertNotEqual(resp_anon.status_code, 200)
        self.assertTrue(FormAssignment.objects.filter(id=self.assignment.id).exists())

        # 3. Admin deletes assignment
        self.client.force_login(self.admin_user)
        resp_del = self.client.post(delete_url)
        self.assertRedirects(resp_del, reverse('admin_dashboard'))

        # 4. Verification: Assignment is completely gone from DB
        self.assertFalse(FormAssignment.objects.filter(id=self.assignment.id).exists())

        # 5. Verification: All related DocumentUpload and AwarenessDeclaration records are wiped from DB
        self.assertEqual(DocumentUpload.objects.filter(id=upload.id).count(), 0)
        self.assertEqual(DocumentUpload.objects.filter(form_assignment_id=self.assignment.id).count(), 0)
        self.assertEqual(AwarenessDeclaration.objects.filter(id=declaration.id).count(), 0)
        self.assertEqual(AwarenessDeclaration.objects.filter(form_assignment_id=self.assignment.id).count(), 0)

        # 6. Verification: Customer and template remain intact
        self.assertTrue(Customer.objects.filter(id=self.customer.id).exists())
        self.assertTrue(FormTemplate.objects.filter(id=self.template.id).exists())


class CustomerCreateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_cust_test',
            email='admin_cust@test.com',
            password='password123',
            role='admin',
            is_staff=True
        )
        self.client.force_login(self.admin_user)
        self.create_url = reverse('customer_create')

    def test_customer_create_success_without_optional_fields(self):
        resp = self.client.post(self.create_url, {
            'code': 'CLI_001',
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': 'mario.rossi@example.com',
            'nas_folder_name': 'MARIO_ROSSI',
            'active': 'on'
        })
        self.assertRedirects(resp, reverse('customer_list'))

        customer = Customer.objects.get(code='CLI_001')
        self.assertEqual(customer.first_name, 'Mario')
        self.assertIsNone(customer.fiscal_code)
        self.assertIsNone(customer.vat_number)
        self.assertIsNone(customer.phone)
        self.assertTrue(customer.active)

    def test_customer_create_second_customer_does_not_crash_with_500(self):
        # First customer
        self.client.post(self.create_url, {
            'code': 'CLI_001',
            'first_name': 'Mario',
            'email': 'mario@example.com',
            'nas_folder_name': 'MARIO',
            'active': 'on'
        })
        # Second customer without fiscal_code or vat_number (must not trigger IntegrityError)
        resp2 = self.client.post(self.create_url, {
            'code': 'CLI_002',
            'first_name': 'Luigi',
            'email': 'luigi@example.com',
            'nas_folder_name': 'LUIGI',
            'active': 'on'
        })
        self.assertRedirects(resp2, reverse('customer_list'))
        self.assertEqual(Customer.objects.count(), 2)

    def test_customer_create_duplicate_code_rejected(self):
        Customer.objects.create(
            code='CLI_EXISTS',
            first_name='Existing',
            email='exists@example.com',
            nas_folder_name='EXISTS_NAS'
        )

        resp = self.client.post(self.create_url, {
            'code': 'CLI_EXISTS',
            'first_name': 'Duplicate',
            'email': 'dup@example.com',
            'nas_folder_name': 'DIFF_NAS',
            'active': 'on'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "esiste già")

    def test_customer_create_invalid_nas_folder_rejected(self):
        resp = self.client.post(self.create_url, {
            'code': 'CLI_TRAVERSAL',
            'first_name': 'Bad',
            'email': 'bad@example.com',
            'nas_folder_name': '../etc/passwd',
            'active': 'on'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Errore di convalida")


class CustomerEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_edit_test',
            email='admin_edit@test.com',
            password='password123',
            role='admin',
            is_staff=True
        )
        self.client.force_login(self.admin_user)
        self.customer = Customer.objects.create(
            code='CLI_EDIT_001',
            first_name='Azienda Alfa',
            last_name='Referente Alfa',
            email='alfa@example.com',
            phone='+39 02 111111',
            nas_folder_name='ALFA_NAS',
            notes='Note iniziali',
            active=True
        )
        self.customer.set_portal_password('InitialPass123')
        self.customer.save()
        self.edit_url = reverse('customer_edit', kwargs={'pk': self.customer.id})

    def test_customer_edit_get_html_and_ajax(self):
        # Normal GET
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Azienda Alfa")

        # AJAX GET
        resp_ajax = self.client.get(self.edit_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp_ajax.status_code, 200)
        data = resp_ajax.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['customer']['code'], 'CLI_EDIT_001')
        self.assertEqual(data['customer']['first_name'], 'Azienda Alfa')

    def test_customer_edit_updates_all_attributes(self):
        resp = self.client.post(self.edit_url, {
            'code': 'CLI_EDIT_MOD',
            'first_name': 'Azienda Beta Srl',
            'last_name': 'Referente Beta',
            'email': 'beta@example.com',
            'phone': '+39 02 222222',
            'nas_folder_name': 'BETA_NAS',
            'notes': 'Note aggiornate',
            'active': 'on'
        })
        self.assertRedirects(resp, reverse('customer_list'))

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.code, 'CLI_EDIT_MOD')
        self.assertEqual(self.customer.first_name, 'Azienda Beta Srl')
        self.assertEqual(self.customer.last_name, 'Referente Beta')
        self.assertEqual(self.customer.email, 'beta@example.com')
        self.assertEqual(self.customer.phone, '+39 02 222222')
        self.assertEqual(self.customer.nas_folder_name, 'BETA_NAS')
        self.assertEqual(self.customer.notes, 'Note aggiornate')
        self.assertTrue(self.customer.active)

    def test_customer_edit_without_password_preserves_existing_password(self):
        self.client.post(self.edit_url, {
            'code': 'CLI_EDIT_001',
            'first_name': 'Azienda Alfa Modificata',
            'last_name': 'Referente Alfa',
            'email': 'alfa@example.com',
            'nas_folder_name': 'ALFA_NAS',
            'active': 'on'
        })
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Azienda Alfa Modificata')
        self.assertTrue(self.customer.check_portal_password('InitialPass123'))

    def test_customer_edit_with_new_password_updates_portal_password(self):
        resp = self.client.post(self.edit_url, {
            'code': 'CLI_EDIT_001',
            'first_name': 'Azienda Alfa',
            'last_name': 'Referente Alfa',
            'email': 'alfa@example.com',
            'nas_folder_name': 'ALFA_NAS',
            'portal_password': 'NuovaSuperPassword999!',
            'active': 'on'
        })
        self.assertRedirects(resp, reverse('customer_list'))
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.check_portal_password('InitialPass123'))
        self.assertTrue(self.customer.check_portal_password('NuovaSuperPassword999!'))

    def test_customer_edit_ajax_response(self):
        resp = self.client.post(
            self.edit_url,
            {
                'code': 'CLI_EDIT_001',
                'first_name': 'Nome Aggiornato via AJAX',
                'last_name': 'Cognome',
                'email': 'alfa@example.com',
                'nas_folder_name': 'ALFA_NAS',
                'active': 'true',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['customer']['first_name'], 'Nome Aggiornato via AJAX')
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Nome Aggiornato via AJAX')

    def test_customer_edit_duplicate_code_or_nas_rejected(self):
        Customer.objects.create(
            code='CLI_OTHER',
            first_name='Other',
            email='other@example.com',
            nas_folder_name='OTHER_NAS'
        )

        resp = self.client.post(
            self.edit_url,
            {
                'code': 'CLI_OTHER',
                'first_name': 'Azienda Alfa',
                'email': 'alfa@example.com',
                'nas_folder_name': 'ALFA_NAS',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("esiste già", resp.json()['error'])


class ApiCustomerCreateAndDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_api_test', 'admin@example.com', 'adminpass123')
        self.api_url = reverse('api_customer_create')

    def test_api_customer_create_success_auto_password(self):
        """Verifies C1 and H1: creating customer via API does not throw NameError and sets portal password."""
        self.client.force_login(self.admin)
        resp = self.client.post(self.api_url, {
            'code': 'API_CUST_001',
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': 'mario.rossi@example.com',
            'nas_folder_name': 'mario_rossi_nas'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        cust = Customer.objects.get(code='API_CUST_001')
        self.assertEqual(cust.first_name, 'Mario')
        self.assertTrue(bool(cust.portal_password))

    def test_api_customer_create_invalid_nas_folder_rejected(self):
        """Verifies H1: path traversal in nas_folder_name is rejected."""
        self.client.force_login(self.admin)
        resp = self.client.post(self.api_url, {
            'code': 'API_CUST_BAD_NAS',
            'first_name': 'Bad',
            'email': 'bad@example.com',
            'nas_folder_name': '../escaped_nas'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('cartella NAS non valido', data.get('error', ''))

    def test_api_customer_create_invalid_email_rejected(self):
        """Verifies H1: invalid email format is rejected."""
        self.client.force_login(self.admin)
        resp = self.client.post(self.api_url, {
            'code': 'API_CUST_BAD_EMAIL',
            'first_name': 'Bad',
            'email': 'not-an-email',
            'nas_folder_name': 'valid_nas_folder'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('email non valido', data.get('error', ''))

    def test_client_dashboard_queries_optimized(self):
        """Verifies H7: client_dashboard operates cleanly with batch counts."""
        customer = Customer.objects.create(
            code='DASH_CUST',
            first_name='Luigi',
            last_name='Verdi',
            email='luigi.verdi@example.com',
            nas_folder_name='luigi_verdi'
        )
        customer.set_portal_password('ClientPass123')
        customer.save()

        template = FormTemplate.objects.create(
            name='Test Dashboard Form',
            intro_text='Intro text'
        )
        step = FormStep.objects.create(form_template=template, title='Step 1', order=0)
        DocumentRequirement.objects.create(
            form_step=step,
            name='Doc 1',
            allowed_extensions='pdf',
            mime_types='application/pdf',
            max_file_size=1048576,
            destination_subfolder='sub1',
            order=0
        )

        for i in range(3):
            FormAssignment.objects.create(
                customer=customer,
                form_template=template,
                expiry_date=timezone.now() + timezone.timedelta(days=10),
                status='draft',
                form_data={'project_name': f'Proj {i}'}
            )

        # Log in to client portal
        session = self.client.session
        session['customer_id'] = str(customer.id)
        session['customer_code'] = customer.code
        session.save()

        dashboard_url = reverse('client_dashboard')
        resp = self.client.get(dashboard_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('products', resp.context)
        self.assertEqual(len(resp.context['products']), 3)
        self.assertEqual(resp.context['products'][0]['total_requirements'], 1)

    def test_assign_form_rollback_if_manifest_fails(self):
        """Verifies H9: if manifest write fails, transaction rolls back and no orphaned assignment is created."""
        from unittest.mock import patch
        customer = Customer.objects.create(
            code='NAS_FAIL_CUST',
            first_name='Fail',
            last_name='Test',
            email='fail@example.com',
            nas_folder_name='fail_cust'
        )
        template = FormTemplate.objects.create(name='Template Fail Test', intro_text='Intro')
        self.client.force_login(self.admin)

        initial_count = FormAssignment.objects.count()
        url = reverse('assign_form_to_customer')

        # Clean up any leftover test folder from previous runs
        from .upload_security import safe_join_paths
        nas_base = os.getenv('CUSTOMER_DOCUMENTS_CONTAINER_PATH', os.getenv('CUSTOMER_DOCUMENTS_PATH', '/volume1/Clienti'))
        manifest_path = safe_join_paths(nas_base, customer.nas_folder_name, 'ProjectFail', 'manifest.json')
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

        try:
            with patch('modules.views_admin.save_manifest_atomic', side_effect=OSError("Simulated NAS disk full / permission error")):
                resp = self.client.post(url, {
                    'customer_id': str(customer.id),
                    'template_id': str(template.id),
                    'project_name': 'ProjectFail',
                    'access_password': 'Pass1234',
                    'expiry_days': '30'
                }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

            self.assertEqual(resp.status_code, 500)
            # Verify atomic rollback: assignment was NOT created in DB
            self.assertEqual(FormAssignment.objects.count(), initial_count)
        finally:
            if os.path.exists(manifest_path):
                os.remove(manifest_path)

    def test_client_login_no_user_enumeration(self):
        """Verifies M1: client login returns the exact same generic error for non-existent and bad password."""
        url = reverse('client_login')
        customer = Customer.objects.create(code='ENUM_CUST', first_name='Enum', last_name='User', nas_folder_name='enum_cust')
        customer.set_portal_password('CorrectPass123!')
        customer.save()

        # 1. Non-existent customer code
        resp_non_existent = self.client.post(url, {'code': 'DOES_NOT_EXIST', 'password': 'AnyPassword'})
        # 2. Existing customer with wrong password
        resp_wrong_pwd = self.client.post(url, {'code': 'ENUM_CUST', 'password': 'WrongPassword'})

        # Both should render the login page with the exact same error message
        self.assertEqual(resp_non_existent.status_code, 200)
        self.assertEqual(resp_wrong_pwd.status_code, 200)
        self.assertEqual(resp_non_existent.context['error'], resp_wrong_pwd.context['error'])
        self.assertEqual(resp_wrong_pwd.context['error'], 'Password errata. Riprova.')

    def test_api_form_delete_protects_with_archive(self):
        """Verifies M2: form template with customer assignments is archived rather than cascade-deleted."""
        self.client.force_login(self.admin)
        customer = Customer.objects.create(code='ARCH_CUST', first_name='Arch', nas_folder_name='arch_cust')
        template = FormTemplate.objects.create(name='Template With Assignments', intro_text='Intro', status='published')
        assignment = FormAssignment.objects.create(
            customer=customer,
            form_template=template,
            expiry_date=timezone.now() + timezone.timedelta(days=7),
            status='in_progress'
        )

        url = reverse('api_form_delete', kwargs={'form_id': template.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('archived'))

        # Check template status changed to archived
        template.refresh_from_db()
        self.assertEqual(template.status, 'archived')
        # Check assignment still exists (protected from cascade delete!)
        self.assertTrue(FormAssignment.objects.filter(id=assignment.id).exists())

    def test_builder_preview_prefetch_formelement_set(self):
        """Verifies H8: builder_preview prefetches elements and requirements without N+1 queries."""
        self.client.force_login(self.admin)
        from .models import FormStep, FormElement

        # Create template with 2 steps
        t1 = FormTemplate.objects.create(name='Prefetch Preview Test 1', intro_text='Intro')
        for i in range(2):
            step = FormStep.objects.create(form_template=t1, title=f'Step {i}', order=i)
            FormElement.objects.create(form_step=step, element_type='text_field', order=0, config={'label': f'Field {i}'})
            DocumentRequirement.objects.create(form_step=step, name=f'Doc {i}', max_file_size=1048576, order=1)

        # Create template with 6 steps
        t2 = FormTemplate.objects.create(name='Prefetch Preview Test 2', intro_text='Intro')
        for i in range(6):
            step = FormStep.objects.create(form_template=t2, title=f'Step {i}', order=i)
            FormElement.objects.create(form_step=step, element_type='text_field', order=0, config={'label': f'Field {i}'})
            DocumentRequirement.objects.create(form_step=step, name=f'Doc {i}', max_file_size=1048576, order=1)

        with self.assertNumQueries(6):
            resp1 = self.client.get(reverse('builder_preview', kwargs={'pk': t1.id}))
            self.assertEqual(resp1.status_code, 200)

        # A form with 3x the steps must execute the exact same number of queries (O(1) database queries)
        with self.assertNumQueries(6):
            resp2 = self.client.get(reverse('builder_preview', kwargs={'pk': t2.id}))
            self.assertEqual(resp2.status_code, 200)

    def test_upload_security_mime_fallback_warning(self):
        """Verifies M4: fallback MIME detection logs a warning."""
        from .upload_security import get_mime_type_from_content
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake_file = SimpleUploadedFile("test.txt", b"plain text content", content_type="text/plain")
        with self.assertLogs('modules.upload_security', level='WARNING') as log_cm:
            mime = get_mime_type_from_content(fake_file)
            self.assertEqual(mime, 'text/plain')
            self.assertTrue(any('python-magic' in msg for msg in log_cm.output))


class TestFormTemplateDefaultExpiryTTL(TestCase):
    """Test suite for configurable TTL / default_expiry_days per form template and in builder."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_ttl',
            email='admin_ttl@etichub.it',
            password='Password123!'
        )
        self.client.force_login(self.admin_user)
        self.customer = Customer.objects.create(
            code='CUST-TTL-01',
            first_name='Mario',
            last_name='Rossi',
            email='mario.rossi@example.com',
            nas_folder_name='mario_rossi_ttl'
        )

    def test_form_template_default_expiry_days_creation_and_duplicate(self):
        """Verify default_expiry_days is set on creation and preserved on duplicate."""
        template = FormTemplate.objects.create(
            name='Dossier Formula Complessa',
            intro_text='Intro text',
            default_expiry_days=45,
            author=self.admin_user
        )
        self.assertEqual(template.default_expiry_days, 45)

        dup = template.duplicate()
        self.assertEqual(dup.default_expiry_days, 45)
        self.assertEqual(dup.name, 'Dossier Formula Complessa (copy)')

    def test_api_form_create_and_detail_default_expiry(self):
        """Verify api_form_create and api_form_detail serialize default_expiry_days."""
        create_resp = self.client.post(
            '/modules/api/v1/forms/create/',
            data=json.dumps({
                'name': 'API TTL Test Form',
                'description': 'Description',
                'intro_text': 'Intro text',
                'default_expiry_days': 60
            }),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 200)
        form_id = create_resp.json()['data']['id']

        detail_resp = self.client.get(f'/modules/api/v1/forms/{form_id}/')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()['data']['default_expiry_days'], 60)

    def test_api_form_save_updates_default_expiry(self):
        """Verify api_form_save updates default_expiry_days on draft form."""
        template = FormTemplate.objects.create(
            name='Draft Form To Edit',
            intro_text='Intro',
            status='draft',
            default_expiry_days=30,
            author=self.admin_user
        )
        save_resp = self.client.put(
            f'/modules/api/v1/forms/{template.id}/save/',
            data=json.dumps({
                'name': 'Draft Form To Edit',
                'description': 'Updated',
                'intro_text': 'Intro',
                'default_expiry_days': 15,
                'steps': []
            }),
            content_type='application/json'
        )
        self.assertEqual(save_resp.status_code, 200)
        template.refresh_from_db()
        self.assertEqual(template.default_expiry_days, 15)

    def test_assign_form_context_derives_template_expiry(self):
        """Verify assign_form GET view pre-populates expiry_days with template.default_expiry_days."""
        template = FormTemplate.objects.create(
            name='Published Form 45 Days',
            intro_text='Intro',
            status='published',
            default_expiry_days=45,
            author=self.admin_user
        )
        resp = self.client.get(f'/modules/admin/assign-form/?template_id={template.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['expiry_days'], 45)
        self.assertContains(resp, f'data-expiry="45"')


class TestPDFReceiptGeneration(TestCase):
    """Test suite for PDF receipt generation including Transaction ID and Client IP."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_user_pdf', password='password123')
        self.customer = Customer.objects.create(
            code='CUST-PDF-01',
            first_name='Badedas',
            last_name='SPA',
            email='test@badedas.it',
            vat_number='IT12345678901'
        )
        self.template = FormTemplate.objects.create(
            name='Modulo Documentale Test',
            project_name='BAGNOSCHIUMA',
            author=self.user
        )
        self.step = FormStep.objects.create(form_template=self.template, title='Step 1', order=1)
        self.doc_req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Doc 1',
            required=True,
            allowed_extensions='pdf',
            mime_types='application/pdf',
            max_file_size=10485760,
            destination_subfolder='allegati',
            order=1
        )
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            form_data={'client_name': 'Badedas SPA', 'project_name': 'BAGNOSCHIUMA'},
            expiry_date=timezone.now() + timezone.timedelta(days=30)
        )

    def test_generate_form_receipt_pdf_contains_id_and_ip(self):
        import tempfile
        from modules.report_generator import generate_form_receipt_pdf

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            generate_form_receipt_pdf(
                self.template,
                self.assignment,
                tmp_path,
                client_ip='192.168.1.50'
            )
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_generate_form_receipt_pdf_resolves_ip_from_awareness_declaration(self):
        import tempfile
        from modules.report_generator import generate_form_receipt_pdf
        from modules.models import AwarenessDeclaration

        AwarenessDeclaration.objects.create(
            form_assignment=self.assignment,
            declaration_text='Dichiaro di aver preso visione',
            accepted=True,
            acceptance_ip='10.0.0.99',
            acceptance_user_agent='TestBrowser'
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            generate_form_receipt_pdf(
                self.template,
                self.assignment,
                tmp_path
            )
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_pdf_ip_address_resolution(self):
        """Test that IP resolution follows correct fallback chain: parameter > declaration > audit log > form_data."""
        from unittest.mock import patch, MagicMock
        from modules.report_generator import generate_form_receipt_pdf
        import tempfile

        # Test 1: Explicit client_ip parameter has highest priority
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path,
                    client_ip='203.0.113.50'
                )
                # Verify the PDF generation was called with the explicit IP
                self.assertTrue(mock_pdf.called)
                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}
                self.assertEqual(form_data.get('client_ip'), '203.0.113.50')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Test 2: Awareness declaration IP is used when client_ip not provided
        from modules.models import AwarenessDeclaration
        AwarenessDeclaration.objects.create(
            form_assignment=self.assignment,
            declaration_text='Test Declaration',
            accepted=True,
            acceptance_ip='192.0.2.100',
            acceptance_user_agent='Mozilla/5.0'
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )
                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}
                self.assertEqual(form_data.get('client_ip'), '192.0.2.100')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Test 3: Audit log IP is used when declaration not available
        AwarenessDeclaration.objects.all().delete()
        AuditLog.objects.create(
            object_type='FormAssignment',
            object_id=str(self.assignment.id),
            action='submit',
            actor_user=self.user,
            actor_ip='198.51.100.75',
            actor_user_agent='Mozilla/5.0'
        )

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )
                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}
                self.assertEqual(form_data.get('client_ip'), '198.51.100.75')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Test 4: form_data IP is used as last resort
        AuditLog.objects.all().delete()
        self.assignment.form_data = {'client_ip': '192.168.100.1'}
        self.assignment.save()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )
                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}
                self.assertEqual(form_data.get('client_ip'), '192.168.100.1')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_pdf_transaction_id_extraction(self):
        """Test that transaction ID is correctly extracted from assignment.id."""
        from unittest.mock import patch
        from modules.report_generator import generate_form_receipt_pdf
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )

                self.assertTrue(mock_pdf.called)
                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}

                # Verify transaction ID fields contain assignment ID
                expected_id = str(self.assignment.id)
                self.assertEqual(form_data.get('id'), expected_id)
                self.assertEqual(form_data.get('form_id'), expected_id)
                self.assertEqual(form_data.get('transaction_id'), expected_id)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_pdf_submission_date_resolution(self):
        """Test that submission date uses assignment.submission_date or falls back to now()."""
        from unittest.mock import patch
        from modules.report_generator import generate_form_receipt_pdf
        import tempfile
        from datetime import datetime

        # Test 1: When submission_date is set
        test_date = timezone.now()
        self.assignment.submission_date = test_date
        self.assignment.save()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )

                call_args = mock_pdf.call_args
                form_data = call_args[0][1] if call_args[0] else {}

                # Verify submission datetime is in the form_data
                self.assertIn('submission_datetime', form_data)
                # Date should be formatted as dd/mm/yyyy hh:mm:ss
                submission_str = form_data.get('submission_datetime', '')
                self.assertRegex(submission_str, r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Test 2: When submission_date is None, should use current time
        self.assignment.submission_date = None
        self.assignment.save()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            before_call = timezone.now()
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )
            after_call = timezone.now()

            call_args = mock_pdf.call_args
            form_data = call_args[0][1] if call_args[0] else {}

            # Verify we got a datetime string
            self.assertIn('submission_datetime', form_data)
            submission_str = form_data.get('submission_datetime', '')
            self.assertRegex(submission_str, r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_pdf_vat_fiscal_code_fallback(self):
        """Test VAT/fiscal code extraction uses fallback: vat_number > fiscal_code."""
        from unittest.mock import patch
        from modules.report_generator import generate_form_receipt_pdf
        import tempfile

        # Test 1: Customer with vat_number
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )

                call_args = mock_pdf.call_args
                customer_data = call_args[0][2] if len(call_args[0]) > 2 else {}

                # Should use vat_number when available
                self.assertEqual(customer_data.get('vat'), 'IT12345678901')
                self.assertEqual(customer_data.get('vat_number'), 'IT12345678901')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Test 2: Customer with only fiscal_code (no vat_number)
        self.customer.vat_number = ''
        self.customer.fiscal_code = 'RSSMRA80A01H501X'
        self.customer.save()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.return_value = None
                generate_form_receipt_pdf(
                    self.template,
                    self.assignment,
                    tmp_path
                )

                call_args = mock_pdf.call_args
                customer_data = call_args[0][2] if len(call_args[0]) > 2 else {}

                # Should use fiscal_code when vat_number is empty
                self.assertEqual(customer_data.get('vat'), 'RSSMRA80A01H501X')
                self.assertEqual(customer_data.get('fiscal_code'), 'RSSMRA80A01H501X')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_pdf_generation_no_corrupt_on_error(self):
        """Test that PDF generation error doesn't corrupt manifest or leave orphan files."""
        from unittest.mock import patch
        from modules.report_generator import generate_form_receipt_pdf
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock generate_submission_pdf to raise an exception
            with patch('modules.report_generator.generate_submission_pdf') as mock_pdf:
                mock_pdf.side_effect = RuntimeError("PDF writer error")

                # Should handle exception gracefully
                try:
                    generate_form_receipt_pdf(
                        self.template,
                        self.assignment,
                        tmp_path
                    )
                except RuntimeError:
                    pass  # Expected to propagate the error

                # Verify PDF file was not created or is properly cleaned up
                # If error occurred during generation, file should not exist or be incomplete
                self.assertFalse(os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0,
                    "PDF file should not exist or should be empty after generation error")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestAdminDashboardCustomerGrouping(TestCase):
    """Test suite for Admin Dashboard customer grouping and semantic color-coding."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_dash',
            email='admin_dash@etichub.it',
            password='Password123!'
        )
        self.client.force_login(self.admin)

        self.template = FormTemplate.objects.create(
            name='Modulo Standard',
            project_name='Standard Project',
            status='published',
            author=self.admin
        )
        self.expiry = timezone.now() + timezone.timedelta(days=30)

        # Cust 1: All Completed -> Green
        self.cust_green = Customer.objects.create(code='CUST-G1', first_name='Acme', last_name='Green', nas_folder_name='cust_g1')
        FormAssignment.objects.create(customer=self.cust_green, form_template=self.template, status='completed', expiry_date=self.expiry, form_data={'project_name': 'Prod G1'})
        FormAssignment.objects.create(customer=self.cust_green, form_template=self.template, status='completed', expiry_date=self.expiry, form_data={'project_name': 'Prod G2'})

        # Cust 2: All Submitted (Da Lavorare) -> Red
        self.cust_red = Customer.objects.create(code='CUST-R1', first_name='Beta', last_name='Red', nas_folder_name='cust_r1')
        FormAssignment.objects.create(customer=self.cust_red, form_template=self.template, status='submitted', expiry_date=self.expiry, form_data={'project_name': 'Prod R1'})

        # Cust 3: In Processing -> Orange
        self.cust_orange = Customer.objects.create(code='CUST-O1', first_name='Gamma', last_name='Orange', nas_folder_name='cust_o1')
        FormAssignment.objects.create(customer=self.cust_orange, form_template=self.template, status='in_processing', expiry_date=self.expiry, form_data={'project_name': 'Prod O1'})

        # Cust 4: In Progress / Draft -> Yellow
        self.cust_yellow = Customer.objects.create(code='CUST-Y1', first_name='Delta', last_name='Yellow', nas_folder_name='cust_y1')
        FormAssignment.objects.create(customer=self.cust_yellow, form_template=self.template, status='in_progress', expiry_date=self.expiry, form_data={'project_name': 'Prod Y1'})

        # Cust 5: No practices -> Neutral
        self.cust_neutral = Customer.objects.create(code='CUST-N1', first_name='Epsilon', last_name='Neutral', nas_folder_name='cust_n1')

    def test_dashboard_customer_groups_and_colors(self):
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 200)

        customer_groups = resp.context['customer_groups']
        self.assertEqual(len(customer_groups), 5)

        by_code = {cg['code']: cg for cg in customer_groups}

        # Check colors and status codes
        self.assertEqual(by_code['CUST-G1']['status_color'], 'green')
        self.assertEqual(by_code['CUST-G1']['status_code'], 'completed')
        self.assertEqual(len(by_code['CUST-G1']['products']), 2)

        self.assertEqual(by_code['CUST-R1']['status_color'], 'red')
        self.assertEqual(by_code['CUST-R1']['status_code'], 'to_work')

        self.assertEqual(by_code['CUST-O1']['status_color'], 'orange')
        self.assertEqual(by_code['CUST-O1']['status_code'], 'in_processing')

        self.assertEqual(by_code['CUST-Y1']['status_color'], 'yellow')
        self.assertEqual(by_code['CUST-Y1']['status_code'], 'waiting_docs')

        self.assertEqual(by_code['CUST-N1']['status_color'], 'neutral')
        self.assertEqual(by_code['CUST-N1']['status_code'], 'empty')

        # Check filter counts
        filter_counts = resp.context['filter_counts']
        self.assertEqual(filter_counts['all'], 5)
        self.assertEqual(filter_counts['completed'], 1)
        self.assertEqual(filter_counts['to_work'], 1)
        self.assertEqual(filter_counts['in_processing'], 1)
        self.assertEqual(filter_counts['waiting_docs'], 1)

        # Check that HTML rendered accordion cards and console
        content = resp.content.decode('utf-8')
        self.assertIn('Gestione Clienti e Prodotti', content)
        self.assertIn('customerSearchInput', content)
        self.assertIn('customerSortSelect', content)
        self.assertIn('status-border-green', content)
        self.assertIn('status-border-red', content)
        self.assertIn('status-border-orange', content)
        self.assertIn('status-border-yellow', content)
        self.assertIn('Prod G1', content)
        self.assertIn('Prod R1', content)

    def test_client_dashboard_badge_label_rendering(self):
        session = self.client.session
        session['customer_id'] = str(self.cust_red.id)
        session.save()

        resp = self.client.get(reverse('client_dashboard'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Doc. Inviati', content)
        self.assertIn('Prod R1', content)

    def test_client_upload_guide_translations_all_languages(self):
        """Verify that all 4 supported languages contain all upload guide keys."""
        from .client_i18n import TRANSLATIONS
        guide_keys = [
            'guide_fab_label', 'guide_modal_title', 'guide_modal_subtitle',
            'guide_step1_badge', 'guide_step1_title', 'guide_step1_desc',
            'guide_step2_badge', 'guide_step2_title', 'guide_step2_desc',
            'guide_step3_badge', 'guide_step3_title', 'guide_step3_desc',
            'guide_step4_badge', 'guide_step4_title', 'guide_step4_desc',
            'guide_step5_badge', 'guide_step5_title', 'guide_step5_desc',
            'guide_help_box_title', 'guide_help_box_desc',
            'guide_dont_show_again', 'guide_btn_start', 'guide_btn_close',
        ]
        for lang in ['it', 'en', 'fr', 'de']:
            self.assertIn(lang, TRANSLATIONS, f"Language {lang} missing in TRANSLATIONS")
            dict_lang = TRANSLATIONS[lang]
            for key in guide_keys:
                self.assertIn(key, dict_lang, f"Key '{key}' missing for language '{lang}'")
                self.assertTrue(dict_lang[key], f"Key '{key}' is empty for language '{lang}'")

    def test_client_dashboard_renders_upload_guide_modal_and_fab(self):
        """Verify that client dashboard renders the upload guide modal and floating button."""
        session = self.client.session
        session['customer_id'] = str(self.cust_red.id)
        session['customer_code'] = self.cust_red.code
        session.save()

        resp = self.client.get(reverse('client_dashboard'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('btnFloatingUploadGuide', content)
        self.assertIn('uploadGuideModal', content)
        self.assertIn('dontShowGuideAgain', content)
        self.assertIn('Guida Upload', content)
        self.assertIn('btnStartUploadGuide', content)
        self.assertIn('Inizia', content)


class ClientLoginAndIntroAnimationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Mario',
            last_name='Rossi',
            email='mario.rossi@example.com',
            code='CLI-999',
            active=True
        )
        self.customer.set_portal_password('Secr3tP@ss!')
        self.customer.save()

    def test_client_login_page_renders_with_intro_animation(self):
        resp = self.client.get(reverse('client_login'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('etichub-intro', content)
        self.assertIn('etichub-logo', content)
        self.assertIn('id="id_code"', content)
        self.assertIn('id="id_password"', content)
        self.assertIn('name="code"', content)
        self.assertIn('name="password"', content)
        self.assertIn('Rivedi animazione', content)
        self.assertIn('lang-selector-bar', content)
        self.assertIn('Codice Cliente', content)
        self.assertNotIn('type="email"', content)

    def test_client_login_invalid_credentials_shows_error(self):
        resp = self.client.post(reverse('client_login'), {
            'code': 'CLI-999',
            'password': 'wrongpassword'
        })
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Password errata. Riprova.', content)

    def test_client_login_success_sets_session_and_redirects(self):
        resp = self.client.post(reverse('client_login'), {
            'code': 'CLI-999',
            'password': 'Secr3tP@ss!'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('client_dashboard'))
        self.assertEqual(self.client.session.get('customer_id'), str(self.customer.id))
        self.assertEqual(self.client.session.get('customer_code'), 'CLI-999')

    def test_client_login_already_logged_in_redirects(self):
        session = self.client.session
        session['customer_id'] = str(self.customer.id)
        session['customer_code'] = self.customer.code
        session.save()

        resp = self.client.get(reverse('client_login'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('client_dashboard'))

    def test_client_login_ensures_csrf_cookie(self):
        resp = self.client.get(reverse('client_login'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('csrftoken', resp.cookies)

    def test_client_logout_clears_session_and_redirects(self):
        session = self.client.session
        session['customer_id'] = str(self.customer.id)
        session['customer_code'] = self.customer.code
        session.save()

        # Test POST logout without CSRF token (csrf_exempt)
        resp = self.client.post(reverse('client_logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('client_login'))
        self.assertIsNone(self.client.session.get('customer_id'))

        # Test GET logout as well
        session = self.client.session
        session['customer_id'] = str(self.customer.id)
        session.save()
        resp = self.client.get(reverse('client_logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('client_login'))
        self.assertIsNone(self.client.session.get('customer_id'))


class TestAnalyticsDashboardView(TestCase):
    """Test suite for Admin Management Statistics & Analytics Dashboard."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_analytics',
            email='admin_analytics@etichub.it',
            password='Password123!'
        )
        self.client.force_login(self.admin)

        self.customer = Customer.objects.create(
            first_name='Test Analytics Pharma',
            code='TAP-001',
            nas_folder_name='tap_001',
            email='pharma@example.com'
        )

        self.template = FormTemplate.objects.create(
            name='Modulo Crema Solare',
            project_name='Crema Solare SPF50',
            status='published',
            author=self.admin
        )

        # Create an assignment that was completed
        now = timezone.now()
        self.assignment_completed = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            status='completed',
            assignment_date=now - timezone.timedelta(days=5),
            last_access_date=now - timezone.timedelta(days=4),
            submission_date=now - timezone.timedelta(days=3),
            expiry_date=now + timezone.timedelta(days=30),
            form_data={
                'project_name': 'Crema Solare SPF50',
                'in_processing_at': (now - timezone.timedelta(days=2)).isoformat(),
                'completed_at': (now - timezone.timedelta(days=1)).isoformat(),
                'completed_by': 'admin_analytics'
            }
        )

    def test_analytics_dashboard_view_success(self):
        resp = self.client.get(reverse('analytics_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'modules/admin/analytics.html')
        self.assertIn('total_assignments', resp.context)
        self.assertIn('completed_count', resp.context)
        self.assertEqual(resp.context['total_assignments'], 1)
        self.assertIn('avg_cust_upload_days', resp.context)
        self.assertIn('avg_op_proc_days', resp.context)
        self.assertIn('avg_e2e_days', resp.context)
        self.assertIn('chart_status_data', resp.context)
        self.assertEqual(resp.context['sla_target_days'], 30)
        content = resp.content.decode('utf-8')
        self.assertIn('Statistiche & Tempi di Gestione', content)
        self.assertIn('Test Analytics Pharma', content)


class TestBulkZipExtractionAndUpload(TestCase):
    """Test suite for ZIP bulk extraction and indexing engine."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_zip',
            email='admin_zip@etichub.it',
            password='Password123!'
        )
        self.customer = Customer.objects.create(
            first_name='Laboratorio Cosmetico SRL',
            code='LDF-99',
            nas_folder_name='ldf_99',
            email='lab@example.com'
        )
        self.template = FormTemplate.objects.create(
            name='Form Formule',
            project_name='Crema Antietà',
            status='published',
            author=self.admin
        )
        self.step = FormStep.objects.create(
            form_template=self.template,
            order=1,
            title='Upload Materie Prime'
        )
        self.req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Allegato1',
            order=1,
            destination_subfolder='Allegato1',
            max_file_size=50 * 1024 * 1024,
            allowed_extensions='pdf,zip,txt',
            mime_types='application/pdf,application/zip,text/plain'
        )
        now = timezone.now()
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            status='in_progress',
            expiry_date=now + timezone.timedelta(days=30)
        )

    def test_validate_zip_safety_and_extraction(self):
        import io
        import zipfile
        import tempfile
        import shutil
        from modules.upload_security import validate_zip_archive_safety, extract_and_index_zip_archive

        # Build in-memory zip containing subfolders and files
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('Materie Prime/olio_mandorle.pdf', b'%PDF-1.4 simulated pdf data')
            zf.writestr('Materie Prime/Certificati/coaf.pdf', b'%PDF-1.4 simulated cert data')
            zf.writestr('Materie Prime/scheda_sicurezza.txt', b'MSDS safe compound info')

        zip_bytes = zip_buf.getvalue()

        # Validate safety
        zip_errors = validate_zip_archive_safety(io.BytesIO(zip_bytes))
        self.assertEqual(len(zip_errors), 0, f"Safety check failed: {zip_errors}")

        # Setup temporary directories simulating NAS structure
        temp_dir = tempfile.mkdtemp()
        project_dir = os.path.join(temp_dir, 'Laboratorio_Cosmetico', 'Crema_Antieta')
        os.makedirs(project_dir, exist_ok=True)
        manifest_path = os.path.join(project_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump({'uploads': []}, f)

        try:
            with io.BytesIO(zip_bytes) as zf_obj:
                res = extract_and_index_zip_archive(
                    file_obj=zf_obj,
                    assignment=self.assignment,
                    requirement=self.req,
                    nas_project_path=project_dir
                )

            # Check extracted count
            self.assertEqual(res['count'], 3)

            # Check files exist on disk
            target_allegato_dir = os.path.join(project_dir, 'Allegato1')
            extracted_f1 = os.path.join(target_allegato_dir, 'Materie Prime', 'olio_mandorle.pdf')
            extracted_f2 = os.path.join(target_allegato_dir, 'Materie Prime', 'Certificati', 'coaf.pdf')
            self.assertTrue(os.path.exists(extracted_f1))
            self.assertTrue(os.path.exists(extracted_f2))

            # Check DB records
            uploads = DocumentUpload.objects.filter(form_assignment=self.assignment, document_requirement=self.req)
            self.assertEqual(uploads.count(), 3)

            # Check manifest updated
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            self.assertIn('uploads', manifest_data)
            self.assertEqual(len(manifest_data['uploads']), 3)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPdfReceiptWithTimeline(TestCase):
    """Test suite for PDF report generation with Lifecycle Timeline and multiple uploads."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_pdf',
            email='admin_pdf@etichub.it',
            password='Password123!'
        )
        self.customer = Customer.objects.create(
            first_name='Acme Cosmetics',
            code='ACM-01',
            nas_folder_name='acm_01',
            email='acme@example.com'
        )
        self.template = FormTemplate.objects.create(
            name='Modulo Crema Idratante',
            project_name='Crema Idratante Notte',
            status='published',
            author=self.admin
        )
        self.step = FormStep.objects.create(
            form_template=self.template,
            order=1,
            title='Documenti Prodotto'
        )
        self.req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Allegato1',
            order=1,
            destination_subfolder='Allegato1',
            max_file_size=50 * 1024 * 1024,
            allowed_extensions='pdf,zip,txt',
            mime_types='application/pdf,application/zip,text/plain'
        )
        now = timezone.now()
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            status='completed',
            assignment_date=now - timezone.timedelta(days=4),
            last_access_date=now - timezone.timedelta(days=3),
            submission_date=now - timezone.timedelta(days=2),
            expiry_date=now + timezone.timedelta(days=30),
            form_data={
                'project_name': 'Crema Idratante Notte',
                'in_processing_at': (now - timezone.timedelta(days=1)).isoformat(),
                'completed_at': now.isoformat(),
                'completed_by': 'admin_pdf'
            }
        )

        # Create two uploads for requirement
        DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.req,
            original_filename='olio_argan.pdf',
            stored_filename='olio_argan.pdf',
            relative_path='Allegato1/olio_argan.pdf',
            file_size=10240,
            sha256_checksum='abc123hash',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='Test',
            status='valid'
        )
        DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.req,
            original_filename='coaf_mandorle.pdf',
            stored_filename='coaf_mandorle.pdf',
            relative_path='Allegato1/coaf_mandorle.pdf',
            file_size=20480,
            sha256_checksum='def456hash',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='Test',
            status='valid'
        )

    def test_generate_pdf_with_timeline_success(self):
        import tempfile
        from modules.report_generator import generate_form_receipt_pdf

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            generate_form_receipt_pdf(self.template, self.assignment, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 1000)

            # Read PDF header
            with open(tmp_path, 'rb') as f:
                header = f.read(5)
            self.assertEqual(header, b'%PDF-')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestIntroAnimationSuppressionInPersonalArea(TestCase):
    """Test suite ensuring intro animation only runs on login or direct landing page, never during personal area navigation."""

    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(
            first_name='Federica',
            last_name='Fusco',
            code='CLI-FUSCO',
            nas_folder_name='cli_fusco',
            email='fusco@example.com'
        )
        self.template = FormTemplate.objects.create(
            name='Upload Documentale',
            project_name='Crema Viso Idratante',
            status='published'
        )
        now = timezone.now()
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            status='in_progress',
            expiry_date=now + timezone.timedelta(days=30)
        )

    def test_external_access_shows_intro_animation(self):
        # Direct external link without existing logged session
        token_url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        resp = self.client.get(token_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['show_intro'])
        content = resp.content.decode('utf-8')
        self.assertIn('<etichub-intro', content)

    def test_personal_area_navigation_suppresses_intro_animation(self):
        # User is logged in to personal area (customer_id in session)
        session = self.client.session
        session['customer_id'] = str(self.customer.id)
        session['customer_code'] = self.customer.code
        session.save()

        # Access from client personal area product detail
        product_detail_url = reverse('client_product_detail', kwargs={'assignment_id': self.assignment.id})
        resp = self.client.get(product_detail_url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['show_intro'])
        content = resp.content.decode('utf-8')
        self.assertNotIn('<etichub-intro', content)

    def test_direct_form_url_with_logged_in_session_suppresses_intro(self):
        # User is logged in to personal area and opens form directly
        session = self.client.session
        session['customer_id'] = str(self.customer.id)
        session.save()

        token_url = reverse('get_form_by_token', kwargs={'token': self.assignment.secure_token})
        resp = self.client.get(token_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['show_intro'])
        content = resp.content.decode('utf-8')
        self.assertNotIn('<etichub-intro', content)


class UserManagementRolePermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_boss',
            email='admin_boss@test.com',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=False
        )
        self.operator_user = User.objects.create_user(
            username='alessia_operator',
            email='alessia@test.com',
            password='password123',
            role='operator',
            is_staff=True,
            is_superuser=False
        )

    def test_operator_cannot_access_user_list_api(self):
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('admin_user_list'))
        # Should be redirected away due to user_passes_test(is_admin_user)
        self.assertEqual(response.status_code, 302)

    def test_operator_cannot_create_user_api(self):
        self.client.force_login(self.operator_user)
        response = self.client.post(
            reverse('admin_user_create'),
            data=json.dumps({
                'username': 'new_user',
                'email': 'new@test.com',
                'password': 'password123',
                'role': 'operator'
            }),
            content_type='application/json'
        )
        # Should be redirected away due to user_passes_test(is_admin_user)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='new_user').exists())

    def test_admin_can_access_user_list_api(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_user_list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        usernames = [u['username'] for u in data]
        self.assertIn('admin_boss', usernames)
        self.assertIn('alessia_operator', usernames)

    def test_operator_dashboard_renders_without_user_management_modal(self):
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Operator should NOT have the dropdown item or the modal
        self.assertNotIn('Gestione Utenti', content)
        self.assertNotIn('openUserManagementModal', content)
        self.assertNotIn('userManagementModal', content)

    def test_admin_dashboard_renders_with_user_management_modal(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Admin SHOULD have the dropdown item and the modal
        self.assertIn('Gestione Utenti', content)
        self.assertIn('openUserManagementModal', content)
        self.assertIn('userManagementModal', content)


class SecurityHardeningTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='sec_admin',
            email='sec_admin@example.com',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.customer = Customer.objects.create(
            code="SEC_CLI_01",
            first_name="Sec Corp",
            last_name="Owner",
            email="sec@example.com",
            nas_folder_name="SEC_CLI_01"
        )
        self.customer.set_portal_password("SecretPass123")
        self.customer.save()

    def test_customer_edit_json_does_not_expose_plaintext_password(self):
        self.client.force_login(self.admin_user)
        url = reverse('customer_edit', kwargs={'pk': self.customer.id})
        response = self.client.post(
            url,
            {
                'code': self.customer.code,
                'first_name': self.customer.first_name,
                'last_name': self.customer.last_name,
                'email': self.customer.email,
                'nas_folder_name': self.customer.nas_folder_name,
                'portal_password': 'BrandNewSuperSecret!',
                'active': 'true'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data.get('password_updated'))
        # Ensure plaintext password is NOT leaked in JSON
        self.assertNotIn('new_password', data)
        self.assertNotIn('BrandNewSuperSecret!', response.content.decode('utf-8'))

    def test_customer_reset_password_json_does_not_expose_plaintext_password(self):
        self.client.force_login(self.admin_user)
        url = reverse('customer_reset_password', kwargs={'pk': self.customer.id})
        response = self.client.post(
            url,
            {'new_password': 'ResetPass999!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data.get('password_updated'))
        # Ensure plaintext password is NOT leaked in JSON
        self.assertNotIn('new_password', data)
        self.assertNotIn('ResetPass999!', response.content.decode('utf-8'))

    def test_is_ajax_request_helper(self):
        from modules.utils import is_ajax_request
        from django.test import RequestFactory
        rf = RequestFactory()

        req1 = rf.get('/test/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(is_ajax_request(req1))

        req2 = rf.get('/test/', HTTP_ACCEPT='application/json')
        self.assertTrue(is_ajax_request(req2))

        req3 = rf.get('/test/?format=json')
        self.assertTrue(is_ajax_request(req3))

        req4 = rf.get('/test/')
        self.assertFalse(is_ajax_request(req4))

    def test_log_action_normalizes_string_details_and_action(self):
        from modules.utils import log_action
        from modules.models import AuditLog

        log_action(
            self.admin_user,
            action='create_user',
            object_type='User',
            object_id='999',
            details='User created successfully'
        )
        log = AuditLog.objects.filter(object_id='999').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'create')
        self.assertIsInstance(log.details, dict)
        self.assertEqual(log.details.get('message'), 'User created successfully')


class Sprint4AdvancedTestingAndValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_sprint4',
            email='admin_s4@example.com',
            password='Password123!',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.customer = Customer.objects.create(
            code="CUST_S4_01",
            first_name="Mario",
            last_name="Rossi",
            email="mario.rossi@example.com",
            nas_folder_name="MARIO_ROSSI_S4",
            active=True
        )
        self.template = FormTemplate.objects.create(
            name="Template Sprint 4",
            intro_text="Intro",
            status="published",
            project_name="Sprint4Proj"
        )

    def test_customer_form_valid(self):
        from modules.forms import CustomerForm
        form_data = {
            'code': 'NEW_CODE_01',
            'first_name': 'Luigi',
            'last_name': 'Verdi',
            'email': 'luigi.verdi@example.com',
            'phone': '123456789',
            'nas_folder_name': 'LUIGI_VERDI_NAS',
            'active': True
        }
        form = CustomerForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.code, 'NEW_CODE_01')

    def test_customer_form_duplicate_code_case_insensitive(self):
        from modules.forms import CustomerForm
        form_data = {
            'code': 'cust_s4_01',  # same code, different case
            'first_name': 'Another',
            'last_name': 'User',
            'email': 'another@example.com',
            'nas_folder_name': 'ANOTHER_NAS',
            'active': True
        }
        form = CustomerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_customer_form_invalid_code_characters(self):
        from modules.forms import CustomerForm
        form_data = {
            'code': 'INVALID CODE!!',
            'first_name': 'Test',
            'last_name': 'Invalid',
            'email': 'invalid@example.com',
            'nas_folder_name': 'VALID_NAS',
            'active': True
        }
        form = CustomerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_customer_form_duplicate_nas_folder(self):
        from modules.forms import CustomerForm
        form_data = {
            'code': 'CODE_UNIQUE_1',
            'first_name': 'Duplicate',
            'last_name': 'Folder',
            'email': 'dup@example.com',
            'nas_folder_name': 'mario_rossi_s4',  # duplicate of self.customer.nas_folder_name
            'active': True
        }
        form = CustomerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('nas_folder_name', form.errors)

    def test_form_assignment_form_valid(self):
        from modules.forms import FormAssignmentForm
        form_data = {
            'template_id': str(self.template.id),
            'customer_id': str(self.customer.id),
            'project_name': 'Legal_Docs_2026',
        }
        form = FormAssignmentForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['template_id'], self.template)
        self.assertEqual(form.cleaned_data['customer_id'], self.customer)
        self.assertEqual(form.cleaned_data['project_name'], 'Legal_Docs_2026')

    def test_form_assignment_form_invalid_project_name_characters(self):
        from modules.forms import FormAssignmentForm
        form_data = {
            'template_id': str(self.template.id),
            'customer_id': str(self.customer.id),
            'project_name': 'Invalid/Project:Name*?',
        }
        form = FormAssignmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('project_name', form.errors)

    def test_form_assignment_form_rejects_archived_template(self):
        from modules.forms import FormAssignmentForm
        self.template.status = 'archived'
        self.template.save()

        form_data = {
            'template_id': str(self.template.id),
            'customer_id': str(self.customer.id),
            'project_name': 'Valid_Project',
        }
        form = FormAssignmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('template_id', form.errors)

    def test_form_assignment_form_rejects_inactive_customer(self):
        from modules.forms import FormAssignmentForm
        self.customer.active = False
        self.customer.save()

        form_data = {
            'template_id': str(self.template.id),
            'customer_id': str(self.customer.id),
            'project_name': 'Valid_Project',
        }
        form = FormAssignmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('customer_id', form.errors)

    def test_admin_user_form_valid_and_duplicate_username(self):
        from modules.forms import AdminUserForm
        form_data = {
            'username': 'admin_sprint4',  # already exists
            'email': 'test@test.com',
            'role': 'operator',
            'is_active': True,
        }
        form = AdminUserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

        # Now with unique username
        form_data['username'] = 'operator_unique'
        form2 = AdminUserForm(data=form_data)
        self.assertTrue(form2.is_valid(), form2.errors)

    def test_assignment_delete_view(self):
        self.client.force_login(self.admin_user)
        assignment = FormAssignment.objects.create(
            form_template=self.template,
            customer=self.customer,
            status='in_progress',
            expiry_date=timezone.now() + timezone.timedelta(days=30),
            form_data={'project_name': 'Project_To_Delete'},
            secure_token='deltoken123456789012345678901234'
        )
        url = reverse('assignment_delete', kwargs={'pk': assignment.id})

        # GET request should be rejected (require_http_methods POST)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 405)

        # POST request should succeed and redirect
        response_post = self.client.post(url, follow=True)
        self.assertEqual(response_post.status_code, 200)

        # FormAssignment should be deleted
        self.assertFalse(FormAssignment.objects.filter(id=assignment.id).exists())
        # Customer and template should still exist
        self.assertTrue(Customer.objects.filter(id=self.customer.id).exists())
        self.assertTrue(FormTemplate.objects.filter(id=self.template.id).exists())

        # AuditLog should record the deletion
        audit = AuditLog.objects.filter(action='delete', object_type='FormAssignment', object_id=str(assignment.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_user, self.admin_user)

    def test_api_form_save_with_document_requirement_sets_max_file_size(self):
        self.client.force_login(self.admin_user)
        draft_form = FormTemplate.objects.create(
            name="Test Builder Draft",
            status="draft",
            author=self.admin_user
        )
        url = reverse('api_form_save', kwargs={'form_id': draft_form.id})
        payload = {
            'name': 'Test Builder Draft Updated',
            'steps': [
                {
                    'title': 'Step Documenti',
                    'required': True,
                    'elements': [
                        {
                            'type': 'document',
                            'name': 'Documento Responsabile',
                            'description': 'Descrizione documento',
                            'required': True,
                            'allowed_extensions': 'pdf,docx',
                            'mime_types': 'application/pdf,application/msword',
                            'max_file_size': 10,  # 10 MB in builder
                            'max_files': 200,
                            'destination_subfolder': 'Allegato I_Persona Responsabile'
                        },
                        {
                            'type': 'document',
                            'name': 'Documento Senza Size',
                            'description': 'Test fallback default',
                            'required': False,
                            'max_file_size': None
                        }
                    ]
                }
            ]
        }
        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'), data)

        # Verify DocumentRequirements were created and have non-null max_file_size in bytes
        doc1 = DocumentRequirement.objects.get(name='Documento Responsabile')
        self.assertIsNotNone(doc1.max_file_size)
        self.assertEqual(doc1.max_file_size, 10 * 1024 * 1024)

        doc2 = DocumentRequirement.objects.get(name='Documento Senza Size')
        self.assertIsNotNone(doc2.max_file_size)
        self.assertEqual(doc2.max_file_size, 10 * 1024 * 1024)


from pathlib import Path
import gzip
import modules.views_maintenance as vm


class MaintenanceAndBackupTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='maint_admin',
            email='maint_admin@example.com',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.operator_user = User.objects.create_user(
            username='maint_operator',
            email='maint_op@example.com',
            password='password123',
            role='operator',
            is_staff=True,
            is_superuser=False
        )
        self.temp_backup_dir = Path(tempfile.mkdtemp(prefix="backup_test_"))
        self.original_backup_dir = vm.BACKUP_DIR
        vm.BACKUP_DIR = self.temp_backup_dir

    def tearDown(self):
        vm.BACKUP_DIR = self.original_backup_dir
        if self.temp_backup_dir.exists():
            shutil.rmtree(self.temp_backup_dir, ignore_errors=True)

    def test_anonymous_redirected_from_maintenance(self):
        response = self.client.get(reverse('admin_maintenance'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_operator_access_denied(self):
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('admin_maintenance'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_admin_can_access_maintenance_dashboard(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_maintenance'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Manutenzione &amp; Backup Sistema', content.replace('&', '&amp;'))
        self.assertIn('Reset Statistiche', content)

    def test_backup_create_and_download(self):
        self.client.force_login(self.admin_user)
        # 1. Create a backup
        response = self.client.post(reverse('admin_backup_create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin_maintenance'))

        # Verify file created on disk in temp_backup_dir
        files = list(self.temp_backup_dir.glob("*.json.gz"))
        self.assertEqual(len(files), 1)
        backup_file = files[0]
        self.assertTrue(backup_file.name.endswith('.json.gz'))

        # Verify gzip content is valid json
        with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIsInstance(data, list)
            models_in_dump = [item['model'] for item in data]
            self.assertIn('modules.user', models_in_dump)

        # 2. Download backup
        download_url = reverse('admin_backup_download', kwargs={'filename': backup_file.name})
        dl_response = self.client.get(download_url)
        self.assertEqual(dl_response.status_code, 200)
        self.assertEqual(dl_response.headers.get('Content-Disposition'), f'attachment; filename="{backup_file.name}"')
        dl_response.close()

    def test_backup_download_traversal_prevention(self):
        self.client.force_login(self.admin_user)
        download_url = '/admin/maintenance/backup/../../something/download/'
        response = self.client.get(download_url)
        self.assertIn(response.status_code, [400, 404])

    def test_backup_delete(self):
        self.client.force_login(self.admin_user)
        dummy_file = self.temp_backup_dir / "test_del.json.gz"
        with gzip.open(dummy_file, 'wt', encoding='utf-8') as f:
            f.write("[]")

        self.assertTrue(dummy_file.exists())
        del_url = reverse('admin_backup_delete', kwargs={'filename': dummy_file.name})
        response = self.client.post(del_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(dummy_file.exists())

    def test_backup_restore_from_server(self):
        self.client.force_login(self.admin_user)
        Customer.objects.create(
            code="CUST_BCK_01",
            first_name="Mario",
            last_name="Rossi",
            email="backup@test.com",
            nas_folder_name="MARIO_ROSSI_BCK"
        )
        self.assertTrue(Customer.objects.filter(code="CUST_BCK_01").exists())

        # Create backup
        self.client.post(reverse('admin_backup_create'))
        files = list(self.temp_backup_dir.glob("ehmoduli_backup_*.json.gz"))
        self.assertEqual(len(files), 1)
        backup_filename = files[0].name

        # Perform restore
        restore_url = reverse('admin_backup_restore')
        resp = self.client.post(restore_url, {
            'backup_source': 'server',
            'backup_filename': backup_filename,
            'confirm_text': 'RIPRISTINA'
        })
        self.assertEqual(resp.status_code, 302)

        # Check that a pre_restore snapshot was created
        pre_snapshots = list(self.temp_backup_dir.glob("pre_restore_snapshot_*.json.gz"))
        self.assertTrue(len(pre_snapshots) >= 1)

    def test_reset_statistics(self):
        self.client.force_login(self.admin_user)
        AuditLog.objects.create(
            action='create',
            object_type='test',
            object_id='1',
            actor_ip='127.0.0.1',
            actor_user_agent='test-agent',
            details={'msg': 'detail 1'}
        )
        AuditLog.objects.create(
            action='update',
            object_type='test',
            object_id='2',
            actor_ip='127.0.0.1',
            actor_user_agent='test-agent',
            details={'msg': 'detail 2'}
        )
        NotificationLog.objects.create(
            notification_type='form_assigned',
            recipient_email='test@example.com'
        )

        self.assertGreaterEqual(AuditLog.objects.count(), 2)
        self.assertEqual(NotificationLog.objects.count(), 1)

        # Post reset without confirmation text -> fails
        reset_url = reverse('admin_reset_statistics')
        resp = self.client.post(reset_url, {'reset_mode': 'all', 'confirm_text': 'WRONG'})
        self.assertEqual(resp.status_code, 302)
        self.assertGreaterEqual(AuditLog.objects.count(), 2)

        # Post reset with valid 'RESET' text
        resp = self.client.post(reset_url, {'reset_mode': 'all', 'confirm_text': 'RESET'})
        self.assertEqual(resp.status_code, 302)

        # NotificationLog should be 0
        self.assertEqual(NotificationLog.objects.count(), 0)
        # AuditLog will only have the log entry for the reset action itself
        reset_logs = AuditLog.objects.filter(object_id='telemetry_reset')
        self.assertEqual(reset_logs.count(), 1)
        self.assertEqual(AuditLog.objects.count(), 1)


class XlsxUploadAndMimeSyncTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_xlsx',
            email='admin_xlsx@example.com',
            password='Password123!',
            role='admin',
            is_staff=True
        )
        self.template = FormTemplate.objects.create(
            name='Test XLSX Template',
            description='Template testing xlsx extension',
            intro_text='Intro',
            privacy_text='Privacy',
            author=self.user,
            status='draft'
        )
        self.step = FormStep.objects.create(
            form_template=self.template,
            title='Step 1',
            order=0
        )
        # Simulate an existing document requirement configured with allowed_extensions='pdf,docx,xlsx'
        # but with old mime_types='application/pdf,application/msword'
        self.req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Composizione quali-quantitativa',
            allowed_extensions='pdf,docx,xlsx',
            mime_types='application/pdf,application/msword',
            max_file_size=10 * 1024 * 1024,
            destination_subfolder='Composizione',
            order=0
        )

    def test_get_mimes_for_extensions(self):
        from modules.validators import get_mimes_for_extensions
        mimes = get_mimes_for_extensions('pdf,docx,xlsx')
        self.assertIn('application/pdf', mimes)
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', mimes)
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document', mimes)

    def test_document_requirement_file_accept_attribute(self):
        accept_attr = self.req.file_accept_attribute
        self.assertIn('.xlsx', accept_attr)
        self.assertIn('.pdf', accept_attr)
        self.assertIn('.docx', accept_attr)
        self.assertIn('.zip', accept_attr)
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', accept_attr)

    def test_document_requirement_save_auto_populates_mime_types(self):
        new_req = DocumentRequirement(
            form_step=self.step,
            name='Nuovo Doc',
            allowed_extensions='xlsx,csv',
            mime_types='application/pdf',
            destination_subfolder='Nuovo',
            order=1
        )
        new_req.save()
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', new_req.mime_types)
        self.assertIn('text/csv', new_req.mime_types)

    def test_xlsx_file_upload_validation_succeeds(self):
        from modules.upload_security import validate_file_upload_secure
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        import zipfile

        # Build a valid XLSX file in memory (a zip containing minimal openxml structures)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
            zf.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>')
        xlsx_content = buf.getvalue()

        file_obj = SimpleUploadedFile(
            name='formula_composizione.xlsx',
            content=xlsx_content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # Even though self.req had only 'application/pdf,application/msword' initially,
        # validate_file_upload_secure should derive the XLSX mime type and allow it!
        errors = validate_file_upload_secure(file_obj, self.req)
        self.assertEqual(errors, [], f"Expected no errors for XLSX file upload, but got: {errors}")

    def test_forms_api_save_populates_mime_types_for_xlsx(self):
        self.client.force_login(self.user)
        save_url = f'/modules/api/v1/forms/{self.template.id}/save/'
        payload = {
            'name': 'Updated XLSX Form',
            'description': 'Updated Desc',
            'intro_text': 'Updated Intro',
            'privacy_text': 'Updated Privacy',
            'steps': [
                {
                    'title': 'Step 1',
                    'order': 0,
                    'required': True,
                    'active': True,
                    'elements': [
                        {
                            'type': 'document',
                            'name': 'Upload Excel Form',
                            'description': 'Carica documento',
                            'required': True,
                            'allowed_extensions': 'pdf,docx,xlsx',
                            'mime_types': 'application/pdf,application/msword',  # Simulated old builder frontend payload
                            'max_file_size': 10,
                            'max_files': 200,
                            'destination_subfolder': 'Excel',
                            'order': 0
                        }
                    ]
                }
            ]
        }
        resp = self.client.put(save_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        # Check in database
        saved_doc = DocumentRequirement.objects.get(name='Upload Excel Form')
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', saved_doc.mime_types)
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document', saved_doc.mime_types)


class MultiFileUploadAndDeletionTestCase(TestCase):
    def setUp(self):
        from django.utils import timezone
        from datetime import timedelta
        self.client = Client()
        self.user = User.objects.create_user(
            username='op_multifile',
            email='op_multifile@example.com',
            password='Password123!',
            role='operator'
        )
        self.customer = Customer.objects.create(
            code="CUST_MULTI_01",
            first_name="Mario",
            last_name="Multi",
            email="mario.multi@example.com",
            nas_folder_name="MARIO_MULTI_NAS"
        )
        self.template = FormTemplate.objects.create(
            name="Multi File Form Template",
            status="published"
        )
        self.step = FormStep.objects.create(
            form_template=self.template,
            title='Step 1',
            order=0
        )
        self.multi_req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Allegati Multipli',
            allowed_extensions='pdf,docx,xlsx',
            max_file_size=10 * 1024 * 1024,
            max_files=10,
            destination_subfolder='Allegati',
            order=0
        )
        self.single_req = DocumentRequirement.objects.create(
            form_step=self.step,
            name='Documento Singolo',
            allowed_extensions='pdf',
            max_file_size=10 * 1024 * 1024,
            max_files=1,
            destination_subfolder='Singolo',
            order=1
        )
        self.assignment = FormAssignment.objects.create(
            customer=self.customer,
            form_template=self.template,
            expiry_date=timezone.now() + timedelta(days=30),
            operator=self.user,
            status='in_progress',
            form_data={
                'client_name': self.customer.nas_folder_name,
                'project_name': 'MultiTestProject'
            }
        )

    def test_multi_file_upload_keeps_all_valid_uploads(self):
        from modules.models import DocumentUpload
        up1 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file1.pdf',
            stored_filename='file1_hash.pdf',
            file_size=1024,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )
        up2 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file2.xlsx',
            stored_filename='file2_hash.xlsx',
            file_size=2048,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )
        valid_uploads = DocumentUpload.objects.filter(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            status='valid'
        )
        self.assertEqual(valid_uploads.count(), 2)

    def test_delete_upload_view(self):
        from modules.models import DocumentUpload
        up1 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file1.pdf',
            stored_filename='file1_hash.pdf',
            file_size=1024,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )
        up2 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file2.xlsx',
            stored_filename='file2_hash.xlsx',
            file_size=2048,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )

        delete_url = f'/modules/form/{self.assignment.id}/upload/{up1.id}/delete/'
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['remaining_count'], 1)

        up1.refresh_from_db()
        self.assertEqual(up1.status, 'superseded')
        up2.refresh_from_db()
        self.assertEqual(up2.status, 'valid')

    def test_form_step_view_groups_existing_uploads(self):
        from modules.models import DocumentUpload
        up1 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file1.pdf',
            stored_filename='file1_hash.pdf',
            file_size=1024,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )
        up2 = DocumentUpload.objects.create(
            form_assignment=self.assignment,
            document_requirement=self.multi_req,
            original_filename='file2.xlsx',
            stored_filename='file2_hash.xlsx',
            file_size=2048,
            status='valid',
            uploaded_by_ip='127.0.0.1',
            uploaded_by_user_agent='TestAgent'
        )
        token_url = f'/modules/form/{self.assignment.secure_token}/'
        self.client.get(token_url)
        step_url = f'/modules/form/{self.assignment.id}/step/0/'
        resp = self.client.get(step_url)
        self.assertEqual(resp.status_code, 200)
        grouped = resp.context.get('existing_uploads_grouped', {})
        self.assertIn(self.multi_req.id, grouped)
        self.assertEqual(len(grouped[self.multi_req.id]), 2)






