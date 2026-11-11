from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class AdminSuperuserAccessTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="dispatcher",
            password="test-password-123",
            is_staff=True,
        )
        self.superadmin = user_model.objects.create_superuser(
            username="superadmin",
            password="test-password-123",
            email="superadmin@example.com",
        )

    def test_staff_user_cannot_log_in(self):
        response = self.client.post(
            "/api/admin/login/",
            {"username": "dispatcher", "password": "test-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_superadmin_can_log_in_and_access_dashboard(self):
        response = self.client.post(
            "/api/admin/login/",
            {"username": "superadmin", "password": "test-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["is_superuser"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
        dashboard_response = self.client.get("/api/admin/stats/")

        self.assertEqual(dashboard_response.status_code, 200)

    def test_staff_user_cannot_access_dashboard(self):
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get("/api/admin/stats/")

        self.assertEqual(response.status_code, 403)
