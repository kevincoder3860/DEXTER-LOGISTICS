import hashlib
import hmac
import json
import logging
import re
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TransportEnquiry
from .permissions import IsSuperAdmin
from .serializers import (
    AdminLoginSerializer,
    AdminNoteSerializer,
    AdminQuoteSerializer,
    TransportEnquirySerializer,
    TransportEnquiryStatusSerializer,
)

logger = logging.getLogger(__name__)
CONFIRMED_QUOTE_STATUSES = {
    TransportEnquiry.EnquiryStatus.QUOTE_CONFIRMED,
    TransportEnquiry.EnquiryStatus.APPROVED,
}


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def public_enquiry_create(request):
    serializer = TransportEnquirySerializer(data=request.data)
    if serializer.is_valid():
        enquiry = serializer.save()
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
        "pickup_location": enquiry.pickup_location,
        "destination": enquiry.destination,
        "transport_category": enquiry.transport_category,
    })


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

    if enquiry.status not in CONFIRMED_QUOTE_STATUSES:
        return Response(
            {"success": False, "message": "Payment is available only for confirmed quotes."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID:
        return Response(
            {"success": False, "message": "This quote has already been paid."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if enquiry.paystack_reference:
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
    if not paystack_response.ok or not paystack_data.get("status"):
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
    if transaction.get("status") == "success":
        enquiry.payment_status = TransportEnquiry.PaymentStatus.PAID
    if reference or enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID:
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
            enquiry = TransportEnquiry.objects.filter(paystack_reference=reference).first()
            if event["event"] == "charge.failed":
                if enquiry and enquiry.payment_status == TransportEnquiry.PaymentStatus.PENDING:
                    enquiry.paystack_reference = ""
                    enquiry.save(update_fields=["paystack_reference", "updated_at"])
                return HttpResponse(status=status.HTTP_200_OK)
            expected_amount = int(enquiry.quoted_amount * 100) if enquiry and enquiry.quoted_amount else None
            if (
                enquiry
                and enquiry.payment_status == TransportEnquiry.PaymentStatus.PENDING
                and transaction.get("currency") == "KES"
                and transaction.get("amount") == expected_amount
            ):
                enquiry.payment_status = TransportEnquiry.PaymentStatus.PAID
                enquiry.save(update_fields=["payment_status", "updated_at"])
            elif not enquiry:
                logger.warning("No pending enquiry payment found for Paystack reference %s", reference)
            elif enquiry.payment_status != TransportEnquiry.PaymentStatus.PAID:
                logger.warning("Paystack success event did not match the quote amount for reference %s", reference)
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
        update_data = {}
        if "status" in request.data:
            status_serializer = TransportEnquiryStatusSerializer(
                enquiry,
                data={"status": request.data["status"]},
                partial=True,
            )
            if not status_serializer.is_valid():
                return Response({"message": "Status update failed.", "errors": status_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            update_data["status"] = status_serializer.validated_data["status"]

        if "admin_notes" in request.data:
            notes_serializer = AdminNoteSerializer(
                enquiry,
                data={"admin_notes": request.data["admin_notes"]},
                partial=True,
            )
            if not notes_serializer.is_valid():
                return Response({"message": "Note update failed.", "errors": notes_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            update_data["admin_notes"] = notes_serializer.validated_data["admin_notes"]

        if "quoted_amount" in request.data:
            quote_serializer = AdminQuoteSerializer(
                enquiry,
                data={"quoted_amount": request.data["quoted_amount"]},
                partial=True,
            )
            if not quote_serializer.is_valid():
                return Response(
                    {"message": "Quote update failed.", "errors": quote_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            update_data["quoted_amount"] = quote_serializer.validated_data["quoted_amount"]

        if not update_data:
            return Response({"message": "No valid update field supplied."}, status=status.HTTP_400_BAD_REQUEST)

        if update_data.get("status") in CONFIRMED_QUOTE_STATUSES:
            quote_amount = update_data.get("quoted_amount", enquiry.quoted_amount)
            if quote_amount is None or quote_amount <= 0:
                return Response(
                    {"message": "Set a positive quote amount before confirming the quote."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if enquiry.payment_status == TransportEnquiry.PaymentStatus.PAID and (
                "quoted_amount" in update_data and update_data["quoted_amount"] != enquiry.quoted_amount
            ):
                return Response(
                    {"message": "A paid quote cannot be changed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for field_name, value in update_data.items():
            setattr(enquiry, field_name, value)
        enquiry.is_unread = False
        enquiry.save()
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
