from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class AutosalonAttorneyAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.url = reverse('autosalon')

    def test_attorney_tab_hidden_without_permission(self):
        user = self.user_model.objects.create_user(username='regular', password='pass1234')
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'autosalon-attorney-tab')

    def test_attorney_tab_visible_with_permission(self):
        user = self.user_model.objects.create_user(username='allowed', password='pass1234')
        permission = Permission.objects.get(codename='view_powerofattorney')
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autosalon-attorney-tab')

    def test_save_attorney_forbidden_without_permission(self):
        user = self.user_model.objects.create_user(username='forbidden', password='pass1234')
        self.client.force_login(user)

        response = self.client.post(self.url, {'action': 'save_attorney'})

        self.assertEqual(response.status_code, 403)
