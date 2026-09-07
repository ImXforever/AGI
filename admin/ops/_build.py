#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ICONS = {
    "dash": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "inbox": '<path d="M3 7h18v12H3z"/><path d="M3 7l9 6 9-6"/>',
    "queue": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1.6"/><circle cx="4" cy="12" r="1.6"/><circle cx="4" cy="18" r="1.6"/>',
    "web": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    "social": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 19v2h8v-2"/>',
    "sales": '<path d="M4 16l5-5 4 3 7-8"/><path d="M14 6h6v6"/>',
    "support": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 015 1c0 2-2.5 2-2.5 4"/><circle cx="12" cy="17" r=".8"/>',
    "ops": '<path d="M12 3l2 4 4 .6-3 3 .8 4.4L12 13l-3.8 2 0.8-4.4-3-3 4-.6z"/>',
    "know": '<path d="M5 5h9a3 3 0 013 3v13H8a3 3 0 00-3 3V5z"/><path d="M14 5v16"/>',
    "ctrl": '<path d="M12 8a4 4 0 100 8 4 4 0 000-8z"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    "audit": '<path d="M8 4h8v16H8z"/><path d="M11 8h5M11 12h5M11 16h3"/>',
    "auto": '<circle cx="12" cy="12" r="3"/><path d="M12 5v2M12 17v2M5 12h2M17 12h2"/>',
    "brain": '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="10.5"/>',
    "live": '<circle cx="12" cy="12" r="3"/><path d="M3 12h4M17 12h4M12 3v4M12 17v4"/>',
    "insights": '<path d="M4 18V8M10 18V4M16 18v-6M20 18H3"/>',
    "market": '<path d="M6 7h12l-1 12H7L6 7z"/><path d="M9 7V5a3 3 0 016 0v2"/>',
    "hub": '<circle cx="8" cy="8" r="2.5"/><circle cx="16" cy="8" r="2.5"/><circle cx="12" cy="16" r="2.5"/><path d="M10 9l2 5M14 9l-2 5"/>',
    "soul": '<path d="M12 21s-7-4.4-9.3-8.6C.9 9 3 5 6.8 5c2 0 3.4 1.1 4.2 2.3h2C13.8 6.1 15.2 5 17.2 5 21 5 23.1 9 21.3 12.4 19 16.6 12 21 12 21z"/><circle cx="9.5" cy="11" r="1"/><circle cx="14.5" cy="11" r="1"/>',
    "sim": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/><circle cx="17" cy="16" r="3"/><path d="M17 14.5v1.5l1 1"/>',
    "db": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "eco": '<circle cx="12" cy="12" r="2.2"/><circle cx="12" cy="12" r="6.5"/><circle cx="12" cy="4" r="1.4"/><circle cx="19" cy="12" r="1.4"/><circle cx="5" cy="12" r="1.4"/><circle cx="16.5" cy="18.2" r="1.4"/><circle cx="7.5" cy="18.2" r="1.4"/>',
}

NAV = [
    ("Command", [
        ("ecosystem.html", "Ecosystem", "eco"),
        ("index.html", "Desk", "dash"),
        ("queue.html", "Approvals", "queue"),
        ("catalog.html", "Catalog", "market"),
        ("settings.html", "Variables", "ctrl"),
        ("soul.html", "Soul", "soul"),
        ("simulator.html", "Simulator", "sim"),
        ("database.html", "Database", "db"),
    ]),
]

# Kept for power users, collapsed under "More" in the rail (1.4.0: the
# first screen a manager sees has six doors, not twenty-one).
NAV_MORE = [
    ("charter.html", "Charter", "ctrl"),
    ("inbox.html", "Inbox", "inbox"),
    ("website.html", "Website flow", "web"),
    ("social.html", "Social flow", "social"),
    ("sales.html", "Sales flow", "sales"),
    ("support.html", "Support flow", "support"),
    ("operations.html", "Operations", "ops"),
    ("knowledge.html", "Knowledge", "know"),
    ("brain.html", "Knowledge brain", "brain"),
    ("control.html", "Control", "ctrl"),
    ("audit.html", "Audit", "audit"),
    ("automation.html", "Automation", "auto"),
    ("live.html", "Live", "live"),
    ("insights.html", "Insights", "insights"),
    ("market.html", "Market", "market"),
    ("hub.html", "Hub", "hub"),
]


def icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">{ICONS[name]}</svg>'


def flow_nav(steps: list[tuple[str, str, str]], current: str) -> str:
    keys = [s[0] for s in steps]
    cur_i = keys.index(current) if current in keys else 0
    bits = ['<nav class="flow" aria-label="Work flow">']
    for i, (key, label, href) in enumerate(steps):
        if i:
            bits.append('<span class="arrow">→</span>')
        cls = "on" if i == cur_i else ("done" if i < cur_i else "")
        bits.append(f'<a class="{cls}" href="{href}"><span class="n">{i + 1}</span>{label}</a>')
    bits.append("</nav>")
    return "".join(bits)


CSS = (ROOT / "ops.css").read_text(encoding="utf-8")
JS = (ROOT / "ops.js").read_text(encoding="utf-8")
LOGIN_IMG = (ROOT / "assets" / "login.jpg.b64").read_text(encoding="utf-8").strip()

THEME_JS = """
<script>
(function () {
  var KEY = "zenovix-theme", THEMES = ["light", "dark", "gray", "neon"];
  function apply(t) {
    if (THEMES.indexOf(t) < 0) t = "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(KEY, t); } catch (e) {}
    document.querySelectorAll(".theme-switch button").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-theme") === t);
    });
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  apply(saved || "dark");
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest(".theme-switch button");
    if (b) { ev.preventDefault(); apply(b.getAttribute("data-theme")); }
  });
})();
</script>
"""

EMAIL = [
    ("capture", "Capture", "inbox.html"),
    ("classify", "Classify", "inbox.html"),
    ("reply", "Reply / draft", "inbox.html"),
    ("follow", "Follow-up", "inbox.html"),
    ("esc", "Escalate", "queue.html"),
]
WEB = [
    ("form", "Form", "website.html"),
    ("lead", "Lead", "website.html"),
    ("edit", "Edit page", "website.html"),
    ("gate", "Policy gate", "queue.html"),
    ("pub", "Publish", "website.html"),
]
SOC = [
    ("plan", "Plan", "social.html"),
    ("caption", "Caption", "social.html"),
    ("sched", "Schedule", "social.html"),
    ("pub", "Publish", "social.html"),
    ("hold", "Hold claims", "queue.html"),
]
SALES = [
    ("lead", "Lead", "sales.html"),
    ("qual", "Qualify", "sales.html"),
    ("quote", "Quote", "sales.html"),
    ("send", "Manager send", "queue.html"),
    ("order", "Order", "sales.html"),
]
SUP = [
    ("req", "Request", "support.html"),
    ("ticket", "Ticket", "support.html"),
    ("first", "First line", "support.html"),
    ("sla", "SLA", "support.html"),
    ("esc", "Escalate", "queue.html"),
]
OPS = [
    ("extract", "Extract", "operations.html"),
    ("remind", "Remind", "operations.html"),
    ("coord", "Coordinate", "operations.html"),
    ("report", "Report", "operations.html"),
]
KNOW = [
    ("draft", "Draft", "knowledge.html"),
    ("review", "Review", "knowledge.html"),
    ("approve", "Approve", "knowledge.html"),
    ("index", "Index", "knowledge.html"),
    ("brain", "Atomic brain", "brain.html"),
]
CTRL = [
    ("matrix", "Matrix", "control.html"),
    ("roles", "Roles", "control.html"),
    ("audit", "Audit", "audit.html"),
    ("future", "Future agents", "control.html"),
]
APPR = [
    ("queue", "Queue", "queue.html"),
    ("review", "Review", "queue.html"),
    ("decide", "Decide", "queue.html"),
    ("run", "Execute", "queue.html"),
    ("audit", "Audit", "audit.html"),
]


THEME_SWITCH = """<div class="theme-switch" id="theme-switch" role="group" aria-label="Theme">
  <button type="button" data-theme="light" title="Light" aria-label="Light theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>
  <button type="button" data-theme="dark" title="Dark" aria-label="Dark theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z"/></svg></button>
  <button type="button" data-theme="gray" title="Gray" aria-label="Gray theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 3v18"/><path d="M12 3a9 9 0 010 18z" fill="currentColor" stroke="none"/></svg></button>
  <button type="button" data-theme="neon" title="Neon" aria-label="Neon theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg></button>
</div>"""

THEME_BOOT = """<script>(function(){try{var t=localStorage.getItem("zenovix-theme");if(!t){t="dark";}document.documentElement.setAttribute("data-theme",t);}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();</script>"""


