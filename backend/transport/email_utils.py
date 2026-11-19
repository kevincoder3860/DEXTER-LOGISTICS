import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email

logger = logging.getLogger(__name__)


def send_shipment_email(to_email, subject, message):
    try:
        recipient = str(to_email or "").strip()
        if not recipient:
            logger.warning("Shipment email skipped because no recipient address was provided.")
            return False
        try:
            validate_email(recipient)
        except ValidationError:
            logger.warning("Shipment email skipped because the recipient address is invalid.")
            return False

        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        if sent_count != 1:
            logger.warning("Shipment email backend did not send the message.")
            return False
        return True
    except Exception:
        logger.exception("Shipment email delivery failed.")
        return False
