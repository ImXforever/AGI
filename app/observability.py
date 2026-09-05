"""Observability: request correlation, RED metrics and a Prometheus endpoint.

The platform already emits structured JSON logs, but before this module there
was no way to answer "how many requests, how slow, how many errors" without
grepping. This adds three things, all dependency-free:

1. ``RequestContextMiddleware`` — assigns every request an ``X-Request-ID``
   (honouring an inbound one so a trace survives a proxy hop), exposes it via a
   ``ContextVar`` so any log line can be correlated, and records latency.
2. ``MetricsRegistry`` — an in-process counter/histogram store implementing the
   RED method (Rate, Errors, Duration) with Prometheus text exposition.
3. ``/metrics`` — the scrape endpoint, and ``/metrics.json`` for humans.

Cardinality is deliberately bounded: metrics are keyed on the *route template*
(``/admin/api/catalog/products/{product_id}``) rather than the raw path, so a
million distinct product ids cannot explode the series count.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable
from contextvars import ContextVar
from threading import Lock
from typing import Any

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_setup import get_logger

log = get_logger("app.observability")

REQUEST_ID_HEADER = "X-Request-ID"

#: Correlation id for the request currently being served, if any.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

#: Latency buckets in seconds (Prometheus cumulative histogram).
DEFAULT_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def current_request_id() -> str:
    """Return the correlation id of the in-flight request ("" outside one)."""
    return request_id_var.get()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in labels)
    return "{" + inner + "}"


class MetricsRegistry:
    """A small, thread-safe counter/gauge/histogram registry.

    Deliberately in-process: the platform runs one app per container and the
    scrape endpoint is per-instance, which is exactly what Prometheus expects.
    """

    def __init__(self, buckets: Iterable[float] = DEFAULT_BUCKETS) -> None:
        self._lock = Lock()
        self._buckets = tuple(sorted(buckets))
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._hist_counts: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = {}
        self._hist_sum: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._help: dict[str, str] = {}

    # -- recording ---------------------------------------------------------

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None):
        return name, tuple(sorted((labels or {}).items()))

    def describe(self, name: str, help_text: str) -> None:
        self._help[name] = help_text

    def inc(self, name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            counts = self._hist_counts.get(key)
            if counts is None:
                counts = [0] * (len(self._buckets) + 1)
                self._hist_counts[key] = counts
                self._hist_sum[key] = 0.0
            placed = False
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    counts[i] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1
            self._hist_sum[key] += value

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._hist_counts.clear()
            self._hist_sum.clear()

    # -- reading -----------------------------------------------------------

    def counter_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            return self._counters.get(self._key(name, labels), 0.0)

    def histogram_count(self, name: str, labels: dict[str, str] | None = None) -> int:
        with self._lock:
            return sum(self._hist_counts.get(self._key(name, labels), []))

    def snapshot(self) -> dict[str, Any]:
        """A JSON-friendly view of every series, for humans and for tests."""
        with self._lock:
            counters = [
                {"name": n, "labels": dict(l), "value": v}
                for (n, l), v in sorted(self._counters.items())
            ]
            gauges = [
                {"name": n, "labels": dict(l), "value": v}
                for (n, l), v in sorted(self._gauges.items())
            ]
            histograms = []
            for (n, l), counts in sorted(self._hist_counts.items()):
                total = sum(counts)
                hsum = self._hist_sum[(n, l)]
                histograms.append(
                    {
                        "name": n,
                        "labels": dict(l),
                        "count": total,
                        "sum": round(hsum, 6),
                        "avg": round(hsum / total, 6) if total else 0.0,
                    }
                )
        return {"counters": counters, "gauges": gauges, "histograms": histograms}

    def render_prometheus(self) -> str:
        """Render the registry in the Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            names_done: set[str] = set()

            for (name, labels), value in sorted(self._counters.items()):
                if name not in names_done:
                    if name in self._help:
                        lines.append(f"# HELP {name} {self._help[name]}")
                    lines.append(f"# TYPE {name} counter")
                    names_done.add(name)
                lines.append(f"{name}{_format_labels(labels)} {value}")

            for (name, labels), value in sorted(self._gauges.items()):
                if name not in names_done:
                    if name in self._help:
                        lines.append(f"# HELP {name} {self._help[name]}")
                    lines.append(f"# TYPE {name} gauge")
                    names_done.add(name)
                lines.append(f"{name}{_format_labels(labels)} {value}")

            for (name, labels), counts in sorted(self._hist_counts.items()):
                if name not in names_done:
                    if name in self._help:
                        lines.append(f"# HELP {name} {self._help[name]}")
                    lines.append(f"# TYPE {name} histogram")
                    names_done.add(name)
                cumulative = 0
                for i, bound in enumerate(self._buckets):
                    cumulative += counts[i]
                    bucket_labels = labels + (("le", str(bound)),)
                    lines.append(f"{name}_bucket{_format_labels(bucket_labels)} {cumulative}")
                cumulative += counts[-1]
                inf_labels = labels + (("le", "+Inf"),)
                lines.append(f"{name}_bucket{_format_labels(inf_labels)} {cumulative}")
                lines.append(f"{name}_sum{_format_labels(labels)} {self._hist_sum[(name, labels)]}")
                lines.append(f"{name}_count{_format_labels(labels)} {cumulative}")

        return "\n".join(lines) + "\n"


#: The process-wide registry.
registry = MetricsRegistry()

registry.describe(
    "Kia-Agent_http_requests_total", "Total HTTP requests by route, method and status."
)
registry.describe("Kia-Agent_http_request_duration_seconds", "HTTP request latency in seconds.")
registry.describe("Kia-Agent_http_requests_in_flight", "Requests currently being served.")
registry.describe(
    "Kia-Agent_http_exceptions_total", "Unhandled exceptions raised while serving a request."
)


def route_template(request: Request) -> str:
    """The matched route pattern, not the concrete path.

    Keeps metric cardinality bounded: ``/products/{product_id}`` stays one
    series no matter how many products exist.
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return str(path)
    return "unmatched"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a correlation id and record RED metrics for every request."""

    def __init__(self, app: Any, metrics: MetricsRegistry | None = None) -> None:
        super().__init__(app)
        self._metrics = metrics if metrics is not None else registry

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
        rid = incoming or uuid.uuid4().hex
        token = request_id_var.set(rid)
        request.state.request_id = rid

        self._metrics.inc("Kia-Agent_http_requests_in_flight", value=1)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        except Exception:
            self._metrics.inc(
                "Kia-Agent_http_exceptions_total",
                {"route": route_template(request), "method": request.method},
            )
            raise
        finally:
            elapsed = time.perf_counter() - started
            labels = {"route": route_template(request), "method": request.method}
            self._metrics.inc("Kia-Agent_http_requests_in_flight", value=-1)
            self._metrics.inc("Kia-Agent_http_requests_total", {**labels, "status": str(status)})
            self._metrics.observe("Kia-Agent_http_request_duration_seconds", elapsed, labels)
            request_id_var.reset(token)


router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=Response)
async def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint (text exposition format)."""
    return Response(
        content=registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/metrics.json")
async def metrics_json() -> dict[str, Any]:
    """The same series as ``/metrics``, as JSON, for dashboards and debugging."""
    return registry.snapshot()
