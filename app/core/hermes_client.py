"""Hermes skill runner — loads skill definitions, plans tool calls, executes inline."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

from app.config import Config, get_config
from app.core.languages import get_language_name
from app.logging_setup import get_logger

log = get_logger("app.core.hermes_client")

_INLINE_PLAN: int = 3
QUOTE_MARKERS: frozenset[str] = frozenset(
    {
        "عرض سعر",
        "quot",
        "quote",
        "تقديراً",
        "pricing",
        "cost",
        "پیش‌فاکتور",
        "فاکتور",
        "قیمت",
        "استعلام",
    }
)
_QUANTITY_UNITS: frozenset[str] = frozenset(
    {
        "كجم",
        "kg",
        "طن",
        "ton",
        "لتر",
        "liter",
        "ل",
        "l",
        "برميل",
        "bbl",
        "م3",
        "m3",
        " غالون",
        "gallon",
        "عدد",
        "بسته",
        "کیلو",
    }
)
_SQL_MARKERS: frozenset[str] = frozenset(
    {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "FROM",
        "WHERE",
        "GROUP BY",
        "ORDER BY",
        "JOIN",
    }
)
_TEMPLATE_HINTS: frozenset[str] = frozenset(
    {
        "template",
        "قالب",
        "نموذج",
        "invoice",
        "فاتورة",
        "quotation",
        "عرض",
        "contract",
        "عقد",
        "پیش‌فاکتور",
    }
)


@dataclass
class SkillDefinition:
    name: str
    directory: str
    description: str
    prompt_ar: str
    prompt_en: str
    tools: list[str] = field(default_factory=list)
    approval_gated: bool = False
    auto_allowed: bool = False
    model_tier: Literal["fast", "standard"] = "fast"
    json_output: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "directory": self.directory,
            "description": self.description,
            "tools": self.tools,
            "approval_gated": self.approval_gated,
            "model_tier": self.model_tier,
        }


@dataclass
class SkillRun:
    success: bool
    text: str = ""
    skill: str = ""
    tools_called: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "text": self.text,
            "skill": self.skill,
            "tools_called": self.tools_called,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


def load_skill(skill_dir: str | Path) -> SkillDefinition | None:
    skill_path = Path(skill_dir)
    if not skill_path.is_dir():
        return None

    yaml_file = skill_path / "skill.yaml"
    if not yaml_file.is_file():
        yaml_file = skill_path / "skill.yml"

    data: dict[str, Any] = {}
    if yaml_file.is_file():
        try:
            with open(yaml_file, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as exc:
            log.error(
                "failed to load skill yaml",
                extra={"action": "load_skill", "path": str(yaml_file), "error": str(exc)},
            )

    prompt_ar = ""
    prompt_en = ""
    prompt_file_ar = skill_path / "prompt_ar.md"
    prompt_file_en = skill_path / "prompt_en.md"
    skill_md = skill_path / "SKILL.md"

    if prompt_file_ar.is_file():
        prompt_ar = prompt_file_ar.read_text(encoding="utf-8").strip()
    if prompt_file_en.is_file():
        prompt_en = prompt_file_en.read_text(encoding="utf-8").strip()
    elif skill_md.is_file():
        prompt_en = skill_md.read_text(encoding="utf-8").strip()

    name = str(data.get("name", skill_path.name))
    description = str(data.get("description", ""))
    if not description and prompt_en:
        lines = [l.strip("# \t\r") for l in prompt_en.split("\n") if l.strip()]
        description = lines[0] if lines else name

    model_tier_raw = str(data.get("model_tier", "fast")).strip().lower()
    model_tier: Literal["fast", "standard"] = "standard" if model_tier_raw == "standard" else "fast"
    raw_tools = data.get("tools", [])
    tools = [str(tool) for tool in raw_tools] if isinstance(raw_tools, list) else []

    return SkillDefinition(
        name=name,
        directory=str(skill_path),
        description=description,
        prompt_ar=prompt_ar or str(data.get("prompt_ar", "")),
        prompt_en=prompt_en or str(data.get("prompt_en", "")),
        tools=tools,
        approval_gated=bool(data.get("approval_gated", False)),
        auto_allowed=bool(data.get("auto_allowed", False)),
        model_tier=model_tier,
        json_output=bool(data.get("json_output", False)),
    )



_SPECIALIST_SOURCE = {
    "email_agent": "email",
    "email": "email",
    "website_agent": "website",
    "website": "website",
    "social_agent": "social",
    "social": "social",
    "sales_agent": "sales",
    "sales": "sales",
    "support_agent": "support",
    "support": "support",
    "ops_agent": "ops",
    "ops": "ops",
}


async def plan_inline_tools(
    skill_name: str,
    user_text: str,
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Plan tool calls from the company charter router, not from free LLM guesses."""
    ctx = dict(context or {})
    lower = user_text.lower()
    planned: list[dict[str, Any]] = []

    if skill_name in _SPECIALIST_SOURCE:
        from app.core.agents.router import route_work

        extras: dict[str, Any] = {}
        raw_extras = ctx.get("extras")
        if isinstance(raw_extras, dict):
            extras = dict(raw_extras)
        for key in (
            "form",
            "field",
            "before",
            "after",
            "platform",
            "caption",
            "scheduled_at",
            "media_url",
            "hashtags",
            "cms_field",
        ):
            if key in ctx and key not in extras:
                extras[key] = ctx[key]
        plan = route_work(
            user_text,
            source=str(ctx.get("source") or _SPECIALIST_SOURCE[skill_name]),
            subject=str(ctx.get("subject") or ""),
            sender=str(ctx.get("sender") or ctx.get("sender_name") or ""),
            extras=extras,
        )
        planned.append(
            {
                "name": plan.action,
                "params": dict(plan.payload),
                "requires_approval": plan.needs_manager,
                "auto": plan.auto_execute,
            }
        )

    if skill_name in ("analytics_agent",):
        for marker in _SQL_MARKERS:
            if marker in lower:
                planned.append(
                    {
                        "name": "execute_analytics_query",
                        "params": {"query_hint": user_text[:500]},
                    }
                )
                break
        if not planned:
            planned.append(
                {
                    "name": "generate_report",
                    "params": {"report_type": "summary", "period": "current"},
                }
            )

    if skill_name in ("customer_agent",):
        if any(w in lower for w in ("تحديث", "update", "تعديل", "ویرایش", "تغییر")):
            planned.append(
                {
                    "name": "update_customer",
                    "params": {"fields_requested": user_text[:300]},
                    "requires_approval": True,
                    "auto": False,
                }
            )

    if len(planned) > _INLINE_PLAN:
        planned = planned[:_INLINE_PLAN]
    return planned


