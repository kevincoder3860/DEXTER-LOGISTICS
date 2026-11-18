import hashlib
import hmac
import json
import logging
import re
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SystemSettings, TransportEnquiry
from .permissions import IsSuperAdmin
from .serializers import (
    AdminLoginSerializer,
    AdminShipmentUpdateSerializer,
    SmsSettingsSerializer,
    TransportEnquirySerializer,
)
from .sms import get_blessed_texts_credentials
from .sms_utils import get_tracking_portal_url, send_blessed_sms

logger = logging.getLogger(__name__)
CONFIRMED_QUOTE_STATUSES = {
    TransportEnquiry.EnquiryStatus.QUOTED,
    TransportEnquiry.EnquiryStatus.QUOTE_CONFIRMED,
    TransportEnquiry.EnquiryStatus.APPROVED,
}
PAYABLE_QUOTE_STATUSES = CONFIRMED_QUOTE_STATUSES | {
    TransportEnquiry.EnquiryStatus.NEW,
    TransportEnquiry.EnquiryStatus.CONTACTED,
}
PAYMENT_CONFIRMABLE_STATUSES = {
    TransportEnquiry.EnquiryStatus.QUOTED,
    TransportEnquiry.EnquiryStatus.QUOTE_CONFIRMED,
    TransportEnquiry.EnquiryStatus.APPROVED,
}


class PaystackVerificationError(Exception):
    pass


def verify_paystack_transaction(reference):
    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=20,
        )
    except requests.RequestException as error:
        logger.exception("Paystack verification request failed for reference %s", reference)
        raise PaystackVerificationError("Unable to contact Paystack to verify this payment.") from error

    try:
        payload = response.json()
    except ValueError as error:
        raise PaystackVerificationError("Paystack returned an invalid verification response.") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise PaystackVerificationError("Paystack returned incomplete verification details.")
    if response.status_code != status.HTTP_200_OK or not payload.get("status"):
        raise PaystackVerificationError(payload.get("message", "Paystack could not verify this transaction."))
    return payload["data"]


