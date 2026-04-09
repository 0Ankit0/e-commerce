import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from celery import shared_task

from src.apps.communications import get_communications_service
from src.apps.communications.delivery_observability import create_queued_message, record_send_attempt
from src.apps.core.celery_app import celery_app  # noqa: F401
from src.apps.core.config import settings
from src.apps.core.time import utc_now
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "iam" / "templates"

RETRYABLE_ERROR_MARKERS = (
    "timeout",
    "temporarily",
    "503",
    "502",
    "connection",
    "unavailable",
    "rate limit",
)


@shared_task(bind=True, name="send_email_task")
def send_email_task(
    self,
    subject: str,
    recipients: List[Dict[str, str]],
    template_name: str,
    context: Dict[str, Any],
    template_dir: str | None = None,
    inline_template: bool = False,
    tracked_message_id: int | None = None,
) -> bool:
    return asyncio.run(
        _send_email_task(
            subject=subject,
            recipients=recipients,
            template_name=template_name,
            context=context,
            template_dir=template_dir,
            inline_template=inline_template,
            tracked_message_id=tracked_message_id,
        )
    )


async def _send_email_task(
    *,
    subject: str,
    recipients: List[Dict[str, str]],
    template_name: str,
    context: Dict[str, Any],
    template_dir: str | None,
    inline_template: bool,
    tracked_message_id: int | None,
) -> bool:
    resolved_dir = str(Path(template_dir) if template_dir else TEMPLATE_DIR)

    async with async_session_factory() as db:
        message = None
        if tracked_message_id:
            from src.apps.communications.models import EmailDeliveryMessage

            message = await db.get(EmailDeliveryMessage, tracked_message_id)
        if not message:
            message = await create_queued_message(
                db,
                subject=subject,
                template_name=template_name,
                recipients=recipients,
                context=context,
                max_attempts=max(1, settings.EMAIL_MAX_RETRIES + 1),
            )

        if not settings.EMAIL_ENABLED and settings.DEBUG:
            sep = "=" * 60
            lines = [
                "",
                sep,
                "  DEV EMAIL (not sent)",
                sep,
                f"  To      : {', '.join(r['email'] for r in recipients)}",
                f"  Subject : {subject}",
                f"  Template: {template_name}",
                sep,
                "",
            ]
            print("\n".join(lines), flush=True)
            await record_send_attempt(
                db,
                message=message,
                success=True,
                provider="debug",
                provider_message_id=f"debug-{message.id}",
                metadata={"mode": "debug"},
                error=None,
                failure_reason=None,
                attempt_count=message.attempt_count + 1,
                next_attempt_at=None,
                dead_letter=False,
            )
            return True

        try:
            result = get_communications_service().send_email(
                subject=subject,
                recipients=recipients,
                template_name=template_name,
                context=context,
                template_dir=resolved_dir,
                inline_template=inline_template,
            )
            attempt_count = message.attempt_count + 1
            if result.success:
                await record_send_attempt(
                    db,
                    message=message,
                    success=True,
                    provider=result.provider,
                    provider_message_id=result.message_id,
                    metadata=result.metadata,
                    error=None,
                    failure_reason=None,
                    attempt_count=attempt_count,
                    next_attempt_at=None,
                    dead_letter=False,
                )
                return True

            msg = (result.error or "Provider reported failure").lower()
            retryable = any(token in msg for token in RETRYABLE_ERROR_MARKERS)
            dead_letter = (not retryable) or (attempt_count >= message.max_attempts)
            next_attempt_at = None if dead_letter else utc_now()
            await record_send_attempt(
                db,
                message=message,
                success=False,
                provider=result.provider,
                provider_message_id=result.message_id,
                metadata=result.metadata,
                error=result.error,
                failure_reason="provider_rejected" if not retryable else "temporary_provider_failure",
                attempt_count=attempt_count,
                next_attempt_at=next_attempt_at,
                dead_letter=dead_letter,
            )
            if not dead_letter:
                countdown = min(300, (2 ** max(0, attempt_count - 1)) + (message.id % 3))
                send_email_task.apply_async(
                    kwargs={
                        "subject": subject,
                        "recipients": recipients,
                        "template_name": template_name,
                        "context": context,
                        "template_dir": template_dir,
                        "inline_template": inline_template,
                        "tracked_message_id": message.id,
                    },
                    countdown=countdown,
                )
            else:
                logger.error("Email delivery dead-lettered id=%s provider=%s reason=%s", message.id, result.provider, result.error)
            return False
        except Exception as exc:
            error = str(exc)
            attempt_count = message.attempt_count + 1
            retryable = any(token in error.lower() for token in RETRYABLE_ERROR_MARKERS)
            dead_letter = (not retryable) or (attempt_count >= message.max_attempts)
            next_attempt_at = None if dead_letter else utc_now()
            await record_send_attempt(
                db,
                message=message,
                success=False,
                provider="unknown",
                provider_message_id=None,
                metadata={},
                error=error,
                failure_reason="exception",
                attempt_count=attempt_count,
                next_attempt_at=next_attempt_at,
                dead_letter=dead_letter,
            )
            if not dead_letter:
                countdown = min(300, (2 ** max(0, attempt_count - 1)) + (message.id % 3))
                send_email_task.apply_async(
                    kwargs={
                        "subject": subject,
                        "recipients": recipients,
                        "template_name": template_name,
                        "context": context,
                        "template_dir": template_dir,
                        "inline_template": inline_template,
                        "tracked_message_id": message.id,
                    },
                    countdown=countdown,
                )
            else:
                logger.error("Failed to send email permanently id=%s: %s", message.id, exc)
            return False
