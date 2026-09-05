"""Orchestrator — classification, safety gating, and main incoming-message handler.

Extended with:
  - Fleet integration: complex queries routed to team mode
  - Memory extraction: after drafting, schedule long-term memory extraction
  - Prompt cache: stable-prefix optimization for LLM calls
  - Guard integration: input/output injection protection
  - Honest admission: admit uncertainty instead of hallucinating
  - Source citation: cite document sources for RAG-based responses
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.config import get_config
from app.constants import (
    LANG_AR,
    LANG_EN,
    SKILL_ANALYTICS,
    SKILL_CUSTOMER,
    SKILL_EMAIL,
    SKILL_KNOWLEDGE,
    SKILL_OPS,
    SKILL_ORCHESTRATOR,
    SKILL_SALES,
    SKILL_SOCIAL,
    SKILL_SUPPORT,
    SKILL_WEBSITE,
)
from app.core import guard
from app.logging_setup import get_logger

if TYPE_CHECKING:
    from app.channels.base import IncomingMessage

log = get_logger("app.core.orchestrator")

MAX_CLASSIFY_ATTEMPTS = 2

SAFETY_MARKERS: frozenset[str] = frozenset(
    {
        "حريق",
        "تسرب",
        "انفجار",
        "اختناق",
        "سقوط",
        "نزيف",
        "إصابة",
        "هاتف الطوارئ",
        "medical",
        "accident",
        "fire",
        "leak",
        "explosion",
        "spill",
        "injury",
        "emergency",
        "hospital",
    }
)

INCIDENT_VERBS: frozenset[str] = frozenset(
    {
        "يحدث",
        "حدث",
        "هب",
        "اشتعل",
        "انفجر",
        "تسرب",
        "انسكب",
        "انقلب",
        "انهار",
    }
)

SAFETY_CERTAIN: float = 0.85

AVAILABILITY_MARKERS: frozenset[str] = frozenset(
    {
        "متاح",
        "متوفر",
        "غير متاح",
        "غير متوفر",
        "نفدت",
        "back in stock",
        "available",
        "unavailable",
        "out of stock",
    }
)

HONEST_ADMISSION_FA = "متأسفانه در حال حاضر اطلاعات کافی برای پاسخ دقیق به این سوال در دسترس نیست. می‌توانم در موارد زیر به شما کمک کنم:"
HONEST_ADMISSION_AR = "أعتذر، لا تتوفر لدي معلومات كافية للإجابة على هذا السؤال بدقة. يمكنني مساعدتك في:"
HONEST_ADMISSION_EN = (
    "I'm sorry, I don't have enough information to answer this accurately. I can help you with:"
)

SOURCE_CITATION_FA = "\n\n📎 منبع: {source}"
SOURCE_CITATION_AR = "\n\n📎 المصدر: {source}"
SOURCE_CITATION_EN = "\n\n📎 Source: {source}"


@dataclass
class Classification:
    intent: str
    skill: str
    confidence: float
    language: str = LANG_EN
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "skill": self.skill,
            "confidence": self.confidence,
            "language": self.language,
        }


CLARIFICATION_FA = "متأسفانه متوجه درخواست شما نشدم. لطفاً سوال یا نیاز خود را دقیق‌تر بیان فرمایید."
CLARIFICATION_AR = "عذراً، لم أتمكن من فهم طلبك بالكامل. هل يمكنك إعادة صياغة طلبك أو توضيح ما تحتاجه؟"
_CLARIFICATION_EN = (
    "Sorry, I couldn't fully understand your request. "
    "Could you please rephrase or clarify what you need?"
)

GUARD_REJECTED_FA = "⚠️ پیام ارسالی به دلیل محتوای غیرمجاز پردازش نشد. لطفاً در صورت داشتن سوال مرتبط، درخواست خود را مجدداً ارسال کنید."
GUARD_REJECTED_AR = (
    "⚠️ تم رفض هذه الرسالة لأنها تحتوي على محتوى غير مسموح به. "
    "إذا كان لديك سؤال حقيقي، يرجى إعادة صياغة الرسالة."
)
GUARD_REJECTED_EN = (
    "⚠️ This message was rejected because it contains disallowed content. "
    "If you have a genuine question, please rephrase it."
)

NO_KNOWLEDGE_FA = (
    "متأسفانه اطلاعات کافی در این زمینه در پایگاه دانش موجود نیست. "
    "آیا می‌توانم در مورد محصولات یا خدمات دیگر به شما کمک کنم؟"
)
NO_KNOWLEDGE_AR = (
    "عذراً، لا تتوفر لدي معلومات كافية حول هذا الموضوع في قاعدة بياناتنا. "
    "هل يمكنني مساعدتك في شيء آخر يتعلق بمنتجاتنا أو خدماتنا؟"
)
NO_KNOWLEDGE_EN = (
    "I'm sorry, I don't have enough information about this topic in our database. "
    "Can I help you with something else related to our products or services?"
)


def validate_classification(raw: dict[str, Any]) -> Classification | None:
    intent = str(raw.get("intent", "")).strip().lower()
    skill = str(raw.get("skill", "")).strip().lower()
    confidence = float(raw.get("confidence", 0.0))
    language = str(raw.get("language", LANG_EN)).strip().lower()

    if not intent or not skill:
        return None
    if confidence < 0.0 or confidence > 1.0:
        confidence = 0.5
    _VALID_LANGS = {"ar", "en", "es", "fr", "de", "it", "pt", "tr", "ru", "zh", "ja", "ko", "hi", "nl", "uk", "sv", "id", "ms", "vi", "he", "fa"}
    if language not in _VALID_LANGS:
        language = LANG_EN

    skill_map: dict[str, str] = {
        "knowledge": SKILL_KNOWLEDGE,
        "customer": SKILL_CUSTOMER,
        "sales": SKILL_SALES,
        "support": SKILL_SUPPORT,
        "analytics": SKILL_ANALYTICS,
        "email": SKILL_EMAIL,
        "website": SKILL_WEBSITE,
        "social": SKILL_SOCIAL,
        "ops": SKILL_OPS,
        "greeting": SKILL_ORCHESTRATOR,
        "general": SKILL_ORCHESTRATOR,
    }
    resolved_skill = skill_map.get(skill, skill)

    return Classification(
        intent=intent,
        skill=resolved_skill,
        confidence=confidence,
        language=language,
        raw=raw,
    )


async def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    brace_start = text.find("{")
    if brace_start == -1:
        return None

    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[brace_start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _is_safety(text: str) -> bool:
    lower = text.lower()
    for marker in SAFETY_MARKERS:
        if marker in lower:
            return True
    for verb in INCIDENT_VERBS:
        if verb in lower:
            return True
    return False


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _get_lang(message: IncomingMessage) -> str:
    """Resolve the best language code for menu/command responses (default 'en')."""
    raw = str(getattr(message, "metadata", {}).get("language", "en") or "en").lower().strip()
    return (
        raw
        if raw
        in {
            "en",
            "fa",
            "ar",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "tr",
            "ru",
            "zh",
            "ja",
            "ko",
            "hi",
            "nl",
            "uk",
            "sv",
            "id",
            "ms",
            "vi",
            "he",
        }
        else "en"
    )


def _has_rag_sources(skill_result: dict[str, Any]) -> bool:
    """Check if the skill result contains RAG/document source metadata."""
    sources = skill_result.get("sources", [])
    if sources:
        return True
    metadata = skill_result.get("metadata", {})
    if metadata.get("source") or metadata.get("rag_results"):
        return True
    return False


def _extract_source_label(skill_result: dict[str, Any]) -> str | None:
    """Extract a human-readable source label from skill result metadata."""
    sources = skill_result.get("sources", [])
    if sources:
        first = sources[0] if isinstance(sources[0], str) else str(sources[0])
        return first

    metadata = skill_result.get("metadata", {})
    source = metadata.get("source", "")
    if source:
        return source

    rag_results = metadata.get("rag_results", [])
    if rag_results and isinstance(rag_results, list):
        first = rag_results[0]
        if isinstance(first, dict):
            return first.get("source", first.get("title", ""))
        return str(first)

    return None


def _append_source_citation(text: str, source: str, language: str) -> str:
    """Append a source citation to the draft text if not already present."""
    if not source:
        return text
    if source in text:
        return text
    lang = (language or "en").lower().strip()
    if lang == "fa":
        template = SOURCE_CITATION_FA
    elif lang == "ar":
        template = SOURCE_CITATION_AR
    else:
        template = SOURCE_CITATION_EN
    return text + template.format(source=source)


def _build_honest_admission(
    language: str,
    skill: str = "",
) -> str:
    """Build an honest admission response when the system cannot answer.

    Instead of hallucinating, the system admits its limitation and offers
    alternative paths for the user.
    """
    lang = (language or "en").lower().strip()

    if lang == "fa":
        base = HONEST_ADMISSION_FA
        capabilities = []
        if skill != SKILL_KNOWLEDGE:
            capabilities.append("- اطلاعات فنی و مشخصات محصولات (knowledge)")
        if skill != SKILL_CUSTOMER:
            capabilities.append("- امور حساب کاربری و سفارش‌ها (customer)")
        if skill != SKILL_SALES:
            capabilities.append("- استعلام قیمت و پیش‌فاکتور (sales)")
        if skill != SKILL_SUPPORT:
            capabilities.append("- پشتیبانی فنی و حل مشکلات (support)")
        capabilities.append("- سوالات عمومی پیرامون خدمات")
        return base + "\n" + "\n".join(capabilities)

    if lang == "ar":
        base = HONEST_ADMISSION_AR
        capabilities = []
        if skill != SKILL_KNOWLEDGE:
            capabilities.append("- معلومات المنتجات والمواصفات الفنية (knowledge)")
        if skill != SKILL_CUSTOMER:
            capabilities.append("- استفسارات الحسابات والفواتير (customer)")
        if skill != SKILL_SALES:
            capabilities.append("- الأسعار والعروض التجارية (sales)")
        if skill != SKILL_SUPPORT:
            capabilities.append("- الدعم الفني وحل المشكلات (support)")
        capabilities.append("- أسئلة عامة حول خدماتنا")
        return base + "\n" + "\n".join(capabilities)

    base = HONEST_ADMISSION_EN
    capabilities = []
    if skill != SKILL_KNOWLEDGE:
        capabilities.append("- Product information and technical specs (knowledge)")
    if skill != SKILL_CUSTOMER:
        capabilities.append("- Account inquiries and billing (customer)")
    if skill != SKILL_SALES:
        capabilities.append("- Pricing and commercial offers (sales)")
    if skill != SKILL_SUPPORT:
        capabilities.append("- Technical support and troubleshooting (support)")
    capabilities.append("- General questions about our services")
    return base + "\n" + "\n".join(capabilities)


def _is_honest_admission_response(text: str) -> bool:
    """Detect if a draft is already an honest admission (avoid double-wrapping)."""
    markers = [
        "أعتذر",
        "لا تتوفر لدي",
        "I'm sorry",
        "I don't have enough",
        "متأسفانه",
        "اطلاعات کافی",
    ]
    return any(m in text for m in markers)


async def classify(
    text: str,
    llm_client: Any,
    *,
    conversation_history: list[dict[str, str]] | None = None,
) -> Classification | None:
    config = get_config()
    system_prompt = (
        "You are an intelligent message classifier for an automated AI business operations platform.\n"
        "Return ONLY JSON in the following format:\n"
        '{"intent": "<goal>", "skill": "<skill_name>", "confidence": <0.0-1.0>, "language": "<lang_code>"}\n\n'
        "Available skills:\n"
        "- knowledge_agent: Product and technical specification questions, FAQ, general info\n"
        "- customer_agent: Account and customer inquiries, profile, orders\n"
        "- sales_agent: Price requests, quotes, discounts, commercial offers\n"
        "- support_agent: Technical support and troubleshooting, issue reporting\n"
        "- analytics_agent: Reports and analytics, business metrics\n"
        "- email_agent: Inbox triage, common replies, drafts, follow-up\n"
        "- website_agent: Contact forms, CMS, product pages\n"
        "- social_agent: Content calendar, captions, comments\n"
        "- ops_agent: Internal tasks, reminders, manager reports\n"
        "- orchestrator: General greeting, chat, or small talk\n\n"
        "Detect the language accurately: 'en' for English, 'fa' for Persian, 'ar' for Arabic, "
        "'es' for Spanish, 'fr' for French, 'de' for German, 'tr' for Turkish, 'ru' for Russian, etc. "
        "Default to 'en' if uncertain."
    )

    user_prompt = f"Message: {text}"
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_lines.append(f"[{role}] {content}")
        user_prompt = (
            "Previous conversation:\n" + "\n".join(history_lines) + f"\n\nCurrent message: {text}"
        )

    for attempt in range(MAX_CLASSIFY_ATTEMPTS):
        raw_text = await llm_client.complete(
            system=system_prompt,
            user=user_prompt,
            tier="fast",
            temperature=0.1,
            json_mode=True,
            max_tokens=200,
            purpose="classification",
        )
        parsed = await _extract_json(raw_text)
        if parsed is not None:
            classification = validate_classification(parsed)
            if classification is not None:
                log.info(
                    "classification ok",
                    extra={
                        "action": "classify",
                        "intent": classification.intent,
                        "skill": classification.skill,
                        "attempt": attempt + 1,
                    },
                )
                return classification

    log.warning(
        "classification failed after %d attempts, trying heuristic fallback",
        MAX_CLASSIFY_ATTEMPTS,
        extra={"action": "classify", "attempts": MAX_CLASSIFY_ATTEMPTS},
    )

    try:
        from app.core.intent import heuristic_intent

        intent = heuristic_intent(text)
        skill_map = {
            "sales": SKILL_SALES,
            "support": SKILL_SUPPORT,
            "knowledge": SKILL_KNOWLEDGE,
            "analytics": SKILL_ANALYTICS,
        }
        skill = skill_map.get(intent, SKILL_ORCHESTRATOR)
        classification = Classification(
            intent=intent,
            skill=skill,
            confidence=0.6,
            language=LANG_EN,
            raw={"source": "heuristic", "intent": intent},
        )
        log.info(
            "heuristic fallback used",
            extra={"action": "classify.heuristic", "intent": intent, "skill": skill},
        )
        return classification
    except Exception as exc:
        log.debug(
            "heuristic fallback failed",
            extra={"action": "classify.heuristic_error", "error": str(exc)},
        )
        return None


async def _queue_draft(
    *,
    message: IncomingMessage,
    classification: Classification,
    draft_text: str,
    skill_name: str,
    services: dict[str, Any],
    conversation_id: str,
    customer_id: str,
) -> str | None:
    from app.constants import MUTATING_TOOLS

    needs_hitl = False
    for tool_name in MUTATING_TOOLS:
        if tool_name in draft_text.lower():
            needs_hitl = True
            break

    pg = services.get("pg")
    if pg is None:
        log.error("pg pool unavailable for draft queue", extra={"action": "queue_draft"})
        return None

    from app.core.repository import create_approval

    approval_id = await create_approval(
        pg=pg,
        conversation_id=conversation_id,
        customer_id=customer_id,
        skill=skill_name,
        intent=classification.intent,
        draft_text=draft_text,
        confidence=classification.confidence,
        needs_hitl=needs_hitl,
    )

    log.info(
        "draft queued",
        extra={
            "action": "queue_draft",
            "approval_id": approval_id,
            "needs_hitl": needs_hitl,
            "skill": skill_name,
        },
    )
    return approval_id


async def _send_template(
    *,
    message: IncomingMessage,
    template_key: str,
    services: dict[str, Any],
    **kwargs: Any,
) -> None:
    from app.channels.base import normalize_text
    from app.core.translations import get_text

    lang = _get_lang(message)
    config = get_config()

    if template_key == "safety_emergency":
        if lang == "fa":
            text = (
                "⚠️ پیام اضطراری در درخواست شما تشخیص داده شد.\n"
                "لطفاً بلافاصله با بخش پشتیبانی تماس بگیرید:\n"
                f"📞 {config.tenant.support_contact}\n"
                "یا با فوریت‌های امدادی تماس حاصل فرمایید."
            )
        elif lang == "ar":
            text = (
                "⚠️ تم اكتشاف حالة طوارئ في رسالتك.\n"
                "يرجى التواصل فوراً مع:\n"
                f"📞 {config.tenant.support_contact}\n"
                "أو الاتصال بخدمات الطوارئ."
            )
        else:
            text = (
                "⚠️ Emergency keyword detected in your message.\n"
                "Please contact immediately:\n"
                f"📞 {config.tenant.support_contact}\n"
                "Or call local emergency services."
            )
    elif template_key == "processing":
        if lang == "fa":
            text = "در حال پردازش درخواست شما، لطفاً شکیبا باشید..."
        elif lang == "ar":
            text = "جاري معالجة طلبك، يرجى الانتظار..."
        else:
            text = "Processing your request, please wait..."
    elif template_key == "clarification":
        text = get_text(lang, "clarification")
    elif template_key == "guard_rejected":
        text = get_text(lang, "guard_rejected")
    else:
        text = get_text(lang, template_key, **kwargs)

    if not text:
        text = get_text("en", template_key, **kwargs) or template_key

    text = normalize_text(text)

    registry = services.get("registry")
    if registry is None:
        return
    adapter = registry.get(message.channel)
    if adapter is None:
        return

    await adapter.send(
        recipient_id=message.sender_id,
        text=text,
        reply_to_ref=None if message.metadata.get("is_callback") else message.external_ref,
    )


async def _send_main_menu(message: IncomingMessage, services: dict[str, Any]) -> None:
    from app.core.translations import get_text

    lang = _get_lang(message)
    text = get_text(lang, "welcome")

    registry = services.get("registry")
    if not registry:
        return
    adapter = registry.get(message.channel)
    if not adapter:
        return

    if message.channel == "telegram":
        await _send_tg_with_keyboard(
            adapter=adapter,
            chat_id=message.sender_id,
            text=text,
            reply_to_ref=None if message.metadata.get("is_callback") else message.external_ref,
            lang=lang,
        )
    else:
        reply_ref = None if message.metadata.get("is_callback") else message.external_ref
        await adapter.send(
            recipient_id=message.sender_id,
            text=text,
            reply_to_ref=reply_ref,
        )


async def _send_help(message: IncomingMessage, services: dict[str, Any]) -> None:
    from app.core.translations import get_text

    lang = _get_lang(message)
    text = get_text(lang, "help")
    await _send_text(message=message, text=text, services=services)


async def _send_language_picker(message: IncomingMessage, services: dict[str, Any]) -> None:
    from app.core.languages import SUPPORTED_MENU_LANGUAGES

    registry = services.get("registry")
    if not registry:
        return
    adapter = registry.get(message.channel)
    if not adapter:
        return

    if message.channel != "telegram":
        await _send_main_menu(message, services)
        return

    import aiogram.types as tg

    flag_map = {
        "en": "🇬🇧",
        "fa": "🇮🇷",
        "ar": "🇸🇦",
        "es": "🇪🇸",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "it": "🇮🇹",
        "pt": "🇵🇹",
        "tr": "🇹🇷",
        "ru": "🇷🇺",
        "zh": "🇨🇳",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
        "hi": "🇮🇳",
        "nl": "🇳🇱",
        "uk": "🇺🇦",
        "sv": "🇸🇪",
        "id": "🇮🇩",
        "ms": "🇲🇾",
        "vi": "🇻🇳",
        "he": "🇮🇱",
    }

    buttons = []
    row = []
    for lang in SUPPORTED_MENU_LANGUAGES:
        flag = flag_map.get(lang.code, "🌐")
        text = f"{flag} {lang.native_name}"
        row.append(tg.InlineKeyboardButton(text=text, callback_data=f"lang_{lang.code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    keyboard = tg.InlineKeyboardMarkup(inline_keyboard=buttons)

    from app.core.translations import get_text

    user_lang = _get_lang(message)
    picker_text = get_text(user_lang, "lang_picker") or get_text("en", "lang_picker")

    try:
        await adapter._bot.send_message(
            chat_id=message.sender_id,
            text=picker_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        log.warning(
            "language_picker_send_failed", extra={"action": "send_lang_picker", "error": str(exc)}
        )
        await adapter.send(recipient_id=message.sender_id, text=picker_text)


async def _send_tg_with_keyboard(
    adapter: Any,
    chat_id: str,
    text: str,
    reply_to_ref: str | None = None,
    lang: str = "en",
) -> None:
    import aiogram.types as tg
    from app.core.translations import get_button_text

    keyboard = tg.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                tg.InlineKeyboardButton(text=get_button_text(lang, "prices"), callback_data="menu_prices"),
            ],
            [
                tg.InlineKeyboardButton(text=get_button_text(lang, "quote"), callback_data="menu_quote"),
                tg.InlineKeyboardButton(text=get_button_text(lang, "support"), callback_data="menu_support"),
            ],
            [
                tg.InlineKeyboardButton(text=get_button_text(lang, "contact"), callback_data="menu_contact"),
                tg.InlineKeyboardButton(text=get_button_text(lang, "help"), callback_data="menu_help"),
            ],
            [
                tg.InlineKeyboardButton(text=get_button_text(lang, "lang"), callback_data="menu_lang"),
            ],
        ]
    )

    try:
        await adapter._bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        log.warning("keyboard_send_failed", extra={"action": "send_keyboard", "error": str(exc)})
        await adapter.send(recipient_id=chat_id, text=text)


def _build_contact_text(lang: str = "en") -> str:
    config = get_config()
    email = config.tenant.support_contact or "support@example.com"
    from app.core.translations import get_text
    return get_text(lang, "contact", email=email)


async def _handle_callback(message: IncomingMessage, data: str, services: dict[str, Any]) -> None:
    responses = {
        "menu_prices": (
            "💰 <b>Products & Pricing</b>\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
            "Send a product name or SKU code to search:\n\n"
            "• <code>PET-001</code> — by SKU code\n"
            "• <b>base lubricant oil</b> — by name\n"
            "• <b>drilling fluid</b> — by category\n\n"
            "Or describe what you need and I'll help you find it."
        ),
        "menu_support": (
            "ðŸ› ï¸ <b>Technical Support</b>\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
            "Describe your issue and I'll create\na support ticket for you.\n\n"
            "Include:\n"
            "• Product name or SKU\n"
            "• Problem description\n"
            "• Urgency level\n\n"
            "🚨 For emergencies, type <b>emergency</b>"
        ),
        "menu_quote": (
            "📋 <b>Request a Quote</b>\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
            "Send the following details:\n\n"
            "1ï¸âƒ£ Product name or SKU\n"
            "2ï¸âƒ£ Quantity needed\n"
            "3ï¸âƒ£ Delivery location (optional)\n"
            "4ï¸âƒ£ Timeline\n\n"
            "I'll prepare a quote for you."
        ),
        "menu_contact": _build_contact_text(),
        "menu_help": HELP_EN,
        "lang_en": "ðŸŒ Language switched to English. Type /start for the menu.",
        "lang_ar": "ðŸŒ Language switched to Arabic. Type /start for the menu.",
    }

    text = responses.get(data, "Unknown command")
    await _send_text(message=message, text=text, services=services)


async def _send_text(
    *,
    message: IncomingMessage,
    text: str,
    services: dict[str, Any],
) -> None:
    """Send raw text to the user via the channel adapter."""
    from app.channels.base import normalize_text

    text = normalize_text(text)
    registry = services.get("registry")
    if registry is None:
        return
    adapter = registry.get(message.channel)
    if adapter is None:
        return

    await adapter.send(
        recipient_id=message.sender_id,
        text=text,
        reply_to_ref=None if message.metadata.get("is_callback") else message.external_ref,
    )


async def _escalate(
    *,
    message: IncomingMessage,
    classification: Classification,
    draft_text: str,
    services: dict[str, Any],
    conversation_id: str,
    customer_id: str,
    reason: str = "low_confidence",
) -> str | None:
    pg = services.get("pg")
    if pg is None:
        return None

    from app.core.repository import create_approval

    approval_id = await create_approval(
        pg=pg,
        conversation_id=conversation_id,
        customer_id=customer_id,
        skill=classification.skill,
        intent=classification.intent,
        draft_text=draft_text,
        confidence=classification.confidence,
        needs_hitl=True,
    )

    redis = services.get("redis")
    if redis is not None:
        import time as _time

        meta_key = f"hitl:meta:{approval_id}"
        await redis.hset(
            meta_key,
            mapping={
                "status": "escalated",
                "reason": reason,
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "skill": classification.skill,
                "created_at": str(int(_time.time())),
            },
        )
        await redis.expire(meta_key, 86400)

    config = get_config()
    if config.hitl.ping_telegram:
        admin_ids = config.channels.telegram_admin_ids
        registry = services.get("registry")
        if registry:
            adapter = registry.get("telegram")
            if adapter:
                admin_text = (
                    f"🔔 Escalation @{message.sender_name} ({message.channel})\n"
                    f"Skill: {classification.skill}\n"
                    f"Intent: {classification.intent}\n"
                    f"Confidence: {classification.confidence:.0%}\n"
                    f"Reason: {reason}\n"
                    f"Message: {message.text[:200]}"
                )
                for admin_id in admin_ids:
                    await adapter.send(recipient_id=admin_id, text=admin_text)

    log.info(
        "escalated to human",
        extra={"action": "escalate", "approval_id": approval_id, "reason": reason},
    )
    return approval_id


def _apply_guard_output(draft_text: str, language: str) -> str:
    """Run output guard check + sanitization on a draft reply.

    Returns the cleaned text. Logs guard actions.
    """
    is_safe, reason = guard.barresi_khorooji(draft_text)
    if not is_safe:
        cleaned, removed = guard.paksazi_khorooji(draft_text)
        log.warning(
            "guard output sanitized",
            extra={"action": "guard_output", "reason": reason, "sentences_removed": removed},
        )
        draft_text = cleaned

    return draft_text


async def handle_incoming(
    message: IncomingMessage,
    services: dict[str, Any],
) -> dict[str, Any]:
    t0 = time.perf_counter()
    config = get_config()
    result: dict[str, Any] = {
        "conversation_id": message.conversation_id,
        "channel": message.channel,
        "handled": False,
        "classification": None,
        "approval_id": None,
    }

    text = message.text.strip()
    if not text and not message.attachments:
        return result

    # --- Send typing indicator ---
    if message.channel == "telegram" and message.sender_id:
        registry = services.get("registry")
        if registry:
            adapter = registry.get("telegram")
            if adapter and hasattr(adapter, "send_chat_action"):
                await adapter.send_chat_action(message.sender_id, "typing")

    # --- Load saved language preference from Redis ---
    if message.sender_id and not message.metadata.get("language"):
        redis = services.get("redis")
        if redis:
            try:
                saved_lang = await redis.get(f"lang:{message.sender_id}")
                if saved_lang:
                    message.metadata["language"] = saved_lang.decode() if isinstance(saved_lang, bytes) else str(saved_lang)
            except Exception:
                pass

    # --- Command handling ---
    cmd = text.lower().replace("@", "").strip("/")

    # Also check metadata for callback_data (inline keyboard button press)
    cb_data = (
        message.metadata.get("callback_data", "")
        if hasattr(message, "metadata") and isinstance(message.metadata, dict)
        else ""
    )
    if cb_data and not cmd:
        cmd = cb_data
    if cb_data:
        cb_id = message.metadata.get("callback_query_id", "")
        if cb_id and message.channel == "telegram":
            registry = services.get("registry")
            if registry:
                adapter = registry.get("telegram")
                if adapter and hasattr(adapter, "answer_callback_query"):
                    await adapter.answer_callback_query(cb_id, "✅")
    if cmd in ("start", "start@Kia-Agentbot", "menu"):
        await _send_language_picker(message, services)
        result["handled"] = True
        return result

    if cmd in ("help", "مساعدة", "المساعدة"):
        await _send_help(message, services)
        result["handled"] = True
        return result

    if cmd in ("prices", "pricing", "menu_prices", "الأسعار", "قیمت", "تسعير"):
        from app.core.translations import get_text

        await _send_text(
            message=message,
            text=get_text(_get_lang(message), "pricing"),
            services=services,
        )
        result["handled"] = True
        return result

    if cmd in ("support", "الدعم", "menu_support", "پشتیبانی", "تcket"):
        from app.core.translations import get_text

        await _send_text(
            message=message,
            text=get_text(_get_lang(message), "support"),
            services=services,
        )
        result["handled"] = True
        return result

    if cmd in ("contact", "تواصل", "اتصال", "اتصال بنا", "menu_contact"):
        from app.core.translations import get_text

        email = get_config().tenant.support_contact or "support@example.com"
        await _send_text(
            message=message,
            text=get_text(_get_lang(message), "contact", email=email),
            services=services,
        )
        result["handled"] = True
        return result

    if cmd in ("menu_quote", "quote", "عرض_سعر"):
        from app.core.translations import get_text

        await _send_text(
            message=message,
            text=get_text(_get_lang(message), "quote"),
            services=services,
        )
        result["handled"] = True
        return result

    if cmd in ("menu_help",):
        await _send_help(message, services)
        result["handled"] = True
        return result

    if cmd in ("lang", "language", "languages", "زبان", "اللغة", "menu_lang"):
        await _send_language_picker(message, services)
        result["handled"] = True
        return result

    if cmd.startswith("lang_"):
        lang_code = cmd.replace("lang_", "").strip().lower()
        message.metadata["language"] = lang_code
        redis = services.get("redis")
        if redis and message.sender_id:
            try:
                await redis.set(f"lang:{message.sender_id}", lang_code, ex=86400 * 90)
            except Exception:
                pass
        pg = services.get("pg")
        if pg and message.sender_id:
            try:
                await pg.execute(
                    "UPDATE customers SET preferred_language = $1 WHERE telegram_id = $2 OR external_id = $2",
                    lang_code,
                    str(message.sender_id),
                )
            except Exception:
                pass
        await _send_main_menu(message, services)
        result["handled"] = True
        return result

    if cmd in ("reminders", "یادآوری", "تذکیر"):
        await _send_reminders_list(message, services)
        result["handled"] = True
        return result

    if cmd in ("today", "today_schedule", "برنامه_امروز"):
        await _send_today_schedule(message, services)
        result["handled"] = True
        return result

    if cmd.startswith("remind_"):
        parts = cmd.split("_", 2)
        if len(parts) >= 3:
            minutes = int(parts[1]) if parts[1].isdigit() else 60
            minutes = max(1, min(minutes, 43200))
            title = parts[2] if len(parts) > 2 else "Reminder"
            await _create_quick_reminder(message, title, minutes, services)
            result["handled"] = True
            return result

    if cmd in ("schedule", "زمانبندی"):
        await _send_text(
            message=message,
            text=(
                "📅 <b>Content Schedule</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "To schedule a post, send:\n"
                "/schedule_post [platform] [time] [caption]\n\n"
                "Platforms: instagram, twitter\n"
                "Time format: YYYY-MM-DD HH:MM\n"
                "Example: /schedule_post instagram 2025-06-15 14:00 New product launch!"
            ),
            services=services,
        )
        result["handled"] = True
        return result

    if cmd in ("content_plan", "content-plan", "برنامه_محتوا"):
        await _send_content_plan(message, services)
        result["handled"] = True
        return result

    if cmd in ("pages", "صفحات"):
        await _send_pages_list(message, services)
        result["handled"] = True
        return result

    if cmd in ("team", "تیم"):
        await _send_team_overview(message, services)
        result["handled"] = True
        return result

    # --- If user language not explicitly set, auto-detect and persist ---
    if not message.metadata.get("language") and text:
        from app.core.languages import detect_language
        detected_lang = detect_language(text)
        message.metadata["language"] = detected_lang
        redis = services.get("redis")
        if redis and message.sender_id:
            try:
                await redis.set(f"lang:{message.sender_id}", detected_lang, ex=86400 * 90)
            except Exception:
                pass

    # --- Layer 1: input guard ---
    is_safe, reason = guard.barresi_vorodi(text)
    if not is_safe:
        log.warning(
            "input guard rejected",
            extra={"action": "handle_incoming", "guard_reason": reason},
        )
        language = message.metadata.get("language", LANG_EN)
        if language == "fa":
            rejection_msg = GUARD_REJECTED_FA
        elif language == "ar":
            rejection_msg = GUARD_REJECTED_AR
        else:
            rejection_msg = GUARD_REJECTED_EN
        await _send_text(message=message, text=rejection_msg, services=services)
        result["handled"] = True
        result["guard_rejected"] = True
        return result

    if _is_safety(text):
        await _send_template(
            message=message,
            template_key="safety_emergency",
            services=services,
        )
        result["handled"] = True
        result["classification"] = Classification(
            intent="safety_emergency",
            skill=SKILL_SUPPORT,
            confidence=1.0,
            language=_get_lang(message),
        ).as_dict()
        log.warning(
            "safety message detected",
            extra={"action": "handle_incoming", "conversation_id": message.conversation_id},
        )
        return result

    llm_client = services.get("llm")
    if llm_client is None:
        log.error("llm client unavailable", extra={"action": "handle_incoming"})
        return result

    conversation_history = message.metadata.get("conversation_history", [])
    classification = await classify(
        text=text,
        llm_client=llm_client,
        conversation_history=conversation_history,
    )

    if classification is None:
        await _send_template(
            message=message,
            template_key="clarification",
            services=services,
        )
        result["handled"] = True
        return result

    result["classification"] = classification.as_dict()

    # Override classification language with user's saved preference
    user_lang = message.metadata.get("language")
    if user_lang:
        classification.language = user_lang

    if classification.confidence < SAFETY_CERTAIN and classification.skill != SKILL_ORCHESTRATOR:
        await _send_template(
            message=message,
            template_key="processing",
            services=services,
        )
        approval_id = await _escalate(
            message=message,
            classification=classification,
            draft_text="",
            services=services,
            conversation_id=message.conversation_id,
            customer_id=message.metadata.get("customer_id", ""),
            reason="low_confidence",
        )
        result["approval_id"] = approval_id
        result["handled"] = True
        return result

    fleet_client = services.get("fleet")
    if fleet_client is not None:
        try:
            llm_svc = services.get("llm")
            atlas_route = await fleet_client.atlas_route(
                text, bool(conversation_history), llm=llm_svc
            )
            if atlas_route.get("mode") == "team":
                log.info(
                    "fleet team mode triggered",
                    extra={"action": "handle_incoming", "roles": atlas_route.get("roles", [])},
                )

                async def _status_cb(msg: str) -> None:
                    log.debug("fleet status", extra={"action": "fleet_status", "msg": msg})

                fleet_answer, fleet_meta = await fleet_client.run_fleet(
                    text,
                    user_id=0,
                    on_status=_status_cb,
                    llm=llm_svc,
                )
                if fleet_answer:
                    draft_text = fleet_answer
                    tools_called: list[str] = []
                    result["fleet"] = fleet_meta
                    from app.core.postprocess import run as postprocess_run

                    post_result = postprocess_run(draft_text, config=config)
                    if post_result.text != draft_text:
                        draft_text = post_result.text

                    draft_text = _apply_guard_output(draft_text, classification.language)

                    has_sources = (
                        _has_rag_sources(fleet_meta) if isinstance(fleet_meta, dict) else False
                    )
                    if has_sources:
                        source_label = (
                            _extract_source_label(fleet_meta)
                            if isinstance(fleet_meta, dict)
                            else None
                        )
                        if source_label:
                            draft_text = _append_source_citation(
                                draft_text,
                                source_label,
                                classification.language,
                            )

                    registry = services.get("registry")
                    if registry:
                        adapter = registry.get(message.channel)
                        if adapter:
                            from app.channels.base import normalize_text

                            await adapter.send(
                                recipient_id=message.sender_id,
                                text=normalize_text(draft_text),
                                reply_to_ref=None
                                if message.metadata.get("is_callback")
                                else message.external_ref,
                            )

                    result["handled"] = True
                    _schedule_memory_extraction(
                        services,
                        message,
                        classification,
                        draft_text,
                    )
                    log.info(
                        "incoming handled via fleet",
                        extra={
                            "action": "handle_incoming",
                            "conversation_id": message.conversation_id,
                            "skill": classification.skill,
                            "mode": "team",
                            "latency_ms": _elapsed_ms(t0),
                        },
                    )
                    return result
        except Exception as exc:
            log.warning(
                "fleet routing failed, falling back to skill",
                extra={"action": "handle_incoming", "error": str(exc)},
            )

    hermes_client = services.get("hermes")
    if hermes_client is None:
        log.error("hermes client unavailable", extra={"action": "handle_incoming"})
        await _send_template(
            message=message,
            template_key="clarification",
            services=services,
        )
        result["handled"] = True
        return result

    try:
        skill_result = await hermes_client.run_skill(
            skill_name=classification.skill,
            user_text=text,
            conversation_id=message.conversation_id,
            customer_id=message.metadata.get("customer_id", ""),
            context={
                "channel": message.channel,
                "sender_name": message.sender_name,
                "language": classification.language,
            },
        )
    except Exception as exc:
        log.exception("hermes skill failed", extra={"action": "handle_incoming", "error": str(exc)})
        skill_result = None

    if skill_result is None or not skill_result.get("success"):
        draft_text = _build_honest_admission(
            language=classification.language,
            skill=classification.skill,
        )
        await _send_text(
            message=message,
            text=draft_text,
            services=services,
        )
        result["handled"] = True
        log.info(
            "honest admission sent (skill unavailable)",
            extra={
                "action": "handle_incoming",
                "conversation_id": message.conversation_id,
                "skill": classification.skill,
                "latency_ms": _elapsed_ms(t0),
            },
        )
        return result

    draft_text = skill_result.get("text", "")
    tools_called = skill_result.get("tools_called", [])

    from app.core.postprocess import run as postprocess_run

    post_result = postprocess_run(draft_text, config=config)
    if post_result.text != draft_text:
        draft_text = post_result.text

    # --- Layer 3: output guard + sanitization ---
    draft_text = _apply_guard_output(draft_text, classification.language)

    # --- Layer 4: QA check (v20) ---
    from app.core.qa_engine import DEFAULT_THRESHOLD
    from app.core.qa_engine import check_response as qa_check

    qa_result = qa_check(
        draft_text,
        original_question=text,
        threshold=DEFAULT_THRESHOLD,
    )
    if qa_result.rewritten:
        draft_text = qa_result.response_text
        log.info(
            "qa_rewrite_applied",
            extra={
                "action": "qa.rewrite",
                "score": qa_result.score.total,
                "issues": len(qa_result.score.issues),
            },
        )
    if not qa_result.passed:
        log.warning(
            "qa_below_threshold",
            extra={
                "action": "qa.warning",
                "score": qa_result.score.total,
                "issues": qa_result.score.issues,
            },
        )

    # --- Source citation for RAG-based responses ---
    if _has_rag_sources(skill_result):
        source_label = _extract_source_label(skill_result)
        if source_label:
            draft_text = _append_source_citation(
                draft_text,
                source_label,
                classification.language,
            )

    # --- Honest admission: if the draft is empty or looks like a
    #     non-answer after all processing, admit it honestly ---
    stripped = draft_text.strip()
    if not stripped or _is_gibberish(stripped):
        draft_text = _build_honest_admission(
            language=classification.language,
            skill=classification.skill,
        )
        log.info(
            "honest admission sent (empty/gibberish after postprocess)",
            extra={
                "action": "handle_incoming",
                "conversation_id": message.conversation_id,
                "skill": classification.skill,
            },
        )

    if tools_called:
        approval_id = await _queue_draft(
            message=message,
            classification=classification,
            draft_text=draft_text,
            skill_name=classification.skill,
            services=services,
            conversation_id=message.conversation_id,
            customer_id=message.metadata.get("customer_id", ""),
        )
        result["approval_id"] = approval_id
    else:
        registry = services.get("registry")
        if registry:
            adapter = registry.get(message.channel)
            if adapter:
                from app.channels.base import normalize_text

                await adapter.send(
                    recipient_id=message.sender_id,
                    text=normalize_text(draft_text),
                    reply_to_ref=None
                    if message.metadata.get("is_callback")
                    else message.external_ref,
                )

    result["handled"] = True
    _schedule_memory_extraction(services, message, classification, draft_text)
    log.info(
        "incoming handled",
        extra={
            "action": "handle_incoming",
            "conversation_id": message.conversation_id,
            "skill": classification.skill,
            "latency_ms": _elapsed_ms(t0),
        },
    )
    return result


def _is_gibberish(text: str) -> bool:
    """Detect if a draft is too short or contains mostly non-content."""
    if len(text.strip()) < 5:
        return True
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.2:
        return True
    return False


# ---------------------------------------------------------------------------
# v17: Reminders & Calendar commands
# ---------------------------------------------------------------------------


async def _send_reminders_list(message: IncomingMessage, services: dict[str, Any]) -> None:
    """List active reminders for the user."""
    user_id = message.metadata.get("customer_id", message.sender_id)
    pool = services.get("pg")
    if pool is None:
        await _send_text(message=message, text="Reminders service unavailable.", services=services)
        return
    import time as _time

    rows = await pool.fetch(
        "SELECT * FROM reminders WHERE user_id = $1 AND status = 'active' AND due_at > $2 ORDER BY due_at LIMIT 10",
        str(user_id),
        _time.time(),
    )
    if not rows:
        await _send_text(message=message, text="No active reminders.", services=services)
        return
    lines = ["Reminders:\n"]
    import datetime

    for i, row in enumerate(rows, 1):
        due = datetime.datetime.fromtimestamp(row["due_at"])
        due_str = due.strftime("%Y-%m-%d %H:%M")
        repeat = row.get("repeat_interval", "none")
        repeat_str = f" ({repeat})" if repeat != "none" else ""
        lines.append(f"{i}. {row['title']}\n   Due: {due_str}{repeat_str}")
    await _send_text(message=message, text="\n".join(lines), services=services)


async def _send_today_schedule(message: IncomingMessage, services: dict[str, Any]) -> None:
    """Send today's calendar schedule."""
    from app.core.calendar_client import get_calendar_client

    client = get_calendar_client()
    events = await client.get_today_schedule()
    if not events:
        await _send_text(message=message, text="No events scheduled for today.", services=services)
        return
    lines = ["Today's Schedule:\n"]
    for i, event in enumerate(events, 1):
        lines.append(f"{i}. {event.to_text()}")
    await _send_text(message=message, text="\n".join(lines), services=services)


