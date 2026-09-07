"""Backup list / restore drill. Live pg_restore is never applied here."""

from __future__ import annotations

from dataclasses import dataclass


def can_restore(*, approval_id: str, role: str) -> tuple[bool, str]:
    if not str(approval_id or "").strip():
        return False, "approval_id required"
    rank = str(role or "").strip().lower()
    if rank not in {"superadmin", "owner", "root"}:
        return False, "superadmin required"
    return True, "ok"


def backup_key_allowed(key: str) -> bool:
    raw = str(key or "").strip()
    if not raw or ".." in raw or raw.startswith("/") or "\\" in raw:
        return False
    return "backups/" in raw or raw.startswith("backups")


@dataclass(frozen=True)
class RestoreResult:
    ok: bool
    verified: bool
    applied: bool
    reason: str

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "ok": self.ok,
            "verified": self.verified,
            "applied": self.applied,
            "reason": self.reason,
        }


def restore_backup(
    key: str,
    *,
    approval_id: str,
    role: str,
    gzip_magic_ok: bool = True,
) -> RestoreResult:
    allowed, why = can_restore(approval_id=approval_id, role=role)
    if not allowed:
        return RestoreResult(ok=False, verified=False, applied=False, reason=why)
    if not backup_key_allowed(key):
        return RestoreResult(ok=False, verified=False, applied=False, reason="invalid key")
    if not gzip_magic_ok:
        return RestoreResult(ok=False, verified=False, applied=False, reason="not a gzip dump")
    return RestoreResult(
        ok=True,
        verified=True,
        applied=False,
        reason="drill verified; live apply refused",
    )