def shell(active: str, title: str, body: str, *, bare: bool = False, flow: str = "", extra_scripts: str = "") -> str:
    nav = []
    for group, items in NAV:
        nav.append(f'<div class="nav-label">{group}</div>')
        for href, label, ic in items:
            on = "on" if href == active else ""
            nav.append(f'<a class="{on}" href="{href}">{icon(ic)}{label}</a>')
    more_open = " open" if any(href == active for href, _, _ in NAV_MORE) else ""
    nav.append(f'<details class="nav-more"{more_open}><summary>More</summary>')
    for href, label, ic in NAV_MORE:
        on = "on" if href == active else ""
        nav.append(f'<a class="{on}" href="{href}">{icon(ic)}{label}</a>')
    nav.append("</details>")
    inner = body if bare else f'<div class="page">{body}</div>'
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0b0f1a">
<title>{title} · Zenovix Ops</title>
{THEME_BOOT}
<style>
{CSS}
</style>
</head>
<body>
<div class="app">
  <aside class="rail">
    <div class="mark">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="var(--panel-2)"/>
        <rect x="7" y="7" width="8" height="8" rx="2" fill="var(--cyan)"/>
        <rect x="17" y="7" width="8" height="8" rx="2" fill="var(--mag)"/>
        <rect x="12" y="17" width="8" height="8" rx="2" fill="var(--ice)"/>
      </svg>
      <div>
        <div class="name">Zenovix Ops</div>
        <div class="sub">Manager console</div>
      </div>
    </div>
    <nav class="nav">{"".join(nav)}</nav>
    <div class="rail-foot">Zenovix answers on its own. Quotes, payments, contracts, price changes and deletions wait for your tap.</div>
  </aside>
  <div class="stage">
    <header class="bar">
      <h1>{title}</h1>
      <div class="bar-right">
        <button class="btn menu-btn" type="button" aria-label="Open menu">Menu</button>
        <input class="search" placeholder="Ctrl+K to jump" aria-label="Search">
        <span class="chip ok"><span class="dot"></span> Live</span>
        <span class="chip warn" id="awaiting-chip">Queue</span>
        {THEME_SWITCH}
        <a class="btn ghost" href="/" data-logout>Sign out</a>
        <span class="chip" id="whoami">Manager</span>
      </div>
    </header>
    <div class="ticker"><span>Zenovix Ops 1.6.0 · Ctrl+K jump · English-first · USD · simulator = the real bot · database export/import as versioned JSON · /admin commands in Telegram · payment / contract / delete never auto</span></div>
    {flow}
    {inner}
  </div>
</div>
<script>
{JS}
</script>
</body>
</html>
"""


PAGES: dict[str, tuple] = {}

ECO = [
    ("eco", "Ecosystem", "ecosystem.html"),
    ("desk", "Desk", "index.html"),
    ("queue", "Approvals", "queue.html"),
]

PAGES["ecosystem.html"] = ("Ecosystem", True, flow_nav(ECO, "eco"), """
<div id="eco-stage" class="brain-stage">
  <div class="desk-cta">
    <div class="ph">Start here</div>
    <div class="big">Your desk has <span id="cta-pending">…</span> waiting</div>
    <p>Approve or reject requests, read conversations, add products and change what the bot says — all from five pages.</p>
    <a class="btn primary" href="index.html">Open the desk</a>
  </div>
  <canvas id="eco-gl"></canvas>
  <canvas id="eco-hud"></canvas>
  <div id="eco-stats">Ecosystem online…</div>
  <aside class="brain-dock" id="eco-dock"></aside>
  <div id="eco-log" class="eco-log" aria-live="polite"></div>
  <div class="brain-tools">
    <button class="btn primary" id="eco-burst" type="button">Burst ×1</button>
    <button class="btn" id="eco-pause" type="button">Pause</button>
    <button class="btn ghost" id="eco-core" type="button">Select orchestrator</button>
  </div>
</div>
""")

PAGES["charter.html"] = ("Charter", False, flow_nav(ECO, "eco"), """
<p class="kicker">v21 · employer charter as code · one orchestrator · six specialists · HITL locked</p>
<div class="g g2">
  <section class="card">
    <h2>Role</h2>
    <p>You are the company's digital operations manager. You handle email, the website, social media and day-to-day work. You know the company knowledge. You follow up. You report. You ask the manager before any important decision.</p>
    <p class="mini">Payments, contracts, price changes, deletions and access changes never run without a manager record.</p>
  </section>
  <section class="card">
    <h2>Building blocks</h2>
    <div class="row rail-card ok"><div><b>LLM brain</b><div style="color:var(--dim)">Understand orders, plan steps, never invent prices</div></div><span class="tag ice">core</span></div>
    <div class="row rail-card ok"><div><b>Tool connectors</b><div style="color:var(--dim)">Email, site, social, CRM, calendar, files</div></div><span class="tag ice">connectors</span></div>
    <div class="row rail-card ok"><div><b>Knowledge base</b><div style="color:var(--dim)">Products, prices, tone, FAQ, instructions</div></div><span class="tag ice">rag</span></div>
    <div class="row rail-card ok"><div><b>Workflows + HITL + reports</b><div style="color:var(--dim)">Rules, audit, daily / weekly digest</div></div><span class="tag ice">govern</span></div>
  </section>
</div>
<section class="card" style="margin-top:12px">
  <h2>Access matrix</h2>
  <table class="table matrix">
    <thead><tr><th>Work</th><th>Mode</th><th>Action</th></tr></thead>
    <tbody>
      <tr><td>Read and classify email</td><td><span class="tag auto">auto</span></td><td>read_email / classify_email</td></tr>
      <tr><td>Answer common questions under rules</td><td><span class="tag auto">auto</span></td><td>reply_common</td></tr>
      <tr><td>Send sensitive or important email</td><td><span class="tag hold">manager</span></td><td>send_email</td></tr>
      <tr><td>Publish ordinary calendar content</td><td><span class="tag auto">auto</span></td><td>publish_calendar</td></tr>
      <tr><td>Sensitive or off-calendar publish</td><td><span class="tag hold">manager</span></td><td>publish_content</td></tr>
      <tr><td>Change price or sensitive site data</td><td><span class="tag never">manager</span></td><td>change_price</td></tr>
      <tr><td>Payment, contract, money transfer</td><td><span class="tag never">manager only</span></td><td>payment / contract</td></tr>
      <tr><td>Delete data or change user access</td><td><span class="tag never">manager only</span></td><td>delete_data / change_access</td></tr>
    </tbody>
  </table>
</section>
<div class="g g3" style="margin-top:12px">
  <section class="card"><h2>Phase 1</h2><p>Email + company knowledge.</p></section>
  <section class="card"><h2>Phase 2</h2><p>Website + contact forms.</p></section>
  <section class="card"><h2>Phase 3</h2><p>Social + content calendar.</p></section>
  <section class="card"><h2>Phase 4</h2><p>CRM, sales and support.</p></section>
  <section class="card"><h2>Phase 5</h2><p>Reporting, QA, advanced automation.</p></section>
  <section class="card"><h2>Later</h2><p>Accounting, HR, content studio, projects — declared, inactive.</p></section>
</div>
<p class="mini" style="margin-top:14px">Live JSON: <code>GET /admin/api/charter</code></p>
""")


PAGES["index.html"] = ("Desk", False, "", """
<div id="desk">
<div class="desk-head">
  <div>
    <div class="label">Manager desk</div>
    <div class="title">Today</div>
    <div class="sub">What needs you, what Zenovix handled, and whether everything is up. Refreshes every 15 seconds.</div>
  </div>
  <div class="h-metrics">
    <div class="metric"><div class="k">Waiting for you</div><div class="v" id="m-pending">–</div></div>
    <div class="metric"><div class="k">Messages 24h</div><div class="v" id="m-msgs">–</div></div>
    <div class="metric"><div class="k">Active chats</div><div class="v" id="m-active">–</div></div>
    <div class="metric"><div class="k">Approved 24h</div><div class="v good" id="m-approved">–</div></div>
    <div class="metric"><div class="k">Open tickets</div><div class="v" id="m-tickets">–</div></div>
    <div class="clock"><span class="blink"></span><span id="desk-clock"></span></div>
  </div>
</div>
<div class="desk-grid">
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph">Needs your decision</span><span class="hint">Approve sends the confirmation to the customer · Reject sends a polite decline</span></div>
      <div class="panel-body" id="desk-pending"><div class="empty">Loading…</div></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Latest conversations</span><span class="hint">tap a row to read the whole thread</span></div>
      <div class="panel-body" id="desk-recent"><div class="empty">Loading…</div></div>
    </section>
  </div>
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph">Traffic</span><span class="hint">messages per hour</span></div>
      <div class="panel-body" id="desk-spark" style="color:var(--cyan)"><div class="empty">Loading…</div></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">System</span><span class="hint">green = fine</span></div>
      <div class="panel-body" id="desk-system"><div class="empty">Loading…</div></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Quick doors</span></div>
      <div class="panel-body chips">
        <a class="chip" href="catalog.html"><b>+</b> Add a product</a>
        <a class="chip" href="settings.html"><b>⚙</b> Bot menu &amp; contact details</a>
        <a class="chip" href="soul.html"><b>♥</b> How Zenovix talks</a>
        <a class="chip" href="queue.html"><b>≡</b> Full approvals list</a>
        <a class="chip" href="/app" target="_blank" rel="noopener"><b>↗</b> Customer app</a>
      </div>
    </section>
  </div>
