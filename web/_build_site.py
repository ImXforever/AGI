#!/usr/bin/env python3
"""Build web/index.html — the public Zenovix landing page (zenovix.ae identity).

Content, palette (indigo / violet → blue gradient), section order and copy come
from the mother site (zenovix.ae, crawled 2026-09-07). On top of the clone we
add what the platform needs:

  * a Manager **Login** button (→ /admin/ops/login.html, same contract as the
    previous landing page, incl. the Telegram one-tap admin login hook);
  * the contact form wired to POST /api/public/enquiry (creates a lead/ticket);
  * an "Ask Zenovix" chat widget wired to POST /api/public/chat (knowledge base).

Run:  python3 web/_build_site.py   (from the repo root)
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "index.html"

# ---------------------------------------------------------------------------
# Content — verbatim from zenovix.ae (English) ----------------------------------
# ---------------------------------------------------------------------------

COMPANY = "Zenovix"
TAGLINE = "AI &amp; Digital Technology"
EMAIL = "studio@zenovix.com"
PHONE = "+971 4570 1100"
PHONE_TEL = "+97145701100"
WHATSAPP = "https://wa.me/97145701100?text=Hello%20Zenovix%2C%20I%27d%20like%20to%20discuss%20a%20project."
ADDRESS = "Office 2703, Aspect Tower, Business Bay, Dubai, UAE"
MAP_URL = "https://www.google.com/maps?cid=9389408557797241110&hl=en"
DIRECTIONS_URL = "https://www.google.com/maps/dir/?api=1&destination=Aspect%20Tower%2C%20Business%20Bay%2C%20Dubai"

NAV = [
    ("#home", "Home"),
    ("#services", "Services"),
    ("#about", "About us"),
    ("#contact", "Contact us"),
]

HERO = {
    "kicker": "Engineered in Dubai · Delivered worldwide",
    "title": 'Intelligent systems for <span class="grad-text">ambitious brands.</span>',
    "lead": (
        "Zenovix designs and engineers AI, cloud, and digital experiences — "
        "a global network with the Gulf at its centre."
    ),
}

MARQUEE = [
    "Artificial Intelligence",
    "Cloud &amp; ICT",
    "Web &amp; Mobile",
    "Automation",
    "Data &amp; Analytics",
    "Animation &amp; 3D",
]

# (id, number, title, description, image, bullets)
SERVICES = [
    (
        "ai",
        "01",
        "Artificial Intelligence",
        "Custom models, computer vision, and conversational AI trained on your data and shipped production-ready.",
        "ai.jpg",
        ["Assistants and chatbots on your own knowledge", "Computer vision and document understanding", "Forecasting models, deployed and monitored"],
    ),
    (
        "cloud",
        "02",
        "Cloud &amp; ICT",
        "Secure infrastructure, networks, and systems integration engineered for scale and reliability.",
        "cloud.jpg",
        ["Cloud architecture and migration", "DevOps, CI/CD and observability", "Identity, security hardening and backup"],
    ),
    (
        "web",
        "03",
        "Web &amp; Mobile",
        "Fast, beautiful websites and apps — bilingual EN/AR ready — with motion and detail that convert.",
        "web.jpg",
        ["Corporate sites, landing pages, e-commerce", "iOS and Android apps", "Full RTL support and performance work"],
    ),
    (
        "automation",
        "04",
        "Intelligent Automation",
        "AI agents and workflow automation that remove friction so your team focuses on judgement.",
        "automation.jpg",
        ["Agents on WhatsApp, Telegram, e-mail and web", "Human-in-the-loop approvals", "CRM / ERP / messaging integrations"],
    ),
    (
        "data",
        "05",
        "Data &amp; Analytics",
        "Dashboards and pipelines that turn raw numbers into decisions — accurate and clear.",
        "data.jpg",
        ["Data warehousing and ETL", "BI dashboards and KPI reporting", "Data quality and governance"],
    ),
    (
        "3d",
        "06",
        "Animation &amp; 3D",
        "Brand films, AI video, and interactive 3D that give your technology a story worth watching.",
        "3d.jpg",
        ["Brand films and explainer animation", "AI-generated video and motion graphics", "3D product visualisation and web 3D"],
    ),
]

ABOUT = {
    "kicker": "About us",
    "title": 'A Dubai studio for <span class="grad-text">the digital frontier.</span>',
    "p1": (
        "Zenovix is a team of engineers, designers, and AI specialists building the systems modern "
        "businesses run on. We work like a partner, not a vendor — close to your goals, obsessive about the details."
    ),
    "p2": (
        "From bilingual platforms for the Gulf to AI products for global markets, we turn ambition into "
        "shipped, measurable technology."
    ),
}

VALUES = [
    ("Strategy first.", "We understand the business before we write a line of code."),
    ("Craft in the details.", "Motion, performance, and polish are not optional."),
    ("Built to last.", "Systems that scale and teams that stay with you after launch."),
]

FORM_SERVICES = [
    "Artificial Intelligence",
    "Cloud & ICT",
    "Web & Mobile",
    "Intelligent Automation",
    "Data & Analytics",
    "Animation & 3D",
    "Other",
]

CHAT_SUGGESTIONS = [
    "What services do you offer?",
    "Can you build an AI agent for WhatsApp?",
    "Do you make bilingual EN/AR websites?",
    "How do I start a project?",
]

# ---------------------------------------------------------------------------
# Icons (inline SVG, stroke = currentColor) -----------------------------------
# ---------------------------------------------------------------------------

ICONS = {
    "check": '<path d="M5 12l4 4L19 6"/>',
    "pin": '<path d="M12 21s7-6.2 7-11a7 7 0 0 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "chat": '<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9h8M8 12h5"/>',
    "send": '<path d="M4 12l16-8-6 16-2-6z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "wa": '<path d="M20 11.5a8 8 0 0 1-11.7 7.1L4 20l1.4-4.2A8 8 0 1 1 20 11.5z"/><path d="M9 9.5c.3 2.5 2.6 4.8 5.1 5.1l1.2-1.2-1.8-.9-.9.6a4 4 0 0 1-2.1-2.1l.6-.9-.9-1.8z"/>',
}


def icon(name: str, size: int = 22, cls: str = "") -> str:
    return (
        f'<svg class="ic {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------------------
# CSS — mother-site tokens (indigo, violet→blue gradient, Space Grotesk/Inter)
# ---------------------------------------------------------------------------

CSS = r"""
:root{
  --bg:#0E0A1E;--bg-2:#120D26;--card:#16112A;--card-2:#1c1540;--ink:#F1ECFB;--muted:#A79FBE;--dim:#8A8794;
  --line:rgba(255,255,255,.10);--line-2:rgba(255,255,255,.18);
  --purple:#8A3FE6;--blue:#3B8DF5;--violet:#5B6BF0;--lilac:#C7A9F5;--wa:#25D366;
  --grad:linear-gradient(135deg,#8A3FE6 0%,#5B6BF0 50%,#3B8DF5 100%);
  --grad-soft:linear-gradient(135deg,rgba(138,63,230,.16),rgba(59,141,245,.16));
  --ff-d:"Space Grotesk","Segoe UI",system-ui,sans-serif;--ff-b:"Inter","Segoe UI",system-ui,sans-serif;
  --container:1200px;--r-sm:10px;--r-md:16px;--r-lg:24px;
  --sh-md:0 16px 40px rgba(0,0,0,.35);--sh-lg:0 30px 80px rgba(0,0,0,.45);--glow:0 0 60px rgba(138,63,230,.35);
  --ease:cubic-bezier(.4,0,.2,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%;background:var(--bg)}
body{margin:0;font:16px/1.65 var(--ff-b);color:var(--ink);background:var(--bg);overflow-x:hidden}
h1,h2,h3,h4{font-family:var(--ff-d);color:var(--ink);line-height:1.1;margin:0 0 14px;letter-spacing:-.02em}
h1{font-size:clamp(2.4rem,5.4vw,4.4rem);font-weight:700}
h2{font-size:clamp(1.7rem,3.4vw,2.7rem);font-weight:700}
h3{font-size:1.25rem;font-weight:600}
h4{font-size:1.05rem;font-weight:600}
p{margin:0 0 14px}
a{color:inherit;text-decoration:none}
img{max-width:100%;display:block}
ul{margin:0;padding:0;list-style:none}
.container{width:min(var(--container),calc(100% - 40px));margin:0 auto}
section{padding:110px 0;position:relative}
.skip{position:absolute;left:-999px;top:8px;background:var(--purple);color:#fff;padding:8px 14px;border-radius:6px;z-index:999}
.skip:focus{left:8px}
.grad-text{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.eyebrow{display:inline-flex;align-items:center;gap:10px;font-size:.78rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--lilac);margin-bottom:18px}
.eyebrow::before{content:"";width:26px;height:2px;background:var(--grad);border-radius:2px}
.lead{font-size:1.12rem;color:var(--muted);max-width:60ch}
.section-head{max-width:760px;margin-bottom:56px}
.section-head.center{margin-left:auto;margin-right:auto;text-align:center}
.section-head.center .lead{margin:0 auto}
.center{text-align:center}
.ic{flex:none}

/* ambient glow */
.orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55;pointer-events:none;z-index:0}
.orb.a{width:520px;height:520px;background:rgba(138,63,230,.35);top:-140px;right:-120px}
.orb.b{width:420px;height:420px;background:rgba(59,141,245,.28);bottom:-160px;left:-120px}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:14px 26px;border-radius:999px;font-weight:600;font-size:.95rem;border:1.5px solid transparent;cursor:pointer;transition:transform .25s var(--ease),box-shadow .25s var(--ease),background .25s var(--ease),border-color .25s var(--ease);font-family:var(--ff-b);line-height:1.2}
.btn:hover{transform:translateY(-2px);box-shadow:var(--sh-md)}
.btn-grad{background:var(--grad);color:#fff;box-shadow:0 10px 30px rgba(138,63,230,.35)}
.btn-ghost{border-color:var(--line-2);color:var(--ink);background:rgba(255,255,255,.04)}
.btn-ghost:hover{background:rgba(255,255,255,.09)}
.btn-block{width:100%}
.btn-sm{padding:10px 18px;font-size:.88rem}

/* header */
.site-header{position:fixed;inset:0 0 auto 0;z-index:100;padding:18px 0;transition:background .35s var(--ease),box-shadow .35s var(--ease),padding .35s var(--ease)}
.site-header.scrolled{background:rgba(14,10,30,.88);backdrop-filter:blur(12px);box-shadow:0 8px 30px rgba(0,0,0,.35);padding:10px 0;border-bottom:1px solid var(--line)}
.site-header .container{display:flex;align-items:center;justify-content:space-between;gap:24px}
.brand img{height:40px;width:auto}
.nav-desktop{display:flex;gap:30px}
.nav-desktop a{color:rgba(241,236,251,.82);font-weight:500;font-size:.95rem;position:relative;padding:6px 0}
.nav-desktop a::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--grad);transform:scaleX(0);transform-origin:left;transition:transform .3s var(--ease);border-radius:2px}
.nav-desktop a:hover::after,.nav-desktop a.on::after{transform:scaleX(1)}
.header-cta{display:flex;align-items:center;gap:12px}
.lang-switch{color:rgba(241,236,251,.8);font-weight:600;font-size:.85rem;padding:8px 12px;border:1px solid var(--line-2);border-radius:999px;letter-spacing:.06em}
.btn-login{border-color:var(--line-2);color:var(--ink);background:rgba(255,255,255,.05)}
.btn-login:hover{background:rgba(255,255,255,.12)}
.nav-toggle{display:none;background:none;border:1px solid var(--line-2);color:#fff;border-radius:10px;padding:8px;cursor:pointer}
.nav-mobile{display:none;background:var(--bg-2);padding:14px 20px 24px;border-top:1px solid var(--line)}
.nav-mobile a{display:block;color:#fff;padding:12px 0;border-bottom:1px solid var(--line);font-weight:500}
.nav-mobile .mobile-cta{display:grid;gap:10px;margin-top:16px}
.nav-mobile .mobile-cta a{display:inline-flex;justify-content:center;border-bottom:0;padding:12px 16px}
.nav-mobile.open{display:block}

/* hero */
.hero{position:relative;min-height:100svh;display:flex;align-items:center;overflow:hidden;background:var(--bg);color:#fff;padding:150px 0 110px}
.hero-media{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:right center;z-index:0;opacity:.9}
.hero-overlay{position:absolute;inset:0;z-index:1;background:linear-gradient(90deg,rgba(14,10,30,.96) 0%,rgba(14,10,30,.82) 40%,rgba(14,10,30,.25) 100%),linear-gradient(180deg,rgba(14,10,30,.2) 0%,rgba(14,10,30,0) 40%,rgba(14,10,30,1) 100%)}
.hero .container{position:relative;z-index:2}
.hero-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:56px;align-items:center}
.hero h1{max-width:13ch}
.hero .lead{color:rgba(241,236,251,.8);max-width:52ch;font-size:1.15rem}
.hero-actions{display:flex;gap:14px;flex-wrap:wrap;margin-top:30px}
.hero-card{background:rgba(22,17,42,.72);backdrop-filter:blur(14px);border:1px solid var(--line);border-radius:var(--r-lg);padding:26px;box-shadow:var(--sh-lg)}
.hero-card h4{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.hero-card p{color:var(--muted);font-size:.95rem}
.hero-card .row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}
.hero-card .row button{background:rgba(255,255,255,.05);border:1px solid var(--line);color:var(--ink);border-radius:12px;padding:12px 8px;font:600 .85rem var(--ff-b);cursor:pointer;transition:background .2s,border-color .2s}
.hero-card .row button:hover{background:var(--grad-soft);border-color:var(--purple)}
.hero-scroll{position:absolute;left:50%;bottom:26px;transform:translateX(-50%);z-index:2;color:rgba(255,255,255,.55);font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;display:flex;flex-direction:column;align-items:center;gap:8px}
.hero-scroll .line{width:1px;height:38px;background:linear-gradient(180deg,var(--lilac),transparent);animation:drop 2s infinite}
@keyframes drop{0%{transform:scaleY(0);transform-origin:top}50%{transform:scaleY(1);transform-origin:top}51%{transform-origin:bottom}100%{transform:scaleY(0);transform-origin:bottom}}

/* marquee */
.marquee{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:18px 0;overflow:hidden;background:var(--bg-2)}
.marquee .track{display:flex;gap:56px;width:max-content;animation:scroll 34s linear infinite;font-family:var(--ff-d);font-weight:600;font-size:1rem;color:var(--muted);white-space:nowrap}
.marquee .track span::before{content:"◆";color:var(--purple);margin-right:22px;font-size:.7rem;vertical-align:middle}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.marquee .track{animation:none}}

/* cards */
.grid{display:grid;gap:24px}
.grid-3{grid-template-columns:repeat(3,1fr)}
.grid-2{grid-template-columns:repeat(2,1fr)}
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);overflow:hidden;transition:transform .35s var(--ease),box-shadow .35s var(--ease),border-color .35s var(--ease);display:flex;flex-direction:column}
.card:hover{transform:translateY(-6px);box-shadow:var(--sh-md),var(--glow);border-color:rgba(138,63,230,.7)}
.card .media{aspect-ratio:16/9;overflow:hidden;background:var(--card-2)}
.card .media img{width:100%;height:100%;object-fit:cover;transition:transform .6s var(--ease)}
.card:hover .media img{transform:scale(1.05)}
.card .body{padding:26px 26px 28px;display:flex;flex-direction:column;flex:1}
.card .num{font-family:var(--ff-d);font-weight:700;font-size:.8rem;letter-spacing:.2em;color:var(--lilac);margin-bottom:10px}
.card p{color:var(--muted);flex:1}
.card ul.bul{margin:4px 0 16px;color:var(--ink);font-size:.92rem}
.card ul.bul li{display:flex;gap:8px;margin-bottom:6px;color:var(--muted)}
.card ul.bul li::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--grad);margin-top:9px;flex:none}
.card .more{color:var(--ink);font-weight:600;font-size:.92rem;display:inline-flex;align-items:center;gap:8px;margin-top:6px}
.card .more:hover{color:var(--lilac)}

