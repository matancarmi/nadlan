"""SMTP email alerts for high-value deals found during daily ingestion."""
import logging
import smtplib
from email.mime.text import MIMEText

from ..config import get_settings
from ..models import Property

logger = logging.getLogger(__name__)


def send_high_value_deal_alert(properties: list[Property]) -> bool:
    """Send one email listing all newly found high-value deals. Returns True on success."""
    if not properties:
        return False

    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        logger.info("SMTP not configured; skipping email alert for %d deals", len(properties))
        return False

    subject = f"🔥 {len(properties)} עסקאות נדל\"ן חמות נמצאו היום"
    lines = [f"נמצאו {len(properties)} נכסים בעלי פוטנציאל גבוה בסבב האיסוף היומי:\n"]
    for p in properties:
        lines.append(
            f"- {p.title} | {p.city} | {int(p.asking_price) if p.asking_price else '?'} ₪ "
            f"| הנחה מוערכת: {p.cma_discount_pct or 0}% | {p.source_url or ''}"
        )
    body = "\n".join(lines)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.alert_email_from or settings.smtp_user
    msg["To"] = settings.alert_email_to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [settings.alert_email_to], msg.as_string())
        logger.info("Sent high-value deal alert email for %d properties", len(properties))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send alert email: %s", exc)
        return False
