from django.contrib import admin

from .models import TransportEnquiry


@admin.register(TransportEnquiry)
class TransportEnquiryAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "full_name",
        "phone_number",
        "transport_category",
        "status",
        "pickup_location",
        "destination",
        "submitted_at",
    )
    list_filter = ("transport_category", "status", "submitted_at")
    search_fields = ("reference_number", "full_name", "phone_number", "pickup_location", "destination")
    readonly_fields = ("reference_number", "submitted_at", "created_at", "updated_at")
