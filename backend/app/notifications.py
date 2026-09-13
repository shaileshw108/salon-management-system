import logging
import re
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import NotificationLog, QueueEntry, QueueStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmsResult:
    provider: str
    message_id: str | None = None


def normalize_indian_mobile(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("91") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "91" + digits[1:]
    if len(digits) == 10:
        return "91" + digits
    raise ValueError("Phone number must be a valid Indian mobile number")


def send_sms(settings: Settings, phone: str, message: str) -> SmsResult:
    provider = settings.sms_provider.strip().lower()
    if provider == "mock":
        logger.info("MOCK SMS to %s: %s", phone, message)
        return SmsResult(provider="mock", message_id="mock")

    if provider != "msg91":
        raise RuntimeError(f"Unsupported SMS provider: {settings.sms_provider}")
    if not settings.msg91_authkey or not settings.msg91_flow_id or not settings.msg91_sender_id:
        raise RuntimeError("MSG91 SMS is not configured")

    mobile = normalize_indian_mobile(phone)
    payload = {
        "flow_id": settings.msg91_flow_id,
        "sender": settings.msg91_sender_id,
        "recipients": [{"mobiles": mobile, "VAR1": message}],
    }
    response = httpx.post(
        "https://control.msg91.com/api/v5/flow",
        headers={"accept": "application/json", "authkey": settings.msg91_authkey, "content-type": "application/json"},
        json=payload,
        timeout=settings.msg91_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if str(data.get("type", "")).lower() == "error":
        raise RuntimeError(data.get("message", "MSG91 rejected the SMS request"))
    return SmsResult(provider="msg91", message_id=data.get("message"))


def send_near_turn_notifications(db: Session, settings: Settings) -> int:
    waiting = db.scalars(
        select(QueueEntry)
        .where(QueueEntry.status == QueueStatus.WAITING)
        .order_by(QueueEntry.token_number)
    ).all()

    sent = 0
    for index, entry in enumerate(waiting):
        people_ahead = index
        if people_ahead > settings.sms_near_turn_threshold:
            continue

        already_sent = db.scalar(
            select(NotificationLog).where(
                NotificationLog.queue_entry_id == entry.id,
                NotificationLog.notification_type == "near_turn_sms",
            )
        )
        if already_sent:
            continue

        message = (
            f"Shiva's Salon: Your turn is coming soon. "
            f"Please reach the salon shortly. Token #{entry.token_number}."
        )
        try:
            result = send_sms(settings, entry.phone, message)
        except Exception as exc:
            logger.error("Unable to send near-turn SMS for queue #%s: %s", entry.id, exc)
            continue

        db.add(
            NotificationLog(
                queue_entry_id=entry.id,
                notification_type="near_turn_sms",
                provider=result.provider,
                provider_message_id=result.message_id,
            )
        )
        sent += 1

    if sent:
        db.commit()
    return sent
