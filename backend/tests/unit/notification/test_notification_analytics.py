import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from src.apps.core import security
from src.apps.notification.models.notification import Notification, NotificationType
from src.apps.notification.models.notification_delivery import (
    NotificationDelivery,
    NotificationDeliveryChannel,
    NotificationDeliveryStatus,
)
from src.apps.notification.services.notification import (
    _enqueue_channel_delivery,
    get_channel_delivery_trends,
    get_template_delivery_trends,
)
from tests.factories import UserFactory


async def _make_user(db: AsyncSession, **kwargs):
    defaults = dict(
        username='notifanalytics',
        email='notifanalytics@example.com',
        hashed_password=security.get_password_hash('TestPass123'),
        is_active=True,
        is_confirmed=True,
    )
    defaults.update(kwargs)
    user = UserFactory.build(**defaults)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, username: str, password: str = 'TestPass123') -> str:
    resp = await client.post(
        '/api/v1/auth/login/?set_cookie=false',
        json={'username': username, 'password': password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['access']


@pytest.mark.asyncio
async def test_enqueue_delivery_persists_channel_outcome_defaults(db_session: AsyncSession):
    user = await _make_user(db_session, username='n-qa-1', email='n-qa-1@example.com')
    notification = Notification(user_id=user.id, title='Queued', body='Outcome', type=NotificationType.INFO)
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    with patch('src.apps.notification.services.notification.dispatch_notification_delivery_task.delay'):
        delivery = await _enqueue_channel_delivery(
            db_session,
            notification,
            NotificationDeliveryChannel.EMAIL,
            target='user:channel',
        )

    assert delivery.status == NotificationDeliveryStatus.QUEUED
    assert delivery.retry_count == 0
    assert delivery.provider_response_code is None
    assert delivery.queued_at is not None


@pytest.mark.asyncio
async def test_delivery_aggregation_returns_channel_and_template_trends(db_session: AsyncSession):
    user = await _make_user(db_session, username='n-qa-2', email='n-qa-2@example.com')
    info = Notification(user_id=user.id, title='Info', body='Body', type=NotificationType.INFO)
    error = Notification(user_id=user.id, title='Error', body='Body', type=NotificationType.ERROR)
    db_session.add(info)
    db_session.add(error)
    await db_session.commit()
    await db_session.refresh(info)
    await db_session.refresh(error)

    db_session.add(
        NotificationDelivery(
            notification_id=info.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.EMAIL,
            status=NotificationDeliveryStatus.DELIVERED,
            target='user:test',
            dedup_key='delivery-1',
            queued_at=info.created_at,
            delivered_at=info.created_at,
        )
    )
    db_session.add(
        NotificationDelivery(
            notification_id=error.id,
            user_id=user.id,
            channel=NotificationDeliveryChannel.SMS,
            status=NotificationDeliveryStatus.FAILED,
            target='user:test',
            dedup_key='delivery-2',
            queued_at=error.created_at,
            provider_response_code='THROTTLED',
            last_error_reason='Rate limited by provider',
        )
    )
    await db_session.commit()

    channel_trends = await get_channel_delivery_trends(db_session)
    assert channel_trends['total'] == 2
    assert len(channel_trends['items']) >= 2

    template_trends = await get_template_delivery_trends(db_session)
    assert template_trends['total'] == 2
    assert any(row['template'] == NotificationType.INFO.value for row in template_trends['items'])
    assert any(row['template'] == NotificationType.ERROR.value for row in template_trends['items'])


@pytest.mark.asyncio
async def test_notification_analytics_api_supports_pagination_and_filters(client: AsyncClient, db_session: AsyncSession):
    user = await _make_user(db_session, username='n-admin', email='n-admin@example.com', is_superuser=True)
    token = await _login(client, user.username)
    headers = {'Authorization': f'Bearer {token}'}

    note = Notification(user_id=user.id, title='Paged', body='Filters', type=NotificationType.SYSTEM)
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    for idx in range(3):
        db_session.add(
            NotificationDelivery(
                notification_id=note.id,
                user_id=user.id,
                channel=NotificationDeliveryChannel.EMAIL if idx < 2 else NotificationDeliveryChannel.SMS,
                status=NotificationDeliveryStatus.DELIVERED if idx == 0 else NotificationDeliveryStatus.FAILED,
                target=f'user:{idx}',
                dedup_key=f'paged-{idx}',
                provider_response_code='ERR' if idx else None,
                last_error_reason='provider timeout' if idx else None,
            )
        )
    await db_session.commit()

    channel_resp = await client.get(
        '/api/v1/analytics/notifications/channels/performance',
        headers=headers,
        params={'channel': 'email', 'limit': 1, 'skip': 0},
    )
    assert channel_resp.status_code == 200, channel_resp.text
    channel_payload = channel_resp.json()
    assert len(channel_payload['items']) == 1
    assert channel_payload['items'][0]['channel'] == 'email'

    template_resp = await client.get(
        '/api/v1/analytics/notifications/templates/performance',
        headers=headers,
        params={'template': 'system', 'limit': 5},
    )
    assert template_resp.status_code == 200, template_resp.text
    template_payload = template_resp.json()
    assert template_payload['items']
    assert all(row['template'] == 'system' for row in template_payload['items'])
