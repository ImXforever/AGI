"""One-customer export pack. Delete stays a separate HITL action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExportPack:
    customer_id: str
    allowed: bool
    reason: str
    records: dict[str, list[dict[str, Any]]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "allowed": self.allowed,
            "reason": self.reason,
            "records": self.records,
        }


def build_export(
    customer_id: str,
    *,
    approval_id: str = "",
    messages: list[dict[str, Any]] | None = None,
    tickets: list[dict[str, Any]] | None = None,
    quotes: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
) -> ExportPack:
    cid = str(customer_id or "").strip()
    if not cid:
        return ExportPack("", False, "customer_id required", {})
    if not str(approval_id or "").strip():
        return ExportPack(cid, False, "approval_id required", {})
    return ExportPack(
        cid,
        True,
        "export ready",
        {
            "messages": list(messages or []),
            "tickets": list(tickets or []),
            "quotes": list(quotes or []),
            "approvals": list(approvals or []),
        },
    )
