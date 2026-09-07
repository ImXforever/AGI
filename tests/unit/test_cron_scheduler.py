"""Tests for v16 cron scheduler."""

from __future__ import annotations

import pytest

from app.core.cron_scheduler import CronScheduler, get_scheduler


class TestCronScheduler:
    def test_register_job(self):
        scheduler = CronScheduler()
        called = False

        async def job():
            nonlocal called
            called = True

        scheduler.register("test-job", 60, job)
        status = scheduler.get_status()
        assert len(status) == 1
        assert status[0]["name"] == "test-job"
        assert status[0]["interval_seconds"] == 60

    def test_unregister_job(self):
        scheduler = CronScheduler()

        async def job():
            pass

        scheduler.register("test-job", 60, job)
        scheduler.unregister("test-job")
        assert len(scheduler.get_status()) == 0

    def test_enable_disable(self):
        scheduler = CronScheduler()

        async def job():
            pass

        scheduler.register("test-job", 60, job)
        scheduler.disable("test-job")
        assert scheduler.get_status()[0]["enabled"] is False
        scheduler.enable("test-job")
        assert scheduler.get_status()[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_run_now(self):
        scheduler = CronScheduler()
        called = False

        async def job():
            nonlocal called
            called = True

        scheduler.register("test-job", 60, job)
        result = await scheduler.run_now("test-job")
        assert result is True
        assert called is True

    @pytest.mark.asyncio
    async def test_run_now_nonexistent(self):
        scheduler = CronScheduler()
        result = await scheduler.run_now("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_run_now_error_handling(self):
        scheduler = CronScheduler()

        async def failing_job():
            raise ValueError("test error")

        scheduler.register("failing", 60, failing_job)
        result = await scheduler.run_now("failing")
        assert result is False
        status = scheduler.get_status()
        assert status[0]["error_count"] == 1

    def test_get_scheduler_singleton(self):
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2
