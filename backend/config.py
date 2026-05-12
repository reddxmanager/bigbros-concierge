from dotenv import load_dotenv

load_dotenv()

import base64
import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Settings(BaseModel):
    google_calendar_family: str = os.getenv("GOOGLE_CALENDAR_FAMILY", "")
    google_calendar_honeymoon: str = os.getenv("GOOGLE_CALENDAR_HONEYMOON", "")
    google_calendar_events: str = os.getenv("GOOGLE_CALENDAR_EVENTS", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    booking_notification_email: str = os.getenv("BOOKING_NOTIFICATION_EMAIL", "")
    environment: str = os.getenv("ENVIRONMENT", "development")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")


settings = Settings()


def _decode_service_account(b64_payload: str) -> Optional[Dict[str, Any]]:
    raw = (b64_payload or "").strip()
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw)
        return json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


GOOGLE_SERVICE_ACCOUNT_INFO: Optional[Dict[str, Any]] = _decode_service_account(
    settings.google_service_account_json
)

CALENDAR_MAP: Dict[str, str] = {
    "Family Suite": settings.google_calendar_family,
    "Honeymoon Suite": settings.google_calendar_honeymoon,
    "Full Buyout": settings.google_calendar_events,
}