</div>
</div>
""")

PAGES["inbox.html"] = ("Inbox", True, flow_nav(EMAIL, "reply"), """
<div class="split3">
  <aside class="pane">
    <div class="filters" id="filters">
      <button class="filter on" data-filter="all" type="button">All 9</button>
      <button class="filter" data-filter="sales" type="button">Sales</button>
      <button class="filter" data-filter="support" type="button">Support</button>
      <button class="filter" data-filter="finance" type="button">Finance</button>
      <button class="filter" data-filter="legal" type="button">Legal</button>
      <button class="filter" data-filter="spam" type="button">Spam</button>
    </div>
    <article class="mail on" data-cat="sales" data-title="Catalog and price list" data-from="buyer@example.com" data-policy="auto" data-action="reply_common" data-body="Please send your product catalog and price list. We buy industrial lubricants in drums.">
      <div class="from">buyer@example.com</div><div class="sub">Catalog and price list</div>
      <div class="meta">Sales · 0.85 · auto</div>
    </article>
    <article class="mail" data-cat="sales" data-title="MOQ for 200L drums" data-from="ops@nordic.eu" data-policy="auto" data-action="reply_common" data-body="What is the minimum order quantity for 200L drums?">
      <div class="from">ops@nordic.eu</div><div class="sub">MOQ for 200L drums</div>
      <div class="meta">Sales · template MOQ</div>
    </article>
    <article class="mail" data-cat="finance" data-title="Invoice payment" data-from="ap@example.com" data-policy="hold" data-action="send_email" data-body="Please process the bank payment for INV-2044. The amount is €12,400.">
      <div class="from">ap@example.com</div><div class="sub">Invoice payment</div>
      <div class="meta">Finance · manager</div>
    </article>
    <article class="mail" data-cat="legal" data-title="Distribution contract review" data-from="legal@partner.com" data-policy="hold" data-action="send_email" data-body="We need to review the distribution contract before Friday.">
      <div class="from">legal@partner.com</div><div class="sub">Distribution contract review</div>
      <div class="meta">Legal · manager</div>
    </article>
    <article class="mail" data-cat="support" data-title="Order error — please check" data-from="user@gmail.com" data-policy="auto" data-action="create_ticket" data-body="There is an error in my last order. Support, please check the shipment.">
      <div class="from">user@gmail.com</div><div class="sub">Order error — please check</div>
      <div class="meta">Support · ticket</div>
    </article>
    <article class="mail" data-cat="support" data-title="Warranty claim on pump" data-from="plant@delta.eu" data-policy="auto" data-action="reply_common" data-body="Need warranty terms for the circulating pump.">
      <div class="from">plant@delta.eu</div><div class="sub">Warranty claim on pump</div>
      <div class="meta">Support · FAQ</div>
    </article>
    <article class="mail" data-cat="sales" data-title="Sample request" data-from="lab@chem.io" data-policy="auto" data-action="reply_common" data-body="Can you send a 1L sample of base oil group II?">
      <div class="from">lab@chem.io</div><div class="sub">Sample request</div>
      <div class="meta">Sales · samples</div>
    </article>
    <article class="mail" data-cat="finance" data-title="Bank details confirmation" data-from="treasury@co.nl" data-policy="hold" data-action="send_email" data-body="Please confirm the IBAN for the next transfer.">
      <div class="from">treasury@co.nl</div><div class="sub">Bank details confirmation</div>
      <div class="meta">Finance · confidential</div>
    </article>
    <article class="mail" data-cat="spam" data-title="Unsubscribe / casino offer" data-from="promo@bulk.invalid" data-policy="auto" data-action="classify_email" data-body="Casino offer. Unsubscribe.">
      <div class="from">promo@bulk.invalid</div><div class="sub">Unsubscribe / casino offer</div>
      <div class="meta">Spam · classify only</div>
    </article>
  </aside>
  <section class="read" id="reader">
    <div style="color:var(--dim)">Step 3 · Reply / draft</div>
    <h2>Catalog and price list</h2>
    <p style="color:var(--dim);margin:0 0 14px">buyer@example.com · today 09:14</p>
    <p>Please send your product catalog and price list. We buy industrial lubricants in drums.</p>
    <p><span class="tag auto">Common reply — automatic under rules</span> <span class="tag">reply_common</span></p>
    <textarea class="letter">Dear Customer,

Thank you for your interest in our products.

Our sales team has received your inquiry and will prepare a detailed response within 24 hours.

Best regards,
Our Company Sales Team</textarea>
    <div class="actions">
      <button class="btn primary" type="button">Keep automatic send</button>
      <button class="btn" type="button">Hold for manager</button>
      <a class="btn ghost" href="sales.html">Create lead</a>
    </div>
  </section>
  <aside class="side-help">
    <h3>Follow-up clock</h3>
    <p class="mini">24h / 48h / 72h if no customer reply.</p>
    <div class="row rail-card ok"><div><b>24h</b><div style="color:var(--dim)">due tomorrow 09:14</div></div><span class="tag auto">armed</span></div>
    <h3 style="margin-top:18px">Knowledge used</h3>
    <p class="mini">Product catalog v4 · Brand voice SOP v2</p>
    <h3 style="margin-top:18px">If this were finance</h3>
    <p class="mini">The flow jumps to Approvals. The agent may draft, never send.</p>
    <a class="btn" href="queue.html" style="margin-top:10px;display:inline-block">Open approval queue</a>
  </aside>
</div>
""")

PAGES["queue.html"] = ("Approvals", False, flow_nav(APPR, "review"), """
<div id="desk">
<div class="strip">Payment, contract, money movement, price change, data deletion and access change never auto-execute — even if the agent is certain.</div>
<section class="panel">
  <div class="panel-head"><span class="ph">Live queue</span><span class="hint">From /admin/api/approvals · approve/reject posts /decide with a real id · the customer is told</span></div>
  <div class="panel-body" id="desk-pending"><div class="empty">Loading…</div></div>
</section>
<section class="panel">
  <div class="panel-head"><span class="ph">Legacy cards</span><span class="hint">older console cards, kept for the /decide contract</span></div>
  <div class="panel-body"><div id="queue-live" class="g g2">Loading…</div></div>
</section>
<section class="panel">
  <div class="panel-head"><span class="ph">Hard gates</span><span class="hint">never automatic</span></div>
  <div class="panel-body">
    <table class="table">
      <thead><tr><th>Action</th><th>Why it never autos</th></tr></thead>
      <tbody>
        <tr><td>payment</td><td>Money movement</td></tr>
        <tr><td>contract</td><td>Legal commitment</td></tr>
        <tr><td>create_quote / change_price</td><td>Commercial commitment</td></tr>
        <tr><td>delete_data / change_access</td><td>Irreversible</td></tr>
      </tbody>
    </table>
  </div>
</section>
</div>
""")

PAGES["website.html"] = ("Website flow", False, flow_nav(WEB, "edit"), """
<div class="g g4">
  <article class="card kpi"><div class="l">Contact forms today</div><div class="n num">7</div><div class="s pos">All became leads</div></article>
  <article class="card kpi"><div class="l">Pages in draft</div><div class="n num">3</div><div class="s">1 legal in review</div></article>
  <article class="card kpi"><div class="l">Open price changes</div><div class="n num">1</div><div class="s neg">Waiting on manager</div></article>
  <article class="card kpi"><div class="l">Published</div><div class="n num">12</div><div class="s">stable pages</div></article>
</div>
<div class="g g21" style="margin-top:12px">
  <section class="card">
    <h2>Pages · edit</h2>
    <table class="table">
      <thead><tr><th>Page</th><th>Status</th><th>Flow step</th><th>Policy</th></tr></thead>
      <tbody>
        <tr><td>Products / base oil</td><td>Draft</td><td>3 Edit</td><td><span class="tag hold">content</span></td></tr>
        <tr><td>PET-001 price</td><td>Review</td><td>4 Gate</td><td><span class="tag never">change_price</span></td></tr>
        <tr><td>Refund policy</td><td>Review</td><td>4 Gate</td><td><span class="tag never">contract</span></td></tr>
        <tr><td>Contact</td><td>Published</td><td>5 Publish</td><td><span class="tag auto">stable</span></td></tr>
        <tr><td>About</td><td>Published</td><td>5 Publish</td><td><span class="tag auto">stable</span></td></tr>
        <tr><td>Technical data sheets</td><td>Draft</td><td>3 Edit</td><td><span class="tag hold">content</span></td></tr>
      </tbody>
    </table>
  </section>
  <section class="card">
    <h2>Form → lead</h2>
    <div class="row rail-card ok"><div><b>Jane Doe</b><div style="color:var(--dim)">jane@example.com · Need product information</div></div><span class="tag auto">create_lead</span></div>
    <div class="row rail-card ok"><div><b>H. Karimi</b><div style="color:var(--dim)">hossein@co.ir · MOQ enquiry</div></div><span class="tag auto">create_lead</span></div>
    <div class="row rail-card ok"><div><b>Nordic Oils</b><div style="color:var(--dim)">ops@nordic.eu · Drum availability</div></div><span class="tag auto">create_lead</span></div>
    <div class="row rail-card ok"><div><b>Delta Trading</b><div style="color:var(--dim)">buy@delta.eu · Repeat SKU</div></div><span class="tag auto">create_lead</span></div>
    <a class="btn" href="sales.html" style="margin-top:10px;display:inline-block">Open in sales flow</a>
  </section>
