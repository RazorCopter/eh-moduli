from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin_test',
            email='admin_test@etichub.it',
            password='TestPassword123!',
            role='admin'
        )

    def test_logout_via_get_redirects_and_flushes_session(self):
        """Clicking a GET logout link must not return 405; it must logout and redirect to login."""
        self.client.force_login(self.user)
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_via_post_redirects_and_flushes_session(self):
        """POST logout must also logout cleanly and redirect to login."""
        self.client.force_login(self.user)
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_unauthenticated_user_safe(self):
        """Unauthenticated user accessing logout is redirected safely without errors."""
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

