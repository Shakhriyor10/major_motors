from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class AutosalonAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.autosalon_url = reverse('autosalon')

    def test_autosalon_available_for_regular_user(self):
        user = self.user_model.objects.create_user(username='manager', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autosalon-attorney-tab')

    def test_autosalon_forbidden_for_blocked_user(self):
        user = self.user_model.objects.create_user(username='blocked', password='pass12345')
        permission = Permission.objects.get(codename='blocked_from_autosalon')
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 403)

    def test_attorney_tab_hidden_for_restricted_user(self):
        user = self.user_model.objects.create_user(username='noattorney', password='pass12345')
        permission = Permission.objects.get(codename='hide_attorney_tab')
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'autosalon-attorney-tab')
        self.assertNotContains(response, 'id="autosalon-attorney"')

    def test_attorney_save_forbidden_for_restricted_user(self):
        user = self.user_model.objects.create_user(username='hiddenpost', password='pass12345')
        permission = Permission.objects.get(codename='hide_attorney_tab')
        user.user_permissions.add(permission)
        self.client.force_login(user)

        response = self.client.post(self.autosalon_url, {'action': 'save_attorney'})

        self.assertEqual(response.status_code, 403)
