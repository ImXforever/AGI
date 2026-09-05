"""Integration tests for observability wired into the live application."""

from __future__ import annotations

from typing import Any

import pytest

from app.observability import REQUEST_ID_HEADER
from tests.conftest import requires_infra

pytestmark = [pytest.mark.integration, requires_infra]


class TestRequestId:
    async def test_every_response_carries_a_correlation_id(self, client: Any):
        resp = await client.get("/healthz")
        assert resp.headers.get(REQUEST_ID_HEADER)

    async def test_an_inbound_correlation_id_is_preserved(self, client: Any):
        """A trace started at the edge proxy must survive into our logs."""
        resp = await client.get("/healthz", headers={REQUEST_ID_HEADER: "trace-abc-123"})
        assert resp.headers[REQUEST_ID_HEADER] == "trace-abc-123"

    async def test_generated_ids_are_unique_per_request(self, client: Any):
        first = (await client.get("/healthz")).headers[REQUEST_ID_HEADER]
        second = (await client.get("/healthz")).headers[REQUEST_ID_HEADER]
        assert first != second


class TestMetricsEndpoint:
    async def test_metrics_are_exposed_in_the_prometheus_format(self, client: Any):
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    async def test_requests_are_counted(self, client: Any):
        await client.get("/healthz")
        body = (await client.get("/metrics")).text
        assert "Kia-Agent_http_requests_total" in body

    async def test_latency_is_recorded_as_a_histogram(self, client: Any):
        await client.get("/healthz")
        body = (await client.get("/metrics")).text
        assert "Kia-Agent_http_request_duration_seconds_bucket" in body

    async def test_the_route_template_is_used_rather_than_the_raw_path(self, client: Any):
        """Cardinality guard: a concrete id must not become its own series."""
        await client.get("/admin/api/catalog/products/does-not-exist")
        body = (await client.get("/metrics")).text
        assert "does-not-exist" not in body

    async def test_status_codes_are_labelled(self, client: Any):
        await client.get("/healthz")
        assert 'status="200"' in (await client.get("/metrics")).text

    async def test_the_json_view_mirrors_the_scrape_endpoint(self, client: Any):
        await client.get("/healthz")
        body = (await client.get("/metrics.json")).json()
        assert set(body) == {"counters", "gauges", "histograms"}
        assert any(c["name"] == "Kia-Agent_http_requests_total" for c in body["counters"])

    async def test_metrics_need_no_authentication(self, client: Any):
        """Prometheus scrapes without a session cookie."""
        client.cookies.clear()
        assert (await client.get("/metrics")).status_code == 200


class TestBuildInfo:
    async def test_buildinfo_reports_the_service_version(self, client: Any):
        body = (await client.get("/buildinfo")).json()
        assert body["service"] == "Kia-Agent-app"
        assert body["version"] in ("10.0.0", "20.0.0", "20.0.3")
        assert body["uptime_s"] >= 0
