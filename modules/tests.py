import os
import shutil
import tempfile
from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Customer, FormTemplate, FormAssignment, AuditLog


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

        # Check in DB
        assignment = FormAssignment.objects.get(id=data['assignment_id'])
        self.assertEqual(assignment.form_data.get('access_password'), generated_pwd)

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