</div>
<section class="card" style="margin-top:12px">
  <h2>Policy gate preview</h2>
  <p class="mini">Ordinary copy can be prepared here. Price, legal and deletes jump to Approvals.</p>
  <div class="toolbar">
    <a class="btn good" href="queue.html">Send PET-001 price to Approvals</a>
    <a class="btn" href="queue.html">Send refund policy to Approvals</a>
    <button class="btn ghost" type="button">Preview HTML</button>
  </div>
</section>
""")

PAGES["social.html"] = ("Social flow", False, flow_nav(SOC, "sched"), """
<p class="kicker">Ordinary calendar posts publish automatically. Sensitive claims and off-calendar posts wait in Approvals.</p>
<div class="cal">
  <div class="day"><em>Mon 7</em><div class="post">Instagram · weekly product update <span class="tag auto">auto</span></div></div>
  <div class="day"><em>Tue 8</em><div class="post">Comment replies · FAQ</div></div>
  <div class="day"><em>Wed 9</em><div class="post">LinkedIn · industry note</div></div>
  <div class="day"><em>Thu 10</em><div class="post">Story · warehouse walkthrough</div></div>
  <div class="day"><em>Fri 11</em><div class="post">Caption draft · Q3 range</div></div>
  <div class="day"><em>Sat 12</em><div class="post">X · short technical tip</div></div>
  <div class="day"><em>Sun 13</em><div class="post">“Guaranteed best price” <span class="tag never">held</span></div></div>
</div>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>Schedule → publish</h2>
    <div class="row rail-card ok"><div><b>Weekly product update</b><div style="color:var(--dim)">instagram · 09:00 · 2,184 chars under limit</div></div><span class="tag auto">publish_calendar</span></div>
    <div class="row rail-card ok"><div><b>Industry note</b><div style="color:var(--dim)">linkedin · 11:00</div></div><span class="tag auto">publish_calendar</span></div>
    <div class="row rail-card"><div><b>Guaranteed best price</b><div style="color:var(--dim)">instagram · off-policy claim</div></div><a class="tag never" href="queue.html">hold</a></div>
  </section>
  <section class="card">
    <h2>Engagement &amp; replies</h2>
    <p style="margin:0">Likes 42 · comments 7 · saves 12 · DMs 3</p>
    <p class="mini">Routine comments use templates. Medical or guaranteed-return claims escalate.</p>
    <table class="table">
      <thead><tr><th>Channel</th><th>Item</th><th>Policy</th></tr></thead>
      <tbody>
        <tr><td>IG comment</td><td>“Great product!”</td><td><span class="tag auto">template</span></td></tr>
        <tr><td>IG DM</td><td>Price for 12 drums</td><td><span class="tag ice">→ sales flow</span></td></tr>
        <tr><td>IG comment</td><td>“Guaranteed returns?”</td><td><span class="tag never">escalate</span></td></tr>
      </tbody>
    </table>
  </section>
</div>
""")

PAGES["sales.html"] = ("Sales flow", False, flow_nav(SALES, "quote"), """
<div class="g g4">
  <article class="card kpi"><div class="l">Open leads</div><div class="n num">18</div><div class="s pos">+4 today</div></article>
  <article class="card kpi"><div class="l">Qualified</div><div class="n num">9</div></article>
  <article class="card kpi"><div class="l">Quotes in queue</div><div class="n num">3</div><div class="s neg">Not sent</div></article>
  <article class="card kpi"><div class="l">Average value</div><div class="n num">€4.2k</div></article>
</div>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>Lead → qualify</h2>
    <table class="table">
      <thead><tr><th>Account</th><th>Source</th><th>Stage</th></tr></thead>
      <tbody>
        <tr><td>buyer@example.com</td><td>Email catalog</td><td><span class="tag auto">lead</span></td></tr>
        <tr><td>Nordic Oils</td><td>Website form</td><td><span class="tag ice">qualified</span></td></tr>
        <tr><td>Delta Trading</td><td>Repeat</td><td><span class="tag ice">qualified</span></td></tr>
        <tr><td>lab@chem.io</td><td>Sample request</td><td><span class="tag auto">lead</span></td></tr>
      </tbody>
    </table>
  </section>
  <section class="card">
    <h2>Quote → manager send</h2>
    <table class="table">
      <thead><tr><th>No.</th><th>Detail</th><th>Policy</th></tr></thead>
      <tbody>
        <tr><td>Q-1042</td><td>Nordic Oils · 12 drums</td><td><span class="tag hold">create_quote</span></td></tr>
        <tr><td>Q-1041</td><td>buyer@ · catalog only</td><td><span class="tag auto">reply_common</span></td></tr>
        <tr><td>Q-1039</td><td>Delta Trading · repeat</td><td><span class="tag hold">create_quote</span></td></tr>
        <tr><td>Q-1038</td><td>Sent 07:55</td><td><span class="tag auto">approved</span></td></tr>
      </tbody>
    </table>
    <a class="btn primary" href="queue.html" style="margin-top:10px;display:inline-block">Send Q-1042 to Approvals</a>
  </section>
</div>
""")

PAGES["support.html"] = ("Support flow", False, flow_nav(SUP, "first"), """
<div class="g g4">
  <article class="card kpi"><div class="l">Open tickets</div><div class="n num">9</div></article>
  <article class="card kpi"><div class="l">First-line auto</div><div class="n num">4</div><div class="s pos">create_ticket</div></article>
  <article class="card kpi"><div class="l">Inside SLA</div><div class="n num">8</div></article>
  <article class="card kpi"><div class="l">Safety escalations</div><div class="n num">1</div><div class="s neg">human</div></article>
</div>
<section class="card" style="margin-top:12px">
  <h2>Request → ticket → first line</h2>
  <table class="table">
    <thead><tr><th>Subject</th><th>Priority</th><th>SLA</th><th>Source</th><th>Action</th></tr></thead>
    <tbody>
      <tr><td>System error, please support</td><td>medium</td><td>4h</td><td>Chat</td><td><span class="tag auto">create_ticket</span></td></tr>
      <tr><td>Warranty claim on pump</td><td>normal</td><td>24h</td><td>Email</td><td><span class="tag auto">FAQ reply</span></td></tr>
      <tr><td>Delivery delay on last order</td><td>normal</td><td>24h</td><td>Email</td><td><span class="tag auto">template</span></td></tr>
      <tr><td>Reported leak at customer site</td><td>high</td><td>now</td><td>WhatsApp</td><td><span class="tag never">safety → human</span></td></tr>
      <tr><td>Login issue on portal</td><td>low</td><td>48h</td><td>Form</td><td><span class="tag auto">create_ticket</span></td></tr>
    </tbody>
  </table>
  <div class="actions">
    <a class="btn bad" href="queue.html">Escalate leak to Approvals / duty manager</a>
  </div>
</section>
""")

PAGES["operations.html"] = ("Operations", False, flow_nav(OPS, "report"), """
<div class="g g2">
  <section class="card">
    <h2>Daily report</h2>
    <table class="table">
      <tbody>
        <tr><td>Messages</td><td class="num">312</td></tr>
        <tr><td>Email received</td><td class="num">128</td></tr>
        <tr><td>Automatic replies</td><td class="num">84</td></tr>
        <tr><td>Work completed</td><td class="num">19</td></tr>
        <tr><td>Follow-ups armed</td><td class="num">11</td></tr>
        <tr><td>Errors</td><td class="num">1</td></tr>
      </tbody>
    </table>
  </section>
  <section class="card">
    <h2>Extract → remind → coordinate</h2>
    <div class="row rail-card crit"><div><b>Follow the distribution contract</b><div style="color:var(--dim)">legal · ops · extracted from mail</div></div><span class="tag never">contract</span></div>
    <div class="row rail-card ok"><div><b>Sales meeting reminder</b><div style="color:var(--dim)">today 16:00</div></div><span class="tag auto">reminder</span></div>
    <div class="row rail-card ok"><div><b>Buyer follow-up 24h</b><div style="color:var(--dim)">buyer@example.com</div></div><span class="tag auto">follow-up</span></div>
    <div class="row rail-card ok"><div><b>Nightly Postgres backup</b><div style="color:var(--dim)">cron 02:00</div></div><span class="tag auto">ok</span></div>
    <div class="row rail-card ok"><div><b>Weekly digest</b><div style="color:var(--dim)">scheduled Sunday</div></div><span class="tag auto">ops_digest</span></div>
  </section>
