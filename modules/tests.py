import os
import json
import shutil
import tempfile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import User, Customer, FormTemplate, FormStep, DocumentRequirement, FormAssignment, AuditLog


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
        self.assertIn('Link Riservato di Accesso Cliente', detail_content)
        self.assertIn(assignment.secure_token, detail_content)
        self.assertIn('ProgettoTest', detail_content)
        self.assertIn('btn-copy-link', detail_content)

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
        self.assertIn('handleFileUpload', content)

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

    def test_assign_form_autogenerates_password_when_empty(self):
        """Admin assigning a form without explicit password autogenerates 8-char password."""
        self.client.force_login(self.admin_user)
        url = reverse('assign_form_to_customer')
        post_data = {
            'customer_id': str(self.customer.id),
            'template_id': str(self.template.id),
            'project_name': 'TestAutoPwdProject',
            'access_password': '',  # Empty password
            'expiry_days': '30',
        }
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        generated_pwd = data.get('access_password')
        self.assertTrue(bool(generated_pwd))
        self.assertEqual(len(generated_pwd), 8)

        # Check in DB: password must be hashed, not stored in plaintext
        assignment = FormAssignment.objects.get(id=data['assignment_id'])
        self.assertTrue(assignment.check_access_password(generated_pwd))
        self.assertNotEqual(assignment.form_data.get('access_password'), generated_pwd)

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











