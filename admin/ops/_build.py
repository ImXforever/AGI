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
    "eco": '<circle cx="12" cy="12" r="2.2"/><circle cx="12" cy="12" r="6.5"/><circle cx="12" cy="4" r="1.4"/><circle cx="19" cy="12" r="1.4"/><circle cx="5" cy="12" r="1.4"/><circle cx="16.5" cy="18.2" r="1.4"/><circle cx="7.5" cy="18.2" r="1.4"/>',
}

NAV = [
    ("Command", [
        ("ecosystem.html", "Ecosystem", "eco"),
        ("index.html", "Overview", "dash"),
        ("inbox.html", "Inbox", "inbox"),
        ("queue.html", "Approvals", "queue"),
    ]),
    ("Flows", [
        ("website.html", "Website flow", "web"),
        ("social.html", "Social flow", "social"),
        ("sales.html", "Sales flow", "sales"),
        ("support.html", "Support flow", "support"),
    ]),
    ("Systems", [
        ("operations.html", "Operations", "ops"),
        ("knowledge.html", "Knowledge", "know"),
        ("brain.html", "Knowledge brain", "brain"),
        ("control.html", "Control", "ctrl"),
        ("audit.html", "Audit", "audit"),
        ("automation.html", "Automation", "auto"),
    ]),
    ("Surface", [
        ("live.html", "Live", "live"),
        ("insights.html", "Insights", "insights"),
        ("market.html", "Market", "market"),
        ("hub.html", "Hub", "hub"),
    ]),
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


def shell(active: str, title: str, body: str, *, bare: bool = False, flow: str = "", extra_scripts: str = "") -> str:
    nav = []
    for group, items in NAV:
        nav.append(f'<div class="nav-label">{group}</div>')
        for href, label, ic in items:
            on = "on" if href == active else ""
            nav.append(f'<a class="{on}" href="{href}">{icon(ic)}{label}</a>')
    inner = body if bare else f'<div class="page">{body}</div>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Kia Ops</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="app">
  <aside class="rail">
    <div class="mark">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="#0b0c10"/>
        <path d="M16 5c3 4 6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 3-7 6-11z" fill="#00f0ff"/>
      </svg>
      <div>
        <div class="name">Kia Ops</div>
        <div class="sub">Manager console</div>
      </div>
    </div>
    <nav class="nav">{"".join(nav)}</nav>
    <div class="rail-foot">Payments, contracts, price changes, deletions and access changes never run without a manager record.</div>
  </aside>
  <div class="stage">
    <header class="bar">
      <h1>{title}</h1>
      <div class="bar-right">
        <input class="search" placeholder="Search work, people, pages" aria-label="Search">
        <span class="chip ok"><span class="dot"></span> Live</span>
        <span class="chip warn">4 awaiting you</span>
        <a class="btn ghost" href="login.html">Sign out</a>
        <span class="chip">Sara · manager</span>
      </div>
    </header>
    <div class="ticker"><span>Kia Ops neon grid · auto replies live · high-risk gates locked · payment / contract / delete never auto · knowledge atom expandable · charter v1.0 · manager console</span></div>
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
    ("inbox", "Inbox", "inbox.html"),
    ("queue", "Approvals", "queue.html"),
]

