import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.config import settings
from src.apps.iam.models.login_attempt import LoginAttempt
from src.apps.observability.models import SecurityIncident
from src.apps.observability.service import (
    build_log_summary,
    create_log_entry,
    create_or_update_incident,
    evaluate_failed_login_burst,
    record_privileged_action_audit,
)


@pytest.mark.unit
class TestObservabilityService:
    @pytest.mark.asyncio
    async def test_create_or_update_incident_deduplicates_open_incident(self, db_session: AsyncSession):
        incident = await create_or_update_incident(
            db_session,
            signal_type="auth.failed_login_burst",
            severity="high",
            title="Repeated failed logins",
            summary="First occurrence",
            fingerprint="auth.failed_login_burst:test",
            metadata={"count": 5},
        )
        await db_session.commit()

        updated = await create_or_update_incident(
            db_session,
            signal_type="auth.failed_login_burst",
            severity="high",
            title="Repeated failed logins",
            summary="Second occurrence",
            fingerprint="auth.failed_login_burst:test",
            metadata={"count": 6},
        )
        await db_session.commit()

        assert updated.id == incident.id
        assert updated.occurrence_count == 2
        assert updated.summary == "Second occurrence"

    @pytest.mark.asyncio
    async def test_build_log_summary_counts_logs_and_incidents(self, db_session: AsyncSession):
        await create_log_entry(
            db_session,
            level="INFO",
            logger_name="api.requests",
            source="api",
            message="Healthy request",
            event_code="http.request.completed",
        )
        await create_log_entry(
            db_session,
            level="ERROR",
            logger_name="api.requests",
            source="api",
            message="Broken request",
            event_code="ops.request_error",
        )
        db_session.add(
            SecurityIncident(
                signal_type="ops.error_spike",
                severity="high",
                status="open",
                title="Error spike",
                summary="Too many 5xx responses",
                fingerprint="ops.error_spike:/broken",
            )
        )
        await db_session.commit()

        summary = await build_log_summary(db_session)

        assert summary["total_logs_24h"] == 2
        assert summary["info_logs_24h"] == 1
        assert summary["error_logs_24h"] == 1
        assert summary["open_incidents"] == 1
        assert summary["critical_incidents"] == 1

    @pytest.mark.asyncio
    async def test_failed_login_burst_uses_configured_threshold(self, db_session: AsyncSession):
        original_threshold = settings.FAILED_LOGIN_BURST_THRESHOLD
        original_window = settings.FAILED_LOGIN_BURST_WINDOW_MINUTES
        try:
            settings.FAILED_LOGIN_BURST_THRESHOLD = 2
            settings.FAILED_LOGIN_BURST_WINDOW_MINUTES = 30
            db_session.add(
                LoginAttempt(
                    user_id=None,
                    attempted_username="burst-threshold-user",
                    ip_address="127.0.0.1",
                    user_agent="pytest",
                    success=False,
                    failure_reason="bad password",
                )
            )
            db_session.add(
                LoginAttempt(
                    user_id=None,
                    attempted_username="burst-threshold-user",
                    ip_address="127.0.0.1",
                    user_agent="pytest",
                    success=False,
                    failure_reason="bad password",
                )
            )
            await db_session.commit()

            await evaluate_failed_login_burst(
                db_session,
                username="burst-threshold-user",
                ip_address="127.0.0.1",
                subject_user_id=None,
                related_log_id=None,
            )
            await db_session.commit()

            incidents = (
                await db_session.execute(
                    select(SecurityIncident).where(
                        SecurityIncident.signal_type == "auth.failed_login_burst"
                    )
                )
            ).scalars().all()
            assert incidents
        finally:
            settings.FAILED_LOGIN_BURST_THRESHOLD = original_threshold
            settings.FAILED_LOGIN_BURST_WINDOW_MINUTES = original_window

    @pytest.mark.asyncio
    async def test_privileged_action_summary_tracks_required_pass_denied_and_bypass(self, db_session: AsyncSession):
        for outcome in ("required", "passed", "denied", "bypass_attempt"):
            await record_privileged_action_audit(
                db_session,
                actor_user_id=1,
                action="admin.rbac.assign_role",
                outcome=outcome,
                metadata={"reason": outcome},
            )
        await db_session.commit()

        summary = await build_log_summary(db_session)

        assert summary["privileged_action_required_24h"] == 1
        assert summary["privileged_action_passed_24h"] == 1
        assert summary["privileged_action_denied_24h"] == 1
        assert summary["privileged_action_bypass_attempt_24h"] == 1
