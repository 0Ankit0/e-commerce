import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def process_recommendation_event(event_id: int) -> None:
    """Hook for future model scoring/event fan-out processing."""
    logger.info("Queued recommendation event for async processing", extra={"event_id": event_id})
