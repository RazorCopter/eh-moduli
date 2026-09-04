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



