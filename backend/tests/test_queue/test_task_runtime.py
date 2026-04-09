import asyncio

import pytest

from app.queue import tasks


def teardown_function() -> None:
    tasks._reset_worker_event_loop()


def test_run_async_reuses_worker_event_loop():
    loop_ids: list[int] = []

    async def capture_loop_id() -> int:
        loop_ids.append(id(asyncio.get_running_loop()))
        return len(loop_ids)

    assert tasks.run_async(capture_loop_id()) == 1
    assert tasks.run_async(capture_loop_id()) == 2
    assert len(set(loop_ids)) == 1


def test_run_async_recreates_closed_worker_loop():
    async def current_loop_id() -> int:
        return id(asyncio.get_running_loop())

    first_loop_id = tasks.run_async(current_loop_id())
    tasks._reset_worker_event_loop()
    second_loop_id = tasks.run_async(current_loop_id())

    assert first_loop_id != second_loop_id


def test_run_async_recreates_loop_after_process_change(monkeypatch):
    loop_ids: list[int] = []
    pids = iter([11111, 22222])

    async def capture_loop_id() -> int:
        loop_ids.append(id(asyncio.get_running_loop()))
        return loop_ids[-1]

    monkeypatch.setattr(tasks.os, "getpid", lambda: next(pids))

    first_loop_id = tasks.run_async(capture_loop_id())
    second_loop_id = tasks.run_async(capture_loop_id())

    assert first_loop_id != second_loop_id


def test_run_async_remains_usable_after_coroutine_failure():
    async def explode() -> None:
        raise RuntimeError("boom")

    async def current_loop_id() -> int:
        return id(asyncio.get_running_loop())

    with pytest.raises(RuntimeError, match="boom"):
        tasks.run_async(explode())

    first_loop_id = tasks.run_async(current_loop_id())
    second_loop_id = tasks.run_async(current_loop_id())

    assert first_loop_id == second_loop_id
