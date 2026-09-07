"""RBAC — role enforcement for the admin API.

Why this exists
---------------
The ``admins`` table has always carried a ``role`` column constrained to
``superadmin | admin | viewer``, and the analytics tool layer declares a
``min_role`` per query template.  But **no admin endpoint ever checked it**:
``require_admin()`` returned any active account, so a ``viewer`` could delete
products, approve HITL drafts, and rotate templates.  The column was decoration.

This module turns the existing column into an enforced privilege boundary.

Role model
----------
Three ranked roles, aligned with the ``admins_role_check`` DB constraint::

    viewer (0)  — read-only
    admin  (1)  — read + write on business objects
    superadmin (2) — everything, including destructive + account operations

The historical tools-layer vocabulary (``viewer/editor/admin``) is mapped onto
this scale by :data:`ROLE_ALIASES` so the two subsystems finally agree.

Usage
-----
Replace the dependency on an endpoint::

    @router.delete("/products/{product_id}")
    async def delete_product(..., admin = Depends(require_superadmin)):

or, for the common read/write split::

    admin: dict = Depends(require_writer)   # admin or superadmin
    admin: dict = Depends(require_admin)    # any authenticated role (read)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger(__name__)

ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"
ROLE_SUPERADMIN = "superadmin"

#: Canonical rank of each role.  Higher rank implies every lower privilege.
ROLE_RANK: dict[str, int] = {
    ROLE_VIEWER: 0,
    ROLE_ADMIN: 1,
    ROLE_SUPERADMIN: 2,
}

#: Legacy/alternate spellings used elsewhere in the codebase.
ROLE_ALIASES: dict[str, str] = {
    "editor": ROLE_ADMIN,  # tools layer vocabulary
    "read": ROLE_VIEWER,
    "readonly": ROLE_VIEWER,
    "read_only": ROLE_VIEWER,
    "owner": ROLE_SUPERADMIN,
    "root": ROLE_SUPERADMIN,
}


def normalize_role(role: str | None) -> str:
    """Map any known spelling onto a canonical role.

    Unknown or missing roles degrade to :data:`ROLE_VIEWER` — the safe default.
    Never raises, so a malformed DB row cannot escalate privileges.
    """
    if not role:
        return ROLE_VIEWER
    value = str(role).strip().lower()
    value = ROLE_ALIASES.get(value, value)
    return value if value in ROLE_RANK else ROLE_VIEWER


def rank_of(role: str | None) -> int:
    """Numeric privilege level of *role* (unknown → lowest)."""
    return ROLE_RANK[normalize_role(role)]


def has_role(actual: str | None, required: str) -> bool:
    """True when *actual* satisfies the *required* minimum role."""
    return rank_of(actual) >= rank_of(required)


def require_role(
    minimum: str,
) -> Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]:
    """Build a FastAPI dependency enforcing a minimum role.

    Layers on top of :func:`require_admin`, so authentication (401) is still
    handled first and this only adds authorisation (403).
    """
    required = normalize_role(minimum)

    async def _dependency(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        actual = normalize_role(admin.get("role"))
        if not has_role(actual, required):
            log.warning(
                "rbac_denied",
                extra={
                    "action": "rbac.check",
                    "actor": admin.get("username", ""),
                    "role": actual,
                    "required": required,
                },
            )
            raise HTTPException(
                status_code=403,
                detail=f"insufficient role: {required!r} required, caller is {actual!r}",
            )
        return admin

    _dependency.__name__ = f"require_role_{required}"
    return _dependency


#: Read access — any authenticated account (viewer and above).
require_viewer = require_role(ROLE_VIEWER)

#: Write access to business objects — admin and above.
require_writer = require_role(ROLE_ADMIN)

#: Destructive / account operations — superadmin only.
require_superadmin = require_role(ROLE_SUPERADMIN)
