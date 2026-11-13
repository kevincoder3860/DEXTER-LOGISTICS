import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import TransportEnquiry


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

    def test_admin_can_set_and_confirm_a_quote_together(self):
        enquiry = TransportEnquiry.objects.create(
            full_name="Njeri Kamau",
            phone_number="0712345678",
            pickup_location="Nairobi",
            destination="Kisumu",
            type_of_goods="Furniture",
            estimated_weight="500 kg",
        )
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.patch(
            f"/api/admin/enquiries/{enquiry.id}/",
            {"status": "QUOTE_CONFIRMED", "quoted_amount": "9800.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["quoted_amount"], "9800.00")
        self.assertEqual(response.data["status"], "QUOTE_CONFIRMED")


@override_settings(PAYSTACK_SECRET_KEY="test-paystack-secret")
class PaystackMpesaPaymentTests(APITestCase):
    def setUp(self):
        self.enquiry = TransportEnquiry.objects.create(
            full_name="Amina Otieno",
            email="amina@example.com",
            phone_number="0712345678",
            transport_category=TransportEnquiry.TransportCategory.GOODS,
            pickup_location="Nairobi",
            destination="Mombasa",
            type_of_goods="General cargo",
            estimated_weight="1 tonne",
            status=TransportEnquiry.EnquiryStatus.QUOTE_CONFIRMED,
            quoted_amount=Decimal("1250.50"),
        )

    def test_new_enquiries_get_unique_drx_tracking_references(self):
        another_enquiry = TransportEnquiry.objects.create(
            full_name="Brian Mwangi",
            phone_number="0711222333",
            pickup_location="Nairobi",
            destination="Nakuru",
            type_of_goods="Boxes",
            estimated_weight="100 kg",
        )

        self.assertRegex(self.enquiry.reference_number, r"^DRX-\d{8}-[A-F0-9]{4}$")
        self.assertRegex(another_enquiry.reference_number, r"^DRX-\d{8}-[A-F0-9]{4}$")
        self.assertNotEqual(self.enquiry.reference_number, another_enquiry.reference_number)

    @patch("transport.views.requests.post")
    def test_initiates_charge_using_confirmed_database_amount(self, post):
        post.return_value = Mock(
            ok=True,
            json=lambda: {
                "status": True,
                "message": "Charge initiated",
                "data": {"reference": "paystack-ref-1", "status": "pending"},
            },
        )

        response = self.client.post(
            "/api/payments/paystack-stk/",
            {
                "order_id": str(self.enquiry.id),
                "phone_number": "0712345678",
                "amount": "1250.50",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "email": "amina@example.com",
                "amount": 125050,
                "currency": "KES",
                "mobile_money": {"phone": "+254712345678", "provider": "mpesa"},
            },
        )
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.paystack_reference, "paystack-ref-1")

        duplicate_response = self.client.post(
            "/api/payments/paystack-stk/",
            {
                "order_id": str(self.enquiry.id),
                "phone_number": "0712345678",
                "amount": "1250.50",
            },
            format="json",
        )
        self.assertEqual(duplicate_response.status_code, 409)
        post.assert_called_once()

    @patch("transport.views.requests.post")
    def test_rejects_unconfirmed_quote_and_invalid_phone(self, post):
        self.enquiry.status = TransportEnquiry.EnquiryStatus.QUOTED
        self.enquiry.save(update_fields=["status"])
        unconfirmed = self.client.post(
            "/api/payments/paystack-stk/",
            {"order_id": str(self.enquiry.id), "phone_number": "0712345678"},
            format="json",
        )
        self.assertEqual(unconfirmed.status_code, 400)

        self.enquiry.status = TransportEnquiry.EnquiryStatus.QUOTE_CONFIRMED
        self.enquiry.save(update_fields=["status"])
        invalid_phone = self.client.post(
            "/api/payments/paystack-stk/",
            {"order_id": str(self.enquiry.id), "phone_number": "12345"},
            format="json",
        )
        self.assertEqual(invalid_phone.status_code, 400)
        post.assert_not_called()

    @patch("transport.views.requests.post")
    def test_rejects_client_amount_different_from_confirmed_quote(self, post):
        response = self.client.post(
            "/api/payments/paystack-stk/",
            {
                "order_id": str(self.enquiry.id),
                "phone_number": "254712345678",
                "amount": "1.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_verified_success_webhook_marks_payment_as_paid(self):
        self.enquiry.paystack_reference = "paystack-ref-2"
        self.enquiry.save(update_fields=["paystack_reference"])
        body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": "paystack-ref-2",
                "amount": 125050,
                "currency": "KES",
            },
        }).encode("utf-8")
        signature = hmac.new(
            b"test-paystack-secret",
            body,
            hashlib.sha512,
        ).hexdigest()

        response = self.client.post(
            "/api/payments/paystack-webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.payment_status, TransportEnquiry.PaymentStatus.PAID)

    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            "/api/payments/paystack-webhook/",
            data=b'{"event":"charge.success"}',
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="invalid",
        )

        self.assertEqual(response.status_code, 401)

    def test_public_tracking_returns_quote_and_payment_state(self):
        response = self.client.get(f"/api/public/track/{self.enquiry.reference_number}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.enquiry.id)
        self.assertEqual(response.data["total_price"], Decimal("1250.50"))
        self.assertEqual(response.data["payment_status"], "PENDING")
