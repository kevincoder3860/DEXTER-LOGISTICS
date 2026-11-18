import uuid

from django.db import models
from django.utils import timezone


class TransportEnquiry(models.Model):
    class TransportCategory(models.TextChoices):
        GOODS = "Goods / Cargo", "Goods / Cargo"
        PASSENGER = "Passenger", "Passenger"

    class EnquiryStatus(models.TextChoices):
        NEW = "NEW", "New Enquiry"
        CONTACTED = "CONTACTED", "CONTACTED"
        QUOTED = "QUOTED", "Quote Issued"
        PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED", "Payment Confirmed"
        QUOTE_CONFIRMED = "QUOTE_CONFIRMED", "QUOTE CONFIRMED"
        APPROVED = "APPROVED", "APPROVED"
        IN_PROGRESS = "IN_PROGRESS", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "CANCELLED"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "PENDING"
        PAID = "PAID", "PAID"
        FAILED = "FAILED", "FAILED"

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
    payment_reference = models.CharField(max_length=100, blank=True, default="")
    mpesa_receipt = models.CharField(max_length=100, blank=True, default="")
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    truck_registration = models.CharField(max_length=50, blank=True, default="")
    driver_name = models.CharField(max_length=255, blank=True, default="")
    driver_phone = models.CharField(max_length=50, blank=True, default="")
    current_checkpoint = models.CharField(max_length=255, blank=True, default="")
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
        today = timezone.localdate().strftime("%Y%m%d")
        while True:
            suffix = uuid.uuid4().hex[:4].upper()
            candidate = f"DRX-{today}-{suffix}"
            if not TransportEnquiry.objects.filter(reference_number=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_number} - {self.full_name}"


class SystemSettings(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_value(cls, key, fallback=""):
        stored_value = cls.objects.filter(key=key).values_list("value", flat=True).first()
        return stored_value or fallback

    @classmethod
    def set_value(cls, key, value):
        setting, _ = cls.objects.update_or_create(key=key, defaults={"value": value})
        return setting

    def __str__(self):
        return self.key