class HermesClient:
    def __init__(self, cfg: Config | None = None, llm_client: Any = None) -> None:
        self._cfg = cfg or get_config()
        self._llm = llm_client
        self._skills: dict[str, SkillDefinition] = {}
        self._http: httpx.AsyncClient | None = None

    async def run_skill(
        self,
        skill_name: str,
        user_text: str,
        *,
        conversation_id: str = "",
        customer_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()

        if self._cfg.llm.mode == "mock":
            return await self._run_inline(
                skill_name=skill_name,
                user_text=user_text,
                conversation_id=conversation_id,
                customer_id=customer_id,
                context=context or {},
            )

        # In direct LLM mode without an explicitly configured external Hermes microservice,
        # run skills directly inline using the configured LLM client.
        if self._cfg.llm.mode == "direct" and (
            not self._cfg.llm.hermes_base_url
            or "http://hermes:3000" in self._cfg.llm.hermes_base_url
        ):
            return await self._run_inline(
                skill_name=skill_name,
                user_text=user_text,
                conversation_id=conversation_id,
                customer_id=customer_id,
                context=context or {},
            )

        if self._cfg.llm.mode in ("router", "direct"):
            result = await self._run_remote(
                skill_name=skill_name,
                user_text=user_text,
                conversation_id=conversation_id,
                customer_id=customer_id,
                context=context or {},
            )
            if result.get("success"):
                return result
            log.warning(
                "hermes remote failed — falling back to inline",
                extra={
                    "action": "run_skill",
                    "skill": skill_name,
                    "error": result.get("error"),
                },
            )
            return await self._run_inline(
                skill_name=skill_name,
                user_text=user_text,
                conversation_id=conversation_id,
                customer_id=customer_id,
                context=context or {},
            )

        return {"success": False, "error": f"unknown llm mode: {self._cfg.llm.mode}"}

    async def sync_skills(self) -> list[dict[str, Any]]:
        from app.constants import SKILL_DIRS

        skills_base = Path(__file__).parent / "skills"
        loaded: list[dict[str, Any]] = []

        for skill_key, sub_dir in SKILL_DIRS.items():
            skill_path = skills_base / sub_dir
            if skill_path.is_dir():
                skill_def = load_skill(skill_path)
                if skill_def is not None:
                    self._skills[skill_def.name] = skill_def
                    loaded.append(skill_def.as_dict())
                else:
                    self._skills[skill_key] = SkillDefinition(
                        name=skill_key,
                        directory=str(skill_path),
                        description=f"Builtin skill: {skill_key}",
                        prompt_ar="",
                        prompt_en="",
                    )
                    loaded.append(self._skills[skill_key].as_dict())

        log.info("skills synced", extra={"action": "sync_skills", "count": len(loaded)})
        return loaded

    async def health(self) -> dict[str, Any]:
        if self._cfg.llm.mode == "mock":
            return {"ok": True, "mode": "mock", "skills_loaded": len(self._skills)}

        if not self._cfg.llm.hermes_base_url or "http://hermes:3000" in self._cfg.llm.hermes_base_url:
            return {"ok": True, "mode": "inline", "skills_loaded": len(self._skills)}

        client = await self._get_http()
        try:
            t0 = time.perf_counter()
            resp = await client.get(
                f"{self._cfg.llm.hermes_base_url.rstrip('/')}/health",
                headers={"Authorization": f"Bearer {self._cfg.llm.hermes_service_token}"},
                timeout=5,
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "ok": resp.status_code < 500,
                "status": resp.status_code,
                "latency_ms": latency,
                "skills_loaded": len(self._skills),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "skills_loaded": len(self._skills)}

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient()
        return self._http

    async def _run_remote(
        self,
        *,
        skill_name: str,
        user_text: str,
        conversation_id: str,
        customer_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        client = await self._get_http()
        t0 = time.perf_counter()

        body = {
            "skill": skill_name,
            "input": user_text,
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "context": context,
        }

        try:
            resp = await client.post(
                f"{self._cfg.llm.hermes_base_url.rstrip('/')}/skills/run",
                json=body,
                headers={
                    "Authorization": f"Bearer {self._cfg.llm.hermes_service_token}",
                    "Content-Type": "application/json",
                },
                timeout=self._cfg.llm.hermes_timeout,
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)

            if resp.status_code >= 400:
                log.error(
                    "hermes remote error",
                    extra={
                        "action": "run_remote",
                        "status": resp.status_code,
                        "skill": skill_name,
                        "latency_ms": latency,
                    },
                )
                return {
                    "success": False,
                    "error": f"HTTP {resp.status_code}",
                    "latency_ms": latency,
                }

            data = resp.json()
            return {
                "success": bool(data.get("success", True)),
                "text": data.get("text", data.get("reply", "")),
                "tools_called": data.get("tools_called", []),
                "tool_results": data.get("tool_results", []),
                "latency_ms": latency,
            }
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            log.error(
                "hermes timeout",
                extra={"action": "run_remote", "skill": skill_name, "latency_ms": latency},
            )
            return {"success": False, "error": "timeout", "latency_ms": latency}
        except Exception as exc:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            log.error(
                "hermes remote failed",
                extra={
                    "action": "run_remote",
                    "skill": skill_name,
                    "error": str(exc),
                    "latency_ms": latency,
                },
            )
            return {"success": False, "error": str(exc), "latency_ms": latency}

    async def _run_inline(
        self,
        *,
        skill_name: str,
        user_text: str,
        conversation_id: str,
        customer_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        t0 = time.perf_counter()

        skill_def = self._skills.get(skill_name)
        if skill_def is None:
            from app.constants import SKILL_DIRS

            skills_base = Path(__file__).parent / "skills"
            sub_dir = SKILL_DIRS.get(skill_name, skill_name)
            skill_path = skills_base / sub_dir
            if skill_path.is_dir():
                skill_def = load_skill(skill_path)
            if skill_def is None:
                skill_def = SkillDefinition(
                    name=skill_name,
                    directory="",
                    description=f"Inline skill: {skill_name}",
                    prompt_ar="",
                    prompt_en="",
                )

        language = (context.get("language") or "en").lower().strip()
        lang_name = get_language_name(language)

        base_prompt = skill_def.prompt_en or skill_def.prompt_ar
        if not base_prompt:
            base_prompt = (
                f"You are an expert AI assistant specialized in {skill_def.description or skill_name}. "
                "Provide accurate, polite, structured, and helpful responses."
            )

        from app.core.company_charter import system_prompt as charter_prompt

        system_prompt = (
            f"{charter_prompt(language=language)}\n\n"
            f"{base_prompt}\n\n"
            f"=== CRITICAL LANGUAGE INSTRUCTION ===\n"
            f"- Target User Language: {lang_name} (code: '{language}')\n"
            f"- You MUST formulate your entire response fluently, naturally, and politely in {lang_name}.\n"
            f"- Do NOT reply in Arabic or any other language unless the target language is Arabic or the user asks for it."
        )

        tool_plan = await self._plan_tool_calls(skill_name, user_text, context)
        user_prompt = self._compose_user_prompt(user_text, context, tool_plan)

        llm_client = self._llm
        if llm_client is None:
            from app.core.llm import LLMClient

            llm_client = LLMClient(self._cfg)

        response_text = await llm_client.complete(
            system=system_prompt,
            user=user_prompt,
            tier=skill_def.model_tier,
            temperature=0.3,
            json_mode=skill_def.json_output,
            max_tokens=1500,
            purpose=f"skill:{skill_name}",
        )

        if not response_text:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return {"success": False, "error": "empty response", "latency_ms": latency}

        tools_called = [t["name"] for t in tool_plan] if tool_plan else []
        tool_results: list[dict[str, Any]] = []

        from app.core.hitl.execute import execute_action
        from app.core.policy import registered_actions
        from app.core.token_saver import compress_tool_outputs

        known_actions = set(registered_actions())
        for tool_call in tool_plan:
            params = dict(tool_call.get("params") or {})
            name = str(tool_call["name"])
            if name in known_actions:
                outcome = execute_action(
                    name,
                    params,
                    actor_role="agent",
                    approved=False,
                    context=context,
                )
                held = (not outcome.executed) and outcome.policy.requires_approval
                tool_result = {
                    "tool": name,
                    "status": "executed" if outcome.executed else ("held" if held else "blocked"),
                    "params": params,
                    "executed": outcome.executed,
                    "reason": outcome.reason,
                }
            else:
                tool_result = {
                    "tool": name,
                    "status": "planned",
                    "params": params,
                }
            tool_results.append(tool_result)
        tool_results = compress_tool_outputs(tool_results)

        latency = round((time.perf_counter() - t0) * 1000, 1)

        log.info(
            "hermes inline run",
            extra={
                "action": "run_inline",
                "skill": skill_name,
                "latency_ms": latency,
                "language": language,
                "tools": len(tools_called),
            },
        )

        return {
            "success": True,
            "text": response_text,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "latency_ms": latency,
        }

    async def _plan_tool_calls(
        self,
        skill_name: str,
        user_text: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return await plan_inline_tools(skill_name, user_text, context)

    def _compose_user_prompt(

        self,
        user_text: str,
        context: dict[str, Any],
        tool_plan: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = []

        sender_name = context.get("sender_name", "")
        if sender_name:
            parts.append(f"Customer Name: {sender_name}")

        channel = context.get("channel", "")
        if channel:
            parts.append(f"Channel: {channel}")

        language = (context.get("language") or "en").lower().strip()
        parts.append(f"User Language: {get_language_name(language)} ({language})")
        parts.append(f"User Message: {user_text}")

        if tool_plan:
            tool_names = [t["name"] for t in tool_plan]
            parts.append(f"Planned Tools: {', '.join(tool_names)}")
            for t in tool_plan:
                if t.get("params"):
                    parts.append(f"  - {t['name']}: {json.dumps(t['params'], ensure_ascii=False)}")
            if any(t.get("requires_approval") for t in tool_plan):
                parts.append(
                    "Guideline: Do not claim the action was executed. "
                    "It requires an explicit manager approval record."
                )

        for marker in _TEMPLATE_HINTS:
            if marker in user_text.lower():
                parts.append("Guideline: Format with clean structure/quote headers if appropriate.")
                break

        for unit in _QUANTITY_UNITS:
            if unit in user_text.lower():
                parts.append("Guideline: Message includes measurement units, ensure calculation accuracy.")
                break

        return "\n".join(parts)

    async def _analytics_template(
        self,
        report_type: str,
        context: dict[str, Any],
    ) -> str:
        templates: dict[str, str] = {
            "summary": (
                "Operational Summary Report:\n"
                "- Total Volume / Sales: [Calculated]\n"
                "- Order Count: [Calculated]\n"
                "- Average Order Value: [Calculated]\n"
            ),
            "detailed": (
                "Detailed Report:\n- Period: [Specified]\n- Products: [Calculated]\n- Customers: [Calculated]\n"
            ),
        }
        return templates.get(report_type, templates["summary"])
