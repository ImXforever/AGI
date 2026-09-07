"""Tests for v0.9 reporting aggregation and KPI safety."""

from __future__ import annotations

from app.core.reporting import build_operational_report, calculate_kpis


def test_report_aggregates_events_without_message_content() -> None:
    report = build_operational_report(
        [
            {"type": "incoming", "channel": "telegram", "category": "support", "text": "secret"},
            {"type": "task_created", "channel": "email", "category": "sales"},
            {"type": "approval_pending", "channel": "email"},
            {"type": "error", "channel": "telegram"},
        ]
    )
    data = report.as_dict()
    assert data["total_events"] == 4
    assert data["messages"] == 1
    assert data["tasks_created"] == 1
    assert data["approvals_pending"] == 1
    assert data["errors"] == 1
    assert data["by_channel"] == {"telegram": 2, "email": 2}
    assert "text" not in data


def test_kpis_handle_empty_and_invalid_values() -> None:
    result = calculate_kpis(response_times_ms=[100, 300, -1], resolved=0, received=0)
    assert result["average_response_ms"] == 200.0
    assert result["response_samples"] == 2
    assert result["resolution_rate"] == 0.0


def test_kpis_calculate_resolution_rate() -> None:
    result = calculate_kpis(response_times_ms=[50], resolved=3, received=4)
    assert result["resolution_rate"] == 0.75
    assert result["received"] == 4
    assert result["resolved"] == 3
