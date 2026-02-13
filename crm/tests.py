from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .access import AUTOSALON_BLOCKED_GROUP, AUTOSALON_HIDE_ATTORNEY_GROUP


class AutosalonAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.autosalon_url = reverse('autosalon')
        self.blocked_group, _ = Group.objects.get_or_create(name=AUTOSALON_BLOCKED_GROUP)
        self.hide_attorney_group, _ = Group.objects.get_or_create(name=AUTOSALON_HIDE_ATTORNEY_GROUP)

    def test_autosalon_available_for_regular_user(self):
        user = self.user_model.objects.create_user(username='manager', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autosalon-attorney-tab')

    def test_autosalon_forbidden_for_blocked_user(self):
        user = self.user_model.objects.create_user(username='blocked', password='pass12345')
        user.groups.add(self.blocked_group)
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 403)

    def test_attorney_tab_hidden_for_restricted_user(self):
        user = self.user_model.objects.create_user(username='noattorney', password='pass12345')
        user.groups.add(self.hide_attorney_group)
        self.client.force_login(user)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'autosalon-attorney-tab')
        self.assertNotContains(response, 'id="autosalon-attorney"')

    def test_attorney_save_for_restricted_user_returns_403(self):
        user = self.user_model.objects.create_user(username='hiddenpost', password='pass12345')
        user.groups.add(self.hide_attorney_group)
        self.client.force_login(user)

        response = self.client.post(self.autosalon_url, {'action': 'save_attorney'})

        self.assertEqual(response.status_code, 403)

    def test_superuser_ignores_restriction_groups(self):
        superuser = self.user_model.objects.create_superuser(
            username='root',
            password='pass12345',
            email='root@example.com',
        )
        superuser.groups.add(self.blocked_group, self.hide_attorney_group)
        self.client.force_login(superuser)

        response = self.client.get(self.autosalon_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autosalon-attorney-tab')
