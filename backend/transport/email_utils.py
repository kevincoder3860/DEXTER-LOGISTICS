import logging

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_TIMEOUT_SECONDS = 10
BREVO_SUCCESS_STATUS_CODES = {200, 201, 202}


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

        api_key = settings.BREVO_API_KEY
        if not api_key:
            logger.warning("Shipment email skipped because BREVO_API_KEY is not configured.")
            return False

        response = requests.post(
            BREVO_API_URL,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {
                    "name": settings.BREVO_SENDER_NAME,
                    "email": settings.BREVO_SENDER_EMAIL,
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "textContent": message,
            },
            timeout=BREVO_TIMEOUT_SECONDS,
        )
        logger.info("Brevo email API returned HTTP %s.", response.status_code)
        if response.status_code not in BREVO_SUCCESS_STATUS_CODES:
            try:
                error_response = response.json()
            except ValueError:
                error_response = response.text
            logger.error(
                "Brevo email API error (HTTP %s): %s",
                response.status_code,
                error_response,
            )
            return False
        return True
    except Exception:
        logger.exception("Shipment email delivery failed.")
        return False
