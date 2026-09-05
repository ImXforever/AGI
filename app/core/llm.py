"""LLM client — unified interface for 9router / direct / mock modes.

Enhanced with:
- Exponential backoff with jitter on 429 rate-limit errors
- Model failover chain: if primary model fails, try fallback models automatically
- Model usage stats tracking (which model was used, success/failure counts)
- ``call_with_fallback()`` method implementing the retry/failover logic
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from typing import Any, Literal

import httpx

from app.config import Config, get_config
from app.logging_setup import get_logger

log = get_logger("app.core.llm")

MOCK_ROUTING: dict[str, dict[str, str]] = {
    "greetings": {
        "intent": "greeting",
        "skill": "orchestrator",
    },
    "safety": {
        "intent": "safety_emergency",
        "skill": "support_agent",
    },
    "price": {
        "intent": "pricing_inquiry",
        "skill": "sales_agent",
    },
    "support": {
        "intent": "technical_support",
        "skill": "support_agent",
    },
    "account": {
        "intent": "account_inquiry",
        "skill": "customer_agent",
    },
    "analytics": {
        "intent": "report_request",
        "skill": "analytics_agent",
    },
    "product": {
        "intent": "product_question",
        "skill": "knowledge_agent",
    },
}


def _build_model_chain(models_str: str) -> list[str]:
    """Parse a comma-separated model list into a clean chain."""
    return [m.strip() for m in models_str.split(",") if m.strip()]


class _ModelStats:
    """Thread-safe-ish usage statistics tracker for LLM models."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, int]] = {}

    def record(self, model: str, *, success: bool) -> None:
        if model not in self._data:
            self._data[model] = {"success": 0, "failure": 0, "total": 0}
        bucket = self._data[model]
        bucket["total"] += 1
        if success:
            bucket["success"] += 1
        else:
            bucket["failure"] += 1

    def snapshot(self) -> dict[str, dict[str, int]]:
        return {k: dict(v) for k, v in self._data.items()}

    def reset(self) -> None:
        self._data.clear()


