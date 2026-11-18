import logging

import requests
from django.conf import settings

from .sms import get_blessed_texts_credentials

logger = logging.getLogger(__name__)

SMS_API_URL = "https://api.blessedtexts.com/api/sms/v1/sendsms"
SMS_TIMEOUT_SECONDS = 15


def send_blessed_sms(phone, message):
    try:
        clean_phone = "".join(str(phone or "").split()).lstrip("+")
        if not clean_phone:
            logger.warning("Blessed Texts SMS skipped because the phone number is empty.")
            return False

        credentials = get_blessed_texts_credentials()
        api_key = credentials["api_key"]
        sender_id = credentials["sender_id"]
        if not api_key or not sender_id:
            logger.warning("Blessed Texts SMS skipped because gateway credentials are not configured.")
            return False

        response = requests.post(
            SMS_API_URL,
            json={
                "api_key": api_key,
                "sender_id": sender_id,
                "message": str(message),
                "phone": clean_phone,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=SMS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get("status_code") != "1000":
            logger.warning("Blessed Texts rejected an SMS request (HTTP %s).", response.status_code)
            return False
        return True
    except Exception:
        logger.exception("Blessed Texts SMS delivery failed.")
        return False


def get_tracking_portal_url():
    return f"{settings.FRONTEND_URL.rstrip('/')}/#tracking"
