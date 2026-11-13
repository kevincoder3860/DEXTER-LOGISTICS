from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import TransportEnquiry


class TransportEnquirySerializer(serializers.ModelSerializer):
    payment_in_progress = serializers.SerializerMethodField()

    class Meta:
        model = TransportEnquiry
        fields = [
            "id",
            "reference_number",
            "full_name",
            "email",
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
            "quoted_amount",
            "payment_status",
            "payment_in_progress",
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
            "quoted_amount",
            "payment_status",
            "submitted_at",
            "created_at",
            "updated_at",
            "is_unread",
        ]

    def get_payment_in_progress(self, obj):
        return bool(obj.paystack_reference) and obj.payment_status == TransportEnquiry.PaymentStatus.PENDING

    def validate(self, attrs):
        full_name = (attrs.get("full_name") or "").strip()
        phone_number = (attrs.get("phone_number") or "").strip()
        pickup_location = (attrs.get("pickup_location") or "").strip()
        destination = (attrs.get("destination") or "").strip()
        transport_category = attrs.get("transport_category") or TransportEnquiry.TransportCategory.GOODS

        if not full_name or not phone_number or not pickup_location or not destination:
            raise serializers.ValidationError({
                "detail": "Full name, phone number, pickup location and destination are required."
            })

        if transport_category == TransportEnquiry.TransportCategory.GOODS:
            if not (attrs.get("type_of_goods") or "").strip():
                raise serializers.ValidationError({
                    "type_of_goods": "Type of goods is required for Goods / Cargo enquiries."
                })
            if not (attrs.get("estimated_weight") or "").strip():
                raise serializers.ValidationError({
                    "estimated_weight": "Estimated weight is required for Goods / Cargo enquiries."
                })
        else:
            if not attrs.get("travel_date"):
                raise serializers.ValidationError({
                    "travel_date": "Travel date is required for Passenger enquiries."
                })
            if attrs.get("number_of_passengers") is None:
                raise serializers.ValidationError({
                    "number_of_passengers": "Number of passengers is required for Passenger enquiries."
                })

        if TransportEnquiry.objects.filter(
            full_name__iexact=full_name,
            phone_number__iexact=phone_number,
            pickup_location__iexact=pickup_location,
            destination__iexact=destination,
        ).exists():
            raise serializers.ValidationError({
                "detail": "A similar enquiry has already been submitted. Please contact the team directly for follow-up."
            })

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


class AdminQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportEnquiry
        fields = ["quoted_amount"]

    def validate_quoted_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("The quote amount must be greater than zero.")
        if (
            self.instance
            and (
                self.instance.payment_status == TransportEnquiry.PaymentStatus.PAID
                or self.instance.paystack_reference
            )
            and value != self.instance.quoted_amount
        ):
            raise serializers.ValidationError("A quote cannot be changed after payment has been initiated.")
        return value


class TransportEnquiryStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportEnquiry
        fields = ["status"]

    def validate_status(self, value):
        if isinstance(value, str):
            normalized = value.strip().replace(" ", "_")
            if normalized == "IN_PROGRESS":
                return "IN_PROGRESS"
        return value