class LLMClient:
    def __init__(self, cfg: Config | None = None) -> None:
        self._cfg = cfg or get_config()
        self._http: httpx.AsyncClient | None = None
        self._stats = _ModelStats()

        # ------------------------------------------------------------------
        # Failover chains built from env / config.
        # LLM_FALLBACK_MODELS_FAST and LLM_FALLBACK_MODELS_STD are optional
        # comma-separated lists that extend the primary model into a chain.
        # Example  LLM_FALLBACK_MODELS_FAST=gpt-4o,gpt-4o-mini
        # ------------------------------------------------------------------
        self._fast_chain: list[str] = [self._cfg.llm.model_fast] + _build_model_chain(
            os.getenv("LLM_FALLBACK_MODELS_FAST", "")
        )
        self._std_chain: list[str] = [self._cfg.llm.model_standard] + _build_model_chain(
            os.getenv("LLM_FALLBACK_MODELS_STD", "")
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        system: str,
        user: str,
        tier: Literal["fast", "standard"] = "fast",
        temperature: float | None = None,
        json_mode: bool = False,
        max_tokens: int = 1024,
        purpose: str = "general",
    ) -> str:
        if self._cfg.llm.mode == "mock":
            return self._mock_orchestrator(user, purpose=purpose)

        if self._cfg.llm.mode == "router":
            return await self._complete_http(
                base_url=self._cfg.llm.router_base_url,
                api_key=self._cfg.llm.router_access_key,
                model=self._cfg.llm.model_fast if tier == "fast" else self._cfg.llm.model_standard,
                system=system,
                user=user,
                temperature=temperature if temperature is not None else self._cfg.llm.temperature,
                json_mode=json_mode,
                max_tokens=max_tokens,
                timeout=self._cfg.llm.router_timeout,
                purpose=purpose,
            )

        return await self._complete_http(
            base_url=self._cfg.llm.direct_base_url,
            api_key=self._cfg.llm.direct_api_key,
            model=self._cfg.llm.direct_model,
            system=system,
            user=user,
            temperature=temperature if temperature is not None else self._cfg.llm.temperature,
            json_mode=json_mode,
            max_tokens=max_tokens,
            timeout=60,
            purpose=purpose,
        )

    async def call_with_fallback(
        self,
        system: str,
        user: str,
        tier: Literal["fast", "standard"] = "fast",
        temperature: float | None = None,
        json_mode: bool = False,
        max_tokens: int = 1024,
        purpose: str = "general",
    ) -> str | None:
        """Try the primary model with exponential backoff, then failover.

        Retry logic (adapted from RAG-LangGraph ``call()``):

        * Try each model in the chain up to 3 times.
        * On HTTP 429 (rate limit): wait with exponential backoff + jitter
          (4 s, 8 s, 16 s + random jitter) then retry the *same* model.
        * On any other error: immediately move to the next model in the chain.
        * If every model in the chain is exhausted, return ``None`` so the
          caller can take the safe path.
        """
        if self._cfg.llm.mode == "mock":
            return self._mock_orchestrator(user, purpose=purpose)

        chain = self._fast_chain if tier == "fast" else self._std_chain
        temp = temperature if temperature is not None else self._cfg.llm.temperature
        base_timeout = self._cfg.llm.router_timeout if self._cfg.llm.mode == "router" else 60

        for model_id in chain:
            base_url, api_key = self._resolve_endpoint()

            wait = 4.0
            for attempt in range(3):
                try:
                    result = await self._complete_http(
                        base_url=base_url,
                        api_key=api_key,
                        model=model_id,
                        system=system,
                        user=user,
                        temperature=temp,
                        json_mode=json_mode,
                        max_tokens=max_tokens,
                        timeout=base_timeout,
                        purpose=purpose,
                    )
                    if result:
                        self._stats.record(model_id, success=True)
                        return result

                    # Empty string from _complete_http means an error occurred
                    # that was already logged inside _complete_http.
                    self._stats.record(model_id, success=False)
                    raise ValueError("empty response")

                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 429 and attempt < 2:
                        jitter = random.SystemRandom().uniform(0, 1.5)
                        log.warning(
                            "429 rate-limited — retrying after backoff",
                            extra={
                                "action": "call_with_fallback",
                                "model": model_id,
                                "attempt": attempt + 1,
                                "wait_s": round(wait + jitter, 1),
                            },
                        )
                        await asyncio.sleep(wait + jitter)
                        wait *= 2
                        continue
                    # Non-429 HTTP error or final attempt → next model
                    self._stats.record(model_id, success=False)
                    log.warning(
                        "model failed — trying next in chain",
                        extra={
                            "action": "call_with_fallback",
                            "model": model_id,
                            "error": str(exc),
                        },
                    )
                    break

                except Exception as exc:
                    msg = str(exc)
                    if ("429" in msg or "Too Many Requests" in msg) and attempt < 2:
                        jitter = random.SystemRandom().uniform(0, 1.5)
                        log.warning(
                            "429 rate-limited — retrying after backoff",
                            extra={
                                "action": "call_with_fallback",
                                "model": model_id,
                                "attempt": attempt + 1,
                                "wait_s": round(wait + jitter, 1),
                            },
                        )
                        await asyncio.sleep(wait + jitter)
                        wait *= 2
                        continue
                    self._stats.record(model_id, success=False)
                    log.warning(
                        "model failed — trying next in chain",
                        extra={
                            "action": "call_with_fallback",
                            "model": model_id,
                            "error": str(exc),
                        },
                    )
                    break

        log.error(
            "all models exhausted — returning None (safe path)",
            extra={"action": "call_with_fallback"},
        )
        return None

    def get_model_stats(self) -> dict[str, dict[str, int]]:
        """Return a snapshot of per-model success/failure counts."""
        return self._stats.snapshot()

    def reset_stats(self) -> None:
        """Clear all model usage statistics."""
        self._stats.reset()

    def get_model_chains(self) -> dict[str, list[str]]:
        """Return the configured failover chains (for diagnostics)."""
        return {
            "fast": list(self._fast_chain),
            "standard": list(self._std_chain),
        }

    async def health(self) -> dict[str, Any]:
        if self._cfg.llm.mode == "mock":
            return {"ok": True, "mode": "mock"}

        base_url = (
            self._cfg.llm.router_base_url
            if self._cfg.llm.mode == "router"
            else self._cfg.llm.direct_base_url
        )
        client = await self._get_http()
        try:
            t0 = time.perf_counter()
            resp = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={
                    "Authorization": f"Bearer {self._cfg.llm.router_access_key if self._cfg.llm.mode == 'router' else self._cfg.llm.direct_api_key}"
                },
                timeout=10,
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return {"ok": resp.status_code < 500, "status": resp.status_code, "latency_ms": latency}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient()
        return self._http

    def _resolve_endpoint(self) -> tuple[str, str]:
        """Return (base_url, api_key) for the current mode."""
        if self._cfg.llm.mode == "router":
            return self._cfg.llm.router_base_url, self._cfg.llm.router_access_key
        return self._cfg.llm.direct_base_url, self._cfg.llm.direct_api_key

    async def _complete_http(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        system: str,
        user: str,
        temperature: float,
        json_mode: bool,
        max_tokens: int,
        timeout: int,
        purpose: str,
    ) -> str:
        client = await self._get_http()

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if timeout < 90:
            timeout = 90

        t0 = time.perf_counter()
        try:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
                timeout=timeout,
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)

            if resp.status_code >= 400:
                log.error(
                    "llm upstream error",
                    extra={
                        "action": "complete",
                        "status": resp.status_code,
                        "purpose": purpose,
                        "latency_ms": latency,
                        "model": model,
                    },
                )
                if (
                    not getattr(self, "_fallback_depth", 0)
                    and self._cfg.llm.mode == "router"
                    and self._cfg.llm.router_fallback_to_direct
                    and self._cfg.llm.direct_base_url
                ):
                    log.info("falling back to direct mode", extra={"action": "complete"})
                    self._fallback_depth = 1
                    try:
                        return await self._complete_http(
                            base_url=self._cfg.llm.direct_base_url,
                            api_key=self._cfg.llm.direct_api_key,
                            model=self._cfg.llm.direct_model,
                            system=system,
                            user=user,
                            temperature=temperature,
                            json_mode=json_mode,
                            max_tokens=max_tokens,
                            timeout=60,
                            purpose=purpose,
                        )
                    finally:
                        self._fallback_depth = 0
                return ""

            raw_text = resp.text
            try:
                data = resp.json()
            except json.JSONDecodeError:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(raw_text)
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            log.info(
                "llm call ok",
                extra={
                    "action": "complete",
                    "purpose": purpose,
                    "latency_ms": latency,
                    "model": model,
                    "tokens_out": len(content),
                },
            )
            return content

        except httpx.TimeoutException:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            log.error(
                "llm timeout",
                extra={
                    "action": "complete",
                    "purpose": purpose,
                    "latency_ms": latency,
                    "model": model,
                },
            )
            return ""
        except httpx.HTTPStatusError:
            raise  # propagate for call_with_fallback to handle 429 retries
        except Exception as exc:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            log.error(
                "llm call failed",
                extra={
                    "action": "complete",
                    "purpose": purpose,
                    "error": str(exc),
                    "latency_ms": latency,
                },
            )
            return ""

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------

    def _mock_orchestrator(self, user_text: str, *, purpose: str = "general") -> str:
        lower = user_text.strip().lower()
        from app.core.languages import detect_language
        lang = detect_language(user_text)

        if purpose == "classification":
            if any(w in lower for w in ("مرحبا", "السلام", "أهلا", "سلام", "درود", "hi", "hello", "hey")):
                routing = MOCK_ROUTING["greetings"]
            elif any(w in lower for w in SAFETY_WORDS_MOCK):
                routing = MOCK_ROUTING["safety"]
            elif any(w in lower for w in ("سعر", "سع", "quot", "price", "cost", "قیمت", "فاکتور")):
                routing = MOCK_ROUTING["price"]
            elif any(w in lower for w in ("دعم", "مشكلة", "error", "bug", "issue", "support", "پشتیبانی", "خراب")):
                routing = MOCK_ROUTING["support"]
            elif any(w in lower for w in ("حساب", "حسابي", "account", "profile", "سفارش")):
                routing = MOCK_ROUTING["account"]
            elif any(w in lower for w in ("تقرير", "إحصا", "report", "analytics", "stat", "آمار", "گزارش")):
                routing = MOCK_ROUTING["analytics"]
            elif any(w in lower for w in ("منتج", "مواصف", "product", "spec", "محصول", "کالا")):
                routing = MOCK_ROUTING["product"]
            else:
                routing = MOCK_ROUTING["greetings"]

            return json.dumps(
                {
                    "intent": routing["intent"],
                    "skill": routing["skill"],
                    "confidence": 0.95,
                    "language": lang,
                },
                ensure_ascii=False,
            )

        return self._mock_skill_reply(lower, lang=lang)

    def _mock_skill_reply(self, text: str, lang: str = "en") -> str:
        if lang == "fa":
            if any(w in text for w in ("سلام", "درود", "خوبی", "hi", "hello")):
                return "سلام و درود! چطور می‌توانم امروز به شما کمک کنم؟"
            if any(w in text for w in ("قیمت", "پیش‌فاکتور", "فاکتور", "سعر", "price")):
                return "برای استعلام قیمت یا دریافت پیش‌فاکتور، لطفاً نام محصول و تعداد درخواستی را مشخص کنید."
            if any(w in text for w in ("محصول", "کالا", "product")):
                return "ما سبد متنوعی از محصولات صنعتی ارائه می‌دهیم. می‌توانید نام محصول را جستجو کنید."
            if any(w in text for w in ("پشتیبانی", "تیکت", "مشکل", "خراب", "support")):
                return "پیام شما دریافت شد. در حال ثبت تیکت پشتیبانی و ارجاع به کارشناسان مربوطه هستیم."
            return "پیام شما دریافت شد. چطور می‌توانم در مورد محصولات و خدمات کمکتان کنم؟"

        if lang == "ar":
            if any(w in text for w in ("مرحبا", "أهلا", "السلام")):
                return "أهلاً وسهلاً! يسعدني خدمتك. كيف يمكنني مساعدتك اليوم؟"
            if any(w in text for w in ("سعر", "quot", "price")):
                return "شكراً لاستفسارك عن الأسعار. يرجى توضيح الكمية والمواصفات المطلوبة."
            if any(w in text for w in ("منتج", "product", "مواصف")):
                return "نوفر مجموعة واسعة من المنتجات الصناعية. يمكنك الاستفسار عن منتج محدد."
            if any(w in text for w in ("دعم", "مشكلة", "support", "error")):
                return "أفهم أنك تواجه مشكلة. سأقوم بإنشاء تذكرة دعم فني للمتابعة."
            return "شكراً لرسالتك. كيف يمكنني مساعدتك اليوم؟"

        # Default English
        if any(w in text for w in ("hi", "hello", "hey", "greetings")):
            return "Hello! How can I assist you with our products and services today?"
        if any(w in text for w in ("price", "quote", "cost")):
            return "Thank you for your pricing inquiry. Please specify the product and required quantity for a formal quote."
        if any(w in text for w in ("product", "catalog", "spec")):
            return "We provide a wide range of industrial products and services. You can search by product name or SKU."
        if any(w in text for w in ("support", "issue", "bug", "help")):
            return "I understand your request. I am logging a support ticket with our technical team."
        return "Thank you for your message. How can I assist you today?"


SAFETY_WORDS_MOCK: frozenset[str] = frozenset(
    {
        "حريق",
        "تسرب",
        "انفجار",
        "accident",
        "fire",
        "leak",
        "explosion",
        "spill",
        "emergency",
        "طوارئ",
        "إصابة",
        "injury",
    }
)
