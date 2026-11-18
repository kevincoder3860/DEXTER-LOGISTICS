import hashlib
import hmac
import json
import requests
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import SystemSettings, TransportEnquiry
from .sms_utils import send_blessed_sms


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

    @patch("transport.views.send_blessed_sms")
    def test_admin_can_set_and_confirm_a_quote_together(self, send_sms):
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

    @patch("transport.views.send_blessed_sms")
    def test_admin_can_save_all_shipment_and_payment_fields_in_one_request(self, send_sms):
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
            {
                "status": "QUOTED",
                "confirmed_quote_amount": "9800.00",
                "payment_status": "PAID",
                "payment_reference": "manual-paystack-ref",
                "estimated_arrival": "2026-11-20T10:00:00Z",
                "truck_registration": "KDA 123A",
                "driver_name": "Driver One",
                "driver_phone": "+254712345678",
                "current_checkpoint": "Sagana",
                "admin_notes": "Verified with provider.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, TransportEnquiry.EnquiryStatus.PAYMENT_CONFIRMED)
        self.assertEqual(enquiry.quoted_amount, Decimal("9800.00"))
        self.assertEqual(enquiry.payment_status, TransportEnquiry.PaymentStatus.PAID)
        self.assertEqual(enquiry.payment_reference, "manual-paystack-ref")
        self.assertEqual(enquiry.truck_registration, "KDA 123A")
        self.assertEqual(enquiry.current_checkpoint, "Sagana")
        self.assertEqual(enquiry.admin_notes, "Verified with provider.")


@override_settings(
    BLESSED_TEXTS_API_KEY="fallback-api-key",
    BLESSED_TEXTS_SENDER_ID="fallback-sender",
)
class SmsSettingsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="sms-dispatcher",
            password="test-password-123",
            is_staff=True,
        )
        self.superadmin = user_model.objects.create_superuser(
            username="sms-admin",
            password="test-password-123",
            email="sms-admin@example.com",
        )

    def test_superadmin_can_read_fallback_and_save_sms_gateway_credentials(self):
        self.client.force_authenticate(user=self.superadmin)

        fallback_response = self.client.get("/api/admin/sms-settings/")
        self.assertEqual(fallback_response.status_code, 200)
        self.assertEqual(
            fallback_response.data,
            {"api_key": "fallback-api-key", "sender_id": "fallback-sender"},
        )

        save_response = self.client.post(
            "/api/admin/sms-settings/",
            {"api_key": "database-api-key", "sender_id": "DEXTER"},
            format="json",
        )

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_response.data["api_key"], "database-api-key")
        self.assertEqual(save_response.data["sender_id"], "DEXTER")
        self.assertEqual(
            SystemSettings.objects.count(),
            2,
        )

    def test_non_superadmin_cannot_access_sms_settings(self):
        self.client.force_authenticate(user=self.staff_user)

        get_response = self.client.get("/api/admin/sms-settings/")
        post_response = self.client.post(
            "/api/admin/sms-settings/",
            {"api_key": "should-not-save", "sender_id": "NOPE"},
            format="json",
        )

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(SystemSettings.objects.exists())


