"""Company digital-operations charter — client requirements as code.

This is the single source of truth for the role, domains, architecture and
the later-phase agents that are declared but not yet activated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CHARTER_VERSION = "1.0.0"

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

ACCESS_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("read_email", "auto", "خواندن و دسته‌بندی ایمیل"),
    ("classify_email", "auto", "خواندن و دسته‌بندی ایمیل"),
    ("reply_common", "auto", "پاسخ به سؤال‌های معمول طبق قوانین"),
    ("send_email", "approval", "ارسال ایمیل حساس یا مهم"),
    ("publish_calendar", "auto", "انتشار محتوای معمولی طبق تقویم"),
    ("publish_content", "approval", "انتشار حساس / خارج از تقویم"),
    ("change_price", "approval", "تغییر قیمت یا اطلاعات حساس سایت"),
    ("payment", "approval", "پرداخت، قرارداد و انتقال پول"),
    ("contract", "approval", "پرداخت، قرارداد و انتقال پول"),
    ("delete_data", "approval", "حذف اطلاعات یا دسترسی کاربران"),
    ("change_access", "approval", "حذف اطلاعات یا دسترسی کاربران"),
)


def system_prompt(*, language: str = "fa") -> str:
    """Return the manager-facing operating prompt injected into every agent."""
    body = ROLE_DEFINITION_FA if (language or "fa").lower().startswith("fa") else ROLE_DEFINITION_EN
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
        "role_fa": ROLE_DEFINITION_FA,
        "domains": [d.key for d in ACTIVE_DOMAINS],
        "agents": [d.agent for d in ACTIVE_DOMAINS],
        "future_agents": list(FUTURE_AGENTS),
        "building_blocks": list(BUILDING_BLOCKS),
        "access_matrix": [
            {"action": action, "mode": mode, "label": label}
            for action, mode, label in ACCESS_MATRIX
        ],
    }
