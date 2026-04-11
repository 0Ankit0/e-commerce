from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.apps.iam.models.user import User
from src.apps.logistics.models import (
    Branch,
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
from src.apps.logistics.services import calculate_branch_kpi_snapshot, resolve_user_branch_scope, ensure_branch_scope_access


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
