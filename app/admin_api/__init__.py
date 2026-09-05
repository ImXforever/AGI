"""Kia-Agent Platform — Admin API router.

Mounts every admin-facing endpoint: auth, approvals, SSE stream,
customers, catalog, quotes, tickets, analytics, audit, templates,
TWA (Telegram Web App) login, and v16 reports.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/admin/api", tags=["admin"])

from app.admin_api.analytics import router as _analytics_router  # noqa: E402
from app.admin_api.approvals import router as _approvals_router  # noqa: E402
from app.admin_api.audit import router as _audit_router  # noqa: E402
from app.admin_api.auth import router as _auth_router  # noqa: E402
from app.admin_api.automation import router as _automation_router  # noqa: E402
from app.admin_api.backup import router as _backup_router  # noqa: E402
from app.admin_api.catalog import router as _catalog_router  # noqa: E402
from app.admin_api.cms import router as _cms_router  # noqa: E402
from app.admin_api.content_calendar import router as _content_router  # noqa: E402
from app.admin_api.customers import router as _customers_router  # noqa: E402
from app.admin_api.qa import router as _qa_router  # noqa: E402
from app.admin_api.quotes import router as _quotes_router  # noqa: E402
from app.admin_api.rbac import require_writer as _require_writer  # noqa: E402, F401
from app.admin_api.reminders import router as _reminders_router  # noqa: E402
from app.admin_api.training import router as _training_router  # noqa: E402
from app.admin_api.reports import router as _reports_router  # noqa: E402
from app.admin_api.stream import router as _stream_router  # noqa: E402
from app.admin_api.team import router as _team_router  # noqa: E402
from app.admin_api.templates import router as _templates_router  # noqa: E402
from app.admin_api.tickets import router as _tickets_router  # noqa: E402
from app.admin_api.twa import router as _twa_router  # noqa: E402

router.include_router(_auth_router)
router.include_router(_approvals_router)
router.include_router(_stream_router)
router.include_router(_catalog_router)
router.include_router(_customers_router)
router.include_router(_quotes_router)
router.include_router(_tickets_router)
router.include_router(_analytics_router)
router.include_router(_audit_router)
router.include_router(_templates_router)
router.include_router(_twa_router)
router.include_router(_reports_router)
router.include_router(_reminders_router)
router.include_router(_content_router)
router.include_router(_cms_router)
router.include_router(_team_router)
router.include_router(_qa_router)
router.include_router(_automation_router)
router.include_router(_backup_router)
router.include_router(_training_router)
