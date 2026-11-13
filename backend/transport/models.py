import uuid
from datetime import datetime

from django.db import models


class TransportEnquiry(models.Model):
    class TransportCategory(models.TextChoices):
        GOODS = "Goods / Cargo", "Goods / Cargo"
        PASSENGER = "Passenger", "Passenger"

    class EnquiryStatus(models.TextChoices):
        NEW = "NEW", "NEW"
        CONTACTED = "CONTACTED", "CONTACTED"
        QUOTED = "QUOTED", "QUOTED"
        QUOTE_CONFIRMED = "QUOTE_CONFIRMED", "QUOTE CONFIRMED"
        APPROVED = "APPROVED", "APPROVED"
        IN_PROGRESS = "IN_PROGRESS", "IN PROGRESS"
        COMPLETED = "COMPLETED", "COMPLETED"
        CANCELLED = "CANCELLED", "CANCELLED"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "PENDING"
        PAID = "PAID", "PAID"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=50)
    transport_category = models.CharField(max_length=50, choices=TransportCategory.choices, default=TransportCategory.GOODS)
    pickup_location = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    type_of_goods = models.CharField(max_length=255, blank=True, default="")
    estimated_weight = models.CharField(max_length=255, blank=True, default="")
    travel_date = models.DateField(null=True, blank=True)
    number_of_passengers = models.IntegerField(null=True, blank=True)
    additional_details = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW)
    quoted_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    paystack_reference = models.CharField(max_length=100, blank=True, default="")
    admin_notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_unread = models.BooleanField(default=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["full_name", "phone_number"]),
            models.Index(fields=["status", "transport_category"]),
        ]

    def generate_reference_number(self):
        today = datetime.now().strftime("%Y%m%d")
        prefix = "DEX"
        while True:
            suffix = uuid.uuid4().hex[:6].upper()
            candidate = f"{prefix}-{today}-{suffix}"
            if not TransportEnquiry.objects.filter(reference_number=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_number} - {self.full_name}"
