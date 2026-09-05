"""Web tools: DuckDuckGo search (no API key) + webpage reader.

Playwright is optional — when installed it renders JS pages; otherwise a
fast httpx + regex extractor is used.
"""

from __future__ import annotations

import asyncio
import html as _h
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

from app.logging_setup import get_logger

logger = get_logger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")
TIMEOUT = 20


# ---------------- URL safety (hermes-agent url_safety style) -------------

def _ip_is_dangerous(ip: str) -> bool:
    """Private/loopback/link-local/reserved targets can reach intranet or
    cloud metadata endpoints — never fetch them."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (a.is_private or a.is_loopback or a.is_link_local
            or a.is_reserved or a.is_multicast or a.is_unspecified)


async def url_guard(url: str) -> str | None:
    """Return a rejection reason for dangerous URLs, else None."""
    try:
        p = urlparse(url)
    except Exception:
        return "URL is not parseable"
    if p.scheme not in ("http", "https"):
        return f"Scheme '{p.scheme or '?'}' is not allowed — only http/https"
    host = (p.hostname or "").strip().lower().rstrip(".")
    if not host:
        return "Invalid hostname"
    if host == "localhost" or host.endswith((".localhost", ".internal", ".local")):
        return "Access to internal hosts is blocked"
    if _ip_is_dangerous(host):
        return "Local/private addresses are blocked"
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as e:
        return f"Host not found: {e}"
    except Exception as e:
        return f"DNS error: {e}"
    for info in infos:
        if info[4] and _ip_is_dangerous(str(info[4][0])):
            return "Host resolves to a private address (SSRF blocked)"
    return None


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo Lite scraping -> [{title, url, snippet}]"""
    query = (query or "").strip()
    if not query:
        return []
    max_results = max(1, min(max_results, 8))
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA},
                                     follow_redirects=True) as c:
            r = await c.get("https://lite.duckduckgo.com/lite/",
                            params={"q": query})
            r.raise_for_status()
            html_text = r.text
    except Exception as e:
        logger.error("search failed: %s", e)
        return [{"error": f"search failed: {e}"}]

    results = []
    for m in re.finditer(
        r'<a[^>]+href="(http[^"]+)"[^>]*class=[\'"]result-link[\'"][^>]*>(.*?)</a>',
        html_text, re.DOTALL):
        url = m.group(1)
        title = re.sub(r"<.*?>", "", m.group(2)).strip()
        tail = html_text[m.end(): m.end() + 900]
        sm = re.search(r'class=[\'"]result-snippet[\'"]>(.*?)</t', tail, re.DOTALL)
        snippet = re.sub(r"<.*?>", "", sm.group(1)).strip()[:220] if sm else ""
        if url.startswith("//"):
            url = "https:" + url
        results.append({"title": title[:120], "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


_TAG_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_ANY = re.compile(r"<[^>]+>")
_WS = re.compile(r"\n{3,}|[ \t]{2,}")


def _html_to_text(html: str) -> str:
    html = _TAG_SCRIPT.sub(" ", html)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", html, flags=re.IGNORECASE)
    text = _TAG_ANY.sub(" ", html)
    text = _h.unescape(text)
    return _WS.sub("\n", text).strip()


async def _get_browser_enabled() -> bool:
    try:
        from app.core.config import settings
        return getattr(settings, "browser_enabled", True)
    except Exception:
        return True


async def read_webpage(url: str, max_chars: int = 3500) -> str:
    """Read a page as clean text. Uses Playwright when available."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return "Invalid URL."
    reason = await url_guard(url)
    if reason:
        return f"Blocked: {reason}"
    if await _get_browser_enabled():
        try:
            from playwright.async_api import async_playwright  # noqa
            return await _read_playwright(url, max_chars)
        except ImportError:
            pass
        except Exception:
            pass  # fall back to plain fetch
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA},
                                     follow_redirects=False) as c:
            r = await c.get(url, follow_redirects=False)
            r.raise_for_status()
            final = await url_guard(str(r.url))
            if final:
                return f"Blocked: {final}"
            ctype = r.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype:
                return f"Non-HTML content ({ctype.split(';')[0]}) — {len(r.content)} bytes."
            text = _html_to_text(r.text)
            return text[:max_chars] or "(empty page)"
    except Exception as e:
        logger.error("Error reading page %s: %s", url, e)
        return f"Error reading page: {e}"


async def _read_playwright(url: str, max_chars: int) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)
        try:
            await page.goto(url, timeout=25000, wait_until="domcontentloaded")
            final = await url_guard(page.url)
            if final:
                return f"Blocked: {final}"
            text = await page.inner_text("body")
        finally:
            await browser.close()
    return text.strip()[:max_chars]
