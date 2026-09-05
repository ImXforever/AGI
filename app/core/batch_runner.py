"""Batch runner — parallel processing of multiple AI tasks.

Adapted from Hermes Agent's batch_runner.py for processing multiple prompts
or tasks concurrently with controlled parallelism and result aggregation.

Use cases:
  - Batch generate product descriptions/titles
  - Batch analyze user feedback
  - Batch notify users with personalized messages
  - Parallel research queries via Fleet

Features:
  - Configurable concurrency (max parallel tasks)
  - Per-task timeout with graceful degradation
  - Progress tracking with callbacks
  - Result aggregation: collect, summarize, fail-count
  - Error isolation: one failed task doesn't kill the batch
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.llm import LLMClient
from app.logging_setup import get_logger

log = get_logger("app.core.batch_runner")

# =========================================================
# Configuration
# =========================================================

DEFAULT_CONCURRENCY = 5
DEFAULT_TASK_TIMEOUT = 60  # seconds per task
DEFAULT_BATCH_TIMEOUT = 300  # seconds for entire batch


# =========================================================
# Result types
# =========================================================


@dataclass
class TaskResult:
    index: int
    success: bool
    result: Any = None
    error: str = ""
    duration: float = 0.0


@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    results: list[TaskResult] = field(default_factory=list)
    duration: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.succeeded / self.total * 100) if self.total > 0 else 0

    def summary(self) -> str:
        lines = [
            "Batch result:",
            f"  total: {self.total}",
            f"  succeeded: {self.succeeded} ({self.success_rate:.0f}%)",
            f"  failed: {self.failed}",
            f"  duration: {self.duration:.1f}s",
        ]
        if self.errors:
            lines.append("  errors:")
            for e in self.errors[:5]:
                lines.append(f"    - {e[:100]}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "duration": round(self.duration, 2),
            "success_rate": round(self.success_rate, 1),
            "results": [
                {
                    "index": r.index,
                    "success": r.success,
                    "result": str(r.result)[:200],
                    "error": r.error[:200],
                    "duration": round(r.duration, 2),
                }
                for r in self.results
            ],
        }


# =========================================================
# Batch runner core
# =========================================================


async def run_batch(
    tasks: list[Any],
    handler: Callable[[int, Any], Awaitable[Any]],
    concurrency: int = DEFAULT_CONCURRENCY,
    task_timeout: float = DEFAULT_TASK_TIMEOUT,
    batch_timeout: float = DEFAULT_BATCH_TIMEOUT,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> BatchResult:
    """Run a batch of tasks concurrently with progress tracking.

    Args:
        tasks: List of task items to process.
        handler: async function(index, task_item) -> result
        concurrency: max parallel workers
        task_timeout: timeout per task (seconds)
        batch_timeout: total timeout for the batch (seconds)
        on_progress: optional async callback(completed, total) for progress

    Returns:
        BatchResult with all outcomes.
    """
    if not tasks:
        return BatchResult(total=0, succeeded=0, failed=0)

    sem = asyncio.Semaphore(concurrency)
    results: list[TaskResult | None] = [None] * len(tasks)
    completed = 0

    async def _run_one(idx: int, item: Any) -> None:
        nonlocal completed
        async with sem:
            t0 = time.monotonic()
            try:
                result = await asyncio.wait_for(handler(idx, item), task_timeout)
                results[idx] = TaskResult(
                    index=idx, success=True, result=result, duration=time.monotonic() - t0
                )
            except TimeoutError:
                results[idx] = TaskResult(
                    index=idx,
                    success=False,
                    error=f"timeout {task_timeout}s",
                    duration=time.monotonic() - t0,
                )
            except Exception as e:
                results[idx] = TaskResult(
                    index=idx, success=False, error=str(e)[:300], duration=time.monotonic() - t0
                )

            completed += 1
            if on_progress:
                try:
                    await on_progress(completed, len(tasks))
                except Exception:
                    log.debug("batch_progress_callback_failed", exc_info=True)

    t0 = time.monotonic()
    try:
        await asyncio.wait_for(
            asyncio.gather(*[_run_one(i, t) for i, t in enumerate(tasks)]),
            timeout=batch_timeout,
        )
    except TimeoutError:
        for i, r in enumerate(results):
            if r is None:
                results[i] = TaskResult(index=i, success=False, error="batch timeout")

    duration = time.monotonic() - t0
    succeeded = sum(1 for r in results if r and r.success)
    failed = sum(1 for r in results if r and not r.success)
    errors = [r.error for r in results if r and not r.success and r.error]

    return BatchResult(
        total=len(tasks),
        succeeded=succeeded,
        failed=failed,
        results=[r for r in results if r],
        duration=duration,
        errors=errors,
    )


# =========================================================
# High-level batch operations
# =========================================================


async def batch_generate(
    prompts: list[str],
    concurrency: int = 3,
    system_prompt: str = "",
    user_key: int = 0,
    *,
    llm: LLMClient | None = None,
) -> list[str]:
    """Generate AI responses for multiple prompts in parallel."""
    if llm is None:
        llm = LLMClient()

    async def _gen(idx: int, prompt: str) -> str:
        return await llm.complete(
            system=system_prompt or "You are a helpful assistant.",
            user=prompt,
            tier="fast",
            max_tokens=800,
            purpose="batch_generate",
        )

    result = await run_batch(prompts, _gen, concurrency=concurrency)
    outputs: list[str] = []
    for r in sorted(result.results, key=lambda x: x.index):
        outputs.append(r.result if r.success else f"[error: {r.error[:100]}]")
    return outputs


async def batch_notify(
    user_ids: list[int],
    message: str,
    bot: Any,
    concurrency: int = 20,
) -> BatchResult:
    """Send a message to multiple users with controlled concurrency."""

    async def _send(idx: int, uid: int) -> str:
        await bot.send_message(uid, message)
        return f"sent to {uid}"

    return await run_batch(user_ids, _send, concurrency=concurrency, task_timeout=10)


async def batch_analyze(
    items: list[dict[str, Any]],
    analysis_prompt: str,
    concurrency: int = 3,
    *,
    llm: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """Analyze a batch of items using AI and return structured results."""
    if llm is None:
        llm = LLMClient()

    async def _analyze(idx: int, item: dict[str, Any]) -> dict[str, Any]:
        raw = await llm.complete(
            system="Professional analyst. Output JSON only.",
            user=f"{analysis_prompt}\n\nData:\n{json.dumps(item, ensure_ascii=False)[:1000]}",
            tier="fast",
            max_tokens=500,
            purpose="batch_analyze",
        )
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            return json.loads(match.group()) if match else {"raw": raw[:300]}
        except Exception:
            return {"raw": raw[:300], "parse_error": True}

    result = await run_batch(items, _analyze, concurrency=concurrency)
    return [r.result if r else {} for r in sorted(result.results, key=lambda x: x.index)]
