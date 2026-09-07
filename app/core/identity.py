"""Customer identity across channels. Merge is HITL — never automatic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MergePlan:
    winner_id: str
    loser_id: str
    allowed: bool
    reason: str


def plan_merge(
    winner_id: str,
    loser_id: str,
    *,
    approval_id: str = "",
) -> MergePlan:
    w = str(winner_id or "").strip()
    l = str(loser_id or "").strip()
    if not w or not l:
        return MergePlan(w, l, False, "both customer ids required")
    if w == l:
        return MergePlan(w, l, False, "cannot merge a customer onto itself")
    if not str(approval_id or "").strip():
        return MergePlan(w, l, False, "approval_id required")
    return MergePlan(w, l, True, "merge recorded under HITL")