</div>
""")

PAGES["knowledge.html"] = ("Knowledge", False, flow_nav(KNOW, "approve"), """
<p class="kicker">Only documents with status=approved enter answers. Confidential items stay hidden from non-manager roles.</p>
<div class="g g2">
  <section class="card">
    <h2>Draft → review → approve → index</h2>
    <table class="table">
      <thead><tr><th>Document</th><th>Version</th><th>Sensitivity</th><th>Step</th></tr></thead>
      <tbody>
        <tr><td>Product catalog</td><td>4</td><td>public</td><td><span class="tag auto">indexed</span></td></tr>
        <tr><td>Brand voice and reply SOP</td><td>2</td><td>internal</td><td><span class="tag auto">indexed</span></td></tr>
        <tr><td>Warranty and MOQ FAQ</td><td>3</td><td>internal</td><td><span class="tag auto">indexed</span></td></tr>
        <tr><td>Shipping windows</td><td>1</td><td>internal</td><td><span class="tag hold">review</span></td></tr>
        <tr><td>Distribution contract terms</td><td>1</td><td>confidential</td><td><span class="tag hold">manager only</span></td></tr>
        <tr><td>2026 price list</td><td>—</td><td>internal</td><td><span class="tag">draft</span></td></tr>
      </tbody>
    </table>
  </section>
  <section class="card">
    <h2>What the agents may use</h2>
    <p class="mini">Email auto-replies read catalog + SOP. Quotes do not invent prices from unapproved drafts.</p>
    <div class="row rail-card ok"><div><b>Indexed chunks</b><div style="color:var(--dim)">1,204 · last rebuild 06:10</div></div><span class="tag auto">RAG</span></div>
    <div class="row rail-card"><div><b>Blocked confidential</b><div style="color:var(--dim)">contract terms hidden from email_agent</div></div><span class="tag never">filter</span></div>
    <a class="btn primary" href="brain.html" style="margin-top:12px;display:inline-block">Open atomic knowledge brain</a>
  </section>
</div>
""")

PAGES["control.html"] = ("Control", False, flow_nav(CTRL, "matrix"), """
<p class="kicker">Access matrix — source of truth for every specialist.</p>
<section class="card">
  <table class="table matrix">
    <thead><tr><th>Work</th><th>Level</th><th>Action in code</th><th>Flow</th></tr></thead>
    <tbody>
      <tr><td>Read and classify email</td><td><span class="tag auto">Automatic</span></td><td>read_email / classify_email</td><td><a href="inbox.html">Email</a></td></tr>
      <tr><td>Reply to common questions</td><td><span class="tag auto">Automatic under rules</span></td><td>reply_common</td><td><a href="inbox.html">Email</a></td></tr>
      <tr><td>Send sensitive or important email</td><td><span class="tag hold">Manager approval</span></td><td>send_email</td><td><a href="queue.html">Approvals</a></td></tr>
      <tr><td>Publish ordinary calendar content</td><td><span class="tag auto">Automatic</span></td><td>publish_calendar</td><td><a href="social.html">Social</a></td></tr>
      <tr><td>Change price or sensitive site information</td><td><span class="tag hold">Manager approval</span></td><td>change_price</td><td><a href="website.html">Website</a></td></tr>
      <tr><td>Payment, contract, money transfer</td><td><span class="tag never">Manager only</span></td><td>payment / contract</td><td><a href="queue.html">Approvals</a></td></tr>
      <tr><td>Delete data or change user access</td><td><span class="tag never">Manager approval</span></td><td>delete_data / change_access</td><td><a href="queue.html">Approvals</a></td></tr>
    </tbody>
  </table>
</section>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>Roles</h2>
    <p>Sara · manager — may approve. Agent — may auto-run only matrix-green actions.</p>
    <p class="mini">A claimed role inside a prompt is not approval.</p>
  </section>
  <section class="card">
    <h2>Future agents</h2>
    <p>Inactive: accounting · hr · content_studio · project</p>
    <p class="mini">Routing them returns domain=future and auto_execute=false.</p>
  </section>
</div>
""")

PAGES["audit.html"] = ("Audit", False, flow_nav(APPR, "audit"), """
<p class="kicker">Every automatic run and every manager decision is logged. This is the last step of the approval flow.</p>
<section class="card">
  <h2>Today’s trail</h2>
  <table class="table">
    <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Result</th><th>Idempotency</th></tr></thead>
    <tbody>
      <tr><td class="num">09:14</td><td>agent</td><td>reply_common</td><td>executed</td><td>r-8841</td></tr>
      <tr><td class="num">09:02</td><td>agent</td><td>create_lead</td><td>executed</td><td>l-2290</td></tr>
      <tr><td class="num">08:50</td><td>agent</td><td>publish_calendar</td><td>executed</td><td>c-1102</td></tr>
      <tr><td class="num">08:41</td><td>agent</td><td>create_ticket</td><td>executed</td><td>t-441</td></tr>
      <tr><td class="num">07:55</td><td>Sara</td><td>create_quote send</td><td>approved</td><td>q-1038</td></tr>
      <tr><td class="num">07:40</td><td>Sara</td><td>publish_content</td><td>rejected</td><td>s-77</td></tr>
      <tr><td class="num">07:12</td><td>agent</td><td>payment</td><td>blocked</td><td>p-12</td></tr>
    </tbody>
  </table>
</section>
""")

PAGES["automation.html"] = ("Automation", False, flow_nav(OPS, "remind"), """
<p class="kicker">Cron jobs from phase 5. They observe and enqueue; they do not bypass the matrix.</p>
<section class="card">
  <h2>Scheduled jobs</h2>
  <table class="table">
    <thead><tr><th>Job</th><th>Every</th><th>Last run</th><th>May auto?</th></tr></thead>
    <tbody>
      <tr><td>daily-report</td><td>24h</td><td>08:00</td><td><span class="tag auto">compile only</span></td></tr>
      <tr><td>followup-check</td><td>1h</td><td>09:00</td><td><span class="tag auto">open tasks</span></td></tr>
      <tr><td>calendar-publish</td><td>5m</td><td>09:05</td><td><span class="tag auto">ordinary posts</span></td></tr>
      <tr><td>ops-digest</td><td>24h</td><td>08:00</td><td><span class="tag auto">compile only</span></td></tr>
    </tbody>
  </table>
</section>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>Rules that stay automatic</h2>
    <p class="mini">classify_email · reply_common · publish_calendar · create_lead · create_ticket · create_task</p>
  </section>
  <section class="card">
    <h2>Rules that always stop</h2>
    <p class="mini">payment · contract · change_price · delete_data · change_access · create_quote send</p>
  </section>
</div>
""")



SURF = [
    ("live", "Live", "live.html"),
    ("insights", "Insights", "insights.html"),
    ("market", "Market", "market.html"),
    ("hub", "Hub", "hub.html"),
]

PAGES["live.html"] = ("Live", False, flow_nav(SURF, "live"), """
<p class="kicker">DropAgent live board, rewritten for Zenovix Ops · mock stream, no backend</p>
<div class="bar-right" style="margin-bottom:14px">
  <span class="status-pill"><span class="dot" id="liveDot"></span><span id="liveMode">Connecting…</span></span>
</div>
<div class="gauges">
  <article class="card gauge"><canvas id="gInbound" width="260" height="260"></canvas><div class="v num" id="vInbound">—</div><div class="l">Inbound today</div></article>
  <article class="card gauge"><canvas id="gQueue" width="260" height="260"></canvas><div class="v num" id="vQueue">—</div><div class="l">Approval queue</div></article>
  <article class="card gauge"><canvas id="gAuto" width="260" height="260"></canvas><div class="v num" id="vAuto">—</div><div class="l">Auto replies</div></article>
  <article class="card gauge"><canvas id="gTickets" width="260" height="260"></canvas><div class="v num" id="vTickets">—</div><div class="l">Open tickets</div></article>
</div>
<div class="g g2" style="margin-top:12px">
  <div class="row rail-card ok"><div><b>New leads today</b><div style="color:var(--dim)">Website + email</div></div><span class="val num" id="rLeads">—</span></div>
  <div class="row rail-card"><div><b>Quotes held</b><div style="color:var(--dim)">create_quote to Approvals</div></div><span class="val num" id="rQuotes">—</span></div>
  <div class="row rail-card crit"><div><b>Payments pending</b><div style="color:var(--dim)">Never auto</div></div><span class="val num" id="rPay">—</span></div>
  <div class="row rail-card crit"><div><b>Withdrawals pending</b><div style="color:var(--dim)">Treasury HITL</div></div><span class="val num" id="rWd">—</span></div>
  <div class="row rail-card"><div><b>Catalog items in review</b><div style="color:var(--dim)">Market surface</div></div><span class="val num" id="rPend">—</span></div>
  <div class="row rail-card ok"><div><b>Tickets open</b><div style="color:var(--dim)">Support first line</div></div><span class="val num" id="rTik">—</span></div>
</div>
<p class="mini" style="margin-top:14px">Gauges are demo-only. This page never talks to DropAgent SQLite.</p>
""")

PAGES["insights.html"] = ("Insights", False, flow_nav(SURF, "insights"), """
<p class="kicker">Fourteen-day snapshot · pure SVG · DropAgent insights, English neon
  <button class="btn" id="expJson" type="button" style="vertical-align:middle;margin-left:8px">JSON snapshot</button>
  <span class="mini">Jump: <kbd class="kk">Ctrl</kbd>+<kbd class="kk">K</kbd></span>
