from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine, TypeVar, cast


T = TypeVar("T")
logger = logging.getLogger(__name__)


def _log_background_failure(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except Exception:
        logger.exception("Background coroutine failed")


def run_async_compatible(
    coroutine: Coroutine[Any, Any, T],
    *,
    background_result: T | None = None,
) -> T:
    """Run a coroutine from sync code and fall back to same-loop background scheduling when needed."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    task = loop.create_task(coroutine)
    task.add_done_callback(_log_background_failure)
    return cast(T, background_result)