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
    list_branch_dashboard_alerts,
    prioritize_aging_shipments,
    reassign_branch_load,
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
    assert branch_a_snapshot['snapshot']['load_balance_spread_percent'] == 0.0
    assert network_snapshot['snapshot']['inventory_on_hand_units'] == 27


@pytest.mark.asyncio
async def test_branch_alerts_include_sla_deterioration_and_escalations(db_session) -> None:
    hub = Hub(name='Hub Alert', code='HUB-A')
    db_session.add(hub)
    await db_session.flush()
    branch = Branch(hub_id=hub.id or 0, name='Alert Branch', code='ALERT')
    db_session.add(branch)
    await db_session.flush()

    overloaded = DeliveryAgent(branch_id=branch.id or 0, name='Overloaded', status=DeliveryAgentStatus.ASSIGNED, capacity=10, current_load=10)
    underutilized = DeliveryAgent(branch_id=branch.id or 0, name='Underutilized', status=DeliveryAgentStatus.AVAILABLE, capacity=10, current_load=1)
    db_session.add(overloaded)
    db_session.add(underutilized)
    await db_session.flush()

    db_session.add(PickupJob(vendor_order_id=10, shipment_id=10, branch_id=branch.id, agent_id=overloaded.id, status=PickupJobStatus.FAILED))
    db_session.add(DeliveryException(shipment_id=11, agent_id=overloaded.id, exception_type='failed_delivery', status=DeliveryExceptionStatus.OPEN))
    db_session.add(DeliveryException(shipment_id=12, agent_id=overloaded.id, exception_type='failed_delivery', status=DeliveryExceptionStatus.RTO_INITIATED))
    await db_session.commit()

    payload = await list_branch_dashboard_alerts(
        db=db_session,
        branch_id=branch.id,
        allowed_branch_ids={branch.id or 0},
        agent_id=None,
        zone_id=None,
        date_from=None,
        date_to=None,
        timezone_name='UTC',
        first_attempt_threshold=90.0,
        rto_rate_threshold=10.0,
        load_spread_threshold=20.0,
    )
    codes = {alert['code'] for alert in payload['alerts']}
    hook_actions = {hook['action'] for hook in payload['escalation_hooks']}
    assert 'first_attempt_drop' in codes
    assert 'rto_spike' in codes
    assert 'load_imbalance' in codes
    assert 'reassign_load' in hook_actions
    assert 'escalate_issues' in hook_actions


@pytest.mark.asyncio
async def test_intervention_actions_block_cross_branch_agent_access(db_session) -> None:
    hub = Hub(name='Hub Scope', code='HUB-S')
    db_session.add(hub)
    await db_session.flush()
    branch_a = Branch(hub_id=hub.id or 0, name='Scoped A', code='SCA')
    branch_b = Branch(hub_id=hub.id or 0, name='Scoped B', code='SCB')
    db_session.add(branch_a)
    db_session.add(branch_b)
    await db_session.flush()

    branch_a_agent = DeliveryAgent(branch_id=branch_a.id or 0, name='A Agent', status=DeliveryAgentStatus.ASSIGNED, capacity=10, current_load=4)
    branch_b_agent = DeliveryAgent(branch_id=branch_b.id or 0, name='B Agent', status=DeliveryAgentStatus.AVAILABLE, capacity=10, current_load=0)
    db_session.add(branch_a_agent)
    db_session.add(branch_b_agent)
    await db_session.flush()
    db_session.add(PickupJob(vendor_order_id=20, shipment_id=20, branch_id=branch_a.id, agent_id=branch_a_agent.id, status=PickupJobStatus.ASSIGNED))
    await db_session.commit()

    with pytest.raises(HTTPException, match='Branch-scoped access denied'):
        await reassign_branch_load(
            db=db_session,
            branch_id=branch_a.id or 0,
            from_agent_id=branch_a_agent.id or 0,
            to_agent_id=branch_b_agent.id or 0,
            limit=5,
        )

    with pytest.raises(HTTPException, match='Branch-scoped access denied'):
        await prioritize_aging_shipments(
            db=db_session,
            branch_id=branch_a.id or 0,
            assignee_agent_id=branch_b_agent.id,
            limit=5,
        )