</p>
<div class="g g4">
  <article class="card kpi"><div class="l">Users</div><div class="n num">248</div><div class="s pos">+18 in 7d</div></article>
  <article class="card kpi"><div class="l">Active 7d</div><div class="n num">91</div></article>
  <article class="card kpi"><div class="l">Sales 14d</div><div class="n num">36</div></article>
  <article class="card kpi"><div class="l">Avg basket</div><div class="n num">EUR 1.9k</div></article>
</div>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>New vs active</h2>
    <div class="chart" id="chartUsers"></div>
    <div class="legend"><span><i style="background:var(--cyan)"></i>New</span><span><i style="background:var(--mag)"></i>Active</span></div>
  </section>
  <section class="card">
    <h2>Daily volume</h2>
    <div class="chart" id="chartGmv"></div>
    <div class="legend"><span><i style="background:var(--lime)"></i>GMV</span></div>
  </section>
  <section class="card">
    <h2>Top products</h2>
    <div id="topProducts"></div>
  </section>
  <section class="card">
    <h2>Categories</h2>
    <div id="topCats"></div>
  </section>
</div>
""")

PAGES["market.html"] = ("Market", False, flow_nav(SURF, "market"), """
<p class="kicker">DropAgent storefront, Zenovix catalog · search, chips, modal · quotes still HITL</p>
<div class="toolbar">
  <input class="search" id="marketQ" placeholder="Search SKU, skill, pack" aria-label="Search catalog" style="width:min(320px,100%)">
  <select id="marketSort" aria-label="Sort" class="btn ghost">
    <option value="new">Newest</option>
    <option value="cheap">Lowest price</option>
    <option value="exp">Highest price</option>
    <option value="sold">Best sellers</option>
  </select>
  <span class="mini" id="marketCnt"></span>
</div>
<div class="chips" id="marketChips"></div>
<div class="market-grid" id="marketGrid"></div>
<div class="modal-wrap" id="modalWrap"><div class="modal" id="modal" role="dialog" aria-modal="true"></div></div>
<div class="toast" id="toast" role="status"></div>
""")


PAGES["settings.html"] = ("Variables", False, "", """
<div class="desk-head">
  <div>
    <div class="label">Variables</div>
    <div class="title">Everything the bot shows and does</div>
    <div class="sub">Company details, menu behaviour, quote rules and alerts. Saved to the database · the bot uses it on the next message · no redeploy.</div>
  </div>
  <div class="save-bar" style="margin:0">
    <span class="mini" id="vars-status"></span>
    <button class="btn" type="button" id="vars-reload">Reload</button>
    <button class="btn primary" type="button" id="vars-save">Save changes</button>
  </div>
</div>
<div class="desk-grid">
  <div class="stack" id="variables"><div class="empty">Loading…</div></div>
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph">Deployment (read-only)</span><span class="hint">set in Railway variables</span></div>
      <div class="panel-body" id="vars-env"><div class="empty">Loading…</div></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Bot (Telegram)</span><span class="hint">UI only</span></div>
      <div class="panel-body" id="bot-status">Loading…</div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">All runtime variables</span><span class="hint">secrets masked</span></div>
      <div class="panel-body">
        <details class="deploy"><summary>Show the full list (advanced)</summary>
          <table class="table" id="settings-table"><tbody><tr><td>Loading…</td></tr></tbody></table>
        </details>
      </div>
    </section>
  </div>
</div>
""")

PAGES["catalog.html"] = ("Catalog", False, "", """
<div id="catalog">
<div class="desk-head">
  <div>
    <div class="label">Catalog</div>
    <div class="title">Products &amp; services the bot sells</div>
    <div class="sub">English is the reference. Add translations and the bot shows each customer their own language. Every product has a short code, a picture, a title and a price.</div>
  </div>
  <div class="save-bar" style="margin:0">
    <span class="mini" id="prod-count"></span>
    <button class="btn primary" type="button" id="prod-new">New product</button>
  </div>
</div>
<div class="desk-grid">
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph" id="prod-title">New product</span><span class="hint">Save = live in the bot immediately</span></div>
      <div class="panel-body">
        <form id="prod-form">
          <div class="form-grid">
            <div class="fld"><span>Code (what customers type)</span><input name="code" placeholder="auto" maxlength="12"><span class="help">Short and unique, e.g. 203. Empty = next free number.</span></div>
            <div class="fld"><span>Name (English)</span><input name="name_en" required maxlength="160" placeholder="Diesel 10 PPM"></div>
            <div class="fld wide"><span>Title (one line, English)</span><input name="title_en" maxlength="200" placeholder="Ultra-low sulphur diesel stored under contamination control"></div>
            <div class="fld"><span>Category</span><select name="category"></select></div>
            <div class="fld"><span>Unit</span><select name="unit">
              <option value="metric ton">metric ton</option><option value="barrel">barrel</option><option value="liter">liter</option>
              <option value="kg">kg</option><option value="piece">piece</option><option value="service">service</option></select></div>
            <div class="fld"><span>Price per unit</span><input type="number" step="0.01" min="0" name="unit_price" value="0"><span class="help">0 = “price on request”.</span></div>
            <div class="fld"><span>Currency</span><input name="currency" value="USD" maxlength="3"></div>
            <div class="fld"><span>Stock</span><input type="number" min="0" name="stock_qty" value="0"></div>
            <div class="fld"><span>Order in the menu</span><input type="number" name="sort_order" value="100"></div>
            <div class="fld"><span>SKU (internal, optional)</span><input name="sku" maxlength="40" placeholder="auto"></div>
            <div class="fld wide"><span>Description (English)</span><textarea name="description_en" maxlength="2000"></textarea></div>
            <div class="fld wide"><span>Image link (optional — or upload below)</span><input name="image_url" placeholder="https://… or /web/assets/img/…"></div>
          </div>
          <div class="switch" style="margin-top:8px"><span><b>Live in the bot</b><div class="help">Off hides the product without deleting it.</div></span><input type="checkbox" name="is_active" checked></div>
          <div class="save-bar">
            <img id="prod-img" class="thumb" alt="" style="display:none;width:92px;height:64px">
            <button class="btn" type="button" id="prod-upload" disabled>Upload image</button>
            <input type="file" id="prod-file" accept="image/jpeg,image/png,image/webp" hidden>
            <span class="mini" id="prod-status"></span>
            <button class="btn ghost" type="button" id="prod-hide" style="display:none">Show / hide</button>
            <button class="btn primary" type="submit">Save product</button>
          </div>
        </form>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Translations</span><span class="hint">optional — English is used when empty</span></div>
      <div class="panel-body form-grid" id="prod-translations"></div>
    </section>
  </div>
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph">Products</span><input class="search" id="prod-search" placeholder="Filter…" style="width:160px"></div>
      <div class="panel-body" style="padding:0 6px 6px">
        <table class="table cat-table"><thead><tr><th></th><th>Code</th><th>Name</th><th>Category</th><th>Price</th><th></th></tr></thead>
        <tbody id="prod-list"><tr><td colspan="6" class="empty">Loading…</td></tr></tbody></table>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Categories</span><button class="btn ghost" type="button" id="cat-new">New</button></div>
      <div class="panel-body">
        <div id="cat-list"><div class="empty">Loading…</div></div>
        <form id="cat-form" style="margin-top:12px">
          <div class="form-grid">
            <div class="fld"><span>Key</span><input name="key" pattern="[a-z0-9][a-z0-9-]*" required placeholder="lubricants"></div>
            <div class="fld"><span>Name (English)</span><input name="name_en" required></div>
            <div class="fld"><span>Icon (emoji)</span><input name="icon" maxlength="4" placeholder="🛢"></div>
            <div class="fld"><span>Order</span><input type="number" name="sort_order" value="100"></div>
          </div>
          <div class="form-grid" id="cat-translations" style="margin-top:8px"></div>
          <div class="switch"><span><b>Shown in the bot</b></span><input type="checkbox" name="is_active" checked></div>
          <div class="save-bar">
            <span class="mini"></span>
            <button class="btn ghost" type="button" id="cat-delete" style="display:none">Delete</button>
            <button class="btn primary" type="submit">Save category</button>
          </div>
        </form>
      </div>
    </section>
  </div>
