"""Internal cron scheduler for periodic tasks (v16).

Runs background checks for follow-ups, report generation, and cleanup.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.cron_scheduler")


@dataclass
class CronJob:
    name: str
    interval_seconds: int
    func: Callable[[], Awaitable[None]]
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0
    error_count: int = 0

    def __post_init__(self) -> None:
        if self.next_run == 0.0:
            self.next_run = time.time() + self.interval_seconds


class CronScheduler:
    """Simple in-process cron scheduler."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def register(
        self,
        name: str,
        interval_seconds: int,
        func: Callable[[], Awaitable[None]],
        *,
        enabled: bool = True,
    ) -> None:
        """Register a cron job."""
        self._jobs[name] = CronJob(
            name=name,
            interval_seconds=interval_seconds,
            func=func,
            enabled=enabled,
        )
        log.info(
            "cron_job_registered",
            extra={"action": "cron.register", "name": name, "interval": interval_seconds},
        )

    def unregister(self, name: str) -> None:
        """Remove a cron job."""
        self._jobs.pop(name, None)

    def get_status(self) -> list[dict[str, Any]]:
        """Return status of all registered jobs."""
        return [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "enabled": job.enabled,
                "last_run": job.last_run,
                "next_run": job.next_run,
                "run_count": job.run_count,
                "error_count": job.error_count,
            }
            for job in self._jobs.values()
        ]

    def enable(self, name: str) -> None:
        """Enable a cron job."""
        if name in self._jobs:
            self._jobs[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a cron job."""
        if name in self._jobs:
            self._jobs[name].enabled = False

    async def run_now(self, name: str) -> bool:
        """Immediately run a specific job."""
        job = self._jobs.get(name)
        if job is None:
            return False
        try:
            await job.func()
            job.last_run = time.time()
            job.run_count += 1
            log.info("cron_job_executed", extra={"action": "cron.run", "name": name})
            return True
        except Exception as exc:
            job.error_count += 1
            log.error(
                "cron_job_failed",
                extra={"action": "cron.run", "name": name, "error": str(exc)},
            )
            return False

    async def _loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = time.time()
            for job in self._jobs.values():
                if not job.enabled:
                    continue
                if now >= job.next_run:
                    try:
                        await job.func()
                        job.last_run = now
                        job.run_count += 1
                        log.debug(
                            "cron_job_executed",
                            extra={"action": "cron.loop", "name": job.name},
                        )
                    except Exception as exc:
                        job.error_count += 1
                        log.error(
                            "cron_job_failed",
                            extra={"action": "cron.loop", "name": job.name, "error": str(exc)},
                        )
                    job.next_run = now + job.interval_seconds
            await asyncio.sleep(10)

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="cron-scheduler")
        log.info("cron_scheduler_started", extra={"action": "cron.start"})

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("cron_scheduler_stopped", extra={"action": "cron.stop"})


_scheduler: CronScheduler | None = None


def get_scheduler() -> CronScheduler:
    """Get or create the global cron scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
    return _scheduler
