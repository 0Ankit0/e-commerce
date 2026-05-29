import asyncio
import pytest

from src.apps.core import tasks as core_tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_email_task_runs_inside_existing_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    called = asyncio.Event()

    async def fake_send_email_task(**kwargs: object) -> bool:
        captured.update(kwargs)
        called.set()
        return True

    monkeypatch.setattr(core_tasks, "_send_email_task", fake_send_email_task)

    result = core_tasks.send_email_task(
        "Subject",
        [{"email": "demo@example.com", "name": "Demo"}],
        "welcome",
        {"hello": "world"},
    )

    await asyncio.wait_for(called.wait(), timeout=1)

    assert result is True
    assert captured["subject"] == "Subject"
    assert captured["template_name"] == "welcome"