def reconcile_verified_payment(enquiry, transaction):
    reference = transaction.get("reference")
    expected_amount = int(enquiry.quoted_amount * 100) if enquiry.quoted_amount else None
    if (
        transaction.get("status") != "success"
        or reference not in {enquiry.paystack_reference, enquiry.payment_reference}
        or transaction.get("currency") != "KES"
        or transaction.get("amount") != expected_amount
    ):
        return False

    was_paid = enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID
    enquiry.payment_status = TransportEnquiry.PaymentStatus.PAID
    enquiry.payment_reference = reference
    receipt = transaction.get("receipt_number") or transaction.get("mpesa_receipt")
    if receipt:
        enquiry.mpesa_receipt = str(receipt)
    if enquiry.status in PAYMENT_CONFIRMABLE_STATUSES:
        enquiry.status = TransportEnquiry.EnquiryStatus.PAYMENT_CONFIRMED
    enquiry.save(
        update_fields=[
            "payment_status",
            "payment_reference",
            "mpesa_receipt",
            "status",
            "updated_at",
        ]
    )
    if not was_paid:
        payment_reference = enquiry.payment_reference or enquiry.reference_number
        send_blessed_sms(
            enquiry.phone_number,
            (
                f"Payment confirmed for tracking ID {enquiry.reference_number}. "
                f"Reference: {payment_reference}. Track: {get_tracking_portal_url()}"
            ),
        )
    return True


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def public_enquiry_create(request):
    serializer = TransportEnquirySerializer(data=request.data)
    if serializer.is_valid():
        enquiry = serializer.save()
        send_blessed_sms(
            enquiry.phone_number,
            (
                f"Thanks {enquiry.full_name}, your enquiry is received. "
                f"Tracking ID: {enquiry.reference_number}. Track: {get_tracking_portal_url()}"
            ),
        )
        return Response(
            {
                "message": "Enquiry submitted successfully.",
                "enquiry": TransportEnquirySerializer(enquiry).data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response({"message": "Validation failed.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_enquiry_track(request, reference_number):
    try:
        enquiry = TransportEnquiry.objects.get(reference_number=reference_number)
    except TransportEnquiry.DoesNotExist:
        return Response({"message": "Enquiry not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "id": enquiry.id,
        "reference_number": enquiry.reference_number,
        "status": enquiry.status,
        "payment_status": enquiry.payment_status,
        "total_price": enquiry.quoted_amount,
        "quoted_amount": enquiry.quoted_amount,
        "payment_reference": enquiry.payment_reference,
        "mpesa_receipt": enquiry.mpesa_receipt,
        "estimated_arrival": enquiry.estimated_arrival,
        "pickup_location": enquiry.pickup_location,
        "destination": enquiry.destination,
        "transport_category": enquiry.transport_category,
        "type_of_goods": enquiry.type_of_goods,
        "estimated_weight": enquiry.estimated_weight,
        "truck_registration": enquiry.truck_registration,
        "driver_name": enquiry.driver_name,
        "driver_phone": enquiry.driver_phone,
        "current_checkpoint": enquiry.current_checkpoint,
        "submitted_at": enquiry.submitted_at,
        "updated_at": enquiry.updated_at,
    })


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def verify_paystack_payment(request):
    order_id = request.data.get("order_id")
    reference = str(request.data.get("reference", "")).strip()
    if not order_id or not reference:
        return Response(
            {"success": False, "message": "order_id and reference are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        enquiry = TransportEnquiry.objects.get(id=order_id)
    except (TransportEnquiry.DoesNotExist, DjangoValidationError, ValueError, TypeError):
        return Response(
            {"success": False, "message": "Shipment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if reference not in {enquiry.paystack_reference, enquiry.payment_reference}:
        return Response(
            {"success": False, "message": "The payment reference does not match this shipment."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not settings.PAYSTACK_SECRET_KEY:
        return Response(
            {"success": False, "message": "Payment verification is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        transaction = verify_paystack_transaction(reference)
    except PaystackVerificationError as error:
        return Response(
            {"success": False, "message": str(error)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if transaction.get("reference") != reference:
        return Response(
            {"success": False, "message": "Paystack returned a different transaction reference."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if transaction.get("status") == "success":
        if not reconcile_verified_payment(enquiry, transaction):
            logger.warning("Paystack verification data did not match shipment %s", enquiry.reference_number)
            return Response(
                {"success": False, "message": "Verified payment details do not match this shipment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"success": True, "payment_status": enquiry.payment_status, "payment_reference": enquiry.payment_reference},
            status=status.HTTP_200_OK,
        )

    if transaction.get("status") == "failed":
        enquiry.payment_status = TransportEnquiry.PaymentStatus.FAILED
        enquiry.save(update_fields=["payment_status", "updated_at"])
    return Response(
        {
            "success": False,
            "payment_status": enquiry.payment_status,
            "message": "Paystack has not confirmed a successful payment.",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def initiate_paystack_mpesa(request):
    order_id = request.data.get("order_id")
    phone_number = str(request.data.get("phone_number", "")).strip()
    submitted_amount = request.data.get("amount")
    if not order_id or not phone_number:
        return Response(
            {"success": False, "message": "order_id and phone_number are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        enquiry = TransportEnquiry.objects.get(id=order_id)
    except (TransportEnquiry.DoesNotExist, DjangoValidationError, ValueError, TypeError):
        return Response(
            {"success": False, "message": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if enquiry.status not in PAYABLE_QUOTE_STATUSES:
        return Response(
            {"success": False, "message": "Payment is unavailable for this shipment status."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID:
        return Response(
            {"success": False, "message": "This quote has already been paid."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if enquiry.paystack_reference and enquiry.payment_status == TransportEnquiry.PaymentStatus.PENDING:
        return Response(
            {"success": False, "message": "A payment request is already in progress. Check your phone before trying again."},
            status=status.HTTP_409_CONFLICT,
        )
    if enquiry.quoted_amount is None or enquiry.quoted_amount <= 0:
        return Response(
            {"success": False, "message": "This confirmed quote has no valid amount."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not enquiry.email:
        return Response(
            {"success": False, "message": "An email address is required to process this payment."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if submitted_amount is not None:
        try:
            requested_amount = Decimal(str(submitted_amount))
            if not requested_amount.is_finite() or requested_amount.quantize(Decimal("0.01")) != enquiry.quoted_amount:
                return Response(
                    {"success": False, "message": "The submitted amount does not match the confirmed quote."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"success": False, "message": "The submitted amount is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    phone_number = re.sub(r"[\s()-]", "", phone_number)
    phone_match = re.fullmatch(r"(?:\+?254|0)([17]\d{8})", phone_number)
    if not phone_match:
        return Response(
            {"success": False, "message": "Enter a valid Kenyan mobile number, e.g. 0712345678."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    formatted_phone = f"+254{phone_match.group(1)}"

    if not settings.PAYSTACK_SECRET_KEY:
        return Response(
            {"success": False, "message": "Payment processing is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    payload = {
        "reference": str(uuid.uuid4()),
        "email": enquiry.email,
        "amount": int(enquiry.quoted_amount * 100),
        "currency": "KES",
        "mobile_money": {"phone": formatted_phone, "provider": "mpesa"},
    }
    try:
        paystack_response = requests.post(
            "https://api.paystack.co/charge",
            json=payload,
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=20,
        )
        paystack_data = paystack_response.json()
    except ValueError:
        logger.error("Paystack returned a non-JSON response for enquiry %s", enquiry.reference_number)
        return Response(
            {"success": False, "message": "The payment provider returned an invalid response."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except requests.RequestException:
        logger.exception("Paystack payment request failed for enquiry %s", enquiry.reference_number)
        return Response(
            {"success": False, "message": "Unable to contact the payment provider. Please try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not isinstance(paystack_data, dict):
        return Response(
            {"success": False, "message": "The payment provider returned an invalid response."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if paystack_response.status_code != status.HTTP_200_OK:
        return Response(
            {
                "success": False,
                "message": paystack_data.get("message", "The payment provider rejected the request."),
                "data": paystack_data.get("data"),
            },
            status=paystack_response.status_code,
        )
    if not paystack_data.get("status"):
        return Response(
            {
                "success": False,
                "message": paystack_data.get("message", "The payment provider rejected the request."),
                "data": paystack_data.get("data"),
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    transaction = paystack_data.get("data")
    if not isinstance(transaction, dict) or not isinstance(transaction.get("reference"), str):
        return Response(
            {"success": False, "message": "The payment provider returned incomplete transaction details."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    reference = transaction.get("reference")
    if reference:
        enquiry.paystack_reference = reference
    if reference:
        enquiry.payment_status = TransportEnquiry.PaymentStatus.PENDING
        enquiry.save(update_fields=["paystack_reference", "payment_status", "updated_at"])

    return Response(
        {
            "success": True,
            "message": paystack_data.get("message", "Payment request initiated."),
            "data": transaction,
        },
        status=status.HTTP_200_OK,
    )


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def paystack_webhook(request):
    secret_key = settings.PAYSTACK_SECRET_KEY
    signature = request.headers.get("x-paystack-signature", "")
    if not secret_key or not signature:
        return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        request.body,
        hashlib.sha512,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)

    try:
        event = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(event, dict):
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

    if event.get("event") in {"charge.success", "charge.failed"}:
        transaction = event.get("data") or {}
        if not isinstance(transaction, dict):
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
        reference = transaction.get("reference")
        if reference:
            enquiry = TransportEnquiry.objects.filter(
                Q(paystack_reference=reference) | Q(payment_reference=reference)
            ).first()
            if event["event"] == "charge.failed":
                if enquiry and enquiry.payment_status == TransportEnquiry.PaymentStatus.PENDING:
                    enquiry.payment_status = TransportEnquiry.PaymentStatus.FAILED
                    enquiry.save(update_fields=["payment_status", "updated_at"])
                return HttpResponse(status=status.HTTP_200_OK)
            if not enquiry:
                logger.warning("No pending enquiry payment found for Paystack reference %s", reference)
                return HttpResponse(status=status.HTTP_200_OK)
            try:
                verified_transaction = verify_paystack_transaction(reference)
            except PaystackVerificationError:
                return HttpResponse(status=status.HTTP_502_BAD_GATEWAY)
            if not reconcile_verified_payment(enquiry, verified_transaction):
                logger.warning("Paystack success event could not be reconciled for reference %s", reference)
    return HttpResponse(status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def admin_login(request):
    serializer = AdminLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )
    return Response({"message": "Login failed.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def admin_enquiries_list(request):
    search = request.query_params.get("search", "").strip()
    status_filter = request.query_params.get("status", "")
    category_filter = request.query_params.get("category", "")

    queryset = TransportEnquiry.objects.all().order_by("-submitted_at")

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(reference_number__icontains=search)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if category_filter:
        queryset = queryset.filter(transport_category=category_filter)

    serializer = TransportEnquirySerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsSuperAdmin])
def admin_enquiry_detail(request, enquiry_id):
    try:
        enquiry = TransportEnquiry.objects.get(id=enquiry_id)
    except TransportEnquiry.DoesNotExist:
        return Response({"message": "Enquiry not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        enquiry.is_unread = False
        enquiry.save(update_fields=["is_unread", "updated_at"])
        serializer = TransportEnquirySerializer(enquiry)
        return Response(serializer.data)

    if request.method == "PATCH":
        update_payload = request.data.copy()
        if "confirmed_quote_amount" in update_payload:
            update_payload["quoted_amount"] = update_payload.pop("confirmed_quote_amount")
        update_serializer = AdminShipmentUpdateSerializer(
            enquiry,
            data=update_payload,
            partial=True,
        )
        if not update_serializer.is_valid():
            return Response(
                {"message": "Shipment updates could not be saved.", "errors": update_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        previous_quote = enquiry.quoted_amount
        previous_payment_status = enquiry.payment_status
        previous_status = enquiry.status
        enquiry = update_serializer.save(is_unread=False)

        quote_changed = enquiry.quoted_amount != previous_quote
        quote_issued = (
            previous_status != TransportEnquiry.EnquiryStatus.QUOTED
            and enquiry.status == TransportEnquiry.EnquiryStatus.QUOTED
        )
        if enquiry.quoted_amount is not None and (quote_changed or quote_issued):
            send_blessed_sms(
                enquiry.phone_number,
                (
                    f"Quote for tracking ID {enquiry.reference_number}: "
                    f"KES {enquiry.quoted_amount:,.2f}. Pay via Paystack on our tracking portal: "
                    f"{get_tracking_portal_url()}"
                ),
            )

        if (
            previous_payment_status != TransportEnquiry.PaymentStatus.PAID
            and enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID
        ):
            payment_reference = enquiry.payment_reference or enquiry.reference_number
            send_blessed_sms(
                enquiry.phone_number,
                (
                    f"Payment confirmed for tracking ID {enquiry.reference_number}. "
                    f"Reference: {payment_reference}. Track: {get_tracking_portal_url()}"
                ),
            )

        if (
            previous_status != enquiry.status
            and enquiry.status in {
                TransportEnquiry.EnquiryStatus.IN_PROGRESS,
                TransportEnquiry.EnquiryStatus.COMPLETED,
            }
        ):
            status_message = [
                f"Shipment {enquiry.reference_number} is now {enquiry.get_status_display()}."
            ]
            if enquiry.current_checkpoint:
                status_message.append(f"Current location: {enquiry.current_checkpoint}.")
            if enquiry.truck_registration:
                status_message.append(f"Truck: {enquiry.truck_registration}.")
            driver_details = " ".join(
                value for value in (enquiry.driver_name, enquiry.driver_phone) if value
            )
            if driver_details:
                status_message.append(f"Driver: {driver_details}.")
            status_message.append(f"Track: {get_tracking_portal_url()}")
            send_blessed_sms(enquiry.phone_number, " ".join(status_message))

        return Response(TransportEnquirySerializer(enquiry).data)

    enquiry.delete()
    return Response({"message": "Enquiry deleted successfully."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def admin_dashboard_stats(request):
    stats = {
        "total": TransportEnquiry.objects.count(),
        "new": TransportEnquiry.objects.filter(status="NEW").count(),
        "contacted": TransportEnquiry.objects.filter(status="CONTACTED").count(),
        "quoted": TransportEnquiry.objects.filter(status="QUOTED").count(),
        "in_progress": TransportEnquiry.objects.filter(status="IN_PROGRESS").count(),
        "completed": TransportEnquiry.objects.filter(status="COMPLETED").count(),
        "cancelled": TransportEnquiry.objects.filter(status="CANCELLED").count(),
        "unread": TransportEnquiry.objects.filter(is_unread=True).count(),
    }
    return Response(stats)


@api_view(["GET", "POST"])
@permission_classes([IsSuperAdmin])
def admin_sms_settings(request):
    if request.method == "GET":
        return Response(get_blessed_texts_credentials())

    serializer = SmsSettingsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": "SMS settings are invalid.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        SystemSettings.set_value("BLESSED_TEXTS_API_KEY", serializer.validated_data["api_key"].strip())
        SystemSettings.set_value("BLESSED_TEXTS_SENDER_ID", serializer.validated_data["sender_id"].strip())
    return Response(
        {
            "message": "SMS settings saved.",
            **get_blessed_texts_credentials(),
        },
        status=status.HTTP_200_OK,
    )