/* about */
.about-grid{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:center}
.about-media{position:relative;border-radius:var(--r-lg);overflow:hidden;box-shadow:var(--sh-lg);border:1px solid var(--line)}
.about-media img{width:100%;height:100%;object-fit:cover;aspect-ratio:4/3}
.badge{position:absolute;bottom:20px;left:20px;background:rgba(14,10,30,.85);backdrop-filter:blur(8px);color:#fff;padding:14px 18px;border-radius:12px;font-size:.88rem;display:flex;align-items:center;gap:10px;border:1px solid var(--line)}
.badge strong{color:var(--lilac)}
.values{margin:28px 0 8px;display:grid;gap:16px}
.values li{display:flex;gap:14px;align-items:flex-start;font-size:1rem;color:var(--muted)}
.values li b{color:var(--ink);font-family:var(--ff-d)}
.values .dot{flex:0 0 auto;width:12px;height:12px;border-radius:50%;background:var(--grad);margin-top:7px;box-shadow:0 0 14px rgba(138,63,230,.6)}

/* contact */
.contact-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;align-items:start}
.form-card{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);padding:36px;box-shadow:var(--sh-md)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form-grid .full{grid-column:1/-1}
label{display:block;font-size:.85rem;font-weight:600;color:var(--muted);margin-bottom:6px}
input,select,textarea{width:100%;padding:13px 14px;border:1px solid var(--line-2);border-radius:12px;font:inherit;color:var(--ink);background:rgba(255,255,255,.04);transition:border-color .2s,box-shadow .2s}
select option{background:#16112A;color:#fff}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--purple);box-shadow:0 0 0 3px rgba(138,63,230,.25)}
textarea{min-height:130px;resize:vertical}
.hp{position:absolute;left:-9999px;opacity:0;height:0;overflow:hidden}
.form-note{font-size:.82rem;color:var(--dim);margin-top:12px}
.form-msg{display:none;padding:12px 14px;border-radius:12px;font-size:.92rem;margin-bottom:16px}
.form-msg.ok{display:block;background:rgba(37,211,102,.12);color:#9ff3bd;border:1px solid rgba(37,211,102,.35)}
.form-msg.err{display:block;background:rgba(255,80,110,.12);color:#ffb3c1;border:1px solid rgba(255,80,110,.35)}
.direct{display:grid;gap:14px;margin-bottom:22px}
.direct .d{display:flex;gap:16px;align-items:flex-start;padding:18px 20px;background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);transition:border-color .25s,transform .25s}
.direct .d:hover{border-color:var(--purple);transform:translateX(4px)}
.direct .ic-wrap{width:44px;height:44px;border-radius:12px;background:var(--grad-soft);color:var(--lilac);display:flex;align-items:center;justify-content:center;flex:none;border:1px solid var(--line)}
.direct h4{margin-bottom:2px}
.direct p{margin:0;color:var(--muted);font-size:.95rem}
.direct p a:hover{color:var(--lilac)}
.map{position:relative;border-radius:var(--r-lg);overflow:hidden;border:1px solid var(--line);margin-bottom:22px}
.map img{aspect-ratio:16/9;width:100%;object-fit:cover}
.map .links{position:absolute;top:16px;right:16px;display:flex;gap:8px}
.desk{background:var(--grad-soft);border:1px solid var(--line-2);border-radius:var(--r-lg);padding:24px}
.desk h4{display:flex;align-items:center;gap:10px}
.desk p{color:var(--muted);font-size:.95rem}
.desk .acts{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}
.desk .acts button{background:rgba(255,255,255,.05);border:1px solid var(--line);color:var(--ink);border-radius:12px;padding:12px 8px;font:600 .85rem var(--ff-b);cursor:pointer;transition:background .2s,border-color .2s}
.desk .acts button:hover{background:rgba(138,63,230,.25);border-color:var(--purple)}

/* cta band */
.cta-band{background:var(--grad);border-radius:var(--r-lg);padding:56px;display:flex;align-items:center;justify-content:space-between;gap:32px;box-shadow:var(--glow)}
.cta-band h2{color:#fff;margin-bottom:8px}
.cta-band p{color:rgba(255,255,255,.85);margin:0}
.cta-band .btn-ghost{border-color:rgba(255,255,255,.55);color:#fff}
.cta-band .btn-white{background:#fff;color:#1c1540}

/* footer */
.site-footer{background:var(--bg-2);color:var(--muted);padding:70px 0 28px;border-top:1px solid var(--line)}
.footer-grid{display:grid;grid-template-columns:1.6fr 1fr 1fr 1.2fr;gap:40px;margin-bottom:44px}
.footer-brand img{height:40px;width:auto;margin-bottom:18px}
.footer-brand p{color:var(--muted);font-size:.95rem;max-width:36ch}
.footer-col h4{color:#fff;margin-bottom:16px;font-size:.95rem;letter-spacing:.04em}
.footer-col li{margin-bottom:10px;font-size:.93rem}
.footer-col a:hover{color:var(--lilac)}
.footer-bottom{border-top:1px solid var(--line);padding-top:22px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;font-size:.85rem}
.footer-legal{display:flex;gap:20px;align-items:center}
.powered{display:inline-flex;align-items:center;gap:6px;color:var(--lilac)}

/* whatsapp float */
.whatsapp-float{position:fixed;right:22px;bottom:96px;z-index:90;width:56px;height:56px;border-radius:50%;background:var(--wa);display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(37,211,102,.35);transition:transform .25s var(--ease)}
.whatsapp-float:hover{transform:scale(1.08)}

/* chat widget */
.zx-fab{position:fixed;right:22px;bottom:24px;z-index:95;display:inline-flex;align-items:center;gap:10px;padding:14px 20px;border-radius:999px;border:0;background:var(--grad);color:#fff;font:600 .95rem var(--ff-b);cursor:pointer;box-shadow:0 12px 32px rgba(138,63,230,.45);transition:transform .25s var(--ease)}
.zx-fab:hover{transform:translateY(-2px)}
.zx-fab .dot{width:8px;height:8px;border-radius:50%;background:#9ff3bd;box-shadow:0 0 0 4px rgba(159,243,189,.25)}
.zx{position:fixed;right:22px;bottom:90px;z-index:96;width:min(400px,calc(100vw - 32px));max-height:min(620px,calc(100svh - 120px));background:var(--card);border:1px solid var(--line-2);border-radius:20px;box-shadow:var(--sh-lg);display:none;flex-direction:column;overflow:hidden}
.zx.open{display:flex}
.zx-head{display:flex;align-items:center;gap:12px;padding:16px 18px;background:var(--grad);color:#fff}
.zx-head .av{width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-weight:700;font-family:var(--ff-d);border:1px solid rgba(255,255,255,.35)}
.zx-head strong{display:block;font-size:.95rem}
.zx-head span{display:block;font-size:.78rem;color:rgba(255,255,255,.8)}
.zx-head button{margin-left:auto;background:none;border:0;color:#fff;cursor:pointer;padding:6px}
.zx-log{padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;flex:1;min-height:220px;background:var(--bg)}
.msg{max-width:86%;padding:11px 14px;border-radius:14px;font-size:.93rem;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
.msg.bot{background:var(--card-2);color:var(--ink);border:1px solid var(--line);border-bottom-left-radius:4px;align-self:flex-start}
.msg.me{background:var(--grad);color:#fff;border-bottom-right-radius:4px;align-self:flex-end}
.msg.typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--lilac);margin-right:4px;animation:blink 1.2s infinite}
.msg.typing span:nth-child(2){animation-delay:.2s}.msg.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
.zx-sug{display:flex;gap:8px;flex-wrap:wrap;padding:0 16px 12px;background:var(--bg)}
.zx-sug button{background:rgba(255,255,255,.04);border:1px solid var(--line-2);color:var(--ink);border-radius:999px;padding:7px 12px;font:500 .8rem var(--ff-b);cursor:pointer}
.zx-sug button:hover{background:var(--grad-soft);border-color:var(--purple)}
.zx-in{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line);background:var(--card)}
.zx-in input{flex:1;border-radius:999px;padding:12px 16px}
.zx-in button{width:46px;height:46px;border-radius:50%;border:0;background:var(--grad);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center}
.zx-foot{font-size:.74rem;color:var(--dim);padding:0 16px 12px;text-align:center;background:var(--card)}

/* reveal */
.rv{opacity:0;transform:translateY(22px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){.rv{opacity:1;transform:none;transition:none}}

.notice{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(20px + env(safe-area-inset-bottom));z-index:200;background:var(--card-2);color:#fff;border:1px solid var(--line-2);border-radius:12px;padding:12px 16px;font-size:.9rem;box-shadow:var(--sh-lg);max-width:min(520px,calc(100vw - 32px))}
.notice[hidden]{display:none}
.site-header{padding-top:calc(18px + env(safe-area-inset-top))}

/* responsive */
@media (max-width:1100px){.grid-3{grid-template-columns:repeat(2,1fr)}.footer-grid{grid-template-columns:1fr 1fr}}
@media (max-width:900px){
  section{padding:80px 0}
  .nav-desktop,.header-cta .lang-switch,.header-cta .btn-grad{display:none}
  .nav-toggle{display:inline-flex}
  .hero{padding:130px 0 90px;min-height:auto}
  .hero-grid,.about-grid,.contact-grid{grid-template-columns:1fr;gap:36px}
  .hero-media{object-position:70% center}
  .cta-band{flex-direction:column;text-align:center;padding:40px 24px}
}
@media (max-width:640px){
  .grid-3,.grid-2,.form-grid{grid-template-columns:1fr}
  .footer-grid{grid-template-columns:1fr}
  .form-card{padding:24px}
  .zx-fab span.t{display:none}
  .whatsapp-float{bottom:88px;right:16px}
  .zx-fab{right:16px;bottom:16px;padding:14px}
  .zx{right:16px;bottom:80px}
  h1{font-size:2.2rem}
}
"""

# ---------------------------------------------------------------------------
# JS — header, reveal, enquiry form, chat widget --------------------------------
# ---------------------------------------------------------------------------

JS = r"""
(function () {
  var header = document.getElementById("site-header");
  var toggle = document.querySelector(".nav-toggle");
  var mobile = document.querySelector(".nav-mobile");
  function onScroll() { header.classList.toggle("scrolled", window.scrollY > 40 || (mobile && mobile.classList.contains("open"))); }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
  if (toggle && mobile) {
    toggle.addEventListener("click", function () {
      var open = mobile.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      onScroll();
    });
    mobile.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { mobile.classList.remove("open"); onScroll(); }); });
  }
  document.getElementById("year").textContent = new Date().getFullYear();

  // active nav + reveal
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav-desktop a"));
  var sections = links.map(function (a) { return document.querySelector(a.getAttribute("href")); }).filter(Boolean);
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          links.forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id); });
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(function (s) { io.observe(s); });
    var rv = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); rv.unobserve(e.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll(".rv").forEach(function (el) { rv.observe(el); });
  } else {
    document.querySelectorAll(".rv").forEach(function (el) { el.classList.add("in"); });
  }

  // service card → preselect the form
  document.querySelectorAll("[data-service]").forEach(function (a) {
    a.addEventListener("click", function () {
      var sel = document.getElementById("f-service");
      if (sel) { sel.value = a.getAttribute("data-service"); }
    });
  });

  // contact form → /api/public/enquiry
  var form = document.getElementById("enquiry-form");
  if (form) {
    var msg = document.getElementById("form-msg");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var btn = form.querySelector("button[type=submit]");
      var data = {};
      new FormData(form).forEach(function (v, k) { data[k] = String(v); });
      msg.className = "form-msg";
      btn.disabled = true; btn.textContent = "Sending…";
      fetch("/api/public/enquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; }); })
        .then(function (res) {
          if (res.ok && res.body && res.body.ok) {
            msg.className = "form-msg ok";
            msg.textContent = "Thank you — your message has been received (ref " + res.body.reference + "). Our team will be in touch shortly.";
            form.reset();
          } else {
            var detail = (res.body && res.body.detail) || "";
            if (Array.isArray(detail)) { detail = detail.map(function (d) { return d.msg || ""; }).join(" "); }
            msg.className = "form-msg err";
            msg.textContent = res.status === 429 ? "Too many requests — please try again in a few minutes." : ("We couldn't send that. " + (detail || "Please check the form and try again."));
          }
        })
        .catch(function () { msg.className = "form-msg err"; msg.textContent = "Network problem — please e-mail studio@zenovix.com."; })
        .then(function () { btn.disabled = false; btn.textContent = "Send message"; });
    });
  }

  // Zenovix chat widget → /api/public/chat
  var fab = document.getElementById("zx-fab"), panel = document.getElementById("zx"), log = document.getElementById("zx-log");
  var input = document.getElementById("zx-input"), send = document.getElementById("zx-send"), sug = document.getElementById("zx-sug");
  var session = ""; try { session = sessionStorage.getItem("zx-session") || ""; } catch (e) {}
  function add(kind, text) {
    var d = document.createElement("div"); d.className = "msg " + kind; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
  }
  function typing() { var d = document.createElement("div"); d.className = "msg bot typing"; d.innerHTML = "<span></span><span></span><span></span>"; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
  function open(state) { panel.classList.toggle("open", state); fab.setAttribute("aria-expanded", state ? "true" : "false"); if (state) { input.focus(); } }
  fab.addEventListener("click", function () { open(!panel.classList.contains("open")); });
  document.getElementById("zx-close").addEventListener("click", function () { open(false); });
  document.querySelectorAll("[data-open-chat]").forEach(function (el) { el.addEventListener("click", function (ev) { ev.preventDefault(); open(true); }); });
  function ask(text) {
    text = (text || "").trim(); if (!text) { return; }
    add("me", text); input.value = ""; sug.style.display = "none";
    var t = typing(); send.disabled = true;
    fetch("/api/public/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, session: session }) })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
      .then(function (res) {
        t.remove();
        if (res.body && res.body.session) { session = res.body.session; try { sessionStorage.setItem("zx-session", session); } catch (e) {} }
        if (res.body && res.body.reply) { add("bot", res.body.reply); }
        else if (res.status === 429) { add("bot", "You're sending messages quickly — please wait a moment and try again."); }
        else { add("bot", "I'm having trouble right now. Please use the contact form or e-mail studio@zenovix.com."); }
      })
      .catch(function () { t.remove(); add("bot", "Network problem — please try again."); })
      .then(function () { send.disabled = false; input.focus(); });
  }
  send.addEventListener("click", function () { ask(input.value); });
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") { ask(input.value); } });
  sug.querySelectorAll("button").forEach(function (b) { b.addEventListener("click", function () { ask(b.textContent); }); });
})();
"""

# ---------------------------------------------------------------------------
# HTML ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def nav_links(cls: str = "") -> str:
    return "".join(f'<a href="{h}"{cls}>{t}</a>' for h, t in NAV)


def services_cards() -> str:
    out = []
    for sid, num, title, desc, img, bullets in SERVICES:
        out.append(
            f'<article class="card rv" id="svc-{sid}">'
            f'<div class="media"><img src="/web/assets/img/{img}" alt="{html.escape(html.unescape(title))}" loading="lazy" width="1200" height="675"></div>'
            f'<div class="body"><div class="num">{num}</div>'
            f"<h3>{title}</h3><p>{desc}</p>"
            f'<ul class="bul">{"".join(f"<li>{b}</li>" for b in bullets)}</ul>'
            f'<a class="more" href="#contact" data-service="{html.escape(html.unescape(title))}">Start a project {icon("arrow", 16)}</a>'
            "</div></article>"
        )
    return "".join(out)


def page() -> str:
    services_options = "".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in FORM_SERVICES
    )
    marquee = "".join(f"<span>{m}</span>" for m in MARQUEE + MARQUEE)
    values = "".join(
        f'<li><span class="dot"></span><span><b>{t}</b> {d}</span></li>' for t, d in VALUES
    )
    suggestions = "".join(
        f'<button type="button">{html.escape(s)}</button>' for s in CHAT_SUGGESTIONS
    )
    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0E0A1E">
<title>{COMPANY} — {TAGLINE}</title>
<meta name="description" content="Zenovix designs and engineers AI, cloud, and digital experiences — a Dubai studio for artificial intelligence, cloud &amp; ICT, web &amp; mobile, intelligent automation, data &amp; analytics, and animation &amp; 3D.">
<meta property="og:title" content="{COMPANY} — {TAGLINE}">
<meta property="og:description" content="Intelligent systems for ambitious brands. Engineered in Dubai · Delivered worldwide.">
<meta property="og:image" content="/web/assets/img/hero.jpg">
<meta property="og:type" content="website">
<link rel="icon" href="/web/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header" id="site-header">
  <div class="container">
    <a class="brand" href="#home" aria-label="{COMPANY} — home"><img src="/web/assets/brand/zenovix-logo-white.png" alt="{COMPANY}" width="780" height="278"></a>
    <nav class="nav-desktop" aria-label="Primary">{nav_links()}</nav>
    <div class="header-cta">
      <a class="lang-switch" href="https://zenovix.ae/?lang=ar" hreflang="ar" lang="ar" title="Arabic site">AR</a>
      <a class="btn btn-grad btn-sm" href="#contact">Start a project</a>
      <a class="btn btn-login btn-sm" id="login-link" data-admin-login href="/admin/ops/login.html" aria-label="Manager login">{icon("lock", 18)}<span>Login</span></a>
      <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="nav-mobile">{icon("menu", 22)}</button>
    </div>
  </div>
  <div class="nav-mobile" id="nav-mobile">
    {nav_links()}
    <div class="mobile-cta">
      <a class="btn btn-grad btn-block" href="#contact">Start a project</a>
      <a class="btn btn-ghost btn-block" href="/admin/ops/login.html" data-admin-login>{icon("lock", 18)} Manager login</a>
      <a class="lang-switch center" href="https://zenovix.ae/?lang=ar" lang="ar">العربية</a>
    </div>
  </div>
</header>

<main id="main">

<section class="hero" id="home">
  <img class="hero-media" src="/web/assets/img/hero.jpg" alt="" fetchpriority="high" width="1600" height="685">
  <div class="hero-overlay"></div>
  <div class="container">
    <div class="hero-grid">
      <div>
        <p class="eyebrow">{HERO["kicker"]}</p>
        <h1>{HERO["title"]}</h1>
        <p class="lead">{HERO["lead"]}</p>
        <div class="hero-actions">
          <a class="btn btn-grad" href="#contact">Start a project</a>
          <a class="btn btn-ghost" href="#services">Explore services</a>
          <a class="btn btn-ghost" href="#" data-open-chat>{icon("chat", 18)} Ask Zenovix</a>
        </div>
      </div>
      <div class="hero-card rv in">
        <h4>{icon("spark", 18)} Zenovix digital desk</h4>
        <p>Services, project enquiries and support in one chat — on the web, WhatsApp and Telegram. Proposals and anything sensitive always wait for a manager.</p>
        <div class="row">
          <button type="button" data-action="products">Services</button>
          <button type="button" data-action="support">Support</button>
          <button type="button" data-action="quote">Quote</button>
        </div>
        <a class="btn btn-grad btn-sm btn-block" href="/app">Start a conversation</a>
      </div>
    </div>
  </div>
  <div class="hero-scroll"><span>Scroll</span><span class="line"></span></div>
</section>

<div class="marquee" aria-hidden="true"><div class="track">{marquee}</div></div>

<section id="services">
  <div class="orb a"></div>
  <div class="container">
    <div class="section-head rv">
      <p class="eyebrow">Services</p>
      <h2>Everything you need to build <span class="grad-text">the intelligent product.</span></h2>
      <p class="lead">One partner for strategy, design, engineering, and the AI that ties it together.</p>
    </div>
    <div class="grid grid-3">{services_cards()}</div>
  </div>
</section>

<section id="about">
  <div class="orb b"></div>
  <div class="container">
    <div class="about-grid">
      <div class="rv">
        <p class="eyebrow">{ABOUT["kicker"]}</p>
        <h2>{ABOUT["title"]}</h2>
        <p class="lead">{ABOUT["p1"]}</p>
        <p class="lead">{ABOUT["p2"]}</p>
        <ul class="values">{values}</ul>
        <a class="btn btn-grad" href="#contact">Talk to the studio</a>
      </div>
      <div class="about-media rv">
        <img src="/web/assets/img/studio.jpg" alt="Zenovix studio, Business Bay, Dubai" loading="lazy" width="1200" height="900">
        <div class="badge">{icon("pin", 18)}<span><strong>Business Bay</strong> · Dubai, UAE</span></div>
      </div>
    </div>
  </div>
</section>

<section id="contact">
  <div class="container">
    <div class="section-head rv">
      <p class="eyebrow">Contact us</p>
      <h2>Let's build something <span class="grad-text">unmistakable.</span></h2>
      <p class="lead">Tell us where your business is going. We'll design the intelligence and the experience that takes it there.</p>
    </div>
    <div class="contact-grid">
      <div class="form-card rv" id="quote">
        <h3>Tell us about your project</h3>
        <div class="form-msg" id="form-msg" role="status" aria-live="polite"></div>
        <form id="enquiry-form" novalidate>
          <div class="form-grid">
            <div><label for="f-name">Name *</label><input id="f-name" name="name" required minlength="2" maxlength="120" autocomplete="name"></div>
            <div><label for="f-company">Company</label><input id="f-company" name="company" maxlength="160" autocomplete="organization"></div>
            <div><label for="f-email">Email *</label><input id="f-email" name="email" type="email" required maxlength="254" autocomplete="email"></div>
            <div><label for="f-phone">Phone</label><input id="f-phone" name="phone" type="tel" maxlength="40" autocomplete="tel" placeholder="+971 …"></div>
            <div class="full"><label for="f-service">Service *</label><select id="f-service" name="service" required><option value="">Select a service</option>{services_options}</select></div>
            <div class="full"><label for="f-message">Project *</label><textarea id="f-message" name="message" required minlength="10" maxlength="4000" placeholder="What do you want to build, for whom, and by when?"></textarea></div>
            <div class="hp" aria-hidden="true"><label for="f-website">Website</label><input id="f-website" name="website" tabindex="-1" autocomplete="off"></div>
          </div>
          <div style="margin-top:18px"><button class="btn btn-grad" type="submit">Send message</button></div>
          <p class="form-note">By sending, you agree to be contacted by Zenovix about your project. We do not share your details with third parties.</p>
        </form>
      </div>
      <div class="rv">
        <div class="direct">
          <div class="d"><div class="ic-wrap">{icon("mail", 20)}</div><div><h4>Email us</h4><p><a href="mailto:{EMAIL}">{EMAIL}</a></p></div></div>
          <div class="d"><div class="ic-wrap">{icon("phone", 20)}</div><div><h4>Call us</h4><p><a href="tel:{PHONE_TEL}">{PHONE}</a></p></div></div>
          <div class="d"><div class="ic-wrap">{icon("wa", 20)}</div><div><h4>WhatsApp</h4><p><a href="{WHATSAPP}" target="_blank" rel="noopener">Chat on WhatsApp</a></p></div></div>
          <div class="d"><div class="ic-wrap">{icon("pin", 20)}</div><div><h4>Find us</h4><p>{ADDRESS}</p></div></div>
          <div class="d"><div class="ic-wrap">{icon("clock", 20)}</div><div><h4>Studio hours</h4><p>Mon–Fri, 9:00–18:00 GST (UTC+4)</p></div></div>
        </div>
        <div class="map">
          <img src="/web/assets/img/studio.jpg" alt="Aspect Tower, Business Bay, Dubai" loading="lazy" width="1200" height="900">
          <div class="links"><a class="btn btn-ghost btn-sm" href="{DIRECTIONS_URL}" target="_blank" rel="noopener">Get directions</a><a class="btn btn-ghost btn-sm" href="{MAP_URL}" target="_blank" rel="noopener">Open in Maps</a></div>
          <div class="badge">{icon("pin", 18)}<span><strong>Aspect Tower</strong>, Business Bay</span></div>
        </div>
        <div class="desk">
          <h4>{icon("spark", 18)} Zenovix digital desk — on Telegram too</h4>
          <p>Services, project enquiries and support in one chat. Proposals and sensitive mail always wait for a manager.</p>
          <div class="acts">
            <button type="button" data-action="products">Services</button>
            <button type="button" data-action="support">Support</button>
            <button type="button" data-action="quote">Quote</button>
          </div>
          <a class="btn btn-grad btn-sm btn-block" href="/app">Start a conversation</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section style="padding-top:0">
  <div class="container">
    <div class="cta-band rv">
      <div>
        <h2>Ready to build with a partner, not a vendor?</h2>
        <p>Tell us where your business is going — we'll come back with next steps, usually the same business day.</p>
      </div>
      <div class="cta-actions" style="display:flex;gap:12px;flex-wrap:wrap">
        <a class="btn btn-white" href="#contact">Start a project</a>
        <a class="btn btn-ghost" href="{WHATSAPP}" target="_blank" rel="noopener">Chat on WhatsApp</a>
      </div>
    </div>
  </div>
</section>

</main>

<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <img src="/web/assets/brand/zenovix-logo-white.png" alt="{COMPANY}" width="780" height="278">
        <p>A Dubai studio for AI and digital technology. Engineered in Dubai · Delivered worldwide.</p>
      </div>
      <div class="footer-col"><h4>Company</h4><ul>
        <li><a href="#services">Services</a></li><li><a href="#about">About us</a></li><li><a href="#contact">Contact us</a></li>
      </ul></div>
      <div class="footer-col"><h4>Services</h4><ul>
        <li><a href="#svc-ai">Artificial Intelligence</a></li><li><a href="#svc-cloud">Cloud &amp; ICT</a></li><li><a href="#svc-web">Web &amp; Mobile</a></li><li><a href="#svc-automation">Intelligent Automation</a></li><li><a href="#svc-data">Data &amp; Analytics</a></li><li><a href="#svc-3d">Animation &amp; 3D</a></li>
      </ul></div>
      <div class="footer-col"><h4>Contact</h4><ul>
        <li><a href="mailto:{EMAIL}">{EMAIL}</a></li><li><a href="tel:{PHONE_TEL}">{PHONE}</a></li><li>{ADDRESS}</li>
        <li><a href="/admin/ops/login.html" data-admin-login>Manager login</a></li>
      </ul></div>
    </div>
    <div class="footer-bottom">
      <span>© <span id="year"></span> {COMPANY}. Crafted with intelligence in Dubai.</span>
      <div class="footer-legal"><a href="https://zenovix.ae" rel="noopener">zenovix.ae</a><span class="powered">{icon("spark", 14)} Zenovix digital desk</span></div>
    </div>
  </div>
</footer>

<a class="whatsapp-float" href="{WHATSAPP}" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">
  <svg width="30" height="30" viewBox="0 0 32 32" fill="#fff" aria-hidden="true"><path d="M16 3C9 3 3.4 8.6 3.4 15.6c0 2.4.7 4.7 1.9 6.7L3 29l6.9-2.2c1.9 1 4 1.6 6.1 1.6 7 0 12.6-5.6 12.6-12.6S23 3 16 3zm0 22.9c-1.9 0-3.8-.5-5.4-1.5l-.4-.2-4.1 1.3 1.3-3.9-.3-.4a10.3 10.3 0 1 1 8.9 4.7zm5.7-7.7c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7.1a8.4 8.4 0 0 1-4.2-3.7c-.3-.5.3-.5.9-1.6.1-.2 0-.4 0-.5l-1-2.3c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4s-1 1-1 2.5 1.1 2.9 1.2 3.1c.2.2 2.1 3.2 5.1 4.5 1.9.8 2.6.9 3.6.7.6-.1 1.8-.7 2-1.4.3-.7.3-1.3.2-1.4l-.5-.3z"/></svg>
</a>

<div class="notice" id="notice" role="status" hidden></div>
<button class="zx-fab" id="zx-fab" type="button" aria-expanded="false" aria-controls="zx">{icon("chat", 20)} <span class="t">Ask Zenovix</span> <span class="dot" aria-hidden="true"></span></button>
<div class="zx" id="zx" role="dialog" aria-label="Ask Zenovix — studio assistant">
  <div class="zx-head">
    <div class="av">Z</div>
    <div><strong>Zenovix · Digital Operations Desk</strong><span>Answers from Zenovix's approved knowledge · English first</span></div>
    <button type="button" id="zx-close" aria-label="Close chat">{icon("close", 20)}</button>
  </div>
  <div class="zx-log" id="zx-log">
    <div class="msg bot">Hello — I'm Zenovix, the studio's digital operations desk. Ask me about AI, cloud &amp; ICT, web &amp; mobile, automation, data or animation &amp; 3D. For proposals and anything sensitive I'll hand over to a manager.</div>
  </div>
  <div class="zx-sug" id="zx-sug">{suggestions}</div>
  <div class="zx-in">
    <input id="zx-input" type="text" maxlength="2000" placeholder="Type your question…" autocomplete="off" aria-label="Your question">
    <button type="button" id="zx-send" aria-label="Send">{icon("send", 20)}</button>
  </div>
  <div class="zx-foot">Zenovix answers from approved company data only. Proposals, contracts and payments always go to a manager.</div>
</div>

<!-- Login → /admin/ops/login.html → after sign-in the console opens at /admin/ops/ecosystem.html.
     Inside Telegram, verified admins get one-tap login (data-admin-login) via /admin/api/twa/login.
     The hidden TWA hook below is upgraded by /web/js/public.js only when Telegram initData is present. -->
<span id="twa-hook" hidden data-admin-target="/admin/ops/ecosystem.html"></span>
<script>{JS}</script>
<script src="/web/js/public.js" defer></script>
</body>
</html>
"""


def main() -> None:
    OUT.write_text(page(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
