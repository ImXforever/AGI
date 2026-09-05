"""Cross-module constants: Redis key namespaces, stream names, HITL states."""

from __future__ import annotations

KEY_SESSION = "sess:{conv_id}"
KEY_DEDUP = "dedup:{channel}:{ext_ref}"
KEY_RATE_LIMIT = "rl:{channel}:{key}"
KEY_WA_SESSION = "wa:sess:{phone}"
KEY_CATALOG_CACHE = "cache:catalog"
KEY_HITL_META = "hitl:meta:{approval_id}"
KEY_HITL_DECIDED = "hitl:decided:{approval_id}"

STREAM_HITL = "hitl:queue"
STREAM_EVENTS = "bus:events"
GROUP_HITL = "app"
GROUP_EVENTS = "consumers"
CONSUMER_PREFIX = "app"

EVENT_INCOMING = "incoming"
EVENT_OUTBOUND = "outbound"
EVENT_APPROVAL_DECIDED = "approval-decided"
EVENT_TIMEOUT = "timeout"
EVENT_ESCALATION = "escalation"


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    TIMEOUT = "timeout"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    TERMINAL = frozenset({APPROVED, REJECTED, EDITED, TIMEOUT, ESCALATED, CANCELLED})
    DECISIONS = frozenset({APPROVED, REJECTED, EDITED})


CHANNEL_TELEGRAM = "telegram"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_EMAIL = "email"
CHANNELS = frozenset({CHANNEL_TELEGRAM, CHANNEL_WHATSAPP, CHANNEL_EMAIL})

SKILL_ORCHESTRATOR = "orchestrator"
SKILL_KNOWLEDGE = "knowledge_agent"
SKILL_CUSTOMER = "customer_agent"
SKILL_SALES = "sales_agent"
SKILL_SUPPORT = "support_agent"
SKILL_ANALYTICS = "analytics_agent"
SKILL_EMAIL = "email_agent"
SKILL_WEBSITE = "website_agent"
SKILL_SOCIAL = "social_agent"
SKILL_OPS = "ops_agent"
AGENT_SKILLS = frozenset(
    {
        SKILL_KNOWLEDGE,
        SKILL_CUSTOMER,
        SKILL_SALES,
        SKILL_SUPPORT,
        SKILL_ANALYTICS,
        SKILL_EMAIL,
        SKILL_WEBSITE,
        SKILL_SOCIAL,
        SKILL_OPS,
    }
)
SKILL_DIRS = {
    SKILL_ORCHESTRATOR: "orchestrator",
    SKILL_KNOWLEDGE: "knowledge",
    SKILL_CUSTOMER: "customer",
    SKILL_SALES: "sales",
    SKILL_SUPPORT: "support",
    SKILL_ANALYTICS: "analytics",
    SKILL_EMAIL: "email",
    SKILL_WEBSITE: "website",
    SKILL_SOCIAL: "social",
    SKILL_OPS: "ops",
}

MUTATING_TOOLS = frozenset(
    {
        "create_quote",
        "create_ticket",
        "update_customer",
        "set_lead_score",
        "send_email",
        "publish_content",
        "change_price",
        "payment",
        "contract",
        "delete_data",
        "change_access",
    }
)
AUTO_ALLOWED_TOOLS = frozenset(
    {
        "create_ticket",
        "create_lead",
        "create_task",
        "create_draft",
        "reply_common",
        "classify_email",
        "read_email",
        "search_knowledge",
        "publish_calendar",
    }
)

R2_DIR_TRANSCRIPTS = "transcripts"
R2_DIR_ATTACHMENTS = "attachments"
R2_DIR_QUOTES = "quotes"
R2_DIR_REPORTS = "reports"
R2_DIR_HERMES = "hermes/outputs"
R2_DIR_BACKUPS = "backups/pg"

LANG_AR = "ar"
LANG_EN = "en"
DEFAULT_LANG = LANG_EN

ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS = "0123456789"