async def _create_quick_reminder(
    message: IncomingMessage,
    title: str,
    minutes: int,
    services: dict[str, Any],
) -> None:
    """Create a quick reminder from chat command."""
    import time as _time

    from app.core.reminder import create_reminder

    user_id = message.metadata.get("customer_id", message.sender_id)
    due_at = _time.time() + minutes * 60
    reminder = create_reminder(
        user_id=str(user_id),
        title=title,
        message=f"Reminder: {title}",
        due_at=due_at,
    )
    pool = services.get("pg")
    if pool:
        await pool.execute(
            """
            INSERT INTO reminders (id, user_id, title, message, due_at, repeat_interval, status, channel, created_at, trigger_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            reminder.id,
            reminder.user_id,
            reminder.title,
            reminder.message,
            reminder.due_at,
            reminder.repeat.value,
            reminder.status.value,
            reminder.channel,
            reminder.created_at,
            reminder.trigger_count,
        )
    await _send_text(
        message=message,
        text=f"Reminder set: {title}\nDue in {minutes} minutes.",
        services=services,
    )


async def _send_content_plan(message: IncomingMessage, services: dict[str, Any]) -> None:
    """Send the content plan for the next 7 days."""
    pool = services.get("pg")
    if pool is None:
        await _send_text(
            message=message, text="Content calendar service unavailable.", services=services
        )
        return
    import datetime
    import time as _time

    now = _time.time()
    week_end = now + 7 * 86400
    rows = await pool.fetch(
        "SELECT * FROM content_calendar WHERE status IN ('scheduled', 'published') AND scheduled_at BETWEEN $1 AND $2 ORDER BY scheduled_at",
        now,
        week_end,
    )
    if not rows:
        await _send_text(
            message=message, text="No content scheduled for the next 7 days.", services=services
        )
        return
    lines = ["📅 Content Plan (Next 7 Days)\n"]
    current_day = ""
    for row in rows:
        sched = datetime.datetime.fromtimestamp(row["scheduled_at"])
        day_key = sched.strftime("%Y-%m-%d")
        if day_key != current_day:
            current_day = day_key
            lines.append(f"\n📆 {sched.strftime('%A, %B %d')}")
        time_str = sched.strftime("%H:%M")
        lines.append(f"  {time_str} — [{row['platform']}] {row['title']} ({row['status']})")
    await _send_text(message=message, text="\n".join(lines), services=services)


async def _send_pages_list(message: IncomingMessage, services: dict[str, Any]) -> None:
    """List CMS pages."""
    pool = services.get("pg")
    if pool is None:
        await _send_text(message=message, text="CMS service unavailable.", services=services)
        return
    rows = await pool.fetch(
        "SELECT id, title, slug, status, updated_at FROM cms_pages ORDER BY updated_at DESC LIMIT 10"
    )
    if not rows:
        await _send_text(message=message, text="No pages found.", services=services)
        return
    import datetime

    lines = ["Pages:\n"]
    for i, row in enumerate(rows, 1):
        updated = datetime.datetime.fromtimestamp(row["updated_at"]).strftime("%Y-%m-%d")
        lines.append(f"{i}. {row['title']} [{row['status']}] (updated {updated})")
    await _send_text(message=message, text="\n".join(lines), services=services)


async def _send_team_overview(message: IncomingMessage, services: dict[str, Any]) -> None:
    """Send team task overview."""
    pool = services.get("pg")
    if pool is None:
        await _send_text(message=message, text="Team service unavailable.", services=services)
        return
    import time as _time

    rows = await pool.fetch(
        "SELECT * FROM team_tasks WHERE status != 'completed' ORDER BY due_at LIMIT 10"
    )
    if not rows:
        await _send_text(message=message, text="No active team tasks.", services=services)
        return
    import datetime

    lines = ["Team Tasks:\n"]
    for i, row in enumerate(rows, 1):
        due = datetime.datetime.fromtimestamp(row["due_at"]).strftime("%m-%d %H:%M")
        overdue = " âš ï¸" if row["due_at"] < _time.time() else ""
        lines.append(
            f"{i}. [{row['priority'].upper()}] {row['title']}\n   → {row['assignee']} ({row['department']}) | Due: {due}{overdue}"
        )
    await _send_text(message=message, text="\n".join(lines), services=services)


# ---------------------------------------------------------------------------
# Memory extraction (fire-and-forget after successful draft)
# ---------------------------------------------------------------------------


def _schedule_memory_extraction(
    services: dict[str, Any],
    message: IncomingMessage,
    classification: Classification,
    draft_text: str,
) -> None:
    """Schedule async memory extraction — non-blocking, best-effort."""
    memory_mod = services.get("memory")
    if memory_mod is None:
        return
    try:
        customer_id = message.metadata.get("customer_id", "")
        if not customer_id:
            return
        try:
            user_id = int(customer_id)
        except (ValueError, TypeError):
            user_id = int(hashlib.md5(customer_id.encode()).hexdigest()[:8], 16)
        schedule_fn = getattr(memory_mod, "schedule_extraction", None)
        if schedule_fn is not None:
            schedule_fn(user_id, message.text, draft_text)
    except Exception:
        log.debug("memory extraction scheduling failed", exc_info=True)


# ---------------------------------------------------------------------------
# Prompt cache wrapper
# ---------------------------------------------------------------------------


def _get_prompt_cache(services: dict[str, Any]) -> Any | None:
    """Return the PromptCache singleton from services, if available."""
    return services.get("prompt_cache")
