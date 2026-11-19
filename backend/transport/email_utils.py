import logging

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT_SECONDS = 10


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

        api_key = settings.RESEND_API_KEY
        if not api_key:
            logger.warning("Shipment email skipped because RESEND_API_KEY is not configured.")
            return False

        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [recipient],
                "subject": subject,
                "text": message,
            },
            timeout=RESEND_TIMEOUT_SECONDS,
        )
        logger.info("Resend email API returned HTTP %s.", response.status_code)
        if not response.ok:
            try:
                error_response = response.json()
            except ValueError:
                error_response = response.text
            logger.error(
                "Resend email API error (HTTP %s): %s",
                response.status_code,
                error_response,
            )
            return False
        return True
    except Exception:
        logger.exception("Shipment email delivery failed.")
        return False