</div>
</div>
""")


PAGES["soul.html"] = ("Soul", False, "", """
<p class="kicker">Who the agent is · stored in Postgres · injected into every reply · edit and save, no redeploy</p>
<div class="soul-hero">
  <img src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wgARCAGkAaQDASIAAhEBAxEB/8QAGgABAQADAQEAAAAAAAAAAAAAAAECAwQFBv/EABgBAQEBAQEAAAAAAAAAAAAAAAABAgME/9oADAMBAAIQAxAAAAH5kbyAAACggAAAAAAAAAAAAKCAAAAAABQQACggAAAAAAAtAARRBAAAKCAAAoICggUEAoAAAIAAAALQoyvbccM9Lgs1LM9IsAgAFABAAUAAECggAFAABAABaiiUGWNN30vzHp783s/Men5Fzrxyx5+oFiiLAIBQQFAAAACwJQAAAAQKUAABSVUueGWs7ufo50xmUzuLFAASiCAAUAAAECglAAAABFKAFJWSY3b3az5u30+i8uHPpm+WjDrHk8/0PPnp4s9biz15mWM3FkoCUQASgAAAgUEAoAAIpQAorrudPp58e/P3c3JjXRhok3vmlNbroHRly2zs6fLyuPS8/Lsk8eel52O+KybASiCAUAAECglAAAFsAFFmVm/0Lw78zVN06aJ0xeZ0JeZ0F53QOe9BOe78rNGzPQd+nT6F5ePNurHpiyUCLAJQQFABAUAABZbALZnZO3p278/Jz3cs5MMc9aiaCCFqCgWEz7OC3PVllp3z7PM9nFjx5u049MEqWAQCgAAgKAAApYspfW8v2t8ObLk6NY06ejiz1xLjoy6/otcfkcfY8mdMFk2KK77nin13iXl5TLGds+zh7Nc+jU1a5+j4vueNm6pZj0JRBKAAACAAoAFS2LKZ+14vs9PP5fVzdK6uTr5JvHPDPO/e9v576HXh4flfpPm3bXKx6ZQz+h+e9vXD3vO9HyL5fnteeGffevk67nLXt06z6Hnen5LOqWc/QBBKAAAFgSgAALLYsGfr+Nv1z37d7fDj4+vTntoqZ6bvQ8q3G/RE1HbymDPec23HA9Xh0LlFm718vXrGensy1yy8bp5cdJDPVLAJQAAAQFABAFloC3GmfoeZnrn13q5Nc+PHs5c9cVmdLB6H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" alt="Agent soul" width="84" height="84">
  <div>
    <h2 id="soul-title">Zenovix · Digital Operations Manager</h2>
    <div class="mini" id="soul-meta">Loading…</div>
  </div>
</div>
<div class="soul-grid">
  <section class="card">
    <h2>Identity</h2>
    <form id="soul-form">
      <div class="g g2">
        <div class="field-block"><label for="agent_name">Agent name</label><input id="agent_name" name="agent_name" maxlength="80" placeholder="Zenovix"></div>
        <div class="field-block"><label for="role_title">Role title</label><input id="role_title" name="role_title" maxlength="120" placeholder="Digital Operations Manager"></div>
      </div>
      <div class="field-block"><label for="company_name">Company</label><input id="company_name" name="company_name" maxlength="160" placeholder="Your company name"></div>
      <div class="field-block"><label for="mission">Mission</label><textarea id="mission" name="mission" maxlength="2000"></textarea><span class="help">What the agent is here to do, in one or two sentences.</span></div>
      <div class="field-block"><label for="personality">Personality</label><textarea id="personality" name="personality" maxlength="2000"></textarea></div>
      <div class="field-block"><label for="tone">Tone</label><input id="tone" name="tone" maxlength="600" placeholder="Warm, professional, concise"></div>
      <div class="field-block"><label for="languages">Languages</label><input id="languages" name="languages" maxlength="600" placeholder="English first; reply in the customer's language"></div>
      <div class="field-block"><label for="greeting">Greeting / self-introduction</label><textarea id="greeting" name="greeting" maxlength="1000"></textarea><span class="help">Used when a customer says hello or asks "who are you?".</span></div>
      <div class="field-block"><label for="boundaries">Boundaries</label><textarea id="boundaries" name="boundaries" maxlength="3000"></textarea><span class="help">What the agent must never do or claim.</span></div>
      <div class="field-block"><label for="style_rules">Style rules</label><textarea id="style_rules" name="style_rules" maxlength="2000"></textarea><span class="help">Formatting rules. Plain text is enforced automatically for chat apps.</span></div>
      <div class="field-block"><label for="signature">E-mail signature</label><input id="signature" name="signature" maxlength="200"></div>
      <div class="actions">
        <button class="btn primary" type="submit" id="soul-save">Save soul</button>
        <button class="btn" type="button" id="soul-reload">Reload</button>
        <button class="btn ghost" type="button" id="soul-default">Load defaults</button>
      </div>
      <p class="mini" id="soul-status" style="margin-top:10px"></p>
    </form>
  </section>
  <section class="card">
    <h2>Prompt preview</h2>
    <p class="mini">Exactly what the model reads at the top of every system prompt.</p>
    <pre id="soul-preview" class="letter" style="max-height:70vh;overflow:auto;white-space:pre-wrap">Loading…</pre>
  </section>
</div>
""")

PAGES["simulator.html"] = ("Simulator", False, "", """
<div class="desk-head">
  <div>
    <div class="label">Simulator</div>
    <div class="title">The bot, exactly — inside the console</div>
    <div class="sub">Every message here goes through the real WhatsApp pipeline: 15-layer guard, menus, catalog, skills, QA and HITL. Drop files in — the bot reads them like a customer's PDF or photo. Nothing is sent to a real phone.</div>
  </div>
  <div class="save-bar" style="margin:0">
    <span class="mini" id="sim-status"></span>
    <select class="sim-select" id="sim-lang" aria-label="Language">
      <option value="">auto language</option><option value="en">English</option><option value="ar">العربية</option><option value="fa">فارسی</option><option value="tr">Türkçe</option><option value="ru">Русский</option><option value="de">Deutsch</option><option value="fr">Français</option><option value="es">Español</option>
    </select>
    <button class="btn" type="button" id="sim-new">New session</button>
    <button class="btn bad" type="button" id="sim-reset">Forget session</button>
  </div>
</div>
<div class="sim-grid" id="simulator">
  <section class="panel sim-phone">
    <div class="panel-head"><span class="ph">WhatsApp clone</span><span class="hint">session <b id="sim-session">—</b></span></div>
    <div class="sim-screen" id="sim-drop">
      <div class="sim-log" id="sim-log"><div class="empty">Say hello — or press a quick command below.</div></div>
      <div class="sim-dropzone" id="sim-dropzone">Drop files here (PDF, images, DOCX, XLSX, CSV, JSON · max 10 MB)</div>
    </div>
    <div class="sim-quick">
      <button type="button" data-sim="start">/start</button><button type="button" data-sim="menu">menu</button><button type="button" data-sim="shop">services</button><button type="button" data-sim="quote">quote</button><button type="button" data-sim="support">support</button><button type="button" data-sim="contact">contact</button><button type="button" data-sim="faq">faq</button><button type="button" data-sim="my_requests">my requests</button>
    </div>
    <form class="sim-input" id="sim-form">
      <button class="btn ghost sim-attach" type="button" id="sim-attach" title="Attach a file">＋</button>
      <input type="file" id="sim-file" multiple hidden>
      <input id="sim-text" placeholder="Type a message… (Enter to send)" autocomplete="off" maxlength="4000">
      <button class="btn primary" type="submit" id="sim-send">Send</button>
    </form>
  </section>
  <div class="stack">
    <section class="panel">
      <div class="panel-head"><span class="ph">Files in this session</span><span class="hint" id="sim-files-hint">0 / 8</span></div>
      <div class="panel-body"><div id="sim-files"><div class="empty">No files. Drop one on the chat or press ＋.</div></div>
      <p class="sim-note">Files are read (PDF text, OCR for images) and sent with your <b>next</b> message as framed DATA — the same way the real bot reads a customer's document. Delete a file and it is gone from the next message.</p></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">Last turn</span><span class="hint">what the pipeline decided</span></div>
      <div class="panel-body" id="sim-debug"><div class="empty">Send a message to see classification, guard and HITL results.</div></div>
    </section>
    <section class="panel">
      <div class="panel-head"><span class="ph">How it works</span><span class="hint">1.6.0</span></div>
      <div class="panel-body sim-note">
        <p>Sender id is <code>sim:&lt;session&gt;</code> on channel <b>whatsapp</b>. Replies are captured instead of being sent to Twilio/Meta; manager alerts still reach Telegram.</p>
        <p>Quotes and tickets you create here are real database rows (tagged <code>simulator</code>) — approve or reject them on the Approvals page.</p>
      </div>
    </section>
  </div>
</div>
""")

PAGES["database.html"] = ("Database", False, "", """
<div class="desk-head">
  <div>
    <div class="label">Database</div>
    <div class="title">Every table, in your hands</div>
    <div class="sub">Browse, add, edit and delete rows. Export any table — or everything — as a versioned JSON file and import it back (upsert on the natural key, exactly like the seed loader).</div>
  </div>
  <div class="save-bar" style="margin:0">
    <span class="mini" id="db-status"></span>
    <button class="btn" type="button" id="db-export-all">Export all (JSON)</button>
    <label class="btn" for="db-import-all-file">Import all…</label>
    <input type="file" id="db-import-all-file" accept="application/json,.json" hidden>
  </div>