PAGES["ecosystem.html"] = ("Ecosystem", True, flow_nav(ECO, "eco"), """
<div id="eco-stage" class="brain-stage">
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

PAGES["index.html"] = ("Overview", False, flow_nav(
    [("map", "All flows", "index.html"), ("hold", "Held work", "queue.html"), ("auto", "Auto log", "audit.html")],
    "map",
), """
<p class="kicker">Friday 5 Sep 2026 · operating day 08:00–17:00 CET · charter v1.0</p>
<div class="strip">Four high-risk items are waiting. Nothing financial, legal or destructive has been executed.</div>
<div class="g g4">
  <article class="card kpi"><div class="l">Inbound mail</div><div class="n num">128</div><div class="s"><span class="pos">84 auto replies</span> · 44 drafts</div><div class="progress"><i style="width:66%"></i></div></article>
  <article class="card kpi"><div class="l">Approval queue</div><div class="n num">4</div><div class="s"><span class="neg">2 critical</span> · 2 high</div><div class="progress"><i style="width:20%;background:var(--crimson)"></i></div></article>
  <article class="card kpi"><div class="l">Calendar publish</div><div class="n num">6</div><div class="s"><span class="pos">3 published</span> · 3 ready</div><div class="progress"><i style="width:50%"></i></div></article>
  <article class="card kpi"><div class="l">Leads / tickets</div><div class="n num">11</div><div class="s">7 leads · 4 first-line tickets</div><div class="progress"><i style="width:40%"></i></div></article>
</div>
<div class="g g4" style="margin-top:12px">
  <a class="card" href="ecosystem.html"><h2>Ecosystem sim</h2><p class="mini">Channels → orchestrator → HITL / auto → storage</p><p><span class="tag ice">Three.js 3D</span></p></a>
  <a class="card" href="inbox.html"><h2>Email flow</h2><p class="mini">Capture → classify → reply → follow-up → escalate</p><p><span class="tag auto">84 auto</span> <span class="tag hold">2 held</span></p></a>
  <a class="card" href="website.html"><h2>Website flow</h2><p class="mini">Form → lead → edit → gate → publish</p><p><span class="tag auto">7 leads</span> <span class="tag never">1 price</span></p></a>
  <a class="card" href="social.html"><h2>Social flow</h2><p class="mini">Plan → caption → schedule → publish / hold</p><p><span class="tag auto">3 live</span> <span class="tag hold">1 claim</span></p></a>
  <a class="card" href="sales.html"><h2>Sales flow</h2><p class="mini">Lead → qualify → quote → manager send</p><p><span class="tag hold">3 quotes</span></p></a>
  <a class="card" href="brain.html"><h2>Knowledge atom</h2><p class="mini">Nucleus · shells 2n² · infinite electrons</p><p><span class="tag ice">Three.js + canvas</span></p></a>
  <a class="card" href="live.html"><h2>Live board</h2><p class="mini">Gauges · mock stream · HITL counts</p><p><span class="tag ice">DropAgent live</span></p></a>
  <a class="card" href="market.html"><h2>Market</h2><p class="mini">Catalog · search · quotes still gated</p><p><span class="tag ice">DropAgent store</span></p></a>
  <a class="card" href="insights.html"><h2>Insights</h2><p class="mini">14-day SVG · no external charts</p><p><span class="tag ice">DropAgent insights</span></p></a>
</div>
<div class="g g2" style="margin-top:12px">
  <section class="card">
    <h2>Needs a manager</h2>
    <div class="row rail-card crit"><div><b>Supplier payment · Rotterdam</b><div style="color:var(--dim)">ops · payment · €12,400</div></div><a class="tag never" href="queue.html">CRITICAL</a></div>
    <div class="row rail-card"><div><b>PET-001 unit price</b><div style="color:var(--dim)">website · change_price · 80.00 → 99.00</div></div><a class="tag hold" href="queue.html">HIGH</a></div>
    <div class="row rail-card"><div><b>Distribution contract mail</b><div style="color:var(--dim)">email · send_email · legal</div></div><a class="tag hold" href="queue.html">HIGH</a></div>
    <div class="row rail-card"><div><b>Ad-hoc social claim</b><div style="color:var(--dim)">social · “Guaranteed best price”</div></div><a class="tag hold" href="queue.html">HIGH</a></div>
  </section>
  <section class="card">
    <h2>Already ran automatically</h2>
    <table class="table">
      <thead><tr><th>Time</th><th>Flow</th><th>Action</th><th>Policy</th></tr></thead>
      <tbody>
        <tr><td class="num">09:14</td><td>Email</td><td>Catalog reply · buyer@</td><td><span class="tag auto">reply_common</span></td></tr>
        <tr><td class="num">09:02</td><td>Website</td><td>Jane Doe → lead</td><td><span class="tag auto">create_lead</span></td></tr>
        <tr><td class="num">08:50</td><td>Social</td><td>Weekly Instagram update</td><td><span class="tag auto">publish_calendar</span></td></tr>
        <tr><td class="num">08:41</td><td>Support</td><td>System error ticket</td><td><span class="tag auto">create_ticket</span></td></tr>
        <tr><td class="num">08:33</td><td>Ops</td><td>Follow-up 24h opened</td><td><span class="tag auto">create_task</span></td></tr>
        <tr><td class="num">08:20</td><td>Email</td><td>Casino spam, no reply</td><td><span class="tag auto">classify_email</span></td></tr>
        <tr><td class="num">08:05</td><td>Sales</td><td>Lead Nordic Oils</td><td><span class="tag auto">create_lead</span></td></tr>
      </tbody>
    </table>
  </section>
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
<div class="strip">Payment, contract, money movement, price change, data deletion and access change never auto-execute — even if the agent is certain.</div>
<div data-tabs>
  <div class="tabs">
    <button class="tab on" data-tab="open" type="button">Open (4)</button>
    <button class="tab" data-tab="never" type="button">Never-auto (always here)</button>
    <button class="tab" data-tab="done" type="button">Decided today</button>
  </div>
  <div data-panel="open">
    <div class="g g2">
      <article class="card rail-card crit">
        <h2>payment · execute</h2>
        <p style="margin:0 0 8px"><b>Supplier payment · Rotterdam</b></p>
        <p style="color:var(--dim)">ops_agent · CRITICAL · €12,400 · IBAN masked · INV-2044</p>
        <p>Draft assembled from the invoice. Execution is blocked until a manager record exists.</p>
        <p><span class="tag never">Manager only</span> <span class="tag">step 3 Decide</span></p>
        <div class="actions">
          <button class="btn good" type="button" data-decide="approved" data-id="">Approve &amp; run</button>
          <button class="btn" type="button">Edit</button>
          <button class="btn bad" type="button" data-decide="rejected" data-id="">Reject</button>
        </div>
      </article>
      <article class="card rail-card">
        <h2>change_price · gate</h2>
        <p style="margin:0 0 8px"><b>PET-001</b></p>
        <p style="color:var(--dim)">website_agent · HIGH · 80.00 → 99.00</p>
        <p>CMS price field. Publishing is held at the policy gate (website flow step 4).</p>
        <p><span class="tag hold">Needs approval</span></p>
        <div class="actions">
          <button class="btn good" type="button" data-decide="approved" data-id="">Approve price</button>
          <a class="btn" href="website.html">View page</a>
          <button class="btn bad" type="button">Reject</button>
        </div>
      </article>
      <article class="card rail-card">
        <h2>send_email · escalate</h2>
        <p style="margin:0 0 8px"><b>Distribution contract</b></p>
        <p style="color:var(--dim)">email_agent · HIGH · legal@partner.com</p>
        <p>Legal language detected. Draft ready; nothing sent. Email flow jumped from classify to escalate.</p>
        <p><span class="tag hold">Sensitive mail</span></p>
        <div class="actions">
          <button class="btn good" type="button" data-decide="approved" data-id="">Approve send</button>
          <a class="btn" href="inbox.html">Open thread</a>
          <button class="btn bad" type="button">Reject</button>
        </div>
      </article>
      <article class="card rail-card">
        <h2>publish_content · hold claims</h2>
        <p style="margin:0 0 8px"><b>Sensitive social claim</b></p>
        <p style="color:var(--dim)">social_agent · HIGH · “Guaranteed best price”</p>
        <p>Off the ordinary calendar path. Guarantee-style claims always wait.</p>
        <p><span class="tag hold">Sensitive publish</span></p>
        <div class="actions">
          <button class="btn good" type="button" data-decide="approved" data-id="">Allow publish</button>
          <a class="btn" href="social.html">Calendar</a>
          <button class="btn bad" type="button">Stop</button>
        </div>
      </article>
    </div>
  </div>
  <div data-panel="never" hidden>
    <section class="card">
      <h2>Hard gates</h2>
      <table class="table">
        <thead><tr><th>Action</th><th>Why it never autos</th><th>Open now</th></tr></thead>
        <tbody>
          <tr><td>payment</td><td>Money movement</td><td>1</td></tr>
          <tr><td>contract</td><td>Legal commitment</td><td>1</td></tr>
          <tr><td>change_price</td><td>Sensitive site data</td><td>1</td></tr>
          <tr><td>delete_data / change_access</td><td>Irreversible</td><td>0</td></tr>
        </tbody>
      </table>
    </section>
  </div>
  <div data-panel="done" hidden>
    <section class="card">
      <h2>Decided today</h2>
      <table class="table">
        <thead><tr><th>Time</th><th>Item</th><th>Decision</th><th>Actor</th></tr></thead>
        <tbody>
          <tr><td class="num">07:55</td><td>Quote Q-1038 send</td><td><span class="tag auto">approved</span></td><td>Sara</td></tr>
          <tr><td class="num">07:40</td><td>Ad-hoc LinkedIn post</td><td><span class="tag never">rejected</span></td><td>Sara</td></tr>
        </tbody>
      </table>
    </section>
  </div>
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
<p class="kicker">DropAgent live board, rewritten for Kia Ops · mock stream, no backend</p>
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
<p class="kicker">Fourteen-day snapshot · pure SVG · DropAgent insights, English neon</p>
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
<p class="kicker">DropAgent storefront, Kia catalog · search, chips, modal · quotes still HITL</p>
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

PAGES["hub.html"] = ("Hub", False, flow_nav(SURF, "hub"), """
<p class="kicker">Glass hub · every Kia Ops door in one place (DropAgent /links pattern)</p>
<h2 style="margin:8px 0 12px;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan)">Command</h2>
<div class="glass-grid">
  <a class="glass" href="ecosystem.html"><span class="ic">◉</span><span><span class="t">Ecosystem</span><div class="d">3D channels · HITL · storage</div></span><span class="go">→</span></a>
  <a class="glass" href="index.html"><span class="ic">⌘</span><span><span class="t">Overview</span><div class="d">Day board</div></span><span class="go">→</span></a>
  <a class="glass" href="inbox.html"><span class="ic">✉</span><span><span class="t">Inbox</span><div class="d">Classify · reply · hold</div></span><span class="go">→</span></a>
  <a class="glass" href="queue.html"><span class="ic">⚖</span><span><span class="t">Approvals</span><div class="d">Never-auto gates</div></span><span class="go">→</span></a>
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
    var payload = {username: form.username.value, password: form.password.value};
    fetch("/admin/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    }).then(function () { window.location.href = "ecosystem.html"; })
      .catch(function () { window.location.href = "ecosystem.html"; });
  });
})();
</script>
"""


def login_html() -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Sign in · Kia Ops</title>\n<style>\n"
        + CSS
        + "\n</style>\n</head>\n<body>\n<main class=\"login\">\n"
        '  <form class="login-card" action="ecosystem.html" method="get">\n'
        '    <div class="sub" style="color:var(--gold-2);letter-spacing:.16em;text-transform:uppercase;font-size:11px">Kia Ops</div>\n'
        "    <h1>Manager console</h1>\n"
        '    <p style="color:var(--dim);margin:0 0 8px">Sign in to review automatic work and decide the rest.</p>\n'
        '    <label class="field">Username\n'
        '      <input name="username" autocomplete="username" value="sara" required>\n'
        "    </label>\n"
        '    <label class="field">Password\n'
        '      <input name="password" type="password" autocomplete="current-password" required>\n'
        "    </label>\n"
        '    <button class="btn primary" type="submit">Sign in</button>\n'
        '    <p class="hint" id="loginHint">Posts to /admin/api/auth/login. If the API is down, the demo console still opens.</p>\n'
        "  </form>\n</main>\n"
        + LOGIN_JS
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
    for name, (title, bare, flow, body) in PAGES.items():
        html = shell(name, title, body, bare=bare, flow=flow)
        if name == "brain.html":
            html = html.replace("</body>", brain_scripts + "\n</body>")
        elif name == "ecosystem.html":
            html = html.replace("</body>", eco_scripts + "\n</body>")
        elif name in drop_pages:
            html = html.replace("</body>", drop_tag + "\n</body>")
        (ROOT / name).write_text(html, encoding="utf-8")
        print(f"{name:18} {html.count(chr(10))+1:4} lines")
    (ROOT / "login.html").write_text(login_html(), encoding="utf-8")
    print("login.html")


if __name__ == "__main__":
    main()
