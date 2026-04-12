from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.commerce.models import Address
from src.apps.core.security import TokenType, create_access_token, get_password_hash, verify_token
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import encode_id
from src.apps.logistics.models import Hub
from src.apps.orders.models import Order, OrderPaymentStatus, PaymentMethod, Shipment


async def _create_admin_headers(db_session: AsyncSession) -> dict[str, str]:
    user = User(
        username='hub_admin',
        email='hub-admin@example.com',
        hashed_password=get_password_hash('TestPass123!'),
        is_active=True,
        is_superuser=True,
        is_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(user.id, expires_delta=timedelta(hours=1))
    payload = verify_token(token, token_type=TokenType.ACCESS)
    exp = payload['exp']
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.add(
        TokenTracking(
            user_id=user.id,
            token_jti=payload['jti'],
            token_type=TokenType.ACCESS,
            ip_address='127.0.0.1',
            user_agent='pytest',
            is_active=True,
            expires_at=expires_at,
        )
    )
    await db_session.commit()
    return {'Authorization': f'Bearer {token}'}


async def _create_hub_and_shipment(db_session: AsyncSession) -> tuple[str, str]:
    buyer = User(username='hub_buyer', email='hub-buyer@example.com', hashed_password='x', is_active=True)
    db_session.add(buyer)
    await db_session.flush()

    address = Address(user_id=buyer.id or 0, name='Hub Buyer', line1='Street 1', city='City', pincode='44600')
    db_session.add(address)
    await db_session.flush()

    hub = Hub(name='Integration Hub', code='HUB-INT')
    db_session.add(hub)
    await db_session.flush()

    order = Order(
        order_number='ORD-HUB-INT',
        user_id=buyer.id or 0,
        address_id=address.id or 0,
        payment_method=PaymentMethod.COD,
        payment_status=OrderPaymentStatus.PENDING,
    )
    db_session.add(order)
    await db_session.flush()

    shipment = Shipment(order_id=order.id or 0, awb='AWB-HUB-INT')
    db_session.add(shipment)
    await db_session.commit()
    return encode_id(hub.id or 0), encode_id(shipment.id or 0)


@pytest.mark.asyncio
async def test_hub_intake_to_dispatch_and_exception_paths(client: AsyncClient, db_session: AsyncSession):
    headers = await _create_admin_headers(db_session)
    hub_id, shipment_id = await _create_hub_and_shipment(db_session)

    queue_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues',
        headers=headers,
        json={'code': 'INT-Q-1'},
    )
    assert queue_resp.status_code == 201, queue_resp.text
    queue_id = queue_resp.json()['queue_id']

    intake_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/intake',
        headers=headers,
        json={'shipment_id': shipment_id},
    )
    assert intake_resp.status_code == 201, intake_resp.text

    hold_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/exception-queue',
        headers=headers,
        json={
            'shipment_id': shipment_id,
            'exception_code': 'barcode_unreadable',
            'notes': 'manual verify',
            'requeue_for_sorting': False,
        },
    )
    assert hold_resp.status_code == 200, hold_resp.text
    assert hold_resp.json()['status'] == 'exception'

    requeue_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/exception-queue',
        headers=headers,
        json={
            'shipment_id': shipment_id,
            'exception_code': 'manual_clear',
            'notes': 'verified',
            'requeue_for_sorting': True,
        },
    )
    assert requeue_resp.status_code == 200, requeue_resp.text

    assign_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/assign',
        headers=headers,
        json={'shipment_id': shipment_id, 'carrier': 'CarrierX', 'vehicle_number': 'VH-9'},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    stage_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/outbound-stage',
        headers=headers,
        json={'shipment_id': shipment_id, 'carrier': 'CarrierX', 'vehicle_number': 'VH-9'},
    )
    assert stage_resp.status_code == 200, stage_resp.text

    dispatch_resp = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/dispatch-scan-out',
        headers=headers,
        json={'shipment_id': shipment_id},
    )
    assert dispatch_resp.status_code == 200, dispatch_resp.text

    workbench_resp = await client.get(f'/api/v1/logistics/hubs/{hub_id}/sort-workbench', headers=headers, params={'queue_id': queue_id})
    assert workbench_resp.status_code == 200, workbench_resp.text
    body = workbench_resp.json()
    assert 'outbound_readiness_board' in body
    assert 'sla_timers' in body

    reports_resp = await client.get(f'/api/v1/logistics/hubs/{hub_id}/operational-reports', headers=headers)
    assert reports_resp.status_code == 200, reports_resp.text
    assert 'throughput_by_shift' in reports_resp.json()


@pytest.mark.asyncio
async def test_hub_exception_flows_cover_missort_damage_reroute_and_scan_mismatch(client: AsyncClient, db_session: AsyncSession):
    headers = await _create_admin_headers(db_session)
    hub_id, shipment_id = await _create_hub_and_shipment(db_session)

    queue_resp = await client.post(f'/api/v1/logistics/hubs/{hub_id}/sort-queues', headers=headers, json={'code': 'INT-Q-EXC'})
    assert queue_resp.status_code == 201, queue_resp.text
    queue_id = queue_resp.json()['queue_id']

    first_scan = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/inbound-scan',
        headers=headers,
        json={'shipment_id': shipment_id},
    )
    assert first_scan.status_code == 201, first_scan.text

    duplicate_scan = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/scan',
        headers=headers,
        json={'shipment_id': shipment_id},
    )
    assert duplicate_scan.status_code == 409, duplicate_scan.text

    hold_damaged = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/recirculation-rework',
        headers=headers,
        json={'shipment_id': shipment_id, 'exception_code': 'damaged_parcel', 'notes': 'box damaged', 'requeue_for_sorting': False},
    )
    assert hold_damaged.status_code == 200, hold_damaged.text
    assert hold_damaged.json()['status'] == 'exception'

    release_missort = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/recirculation-rework',
        headers=headers,
        json={'shipment_id': shipment_id, 'exception_code': 'missort_corrected', 'notes': 'reroute to lane b', 'requeue_for_sorting': True},
    )
    assert release_missort.status_code == 200, release_missort.text
    assert release_missort.json()['status'] == 'scanned'

    reassign_lane = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/bulk-actions',
        headers=headers,
        json={
            'shipment_ids': [shipment_id],
            'action': 'reassign_lane',
            'carrier': 'Carrier-R',
            'vehicle_number': 'VEH-R',
            'notes': 'reroute after missort',
        },
    )
    assert reassign_lane.status_code == 200, reassign_lane.text

    dispatch = await client.post(
        f'/api/v1/logistics/hubs/{hub_id}/sort-queues/{queue_id}/bulk-actions',
        headers=headers,
        json={'shipment_ids': [shipment_id], 'action': 'dispatch', 'carrier': 'Carrier-R', 'vehicle_number': 'VEH-R'},
    )
    assert dispatch.status_code == 200, dispatch.text
