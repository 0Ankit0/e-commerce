from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.apps.iam.models.user import User
from src.apps.logistics.models import (
    Branch,
    BranchInventory,
    DeliveryAgent,
    DeliveryAgentStatus,
    DeliveryException,
    DeliveryExceptionStatus,
    Hub,
    PickupJob,
    PickupJobStatus,
    ReversePickupJob,
    ReversePickupStatus,
)
from src.apps.logistics.services import (
    build_branch_kpi_snapshot,
    calculate_branch_kpi_snapshot,
    ensure_branch_scope_access,
    resolve_user_branch_scope,
)


def test_calculate_branch_kpi_snapshot_includes_success_failure_and_backlog() -> None:
    snapshot = calculate_branch_kpi_snapshot(
        movement_count=4,
        total_moved_units=21,
        agent_count=3,
        active_agent_count=2,
        pickup_jobs=[
            PickupJob(status=PickupJobStatus.PICKED_UP),
            PickupJob(status=PickupJobStatus.PENDING),
        ],
        reverse_pickups=[
            ReversePickupJob(status=ReversePickupStatus.RECEIVED),
            ReversePickupJob(status=ReversePickupStatus.REQUESTED),
        ],
        exceptions=[
            DeliveryException(status=DeliveryExceptionStatus.OPEN, exception_type='failed_delivery'),
            DeliveryException(status=DeliveryExceptionStatus.RESOLVED, exception_type='address_issue'),
        ],
    )

    assert snapshot['completed_pickups'] == 1
    assert snapshot['failed_deliveries'] == 1
    assert snapshot['backlog_shipments'] == 3
    assert snapshot['delivery_success_rate_percent'] == 50.0


@pytest.mark.asyncio
async def test_branch_scope_enforces_agent_branch_authorization(db_session) -> None:
    user = User(username='agent-user', email='agent-user@example.com', hashed_password='x', is_active=True)
    db_session.add(user)
    await db_session.flush()

    hub = Hub(name='Test Hub', code='TEST-HUB')
    db_session.add(hub)
    await db_session.flush()
    branch = Branch(hub_id=hub.id or 0, name='Branch Scope', code='B-SCOPE')
    db_session.add(branch)
    await db_session.flush()

    branch_agent = DeliveryAgent(branch_id=branch.id or 0, user_id=user.id, name='Branch Rider', status=DeliveryAgentStatus.AVAILABLE)
    db_session.add(branch_agent)
    await db_session.flush()

    allowed = await resolve_user_branch_scope(user, db_session)
    assert allowed == {branch.id}

    ensure_branch_scope_access(allowed_branch_ids=allowed, requested_branch_id=branch.id)

    with pytest.raises(HTTPException, match='Branch-scoped access denied'):
        ensure_branch_scope_access(allowed_branch_ids=allowed, requested_branch_id=22)


@pytest.mark.asyncio
async def test_branch_snapshot_isolation_and_extended_metrics(db_session) -> None:
    hub = Hub(name='Hub', code='HUB-1')
    db_session.add(hub)
    await db_session.flush()
    branch_a = Branch(hub_id=hub.id or 0, name='A', code='BRA')
    branch_b = Branch(hub_id=hub.id or 0, name='B', code='BRB')
    db_session.add(branch_a)
    db_session.add(branch_b)
    await db_session.flush()

    agent_a = DeliveryAgent(branch_id=branch_a.id or 0, name='A1', status=DeliveryAgentStatus.ASSIGNED, capacity=10, current_load=5)
    agent_b = DeliveryAgent(branch_id=branch_b.id or 0, name='B1', status=DeliveryAgentStatus.AVAILABLE, capacity=10, current_load=1)
    db_session.add(agent_a)
    db_session.add(agent_b)
    await db_session.flush()

    db_session.add(BranchInventory(branch_id=branch_a.id or 0, quantity=20))
    db_session.add(BranchInventory(branch_id=branch_b.id or 0, quantity=7))
    db_session.add(PickupJob(vendor_order_id=1, shipment_id=1, branch_id=branch_a.id, agent_id=agent_a.id, status=PickupJobStatus.PICKED_UP))
    db_session.add(PickupJob(vendor_order_id=2, shipment_id=2, branch_id=branch_a.id, agent_id=agent_a.id, status=PickupJobStatus.FAILED))
    db_session.add(PickupJob(vendor_order_id=3, shipment_id=3, branch_id=branch_b.id, agent_id=agent_b.id, status=PickupJobStatus.PENDING))
    db_session.add(DeliveryException(shipment_id=1, agent_id=agent_a.id, exception_type='failed_delivery', status=DeliveryExceptionStatus.RTO_INITIATED))
    await db_session.commit()

    branch_a_snapshot = await build_branch_kpi_snapshot(
        db=db_session,
        branch_id=branch_a.id,
        allowed_branch_ids={branch_a.id or 0},
        agent_id=None,
        zone_id=None,
        date_from=None,
        date_to=None,
        timezone_name='UTC',
    )
    network_snapshot = await build_branch_kpi_snapshot(
        db=db_session,
        branch_id=None,
        allowed_branch_ids=None,
        agent_id=None,
        zone_id=None,
        date_from=None,
        date_to=None,
        timezone_name='UTC',
    )

    assert branch_a_snapshot['snapshot']['inventory_on_hand_units'] == 20
    assert branch_a_snapshot['snapshot']['attempt_success_rate_percent'] == 50.0
    assert branch_a_snapshot['snapshot']['rto_rate_percent'] == 100.0
    assert network_snapshot['snapshot']['inventory_on_hand_units'] == 27
