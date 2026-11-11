from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import TransportEnquiry


class TransportEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportEnquiry
        fields = [
            "id",
            "reference_number",
            "full_name",
            "phone_number",
            "transport_category",
            "pickup_location",
            "destination",
            "type_of_goods",
            "estimated_weight",
            "travel_date",
            "number_of_passengers",
            "additional_details",
            "status",
            "admin_notes",
            "submitted_at",
            "created_at",
            "updated_at",
            "is_unread",
        ]
        read_only_fields = [
            "id",
            "reference_number",
            "status",
            "submitted_at",
            "created_at",
            "updated_at",
            "is_unread",
        ]

    def validate(self, attrs):
        full_name = (attrs.get("full_name") or "").strip()
        phone_number = (attrs.get("phone_number") or "").strip()
        pickup_location = (attrs.get("pickup_location") or "").strip()
        destination = (attrs.get("destination") or "").strip()

        if not full_name or not phone_number or not pickup_location or not destination:
            raise serializers.ValidationError("Full name, phone number, pickup location and destination are required.")

        if TransportEnquiry.objects.filter(
            full_name__iexact=full_name,
            phone_number__iexact=phone_number,
            pickup_location__iexact=pickup_location,
            destination__iexact=destination,
        ).exists():
            raise serializers.ValidationError("A similar enquiry has already been submitted. Please contact the team directly for follow-up.")

        return attrs

    def create(self, validated_data):
        enquiry = TransportEnquiry(**validated_data)
        enquiry.save()
        return enquiry


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if user is None or not user.is_active:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_superuser:
            raise serializers.ValidationError("Only superadmins can access this dashboard.")
        return {"user": user}


class AdminNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportEnquiry
        fields = ["admin_notes"]


class TransportEnquiryStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportEnquiry
        fields = ["status"]
