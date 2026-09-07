"""Unit tests for the metrics registry and request-context middleware."""

from __future__ import annotations

import pytest

from app.observability import (
    DEFAULT_BUCKETS,
    MetricsRegistry,
    current_request_id,
    request_id_var,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def reg() -> MetricsRegistry:
    return MetricsRegistry()


class TestCounters:
    def test_an_unseen_counter_reads_zero(self, reg: MetricsRegistry):
        assert reg.counter_value("nope") == 0.0

    def test_increments_accumulate(self, reg: MetricsRegistry):
        reg.inc("hits")
        reg.inc("hits")
        assert reg.counter_value("hits") == 2.0

    def test_a_custom_step_is_honoured(self, reg: MetricsRegistry):
        reg.inc("bytes", value=512)
        assert reg.counter_value("bytes") == 512

    def test_counters_can_be_decremented_for_in_flight_gauges(self, reg: MetricsRegistry):
        reg.inc("in_flight", value=1)
        reg.inc("in_flight", value=-1)
        assert reg.counter_value("in_flight") == 0.0

    def test_label_sets_are_tracked_independently(self, reg: MetricsRegistry):
        reg.inc("req", {"route": "/a"})
        reg.inc("req", {"route": "/b"})
        reg.inc("req", {"route": "/a"})
        assert reg.counter_value("req", {"route": "/a"}) == 2.0
        assert reg.counter_value("req", {"route": "/b"}) == 1.0

    def test_label_order_does_not_create_a_new_series(self, reg: MetricsRegistry):
        reg.inc("req", {"a": "1", "b": "2"})
        reg.inc("req", {"b": "2", "a": "1"})
        assert reg.counter_value("req", {"a": "1", "b": "2"}) == 2.0


class TestGauges:
    def test_a_gauge_holds_the_last_value(self, reg: MetricsRegistry):
        reg.set_gauge("queue_depth", 5)
        reg.set_gauge("queue_depth", 2)
        assert reg.snapshot()["gauges"][0]["value"] == 2


class TestHistograms:
    def test_observations_are_counted(self, reg: MetricsRegistry):
        for _ in range(3):
            reg.observe("latency", 0.02)
        assert reg.histogram_count("latency") == 3

    def test_the_sum_and_average_are_tracked(self, reg: MetricsRegistry):
        reg.observe("latency", 0.1)
        reg.observe("latency", 0.3)
        hist = reg.snapshot()["histograms"][0]
        assert hist["sum"] == pytest.approx(0.4)
        assert hist["avg"] == pytest.approx(0.2)

    def test_values_beyond_the_last_bucket_still_count(self, reg: MetricsRegistry):
        reg.observe("latency", DEFAULT_BUCKETS[-1] * 100)
        assert reg.histogram_count("latency") == 1

    def test_histograms_are_label_aware(self, reg: MetricsRegistry):
        reg.observe("latency", 0.1, {"route": "/a"})
        reg.observe("latency", 0.1, {"route": "/b"})
        assert reg.histogram_count("latency", {"route": "/a"}) == 1


class TestPrometheusRendering:
    def test_an_empty_registry_renders_without_error(self, reg: MetricsRegistry):
        assert reg.render_prometheus().strip() == ""

    def test_a_counter_is_rendered_with_its_type(self, reg: MetricsRegistry):
        reg.describe("hits_total", "Total hits.")
        reg.inc("hits_total")
        out = reg.render_prometheus()
        assert "# HELP hits_total Total hits." in out
        assert "# TYPE hits_total counter" in out
        assert "hits_total 1.0" in out

    def test_labels_are_rendered_in_prometheus_syntax(self, reg: MetricsRegistry):
        reg.inc("req_total", {"route": "/a", "method": "GET"})
        assert 'req_total{method="GET",route="/a"} 1.0' in reg.render_prometheus()

    def test_quotes_in_label_values_are_escaped(self, reg: MetricsRegistry):
        reg.inc("req_total", {"route": 'a"b'})
        assert '\\"' in reg.render_prometheus()

    def test_a_histogram_renders_cumulative_buckets(self, reg: MetricsRegistry):
        reg.observe("latency_seconds", 0.02)
        out = reg.render_prometheus()
        assert "# TYPE latency_seconds histogram" in out
        assert "latency_seconds_bucket" in out
        assert 'le="+Inf"' in out
        assert "latency_seconds_count" in out
        assert "latency_seconds_sum" in out

    def test_bucket_counts_are_monotonically_cumulative(self, reg: MetricsRegistry):
        for value in (0.001, 0.03, 2.0):
            reg.observe("latency_seconds", value)
        counts = [
            float(line.rsplit(" ", 1)[1])
            for line in reg.render_prometheus().splitlines()
            if line.startswith("latency_seconds_bucket")
        ]
        assert counts == sorted(counts)
        assert counts[-1] == 3

    def test_the_inf_bucket_equals_the_total_count(self, reg: MetricsRegistry):
        for value in (0.001, 50.0):
            reg.observe("latency_seconds", value)
        lines = reg.render_prometheus().splitlines()
        inf = next(l for l in lines if 'le="+Inf"' in l)
        count = next(l for l in lines if l.startswith("latency_seconds_count"))
        assert inf.rsplit(" ", 1)[1] == count.rsplit(" ", 1)[1]

    def test_output_ends_with_a_newline(self, reg: MetricsRegistry):
        reg.inc("x")
        assert reg.render_prometheus().endswith("\n")


class TestSnapshotAndReset:
    def test_the_snapshot_has_all_three_sections(self, reg: MetricsRegistry):
        assert set(reg.snapshot()) == {"counters", "gauges", "histograms"}

    def test_reset_clears_everything(self, reg: MetricsRegistry):
        reg.inc("a")
        reg.set_gauge("b", 1)
        reg.observe("c", 0.1)
        reg.reset()
        snap = reg.snapshot()
        assert snap["counters"] == [] and snap["gauges"] == [] and snap["histograms"] == []


class TestRequestId:
    def test_outside_a_request_the_id_is_empty(self):
        assert current_request_id() == ""

    def test_the_context_var_is_readable(self):
        token = request_id_var.set("abc123")
        try:
            assert current_request_id() == "abc123"
        finally:
            request_id_var.reset(token)
