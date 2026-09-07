from __future__ import annotations

from app.core.capacity import simulate_burst, simulate_members


def test_ten_thousand_members_fit_a_single_railway_web() -> None:
    report = simulate_members(10_000)
    d = report.as_dict()
    assert d["members"] == 10_000
    assert d["inbound_per_sec"] < 2.0
    assert d["redis_mb"] < 80
    assert d["verdict"] in {"yes", "yes-with-worker"}
    assert d["workers_recommended"] <= 2


def test_hitl_is_the_human_bottleneck_not_cpu() -> None:
    report = simulate_members(10_000, auto_ratio=0.85)
    assert report.hitl_per_hour < 500
    # Staffing note is allowed; software still says yes.
    assert report.verdict.startswith("yes")


def test_burst_of_10k_events_drains_under_three_minutes() -> None:
    burst = simulate_burst(10_000, consume_rps=80.0)
    assert burst["ok"] is True
    assert burst["drain_seconds"] < 180


def test_ops_html_points_at_admin_api() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "admin" / "ops"
    js = (root / "ops.js").read_text(encoding="utf-8")
    assert "/admin/api" in js
    assert "/approvals/" in js
    queue = (root / "queue.html").read_text(encoding="utf-8")
    assert "data-decide" in queue
    login = (root / "login.html").read_text(encoding="utf-8")
    assert "/admin/api/auth/login" in login
    fa = sum(1 for c in queue if "\u0600" <= c <= "\u06ff")
    assert fa == 0
