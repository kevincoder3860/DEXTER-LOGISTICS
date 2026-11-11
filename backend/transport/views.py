from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TransportEnquiry
from .permissions import IsSuperAdmin
from .serializers import (
    AdminLoginSerializer,
    AdminNoteSerializer,
    TransportEnquirySerializer,
    TransportEnquiryStatusSerializer,
)


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

        if not update_data:
            return Response({"message": "No valid update field supplied."}, status=status.HTTP_400_BAD_REQUEST)

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