@override_settings(
    BLESSED_TEXTS_API_KEY="fallback-api-key",
    BLESSED_TEXTS_SENDER_ID="fallback-sender",
)
class BlessedTextsSmsTests(APITestCase):
    @patch("transport.sms_utils.requests.post")
    def test_sms_uses_dynamic_credentials_and_normalizes_the_phone(self, post):
        SystemSettings.set_value("BLESSED_TEXTS_API_KEY", "database-api-key")
        SystemSettings.set_value("BLESSED_TEXTS_SENDER_ID", "DEXTER")
        response = Mock(status_code=200)
        response.json.return_value = {"status_code": "1000"}
        post.return_value = response

        result = send_blessed_sms("+254 722 123456", "Test message")

        self.assertTrue(result)
        post.assert_called_once_with(
            "https://api.blessedtexts.com/api/sms/v1/sendsms",
            json={
                "api_key": "database-api-key",
                "sender_id": "DEXTER",
                "message": "Test message",
                "phone": "254722123456",
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15,
        )

    @patch("transport.sms_utils.requests.post", side_effect=requests.Timeout("provider timed out"))
    def test_sms_network_failure_does_not_raise(self, post):
        with self.assertLogs("transport.sms_utils", level="ERROR"):
            self.assertFalse(send_blessed_sms("0722123456", "Test message"))
        post.assert_called_once()

    @patch("transport.sms_utils.requests.post")
    def test_sms_rejects_unsuccessful_provider_status(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"status_code": "9000"}
        post.return_value = response

        self.assertFalse(send_blessed_sms("0722123456", "Test message"))

    @patch("transport.views.send_blessed_sms")
    @override_settings(FRONTEND_URL="https://freight.example")
    def test_new_enquiry_sends_tracking_id_and_portal_link(self, send_sms):
        response = self.client.post(
            "/api/public/enquiries/",
            {
                "full_name": "Amina Otieno",
                "email": "amina@example.com",
                "phone_number": "0722123456",
                "pickup_location": "Nairobi",
                "destination": "Mombasa",
                "type_of_goods": "General cargo",
                "estimated_weight": "1 tonne",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        reference = response.data["enquiry"]["reference_number"]
        send_sms.assert_called_once()
        self.assertEqual(send_sms.call_args.args[0], "0722123456")
        self.assertIn(reference, send_sms.call_args.args[1])
        self.assertIn("https://freight.example/#tracking", send_sms.call_args.args[1])


@override_settings(FRONTEND_URL="https://freight.example")
class ShipmentSmsNotificationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="shipment-sms-admin",
            password="test-password-123",
            email="shipment-sms-admin@example.com",
        )
        self.client.force_authenticate(user=self.admin)
        self.enquiry = TransportEnquiry.objects.create(
            full_name="Amina Otieno",
            phone_number="0722123456",
            pickup_location="Nairobi",
            destination="Mombasa",
            type_of_goods="General cargo",
            status=TransportEnquiry.EnquiryStatus.NEW,
        )

    @patch("transport.views.send_blessed_sms")
    def test_quote_and_dispatch_status_changes_send_relevant_updates(self, send_sms):
        quote_response = self.client.patch(
            f"/api/admin/enquiries/{self.enquiry.id}/",
            {"status": "QUOTED", "confirmed_quote_amount": "1250.50"},
            format="json",
        )
        self.assertEqual(quote_response.status_code, 200, quote_response.data)
        self.assertEqual(send_sms.call_count, 1)
        self.assertIn("KES 1,250.50", send_sms.call_args.args[1])
        self.assertIn("https://freight.example/#tracking", send_sms.call_args.args[1])

        dispatch_response = self.client.patch(
            f"/api/admin/enquiries/{self.enquiry.id}/",
            {
                "status": "IN_PROGRESS",
                "current_checkpoint": "Sagana",
                "truck_registration": "KDA 123A",
                "driver_name": "Driver One",
                "driver_phone": "0711222333",
            },
            format="json",
        )
        self.assertEqual(dispatch_response.status_code, 200, dispatch_response.data)
        self.assertEqual(send_sms.call_count, 2)
        dispatch_message = send_sms.call_args.args[1]
        self.assertIn("In Transit", dispatch_message)
        self.assertIn("KDA 123A", dispatch_message)
        self.assertIn("Driver One 0711222333", dispatch_message)
        self.assertIn("Sagana", dispatch_message)

        completed_response = self.client.patch(
            f"/api/admin/enquiries/{self.enquiry.id}/",
            {"status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(completed_response.status_code, 200, completed_response.data)
        self.assertEqual(send_sms.call_count, 3)
        self.assertIn("Completed", send_sms.call_args.args[1])

    @patch("transport.views.send_blessed_sms")
    def test_admin_marking_payment_paid_sends_confirmation_and_reference(self, send_sms):
        self.enquiry.quoted_amount = Decimal("1250.50")
        self.enquiry.status = TransportEnquiry.EnquiryStatus.QUOTED
        self.enquiry.save(update_fields=["quoted_amount", "status"])

        response = self.client.patch(
            f"/api/admin/enquiries/{self.enquiry.id}/",
            {
                "status": "PAYMENT_CONFIRMED",
                "payment_status": "PAID",
                "payment_reference": "manual-payment-ref",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        send_sms.assert_called_once()
        self.assertIn("manual-payment-ref", send_sms.call_args.args[1])


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
            status_code=200,
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
            {
                key: value
                for key, value in post.call_args.kwargs["json"].items()
                if key != "reference"
            },
            {
                "email": "amina@example.com",
                "amount": 125050,
                "currency": "KES",
                "mobile_money": {"phone": "+254712345678", "provider": "mpesa"},
            },
        )
        uuid.UUID(post.call_args.kwargs["json"]["reference"])
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
    def test_retry_uses_a_new_paystack_reference(self, post):
        post.side_effect = lambda *args, **kwargs: Mock(
            ok=True,
            status_code=200,
            json=lambda: {
                "status": True,
                "message": "Charge initiated",
                "data": {"reference": kwargs["json"]["reference"], "status": "pending"},
            },
        )

        payload = {
            "order_id": str(self.enquiry.id),
            "phone_number": "0712345678",
        }
        first_response = self.client.post("/api/payments/paystack-stk/", payload, format="json")
        first_reference = post.call_args.kwargs["json"]["reference"]
        self.assertEqual(first_response.status_code, 200)

        TransportEnquiry.objects.filter(id=self.enquiry.id).update(paystack_reference="")
        second_response = self.client.post("/api/payments/paystack-stk/", payload, format="json")
        second_reference = post.call_args.kwargs["json"]["reference"]

        self.assertEqual(second_response.status_code, 200)
        self.assertNotEqual(first_reference, second_reference)

    @patch("transport.views.requests.post")
    def test_paystack_conflict_message_and_status_are_returned(self, post):
        post.return_value = Mock(
            ok=False,
            status_code=409,
            json=lambda: {
                "status": False,
                "message": "Duplicate reference",
                "data": {"reference": "duplicate-reference"},
            },
        )

        response = self.client.post(
            "/api/payments/paystack-stk/",
            {
                "order_id": str(self.enquiry.id),
                "phone_number": "0712345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["message"], "Duplicate reference")

    @patch("transport.views.requests.post")
    def test_rejects_unconfirmed_quote_and_invalid_phone(self, post):
        self.enquiry.status = TransportEnquiry.EnquiryStatus.CANCELLED
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

    @patch("transport.views.requests.get")
    @patch("transport.views.send_blessed_sms")
    def test_verified_success_webhook_marks_payment_as_paid(self, send_sms, get):
        self.enquiry.paystack_reference = "paystack-ref-2"
        self.enquiry.save(update_fields=["paystack_reference"])
        get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {
                    "status": "success",
                    "reference": "paystack-ref-2",
                    "amount": 125050,
                    "currency": "KES",
                    "receipt_number": "RCP123",
                },
            },
        )
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
        get.assert_called_once_with(
            "https://api.paystack.co/transaction/verify/paystack-ref-2",
            headers={"Authorization": "Bearer test-paystack-secret"},
            timeout=20,
        )
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.payment_status, TransportEnquiry.PaymentStatus.PAID)
        self.assertEqual(self.enquiry.payment_reference, "paystack-ref-2")
        self.assertEqual(self.enquiry.mpesa_receipt, "RCP123")
        self.assertEqual(self.enquiry.status, TransportEnquiry.EnquiryStatus.PAYMENT_CONFIRMED)
        send_sms.assert_called_once()
        self.assertIn("paystack-ref-2", send_sms.call_args.args[1])

    @patch("transport.views.requests.get")
    @patch("transport.views.send_blessed_sms")
    def test_payment_verification_endpoint_reconciles_successful_transaction(self, send_sms, get):
        self.enquiry.paystack_reference = "verified-ref"
        self.enquiry.save(update_fields=["paystack_reference"])
        get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {
                    "status": "success",
                    "reference": "verified-ref",
                    "amount": 125050,
                    "currency": "KES",
                    "receipt_number": "RCP456",
                },
            },
        )

        response = self.client.post(
            "/api/payments/paystack-verify/",
            {"order_id": str(self.enquiry.id), "reference": "verified-ref"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        get.assert_called_once_with(
            "https://api.paystack.co/transaction/verify/verified-ref",
            headers={"Authorization": "Bearer test-paystack-secret"},
            timeout=20,
        )
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.payment_status, TransportEnquiry.PaymentStatus.PAID)
        self.assertEqual(self.enquiry.payment_reference, "verified-ref")
        self.assertEqual(self.enquiry.mpesa_receipt, "RCP456")
        send_sms.assert_called_once()
        self.assertIn("verified-ref", send_sms.call_args.args[1])

    @patch("transport.views.requests.get")
    def test_payment_verification_rejects_non_success_transaction(self, get):
        self.enquiry.paystack_reference = "failed-ref"
        self.enquiry.save(update_fields=["paystack_reference"])
        get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {"status": "failed", "reference": "failed-ref"},
            },
        )

        response = self.client.post(
            "/api/payments/paystack-verify/",
            {"order_id": str(self.enquiry.id), "reference": "failed-ref"},
            format="json",
        )

        self.assertFalse(response.data["success"])
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.payment_status, TransportEnquiry.PaymentStatus.FAILED)

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