</div>
<div class="db-grid" id="database">
  <section class="panel db-tables">
    <div class="panel-head"><span class="ph">Tables</span><span class="hint" id="db-version">—</span></div>
    <div class="panel-body"><div id="db-table-list"><div class="empty">Loading…</div></div></div>
  </section>
  <section class="panel db-main">
    <div class="panel-head"><span class="ph" id="db-title">Pick a table</span><span class="hint" id="db-count"></span></div>
    <div class="panel-body">
      <div class="db-toolbar">
        <input id="db-search" placeholder="Search text columns…" autocomplete="off">
        <button class="btn" type="button" id="db-refresh">Refresh</button>
        <button class="btn primary" type="button" id="db-add">Add row</button>
        <button class="btn" type="button" id="db-export">Export table</button>
        <label class="btn" for="db-import-file">Import…</label>
        <input type="file" id="db-import-file" accept="application/json,.json" hidden>
      </div>
      <div class="db-wrap"><table class="table db-rows" id="db-rows"><tbody><tr><td class="empty">Choose a table on the left.</td></tr></tbody></table></div>
      <div class="db-pager"><button class="btn ghost" type="button" id="db-prev">‹ Prev</button><span class="mini" id="db-page">—</span><button class="btn ghost" type="button" id="db-next">Next ›</button></div>
    </div>
  </section>
</div>
<div class="db-modal" id="db-modal" hidden>
  <div class="db-modal-box">
    <div class="panel-head"><span class="ph" id="db-modal-title">Row</span><button class="btn ghost" type="button" id="db-modal-close">Close</button></div>
    <div class="db-modal-body" id="db-modal-body"></div>
    <div class="save-bar"><span class="mini" id="db-modal-status"></span><button class="btn bad" type="button" id="db-modal-delete">Delete</button><button class="btn primary" type="button" id="db-modal-save">Save</button></div>
  </div>
</div>
""")

PAGES["hub.html"] = ("Hub", False, flow_nav(SURF, "hub"), """
<p class="kicker">Glass hub · every Zenovix Ops door in one place (DropAgent /links pattern)</p>
<h2 style="margin:8px 0 12px;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan)">Command</h2>
<div class="glass-grid">
  <a class="glass" href="ecosystem.html"><span class="ic">◉</span><span><span class="t">Ecosystem</span><div class="d">3D channels · HITL · storage</div></span><span class="go">→</span></a>
  <a class="glass" href="charter.html"><span class="ic">⚖</span><span><span class="t">Charter</span><div class="d">Access matrix · phases · specialists</div></span><span class="go">→</span></a>
  <a class="glass" href="index.html"><span class="ic">⌘</span><span><span class="t">Overview</span><div class="d">Day board</div></span><span class="go">→</span></a>
  <a class="glass" href="inbox.html"><span class="ic">✉</span><span><span class="t">Inbox</span><div class="d">Classify · reply · hold</div></span><span class="go">→</span></a>
  <a class="glass" href="queue.html"><span class="ic">⚖</span><span><span class="t">Approvals</span><div class="d">Never-auto gates</div></span><span class="go">→</span></a>
  <a class="glass" href="soul.html"><span class="ic">♥</span><span><span class="t">Soul</span><div class="d">Name · role · tone · boundaries</div></span><span class="go">→</span></a>
  <a class="glass" href="live.html"><span class="ic">◉</span><span><span class="t">Live</span><div class="d">Gauges · mock stream</div></span><span class="go">→</span></a>
</div>
<h2 style="margin:22px 0 12px;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan)">Flows and knowledge</h2>
<div class="glass-grid">
  <a class="glass" href="sales.html"><span class="ic">↗</span><span><span class="t">Sales</span><div class="d">Lead to quote</div></span><span class="go">→</span></a>
  <a class="glass" href="market.html"><span class="ic">▣</span><span><span class="t">Market</span><div class="d">Catalog surface</div></span><span class="go">→</span></a>
  <a class="glass" href="insights.html"><span class="ic">▦</span><span><span class="t">Insights</span><div class="d">14-day SVG</div></span><span class="go">→</span></a>
  <a class="glass" href="brain.html"><span class="ic">⚛</span><span><span class="t">Knowledge brain</span><div class="d">Atom · shells</div></span><span class="go">→</span></a>
</div>
<p class="mini" style="margin-top:18px">Product PWA / 3D landing from DropAgent stay in that repo. This hub is ops-only, English, neon.</p>
""")

PAGES["brain.html"] = ("Knowledge brain", True, flow_nav(KNOW, "brain"), """
<div id="brain-stage" class="brain-stage">
  <canvas id="gl"></canvas>
  <canvas id="hud"></canvas>
  <div id="atom-stats">Loading atom…</div>
  <aside class="brain-dock" id="dock-body"></aside>
  <div class="brain-tools">
    <button class="btn primary" id="btn-add-e" type="button">Add electron</button>
    <button class="btn" id="btn-add-shell" type="button">Add shell (n+1)</button>
    <button class="btn ghost" id="btn-nucleus" type="button">Select nucleus</button>
  </div>
</div>
""")


def unpack(entry):
    title, bare, flow, body = entry
    return title, bare, flow, body


LOGIN_JS = """
<script>
(function () {
  var form = document.querySelector("form.login-card");
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var hint = document.getElementById("loginHint");
    var payload = {username: form.username.value, password: form.password.value};
    fetch("/admin/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (r.ok) window.location.href = "ecosystem.html";
      else if (hint) hint.textContent = "Sign-in failed. Check username and password.";
    }).catch(function () {
      if (hint) hint.textContent = "Cannot reach the login API.";
    });
  });
})();
</script>
"""


def login_html() -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en" data-theme="dark">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="color-scheme" content="dark light">\n'
        "<title>Sign in · Zenovix Ops</title>\n"
        + THEME_BOOT
        + "\n<style>\n"
        + CSS
        + '\n</style>\n</head>\n<body>\n<main class="login">\n'
        '  <form class="login-card">\n'
        '    <img class="login-art" src="data:image/jpeg;base64,' + LOGIN_IMG + '" alt="" width="96" height="96">\n'
        '    <div class="sub" style="color:var(--gold-2);letter-spacing:.16em;text-transform:uppercase;font-size:11px">Zenovix Ops</div>\n'
        "    <h1>Manager console</h1>\n"
        '    <p style="color:var(--dim);margin:0 0 8px">Sign in to review automatic work and decide the rest. First page is the 3D ecosystem.</p>\n'
        '    <label class="field">Username\n'
        '      <input name="username" autocomplete="username" required>\n'
        "    </label>\n"
        '    <label class="field">Password\n'
        '      <input name="password" type="password" autocomplete="current-password" required>\n'
        "    </label>\n"
        '    <button class="btn primary" type="submit">Sign in</button>\n'
        '    <p class="hint" id="loginHint">Posts to /admin/api/auth/login, then opens ecosystem.html. Failed login stays here.</p>\n'
        '    <div class="login-links"><a href="/">← Back to the landing page</a>' + THEME_SWITCH + "</div>\n"
        "  </form>\n</main>\n"
        + LOGIN_JS
        + THEME_JS
        + "</body>\n</html>\n"
    )


def main() -> None:
    three = (ROOT / "vendor" / "three.min.js").read_text(encoding="utf-8", errors="replace")
    atom_js = (ROOT / "knowledge-atom.js").read_text(encoding="utf-8")
    view_js = (ROOT / "brain-view.js").read_text(encoding="utf-8")
    eco_js = (ROOT / "ecosystem-view.js").read_text(encoding="utf-8")
    brain_scripts = (
        "<script>" + three + "</script>\n<script>" + atom_js + "</script>\n<script>" + view_js + "</script>"
    )
    eco_scripts = "<script>" + three + "</script>\n<script>" + eco_js + "</script>"
    drop_js = (ROOT / "drop-front.js").read_text(encoding="utf-8")
    drop_tag = "<script>" + drop_js + "</script>"
    drop_pages = {"live.html", "insights.html", "market.html"}
    # 1.5.0+ — simulator / database pages and the 3D background (admin only).
    sim_tag = "<script>" + (ROOT / "sim.js").read_text(encoding="utf-8") + "</script>"
    db_tag = "<script>" + (ROOT / "db.js").read_text(encoding="utf-8") + "</script>"
    bg_js = (ROOT / "bg3d.js").read_text(encoding="utf-8")
    # brain / ecosystem already ship three.js inline; every other page loads
    # it once from vendor/ (browser-cached, ~650 KB) so pages stay small.
    bg_full = (
        '<script src="vendor/three.min.js?v=1.6.0" defer></script>\n'
        '<script>window.addEventListener("DOMContentLoaded",function(){' + bg_js + "});</script>"
    )
    bg_lite = "<script>" + bg_js + "</script>"
    for name, (title, bare, flow, body) in PAGES.items():
        html = shell(name, title, body, bare=bare, flow=flow)
        if name == "brain.html":
            html = html.replace("</body>", brain_scripts + "\n" + bg_lite + "\n</body>")
        elif name == "ecosystem.html":
            html = html.replace("</body>", eco_scripts + "\n" + bg_lite + "\n</body>")
        else:
            extra = ""
            if name in drop_pages:
                extra = drop_tag + "\n"
            elif name == "simulator.html":
                extra = sim_tag + "\n"
            elif name == "database.html":
                extra = db_tag + "\n"
            html = html.replace("</body>", extra + bg_full + "\n</body>")
        (ROOT / name).write_text(html, encoding="utf-8")
        print(f"{name:18} {html.count(chr(10))+1:4} lines")
    login = login_html().replace("</body>", bg_full + "\n</body>")
    (ROOT / "login.html").write_text(login, encoding="utf-8")
    print("login.html")


if __name__ == "__main__":
    main()
