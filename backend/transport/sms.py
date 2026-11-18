from django.conf import settings

from .models import SystemSettings


def get_blessed_texts_credentials():
    return {
        "api_key": SystemSettings.get_value(
            "BLESSED_TEXTS_API_KEY",
            settings.BLESSED_TEXTS_API_KEY,
        ),
        "sender_id": SystemSettings.get_value(
            "BLESSED_TEXTS_SENDER_ID",
            settings.BLESSED_TEXTS_SENDER_ID,
        ),
    }
