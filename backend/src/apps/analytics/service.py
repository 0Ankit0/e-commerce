"""AnalyticsService — the public API consumed by the rest of the application.

This class is the *Context* in the Strategy pattern: it holds a reference to
an *AnalyticsProvider* and delegates every call to it.  When analytics are
disabled (provider is None) all methods silently no-op, so call sites never
need to guard against ``None``.
"""
import logging
from typing import Any

from src.apps.analytics.interface import AnalyticsProvider

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    High-level analytics service used throughout the application.

    Instantiate via :func:`src.apps.analytics.factory.build_analytics_service`
    or the module-level helpers in :mod:`src.apps.analytics`.
    """

    def __init__(self, provider: AnalyticsProvider | None) -> None:
        self._provider = provider
        if provider is None:
            logger.debug("Analytics disabled — all calls are no-ops.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """True when a provider is configured and analytics are active."""
        return self._provider is not None

    # ------------------------------------------------------------------
    # Sending operations
    # ------------------------------------------------------------------

    async def capture(
        self,
        distinct_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Record a named event for *distinct_id* (a user ID or anonymous ID)."""
        if self._provider:
            try:
                await self._provider.capture(distinct_id, event, properties)
            except Exception as exc:
                logger.warning("Analytics capture error: %s", exc)

    async def identify(
        self,
        distinct_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Attach persistent traits to a person record."""
        if self._provider:
            try:
                await self._provider.identify(distinct_id, properties)
            except Exception as exc:
                logger.warning("Analytics identify error: %s", exc)

    async def alias(self, distinct_id: str, alias: str) -> None:
        """Merge *alias* into the person identified by *distinct_id*."""
        if self._provider:
            try:
                await self._provider.alias(distinct_id, alias)
            except Exception as exc:
                logger.warning("Analytics alias error: %s", exc)

    async def group(
        self,
        distinct_id: str,
        group_type: str,
        group_key: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Associate *distinct_id* with a group (e.g. organisation / tenant)."""
        if self._provider:
            try:
                await self._provider.group(distinct_id, group_type, group_key, properties)
            except Exception as exc:
                logger.warning("Analytics group error: %s", exc)

    async def page(
        self,
        distinct_id: str,
        path: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Record a page / screen view."""
        if self._provider:
            try:
                await self._provider.page(distinct_id, path, properties)
            except Exception as exc:
                logger.warning("Analytics page error: %s", exc)

    # ------------------------------------------------------------------
    # Retrieving operations
    # ------------------------------------------------------------------

    async def get_feature_flag(
        self,
        distinct_id: str,
        flag_key: str,
        default: bool = False,
    ) -> bool | str:
        """Return the feature-flag value for *distinct_id*, or *default*."""
        if self._provider:
            try:
                return await self._provider.get_feature_flag(distinct_id, flag_key, default)
            except Exception as exc:
                logger.warning("Analytics get_feature_flag error: %s", exc)
        return default

    async def get_all_feature_flags(
        self,
        distinct_id: str,
    ) -> dict[str, bool | str]:
        """Return all feature flags for *distinct_id*."""
        if self._provider:
            try:
                return await self._provider.get_all_feature_flags(distinct_id)
            except Exception as exc:
                logger.warning("Analytics get_all_feature_flags error: %s", exc)
        return {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def flush(self) -> None:
        """Force-flush any pending events to the provider."""
        if self._provider:
            try:
                await self._provider.flush()
            except Exception as exc:
                logger.warning("Analytics flush error: %s", exc)

    async def shutdown(self) -> None:
        """Flush and shut down the provider (call on application shutdown)."""
        if self._provider:
            try:
                await self._provider.shutdown()
            except Exception as exc:
                logger.warning("Analytics shutdown error: %s", exc)

    def build_hub_operational_metrics(
        self,
        *,
        scanned_shipments: int,
        throughput_shipments: int,
        dwell_samples_minutes: list[float],
        exception_shipments: int,
        sla_minutes: int = 180,
    ) -> dict[str, float | int]:
        """Calculate hub operational metrics used by logistics dashboards."""
        average_dwell = round(sum(dwell_samples_minutes) / len(dwell_samples_minutes), 2) if dwell_samples_minutes else 0.0
        mis_sort_rate = round((exception_shipments / scanned_shipments) * 100, 2) if scanned_shipments else 0.0
        sla_breaches = len([sample for sample in dwell_samples_minutes if sample > sla_minutes])
        return {
            "throughput_shipments": throughput_shipments,
            "average_dwell_time_minutes": average_dwell,
            "mis_sort_rate_percent": mis_sort_rate,
            "sla_breach_shipments": sla_breaches,
            "sla_target_minutes": sla_minutes,
        }

    def build_hub_exception_analytics(
        self,
        *,
        exception_causes: dict[str, int],
    ) -> dict[str, object]:
        ranked = sorted(exception_causes.items(), key=lambda item: item[1], reverse=True)
        total = sum(exception_causes.values())
        return {
            "exception_categories": [{"category": key, "count": value} for key, value in ranked],
            "top_exception_category": ranked[0][0] if ranked else None,
            "total_exception_shipments": total,
        }

    def build_hub_execution_analytics(
        self,
        *,
        throughput_shipments: int,
        average_dwell_time_minutes: float,
        sort_error_rate_percent: float,
        sla_breach_shipments: int,
    ) -> dict[str, int | float]:
        return {
            "throughput_shipments": throughput_shipments,
            "dwell_time_minutes": round(average_dwell_time_minutes, 2),
            "sort_error_rate_percent": round(sort_error_rate_percent, 2),
            "sla_breach_shipments": sla_breach_shipments,
        }

    def build_branch_inventory_health(
        self,
        *,
        inventory_on_hand_units: int,
        items_at_risk: int,
        total_items: int,
    ) -> dict[str, int | float | str]:
        risk_ratio = round((items_at_risk / total_items) * 100, 2) if total_items else 0.0
        return {
            "inventory_on_hand_units": inventory_on_hand_units,
            "items_at_risk": items_at_risk,
            "inventory_risk_ratio_percent": risk_ratio,
            "inventory_posture": "at_risk" if items_at_risk else "healthy",
        }

    def build_branch_undelivered_aging_buckets(
        self,
        *,
        over_2h: int,
        over_6h: int,
        over_12h: int,
    ) -> dict[str, int]:
        return {
            "aging_queue_over_2h": over_2h,
            "aging_queue_over_6h": over_6h,
            "aging_queue_over_12h": over_12h,
        }

    def build_branch_attempt_and_exception_metrics(
        self,
        *,
        first_attempt_successes: int,
        total_attempts: int,
        rto_count: int,
        open_exceptions: int,
    ) -> dict[str, int | float]:
        first_attempt_success_rate = round((first_attempt_successes / total_attempts) * 100, 2) if total_attempts else 0.0
        rto_rate = round((rto_count / open_exceptions) * 100, 2) if open_exceptions else 0.0
        return {
            "first_attempt_success_rate_percent": first_attempt_success_rate,
            "rto_rate_percent": rto_rate,
            "open_exceptions": open_exceptions,
            "rto_count": rto_count,
        }

    def build_branch_agent_utilization(
        self,
        *,
        assigned_agents: int,
        active_agents: int,
        average_utilization_percent: float,
    ) -> dict[str, int | float]:
        return {
            "assigned_agents": assigned_agents,
            "active_agent_count": active_agents,
            "avg_agent_utilization_percent": round(average_utilization_percent, 2),
        }
