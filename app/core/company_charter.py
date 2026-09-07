"""Company digital-operations charter — client requirements as code.

v21 is the employer-facing product: one operations manager, specialist
agents, shared knowledge, HITL for money/legal/confidential/sensitive
publish. Not an autonomous company-builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CHARTER_VERSION = "2.1.0"
PRODUCT_VERSION = "21.0.0"

ROLE_DEFINITION_FA = (
    "تو مدیر عملیات دیجیتال شرکت من هستی. وظیفه‌ات این است که ایمیل، سایت، "
    "شبکه‌های اجتماعی و کارهای روزمره شرکت را مدیریت کنی، اطلاعات شرکت را بشناسی، "
    "کارها را پیگیری کنی، گزارش بدهی و هرجا نیاز به تصمیم مهم بود، از من تأیید بگیری. "
    "تو باید فعالیت‌ها را ثبت کنی، از اطلاعات محرمانه محافظت کنی و هیچ اقدام پرریسکی را "
    "بدون اجازه انجام ندهی. هدف تو این است که عملیات شرکت سریع‌تر، منظم‌تر و کم‌خطاتر "
    "انجام شود و مدیر بتواند روی تصمیم‌های مهم تمرکز کند."
)

ROLE_DEFINITION_EN = (
    "You are the company's digital operations manager. You handle email, the website, "
    "social media and day-to-day work, you know the company knowledge, you follow up, "
    "you report, and you ask the manager before any important decision. You log activity, "
    "protect confidential information, and never take a high-risk action without permission. "
    "Your goal is faster, more orderly, lower-error operations so the manager can focus on "
    "the decisions that matter."
)


@dataclass(frozen=True)
class Domain:
    key: str
    agent: str
    responsibilities: tuple[str, ...]
    phase: int


@dataclass(frozen=True)
class Phase:
    number: int
    title: str
    scope: str


ACTIVE_DOMAINS: tuple[Domain, ...] = (
    Domain(
        "email",
        "email_agent",
        (
            "read and classify inbound email",
            "auto-reply to common questions under policy",
            "draft important replies for manager approval",
            "follow up unanswered requests",
            "escalate finance, legal and confidential mail",
        ),
        1,
    ),
    Domain(
        "website",
        "website_agent",
        (
            "ingest contact forms as leads",
            "prepare page and product content",
            "report site issues",
            "hold price, legal and delete changes for approval",
        ),
        2,
    ),
    Domain(
        "social",
        "social_agent",
        (
            "plan the content calendar",
            "write captions and prepare posts/stories",
            "auto-publish ordinary calendar content",
            "reply to comments and DMs under policy",
            "report engagement",
        ),
        3,
    ),
    Domain(
        "sales",
        "sales_agent",
        (
            "first-line product and service answers",
            "register leads",
            "prepare quotes (approval-gated before send)",
            "track orders and hand off complex deals",
        ),
        4,
    ),
    Domain(
        "support",
        "support_agent",
        (
            "first-line customer requests",
            "open tickets",
            "follow up issues",
            "escalate complex or safety cases",
        ),
        4,
    ),
    Domain(
        "ops",
        "ops_agent",
        (
            "extract and track internal tasks",
            "reminders and team coordination",
            "daily and weekly manager reports",
            "connect information across domains",
        ),
        5,
    ),
)

FUTURE_AGENTS: tuple[str, ...] = (
    "accounting_agent",
    "hr_agent",
    "content_studio_agent",
    "project_agent",
)

BUILDING_BLOCKS: tuple[str, ...] = (
    "llm_brain",
    "tool_connectors",
    "company_knowledge_base",
    "deterministic_workflows",
    "rbac_and_hitl",
    "operational_reporting",
)

EXECUTION_PHASES: tuple[Phase, ...] = (
    Phase(1, "Email and knowledge", "Connect inbox plus the company knowledge base."),
    Phase(
        2, "Website and forms", "Ingest contact forms; prepare pages; gate price and legal edits."
    ),
    Phase(
        3,
        "Social and calendar",
        "Plan captions; auto-publish ordinary calendar posts; hold claims.",
    ),
    Phase(4, "CRM, sales and support", "Leads, quotes, tickets, first-line replies."),
    Phase(5, "Reporting and quality", "Daily/weekly reports, audit, advanced automation."),
)

# (action, mode, english label) — mode must match policy.py
ACCESS_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("read_email", "auto", "Read and classify email"),
    ("classify_email", "auto", "Read and classify email"),
    ("reply_common", "auto", "Answer common questions under rules"),
    ("create_lead", "auto", "Register a sales or website lead"),
    ("create_ticket", "auto", "Open a first-line support ticket"),
    ("create_task", "auto", "Register an internal follow-up task"),
    ("create_quote", "approval", "Prepare a quote — send only after manager approval"),
    ("send_email", "approval", "Send sensitive or important email"),
    ("publish_calendar", "auto", "Publish ordinary calendar content"),
    ("publish_content", "approval", "Sensitive or off-calendar publish"),
    ("change_price", "approval", "Change price or sensitive site data"),
    ("payment", "approval", "Payment, contract and money transfer"),
    ("contract", "approval", "Payment, contract and money transfer"),
    ("delete_data", "approval", "Delete data or change user access"),
    ("change_access", "approval", "Delete data or change user access"),
)

COMPARISON_AXES: tuple[tuple[str, str, str], ...] = (
    ("Who owns the company", "You. Code, data, keys, Railway.", "The platform. Sandbox company."),
    ("Money and contracts", "Never without a manager record.", "Often auto-executed."),
    ("Revenue share", "None. Your tenant, your margin.", "Subscription plus a cut of revenue/ads."),
    ("Knowledge", "Your catalog, FAQ, tone, prices.", "Generated landing + guessed research."),
    ("Audit", "Postgres ledger of every decision.", "Credits and task ticks."),
    ("Role of the human", "Manager of exceptions.", "Spectator of an autonomous loop."),
)


def system_prompt(*, language: str = "en") -> str:
    """Return the manager-facing operating prompt injected into every agent."""
    lang = (language or "en").lower()
    body = ROLE_DEFINITION_FA if lang.startswith("fa") else ROLE_DEFINITION_EN
    domains = "\n".join(
        f"- {d.key} → {d.agent}: " + "; ".join(d.responsibilities[:2]) for d in ACTIVE_DOMAINS
    )
    return (
        f"{body}\n\n"
        "Architecture: one central orchestrator coordinates specialist agents. "
        "All agents share the company knowledge base and report to the manager.\n"
        f"Active specialists:\n{domains}\n"
        "Never execute payment, contract, money transfer, price change, "
        "data deletion or access change without an explicit manager approval record."
    )


def domain_for_agent(agent: str) -> Domain | None:
    for domain in ACTIVE_DOMAINS:
        if domain.agent == agent or domain.key == agent:
            return domain
    return None


def is_future_agent(name: str) -> bool:
    return name.strip().lower() in FUTURE_AGENTS


def charter_snapshot() -> dict[str, Any]:
    return {
        "version": CHARTER_VERSION,
        "product_version": PRODUCT_VERSION,
        "role_en": ROLE_DEFINITION_EN,
        "role_fa": ROLE_DEFINITION_FA,
        "domains": [d.key for d in ACTIVE_DOMAINS],
        "agents": [d.agent for d in ACTIVE_DOMAINS],
        "future_agents": list(FUTURE_AGENTS),
        "building_blocks": list(BUILDING_BLOCKS),
        "phases": [
            {"number": p.number, "title": p.title, "scope": p.scope} for p in EXECUTION_PHASES
        ],
        "access_matrix": [
            {"action": action, "mode": mode, "label": label}
            for action, mode, label in ACCESS_MATRIX
        ],
        "comparison": [
            # "zenovix" is the 1.6.0 key; "kia" kept one release for old readers.
            {"axis": axis, "zenovix": ours, "kia": ours, "autonomous_saas": other}
            for axis, ours, other in COMPARISON_AXES
        ],
    }
