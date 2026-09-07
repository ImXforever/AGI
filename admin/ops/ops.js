(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var filters = document.getElementById("filters");
  if (filters) {
    filters.addEventListener("click", function (event) {
      var btn = event.target.closest(".filter");
      if (!btn) return;
      filters.querySelectorAll(".filter").forEach(function (el) {
        el.classList.toggle("on", el === btn);
      });
      var cat = btn.getAttribute("data-filter");
      document.querySelectorAll(".mail").forEach(function (mail) {
        mail.style.display = cat === "all" || mail.getAttribute("data-cat") === cat ? "" : "none";
      });
    });
  }

  var reader = document.getElementById("reader");
  document.querySelectorAll(".mail").forEach(function (mail) {
    mail.addEventListener("click", function () {
      document.querySelectorAll(".mail").forEach(function (el) {
        el.classList.toggle("on", el === mail);
      });
      if (!reader) return;
      var policy = mail.getAttribute("data-policy") || "";
      var tag = policy === "hold" ? "hold" : "auto";
      var label = policy === "hold" ? "Held for manager" : "Automatic under rules";
      reader.innerHTML =
        '<div style="color:var(--dim)">Email · ' +
        esc(mail.getAttribute("data-cat")) +
        " · proposed action</div>" +
        "<h2>" +
        esc(mail.getAttribute("data-title")) +
        "</h2>" +
        '<p style="color:var(--dim);margin:0 0 14px">' +
        esc(mail.getAttribute("data-from")) +
        "</p>" +
        "<p>" +
        esc(mail.getAttribute("data-body")) +
        "</p>" +
        '<p><span class="tag ' +
        tag +
        '">' +
        label +
        '</span> <span class="tag">' +
        esc(mail.getAttribute("data-action")) +
        "</span></p>" +
        '<textarea class="letter"></textarea>' +
        '<div class="actions">' +
        (policy === "hold"
          ? '<button class="btn good" type="button">Approve send</button><button class="btn bad" type="button">Reject</button>'
          : '<button class="btn primary" type="button">Keep automatic send</button><button class="btn" type="button">Hold for manager</button>') +
        "</div>";
    });
  });

  document.querySelectorAll("[data-tabs]").forEach(function (root) {
    var tabs = root.querySelectorAll(".tab");
    var panels = root.querySelectorAll("[data-panel]");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var id = tab.getAttribute("data-tab");
        tabs.forEach(function (t) { t.classList.toggle("on", t === tab); });
        panels.forEach(function (p) {
          p.hidden = p.getAttribute("data-panel") !== id;
        });
      });
    });
  });

  var API = "/admin/api";

  function api(path, opts) {
    opts = opts || {};
    return fetch(API + path, {
      credentials: "same-origin",
      headers: Object.assign({ "Content-Type": "application/json", Accept: "application/json" }, opts.headers || {}),
      method: opts.method || "GET",
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(function (r) {
      return r.json().then(function (d) {
        d._status = r.status;
        d._ok = r.ok;
        return d;
      }).catch(function () {
        return { _status: r.status, _ok: r.ok };
      });
    });
  }

  function toast(msg) {
    var el = document.getElementById("toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.className = "toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(function () { el.classList.remove("show"); }, 2400);
  }

  function bindDecide(root) {
    (root || document).querySelectorAll("[data-decide]").forEach(function (btn) {
      if (btn.getAttribute("data-bound") === "1") return;
      btn.setAttribute("data-bound", "1");
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        var status = btn.getAttribute("data-decide");
        if (!id) {
          toast("Demo card — not executed. Live items load from /admin/api/approvals");
          return;
        }
        api("/approvals/" + encodeURIComponent(id) + "/decide", {
          method: "POST",
          body: { status: status, note: "ops console" },
        }).then(function (d) {
          if (d._status === 401) {
            toast("Sign in required");
            return;
          }
          if (!d._ok) {
            toast((d.detail || "Decide failed") + " (" + d._status + ")");
            return;
          }
          toast((status === "approved" ? "Approved" : "Rejected") + " · " + (d.execution && d.execution.executed ? "executed" : "recorded"));
          if (btn.closest(".card")) btn.closest(".card").setAttribute("data-decided", status);
        }).catch(function () {
          toast("API unreachable — nothing executed");
        });
      });
    });
  }
  bindDecide(document);

  document.addEventListener("click", function (event) {
    var menu = event.target.closest(".menu-btn");
    if (menu) {
      var rail = document.querySelector(".rail");
      if (rail) rail.classList.toggle("open");
      return;
    }
    var out = event.target.closest("[data-logout]");
    if (out) {
      event.preventDefault();
      api("/auth/logout", { method: "POST" }).finally(function () {
        window.location.href = "/";
      });
    }
  });


  // ---------- Theme switcher (Light / Dark / Gray / Neon, persisted) ----------
  var THEME_KEY = "zenovix-theme";
  var THEMES = ["light", "dark", "gray", "neon"];
  function applyTheme(t) {
    if (THEMES.indexOf(t) < 0) t = "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
    document.querySelectorAll(".theme-switch button").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-theme") === t);
    });
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      var bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
      if (bg) meta.setAttribute("content", bg);
    }
  }
  var savedTheme = null;
  try { savedTheme = localStorage.getItem(THEME_KEY); } catch (e) {}
  applyTheme(savedTheme || "dark");
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest(".theme-switch button");
    if (b) { ev.preventDefault(); applyTheme(b.getAttribute("data-theme")); }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key && ev.key.toLowerCase() === "t" && ev.altKey) {
      var cur = document.documentElement.getAttribute("data-theme") || "dark";
      applyTheme(THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length]);
    }
  });

  // ---------- Soul editor ----------
  var soulForm = document.getElementById("soul-form");
  if (soulForm) {
    var SOUL_FIELDS = ["agent_name", "company_name", "role_title", "mission", "personality", "tone",
      "languages", "greeting", "boundaries", "style_rules", "signature"];
    var soulStatus = document.getElementById("soul-status");
    var soulPreview = document.getElementById("soul-preview");
    function soulSay(msg) { if (soulStatus) soulStatus.textContent = msg; }
    function fillSoul(d) {
      SOUL_FIELDS.forEach(function (k) {
        var el = soulForm.elements[k];
        if (el) el.value = d[k] || "";
      });
      if (soulPreview) soulPreview.textContent = d.prompt_preview || "";
      var title = document.getElementById("soul-title");
      if (title) title.textContent = (d.agent_name || "Zenovix") + " · " + (d.role_title || "Digital Operations Manager");
      var meta = document.getElementById("soul-meta");
      if (meta) {
        meta.textContent = (d.source === "db" ? "Stored in Postgres" : "Built-in default (not saved yet)") +
          " · version " + (d.version || 0) + (d.updated_by ? " · last edited by " + d.updated_by : "");
      }
    }
    function loadSoul(path) {
      soulSay("Loading…");
      api(path || "/soul").then(function (d) {
        if (d._status === 401) { soulSay("Sign in required"); return; }
        if (!d._ok) { soulSay("Could not load the soul (" + d._status + ")"); return; }
        fillSoul(d);
        soulSay("");
      }).catch(function () { soulSay("API unreachable"); });
    }
    soulForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var body = {};
      SOUL_FIELDS.forEach(function (k) {
        var el = soulForm.elements[k];
        if (el) body[k] = el.value;
      });
      soulSay("Saving…");
      api("/soul", { method: "PUT", body: body }).then(function (d) {
        if (d._status === 401) { soulSay("Sign in required"); return; }
        if (d._status === 403) { soulSay("Your role cannot edit the soul (writer or superadmin needed)"); return; }
        if (!d._ok) { soulSay((d.detail && JSON.stringify(d.detail)) || "Save failed (" + d._status + ")"); return; }
        fillSoul(d);
        soulSay("Saved · the next reply uses the new soul");
        toast("Soul saved");
      }).catch(function () { soulSay("API unreachable — nothing saved"); });
    });
    var reloadBtn = document.getElementById("soul-reload");
    if (reloadBtn) reloadBtn.addEventListener("click", function () { loadSoul("/soul"); });
    var defBtn = document.getElementById("soul-default");
    if (defBtn) defBtn.addEventListener("click", function () {
      api("/soul/default").then(function (d) {
        if (!d._ok) { soulSay("Could not load defaults"); return; }
        d.source = "default";
        fillSoul(d);
        soulSay("Defaults loaded into the form — press Save to apply");
      });
    });
    loadSoul("/soul");
  }

  api("/auth/session").then(function (d) {
    var who = document.getElementById("whoami");
    if (who && d._ok && d.authenticated) {
      who.textContent = (d.username || "manager") + " · manager";
    }
  }).catch(function () {});

  api("/approvals?status=pending&limit=50").then(function (d) {
    if (!d._ok) return;
    var chip = document.getElementById("awaiting-chip");
    var n = d.total != null ? d.total : (d.items || []).length;
    if (chip) chip.textContent = n + " awaiting you";
    var cta = document.getElementById("cta-pending");
    if (cta) cta.textContent = String(n);
    var live = document.getElementById("queue-live");
    if (!live) return;
    var items = d.items || [];
    if (!items.length) {
      live.innerHTML = '<p class="mini">No pending approvals in Postgres.</p>';
      return;
    }
    live.innerHTML = items.map(function (it) {
      var id = it.id || "";
      var action = (it.payload && (it.payload.action || it.payload.type)) || it.channel || "held";
      return (
        '<article class="card rail-card" data-approval="' + esc(id) + '">' +
        "<h2>" + esc(action) + " · live</h2>" +
        "<p>" + esc(it.channel || "") + " · " + esc(it.status || "") + "</p>" +
        '<p class="mini">' + esc(id) + "</p>" +
        '<div class="actions">' +
        '<button class="btn good" type="button" data-decide="approved" data-id="' + esc(id) + '">Approve</button>' +
        '<button class="btn bad" type="button" data-decide="rejected" data-id="' + esc(id) + '">Reject</button>' +
        "</div></article>"
      );
    }).join("");
    bindDecide(live);
  }).catch(function () {});

  var liveMode = document.getElementById("liveMode");
  if (liveMode) {
    api("/stream/stats").then(function (d) {
      if (d._ok) {
        liveMode.textContent = "API live · pending " + (d.pending || 0);
        var q = document.getElementById("vQueue");
        if (q && d.pending != null) q.textContent = String(d.pending);
      }
    }).catch(function () {});
  }

  function secretKey(k) {
    return /token|secret|password|key|credentials|cookie/i.test(k);
  }

  function showVal(k, v) {
    if (v == null) return "";
    if (Array.isArray(v)) return v.map(function (x) { return String(x); }).join(", ");
    var s = String(v);
    if (secretKey(k) && s && s.indexOf("***") !== 0) return "***";
    return s;
  }

  function flatten(obj, prefix, rows) {
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      Object.keys(obj).forEach(function (k) {
        flatten(obj[k], prefix ? prefix + "." + k : k, rows);
      });
      return;
    }
    rows.push([prefix, showVal(prefix, obj)]);
  }

  var jsonEl = document.getElementById("settings-json");
  var tableEl = document.getElementById("settings-table");
  var botEl = document.getElementById("bot-status");
  if (jsonEl || tableEl || botEl) {
    api("/settings").then(function (d) {
      if (!d._ok) {
        if (jsonEl) jsonEl.textContent = "Sign in required.";
        if (botEl) botEl.textContent = "Sign in required.";
        return;
      }
      if (jsonEl) jsonEl.textContent = JSON.stringify(d, null, 2);
      var groups = d.groups || {};
      if (tableEl) {
        var rows = [];
        flatten(groups, "", rows);
        var body = rows.map(function (r) {
          return "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>";
        }).join("");
        tableEl.innerHTML = "<thead><tr><th>Variable</th><th>Value</th></tr></thead><tbody>" + body + "</tbody>";
      }
      if (botEl) {
        var ch = groups.channels || {};
        botEl.innerHTML =
          '<div class="row rail-card ok"><div><b>Telegram</b><div style="color:var(--dim)">Token masked · webhook secret masked · admin ids ' +
          esc(Array.isArray(ch.telegram_admin_ids) ? ch.telegram_admin_ids.length : "—") +
          "</div></div><span class=\"tag ice\">UI only</span></div>" +
          '<div class="row"><div><b>WhatsApp</b><div style="color:var(--dim)">' +
          (ch.whatsapp_enabled ? "enabled" : "disabled · 404") +
          "</div></div><span class=\"tag\">optional</span></div>" +
          '<p class="mini">Bot start/stop is the Railway service. This console does not dump DropAgent or any other product backend. Never paste the bot token in chat.</p>';
      }
    }).catch(function () {
      if (jsonEl) jsonEl.textContent = "Sign in required.";
    });
  }

  /* DropAgent admin chrome — English, Zenovix pages only. Commerce rails stay out. */
  (function chrome() {
    var banner = document.getElementById("netBanner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "netBanner";
      banner.setAttribute("role", "status");
      document.body.appendChild(banner);
    }
    function setNet(off) {
      banner.textContent = off
        ? "Offline — Zenovix Ops will refresh when the network returns"
        : "";
      banner.classList.toggle("show", !!off);
    }
    window.addEventListener("offline", function () { setNet(true); });
    window.addEventListener("online", function () {
      setNet(false);
      toast("Online — refreshing queue");
      api("/approvals?status=pending&limit=50").then(function (d) {
        if (!d._ok) return;
        var chip = document.getElementById("awaiting-chip");
        var n = d.total != null ? d.total : (d.items || []).length;
        if (chip) chip.textContent = n + " awaiting you";
        paintQueueBadge(n);
      }).catch(function () {});
    });
    if (typeof navigator !== "undefined" && navigator.onLine === false) setNet(true);

    function paintQueueBadge(n) {
      var link = document.querySelector('.nav a[href="queue.html"]');
      if (!link) return;
      var el = link.querySelector(".nav-badge");
      if (n > 0) {
        if (!el) {
          el = document.createElement("span");
          el.className = "nav-badge";
          link.appendChild(el);
        }
        el.textContent = n > 99 ? "99+" : String(n);
      } else if (el) el.remove();
    }
    api("/approvals?status=pending&limit=50").then(function (d) {
      if (d._ok) {
        var n = d.total != null ? d.total : (d.items || []).length;
        paintQueueBadge(n);
      }
    }).catch(function () {});

    var PAL_SEL = 0;
    var COMMANDS = [
      { i: "E", t: "Ecosystem", h: "3D channels", href: "ecosystem.html" },
      { i: "D", t: "Desk", h: "Today · approvals · conversations", href: "index.html" },
      { i: "A", t: "Approvals", h: "HITL queue", href: "queue.html" },
      { i: "C", t: "Catalog", h: "Products, codes, images, translations", href: "catalog.html" },
      { i: "V", t: "Variables", h: "Company, bot menu, quotes, alerts", href: "settings.html" },
      { i: "♥", t: "Soul", h: "Name, role, tone", href: "soul.html" },
      { i: "S", t: "Simulator", h: "The real bot, in the console · drop files", href: "simulator.html" },
      { i: "X", t: "Database", h: "Every table · JSON export / import", href: "database.html" },
      { i: "K", t: "Knowledge", h: "Approved docs", href: "knowledge.html" },
      { i: "B", t: "Knowledge brain", h: "Atom view", href: "brain.html" },
      { i: "I", t: "Inbox", h: "Classify and reply", href: "inbox.html" },
      { i: "T", t: "Audit", h: "Trail", href: "audit.html" },
      { i: "M", t: "Control", h: "Matrix and roles", href: "control.html" },
      { i: "R", t: "Insights", h: "14-day SVG", href: "insights.html" },
      { i: "H", t: "Hub", h: "All doors", href: "hub.html" },
    ];

    var pal = document.getElementById("pal");
    if (!pal) {
      pal = document.createElement("div");
      pal.id = "pal";
      pal.className = "pal-ovl";
      pal.innerHTML =
        '<div class="pal-box" role="dialog" aria-label="Command palette">' +
        '<input id="palInput" placeholder="Jump to a page… (Ctrl+K)" autocomplete="off">' +
        '<div id="palList"></div></div>';
      document.body.appendChild(pal);
      pal.addEventListener("click", function (e) {
        if (e.target === pal) palClose();
      });
    }
    var palInput = document.getElementById("palInput");
    var palList = document.getElementById("palList");

    function palOpen() {
      pal.classList.add("open");
      PAL_SEL = 0;
      palRender("");
      if (palInput) {
        palInput.value = "";
        setTimeout(function () { palInput.focus(); }, 20);
      }
    }
    function palClose() { pal.classList.remove("open"); }
    function palRender(q) {
      q = (q || "").trim().toLowerCase();
      var list = COMMANDS.filter(function (c) {
        return !q || (c.t + " " + c.h).toLowerCase().indexOf(q) !== -1;
      });
      PAL_SEL = Math.min(PAL_SEL, Math.max(0, list.length - 1));
      palList.innerHTML = list.length
        ? list.map(function (c, i) {
            return (
              '<div class="pal-item' + (i === PAL_SEL ? " sel" : "") + '" data-i="' + i + '">' +
              '<span class="pi-ic">' + c.i + "</span><span class=\"pi-t\">" + esc(c.t) + "</span>" +
              '<span class="pi-h">' + esc(c.h) + "</span></div>"
            );
          }).join("")
        : '<div class="pal-none">No matching page</div>';
      palList._list = list;
      palList.querySelectorAll(".pal-item").forEach(function (el) {
        el.onclick = function () {
          var item = list[+el.getAttribute("data-i")];
          palClose();
          if (item) window.location.href = item.href;
        };
      });
    }
    if (palInput) {
      palInput.addEventListener("input", function () { palRender(palInput.value); });
    }
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === "k") {
        e.preventDefault();
        pal.classList.contains("open") ? palClose() : palOpen();
        return;
      }
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        var tag = (e.target && e.target.tagName) || "";
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          e.preventDefault();
          palOpen();
          return;
        }
      }
      if (!pal.classList.contains("open")) return;
      var list = palList._list || [];
      if (e.key === "Escape") { e.preventDefault(); palClose(); }
      else if (e.key === "ArrowDown") {
        e.preventDefault();
        PAL_SEL = (PAL_SEL + 1) % Math.max(1, list.length);
        palRender(palInput ? palInput.value : "");
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        PAL_SEL = (PAL_SEL - 1 + list.length) % Math.max(1, list.length);
        palRender(palInput ? palInput.value : "");
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (list[PAL_SEL]) {
          palClose();
          window.location.href = list[PAL_SEL].href;
        }
      }
    });

    var search = document.querySelector(".bar .search");
    if (search) {
      search.setAttribute("placeholder", "Ctrl+K to jump");
      search.addEventListener("focus", function () { palOpen(); search.blur(); });
    }

    document.addEventListener("click", function (e) {
      var btn = e.target.closest("#expJson");
      if (!btn) return;
      var payload = {
        generated_at: new Date().toISOString(),
        page: location.pathname,
        awaiting: (document.getElementById("awaiting-chip") || {}).textContent || "",
      };
      var blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "zenovix-ops-" + new Date().toISOString().slice(0, 10) + ".json";
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      toast("JSON snapshot downloaded");
    });
  })();
  /* =====================================================================
     1.4.0 — Manager desk, Catalog editor, Business variables.
     One API call per page (/admin/api/desk), readable rows, one-tap
     approve/reject that tells the customer, and forms a non-technical
     manager can use. Reads only /admin/api/*.
     ===================================================================== */
  (function desk140() {
    function fmtAge(s) {
      if (s == null) return "";
      if (s < 60) return s + "s";
      if (s < 3600) return Math.floor(s / 60) + "m";
      if (s < 86400) return Math.floor(s / 3600) + "h";
      return Math.floor(s / 86400) + "d";
    }
    function fmtTime(iso) {
      if (!iso) return "";
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    function money(v, cur) {
      if (v == null || v === "" || Number(v) <= 0) return "on request";
      return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) + " " + (cur || "USD");
    }
    function sparkline(el, points) {
      if (!el) return;
      var vals = points.map(function (p) { return Number(p.n || 0); });
      if (!vals.length) { el.innerHTML = '<div class="empty">No messages in the last 24 hours</div>'; return; }
      var w = 600, h = 64, max = Math.max.apply(null, vals.concat([1]));
      var step = vals.length > 1 ? w / (vals.length - 1) : w;
      var d = vals.map(function (v, i) {
        return (i ? "L" : "M") + (i * step).toFixed(1) + " " + (h - 4 - (v / max) * (h - 10)).toFixed(1);
      }).join(" ");
      el.innerHTML =
        '<svg class="spark" viewBox="0 0 ' + w + " " + h + '" preserveAspectRatio="none" aria-hidden="true">' +
        '<path d="' + d + " L" + w + " " + h + " L0 " + h + ' Z" fill="currentColor" opacity=".08"/>' +
        '<path d="' + d + '" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>' +
        '<div class="mini">' + vals.reduce(function (a, b) { return a + b; }, 0) + " messages · 24h · peak " + max + "/h</div>";
    }

    // ---------- drawer: one conversation ----------
    var drawer = null;
    function ensureDrawer() {
      if (drawer) return drawer;
      drawer = document.createElement("aside");
      drawer.className = "drawer";
      drawer.innerHTML =
        '<div class="drawer-head"><span class="ph" id="dr-title">Conversation</span>' +
        '<button class="btn ghost" type="button" id="dr-close">Close</button></div>' +
        '<div class="drawer-body" id="dr-body"></div>';
      document.body.appendChild(drawer);
      drawer.querySelector("#dr-close").addEventListener("click", function () { drawer.classList.remove("open"); });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") drawer.classList.remove("open"); });
      return drawer;
    }
    function openConversation(id) {
      if (!id) return;
      var d = ensureDrawer();
      d.classList.add("open");
      var body = d.querySelector("#dr-body");
      body.innerHTML = '<div class="empty">Loading…</div>';
      api("/desk/conversation/" + encodeURIComponent(id)).then(function (r) {
        if (!r._ok) { body.innerHTML = '<div class="empty">' + esc(r.detail || "Could not load") + "</div>"; return; }
        var c = r.conversation || {};
        d.querySelector("#dr-title").textContent = (c.customer || "Customer") + " · " + (c.channel || "") + (c.language ? " · " + c.language : "");
        var html = "";
        if (r.requests && r.requests.length) {
          html += '<div class="panel" style="margin-bottom:12px"><div class="panel-head"><span class="ph">Requests</span></div><div class="panel-body">' +
            r.requests.map(function (q) {
              return '<div class="sys-row"><span>' + esc(q.reference || "") + " · " + esc(money(q.total, q.currency)) + '</span><span class="sys-mode ' +
                (q.status === "sent" ? "up" : q.status === "rejected" ? "down" : "") + '">' + esc(q.status) + "</span></div>";
            }).join("") + "</div></div>";
        }
        if (r.memories && r.memories.length) {
          html += '<div class="panel" style="margin-bottom:12px"><div class="panel-head"><span class="ph">What Zenovix remembers</span><span class="hint">long-term memory</span></div><div class="panel-body">' +
            r.memories.map(function (m) { return '<div class="log-line"><b>' + esc(m.kind) + "</b> · " + esc(m.content) + "</div>"; }).join("") + "</div></div>";
        }
        html += (r.turns || []).map(function (t) {
          var role = t.role === "agent" ? "agent" : t.role === "system" ? "system" : "user";
          return '<div class="turn ' + role + '"><div class="who">' + (role === "agent" ? "Zenovix" : role === "system" ? "system" : "customer") +
            " · " + esc(fmtTime(t.at)) + '</div><div class="txt">' + esc(t.text) + "</div></div>";
        }).join("") || '<div class="empty">No messages stored yet</div>';
        body.innerHTML = html;
        body.scrollTop = body.scrollHeight;
      }).catch(function () { body.innerHTML = '<div class="empty">API unreachable</div>'; });
    }
    document.addEventListener("click", function (e) {
      var row = e.target.closest("[data-conv]");
      if (row && !e.target.closest("button")) openConversation(row.getAttribute("data-conv"));
    });

    // ---------- desk page ----------
    var deskRoot = document.getElementById("desk");
    function decide(id, status, btn) {
      var row = btn && btn.closest(".event-row");
      if (row) row.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
      api("/approvals/" + encodeURIComponent(id) + "/decide", { method: "POST", body: { status: status, note: "desk" } })
        .then(function (d) {
          if (!d._ok) {
            toast((d.detail || "Decide failed") + " (" + d._status + ")");
            if (row) row.querySelectorAll("button").forEach(function (b) { b.disabled = false; });
            return;
          }
          var told = d.delivered && d.delivered.sent;
          toast((status === "approved" ? "Approved" : "Rejected") + (d.reference ? " · " + d.reference : "") + (told ? " · customer notified" : " · recorded"));
          if (row) { row.setAttribute("data-decided", status); row.querySelector(".ev-actions").innerHTML = '<span class="sys-mode ' + (status === "approved" ? "up" : "down") + '">' + status + (told ? " · sent" : "") + "</span>"; }
          loadDesk();
        }).catch(function () { toast("API unreachable — nothing executed"); });
    }
    function paintDesk(d) {
      var m = d.metrics || {};
      var set = function (id, v, cls) { var el = document.getElementById(id); if (el) { el.textContent = v; if (cls) el.className = "v " + cls; } };
      set("m-pending", m.pending || 0, (m.pending || 0) > 0 ? "warn" : "good");
      set("m-msgs", m.messages_24h || 0);
      set("m-active", m.active_24h || 0);
      set("m-approved", m.approved_24h || 0, "good");
      set("m-tickets", m.open_tickets || 0, (m.open_tickets || 0) > 0 ? "warn" : "");
      var chip = document.getElementById("awaiting-chip");
      if (chip) chip.textContent = (m.pending || 0) + " awaiting you";
      var pend = document.getElementById("desk-pending");
      if (pend) {
        var items = d.pending || [];
        pend.innerHTML = items.length ? items.map(function (it) {
          return '<div class="event-row" data-approval="' + esc(it.id) + '">' +
            '<span class="sev ' + esc(it.severity) + '"></span>' +
            '<div><div class="ev-who">' + esc(it.who) + (it.reference ? '<span class="ref">' + esc(it.reference) + "</span>" : "") + "</div>" +
            '<div class="ev-what">' + esc(it.what || it.kind) + (it.amount ? " · " + esc(it.amount) : "") + "</div>" +
            '<div class="ev-meta">' + esc(it.kind) + " · " + esc(it.channel || "—") + (it.language ? " · " + esc(it.language) : "") + " · waiting " + fmtAge(it.age_s) + "</div></div>" +
            '<div class="ev-actions">' +
            '<button class="btn good" type="button" data-ok="' + esc(it.id) + '">Approve</button>' +
            '<button class="btn bad" type="button" data-no="' + esc(it.id) + '">Reject</button>' +
            (it.conversation_id ? '<button class="btn ghost" type="button" data-conv="' + esc(it.conversation_id) + '">Read</button>' : "") +
            "</div></div>";
        }).join("") : '<div class="empty">Nothing waiting for you. Zenovix is answering on its own.</div>';
        pend.querySelectorAll("[data-ok]").forEach(function (b) { b.onclick = function () { decide(b.getAttribute("data-ok"), "approved", b); }; });
        pend.querySelectorAll("[data-no]").forEach(function (b) { b.onclick = function () { decide(b.getAttribute("data-no"), "rejected", b); }; });
      }
      var rec = document.getElementById("desk-recent");
      if (rec) {
        var rows = d.recent || [];
        rec.innerHTML = rows.length ? rows.map(function (c) {
          return '<div class="led-row" data-conv="' + esc(c.id) + '"><div><div class="l1">' + esc(c.customer || "customer") +
            ' <span class="mini">· ' + esc(c.channel) + (c.language ? " · " + esc(c.language) : "") + "</span></div>" +
            '<div class="l2">' + (c.last_role === "agent" ? "Zenovix: " : "") + esc(c.last_text || "") + "</div></div>" +
            '<div class="r">' + c.turns + " msgs<br>" + esc(fmtTime(c.updated_at)) + "</div></div>";
        }).join("") : '<div class="empty">No conversations yet</div>';
      }
      sparkline(document.getElementById("desk-spark"), d.volume || []);
      var sys = document.getElementById("desk-system");
      if (sys) {
        var s = d.system || {};
        var line = function (k, ok, txt) { return '<div class="sys-row"><span>' + k + '</span><span class="sys-mode ' + (ok ? "up" : "down") + '">' + esc(txt || (ok ? "up" : "down")) + "</span></div>"; };
        sys.innerHTML = line("Database", s.postgres) + line("Redis", s.redis) +
          (s.channels || []).map(function (c) { return line(c.name === "telegram" ? "Telegram bot" : c.name === "whatsapp" ? "WhatsApp" : "E-mail", c.up, c.up ? "up" : "off"); }).join("") +
          '<div class="sys-row"><span>Brain</span><span class="sys-mode up">' + esc(s.llm_mode || "") + "</span></div>" +
          '<div class="sys-row"><span>Manager time-out</span><span class="sys-mode">' + Math.round((s.hitl_timeout_s || 0) / 60) + " min · " + esc(s.hitl_fallback || "") + "</span></div>" +
          '<div class="sys-row"><span>Version</span><span class="sys-mode">' + esc(d.version || "") + " · up " + fmtAge(d.uptime_s) + "</span></div>";
      }
      var who = document.getElementById("whoami");
      if (who && d.viewer) who.textContent = d.viewer + " · " + (d.role || "manager");
    }
    var deskTimer = null;
    function loadDesk() {
      if (!deskRoot) return;
      api("/desk").then(function (d) {
        if (d._status === 401) { window.location.href = "login.html"; return; }
        if (!d._ok) { toast("Desk failed (" + d._status + ")"); return; }
        paintDesk(d);
      }).catch(function () { var p = document.getElementById("desk-pending"); if (p) p.innerHTML = '<div class="empty">API unreachable</div>'; });
    }
    if (deskRoot) {
      loadDesk();
      deskTimer = setInterval(loadDesk, 15000);
      var clock = document.getElementById("desk-clock");
      if (clock) setInterval(function () { clock.textContent = new Date().toLocaleTimeString(); }, 1000);
    }

    // ---------- catalog editor ----------
    var cat = document.getElementById("catalog");
    if (cat) {
      var LANGS = [];
      var CATS = [];
      var PRODUCTS = [];
      var current = null;
      var form = document.getElementById("prod-form");
      var listEl = document.getElementById("prod-list");
      var status = document.getElementById("prod-status");
      var trWrap = document.getElementById("prod-translations");
      function say(m) { if (status) status.textContent = m; }

      function paintList() {
        if (!listEl) return;
        var q = (document.getElementById("prod-search") || {}).value || "";
        q = q.toLowerCase();
        var rows = PRODUCTS.filter(function (p) {
          return !q || ((p.code || "") + " " + (p.name_en || "") + " " + (p.sku || "") + " " + (p.category || "")).toLowerCase().indexOf(q) !== -1;
        });
        listEl.innerHTML = rows.length ? rows.map(function (p) {
          var img = p.has_image ? "/admin/api/catalog/products/" + p.id + "/image" : (p.image_url && p.image_url.indexOf("/admin/api/") !== 0 ? p.image_url : "");
          return '<tr data-pid="' + esc(p.id) + '" class="' + (current && current.id === p.id ? "on" : "") + '">' +
            "<td>" + (img ? '<img class="thumb" src="' + esc(img) + '" alt="">' : '<span class="thumb"></span>') + "</td>" +
            '<td><b>' + esc(p.code || "") + "</b></td>" +
            "<td>" + esc(p.name_en) + '<div class="mini">' + esc(p.title_en || "") + "</div></td>" +
            "<td>" + esc(p.category || "") + "</td>" +
            '<td class="num">' + esc(money(p.unit_price, p.currency)) + (p.unit ? " / " + esc(p.unit) : "") + "</td>" +
            '<td><span class="sys-mode ' + (p.is_active ? "up" : "down") + '">' + (p.is_active ? "live" : "hidden") + "</span></td></tr>";
        }).join("") : '<tr><td colspan="6" class="empty">No products yet — press New product.</td></tr>';
        listEl.querySelectorAll("tr[data-pid]").forEach(function (tr) {
          tr.onclick = function () {
            var p = PRODUCTS.filter(function (x) { return x.id === tr.getAttribute("data-pid"); })[0];
            if (p) edit(p);
          };
        });
        var count = document.getElementById("prod-count");
        if (count) count.textContent = PRODUCTS.length + " products · " + PRODUCTS.filter(function (p) { return p.is_active; }).length + " live";
      }
      function paintCategoryOptions() {
        var sel = form && form.elements.category;
        if (!sel) return;
        var v = sel.value;
        sel.innerHTML = CATS.map(function (c) { return '<option value="' + esc(c.key) + '">' + esc((c.icon ? c.icon + " " : "") + (c.name_en || c.key)) + "</option>"; }).join("") +
          '<option value="__new">+ New category…</option>';
        if (v) sel.value = v;
        var ctab = document.getElementById("cat-list");
        if (ctab) {
          ctab.innerHTML = CATS.map(function (c) {
            return '<div class="led-row" data-catkey="' + esc(c.key) + '"><div><div class="l1">' + esc((c.icon ? c.icon + " " : "") + (c.name_en || c.key)) +
              ' <span class="mini">· ' + esc(c.key) + "</span></div>" +
              '<div class="l2">' + esc(Object.keys(c.names || {}).map(function (k) { return k + ": " + c.names[k]; }).join(" · ")) + "</div></div>" +
              '<div class="r">' + (c.products || 0) + " products</div></div>";
          }).join("") || '<div class="empty">No categories yet</div>';
          ctab.querySelectorAll("[data-catkey]").forEach(function (row) {
            row.onclick = function () { editCategory(CATS.filter(function (c) { return c.key === row.getAttribute("data-catkey"); })[0]); };
          });
        }
      }
      function paintTranslations(p) {
        if (!trWrap) return;
        var names = (p && p.names) || {};
        var titles = (p && p.titles) || {};
        trWrap.innerHTML = LANGS.map(function (l) {
          return '<div class="fld"><span>' + esc(l.name) + " (" + esc(l.code) + ")</span>" +
            '<input data-tr-name="' + esc(l.code) + '" value="' + esc(names[l.code] || "") + '" placeholder="Name in ' + esc(l.name) + '">' +
            '<input data-tr-title="' + esc(l.code) + '" value="' + esc(titles[l.code] || "") + '" placeholder="One-line title (optional)" style="margin-top:4px"></div>';
        }).join("");
      }
      function edit(p) {
        current = p;
        if (!form) return;
        ["sku", "code", "name_en", "title_en", "category", "unit", "unit_price", "currency", "stock_qty", "sort_order", "description_en", "image_url"].forEach(function (k) {
          if (form.elements[k]) form.elements[k].value = p[k] == null ? "" : p[k];
        });
        if (form.elements.is_active) form.elements.is_active.checked = !!p.is_active;
        var img = document.getElementById("prod-img");
        if (img) {
          var src = p.has_image ? "/admin/api/catalog/products/" + p.id + "/image?t=" + Date.now() : (p.image_url && p.image_url.indexOf("/admin/api/") !== 0 ? p.image_url : "");
          img.src = src || "";
          img.style.display = src ? "block" : "none";
        }
        paintTranslations(p);
        var title = document.getElementById("prod-title");
        if (title) title.textContent = "Edit · " + (p.code || "") + " · " + (p.name_en || "");
        say("");
        paintList();
        var del = document.getElementById("prod-hide");
        if (del) del.style.display = "";
        var up = document.getElementById("prod-upload");
        if (up) up.disabled = false;
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      function blank() {
        current = null;
        if (form) {
          form.reset();
          form.elements.currency.value = "USD";
          form.elements.unit.value = "metric ton";
          form.elements.sort_order.value = 100;
          form.elements.is_active.checked = true;
        }
        var img = document.getElementById("prod-img");
        if (img) img.style.display = "none";
        paintTranslations(null);
        var title = document.getElementById("prod-title");
        if (title) title.textContent = "New product";
        var del = document.getElementById("prod-hide");
        if (del) del.style.display = "none";
        var up = document.getElementById("prod-upload");
        if (up) up.disabled = true;
        say("Fill in the English name and price, then Save. Code is assigned automatically if empty.");
      }
      function collect() {
        var body = {};
        ["sku", "code", "name_en", "title_en", "category", "unit", "currency", "description_en", "image_url"].forEach(function (k) {
          if (form.elements[k]) body[k] = form.elements[k].value.trim();
        });
        body.unit_price = Number(form.elements.unit_price.value || 0);
        body.stock_qty = Number(form.elements.stock_qty.value || 0);
        body.sort_order = Number(form.elements.sort_order.value || 100);
        body.is_active = !!form.elements.is_active.checked;
        body.names = {}; body.titles = {};
        trWrap.querySelectorAll("[data-tr-name]").forEach(function (i) { if (i.value.trim()) body.names[i.getAttribute("data-tr-name")] = i.value.trim(); });
        trWrap.querySelectorAll("[data-tr-title]").forEach(function (i) { if (i.value.trim()) body.titles[i.getAttribute("data-tr-title")] = i.value.trim(); });
        if (body.category === "__new") body.category = "";
        if (!body.sku) body.sku = "PRD-" + (body.code || Date.now().toString(36).toUpperCase());
        return body;
      }
      function loadAll() {
        say("Loading…");
        Promise.all([api("/catalog/products?limit=200"), api("/catalog/categories"), api("/catalog/languages")]).then(function (r) {
          if (r[0]._status === 401) { window.location.href = "login.html"; return; }
          PRODUCTS = (r[0].items || []);
          CATS = (r[1].items || []);
          LANGS = (r[2].items || []);
          paintCategoryOptions();
          paintList();
          if (current) {
            var again = PRODUCTS.filter(function (p) { return p.id === current.id; })[0];
            if (again) edit(again);
          } else { blank(); }
        }).catch(function () { say("API unreachable"); });
      }
      if (form) {
        form.addEventListener("submit", function (ev) {
          ev.preventDefault();
          var body = collect();
          if (!body.name_en) { say("English name is required."); return; }
          say("Saving…");
          var req = current ? api("/catalog/products/" + encodeURIComponent(current.id), { method: "PUT", body: body })
                            : api("/catalog/products", { method: "POST", body: body });
          req.then(function (d) {
            if (d._status === 403) { say("Your role cannot edit the catalog."); return; }
            if (!d._ok) { say((d.detail && (typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail))) || "Save failed"); return; }
            toast(current ? "Product saved" : "Product created · code " + (d.code || ""));
            if (!current && d.product_id) current = { id: d.product_id };
            loadAll();
          }).catch(function () { say("API unreachable — nothing saved"); });
        });
        form.elements.category.addEventListener("change", function () {
          if (form.elements.category.value !== "__new") return;
          var key = prompt("New category key (lowercase, e.g. lubricants):", "");
          if (!key) { form.elements.category.value = CATS.length ? CATS[0].key : ""; return; }
          key = key.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-+|-+$/g, "");
          var name = prompt("English name shown to customers:", key.replace(/-/g, " "));
          api("/catalog/categories/" + encodeURIComponent(key), { method: "PUT", body: { key: key, name_en: name || key, names: {}, icon: "", sort_order: 100, is_active: true } })
            .then(function () { return api("/catalog/categories"); })
            .then(function (r) { CATS = r.items || []; paintCategoryOptions(); form.elements.category.value = key; });
        });
      }
      var newBtn = document.getElementById("prod-new");
      if (newBtn) newBtn.addEventListener("click", blank);
      var hideBtn = document.getElementById("prod-hide");
      if (hideBtn) hideBtn.addEventListener("click", function () {
        if (!current) return;
        var next = !current.is_active;
        api("/catalog/products/" + encodeURIComponent(current.id), { method: "PUT", body: { is_active: next } }).then(function (d) {
          if (!d._ok) { say(d.detail || "Failed"); return; }
          toast(next ? "Product is live in the bot" : "Product hidden from the bot");
          loadAll();
        });
      });
      var search = document.getElementById("prod-search");
      if (search) search.addEventListener("input", paintList);
      var file = document.getElementById("prod-file");
      var upBtn = document.getElementById("prod-upload");
      if (upBtn && file) {
        upBtn.addEventListener("click", function () { file.click(); });
        file.addEventListener("change", function () {
          var f = file.files && file.files[0];
          if (!f || !current) return;
          if (f.size > 2 * 1024 * 1024) { say("Image must be under 2 MB."); return; }
          say("Uploading image…");
          fetch("/admin/api/catalog/products/" + encodeURIComponent(current.id) + "/image", {
            method: "POST", credentials: "same-origin", headers: { "Content-Type": f.type || "image/jpeg" }, body: f
          }).then(function (r) { return r.json().then(function (d) { d._ok = r.ok; return d; }); })
            .then(function (d) { if (!d._ok) { say(d.detail || "Upload failed"); return; } toast("Image saved — the bot sends it with the product"); loadAll(); })
            .catch(function () { say("Upload failed"); });
          file.value = "";
        });
      }
      // categories editor
      var catForm = document.getElementById("cat-form");
      function editCategory(c) {
        if (!catForm) return;
        catForm.elements.key.value = c ? c.key : "";
        catForm.elements.key.readOnly = !!c;
        catForm.elements.name_en.value = c ? (c.name_en || "") : "";
        catForm.elements.icon.value = c ? (c.icon || "") : "";
        catForm.elements.sort_order.value = c ? (c.sort_order || 100) : 100;
        catForm.elements.is_active.checked = c ? !!c.is_active : true;
        var wrap = document.getElementById("cat-translations");
        var names = (c && c.names) || {};
        wrap.innerHTML = LANGS.map(function (l) {
          return '<div class="fld"><span>' + esc(l.name) + '</span><input data-cat-name="' + esc(l.code) + '" value="' + esc(names[l.code] || "") + '"></div>';
        }).join("");
        var del = document.getElementById("cat-delete");
        if (del) del.style.display = c ? "" : "none";
        catForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      if (catForm) {
        catForm.addEventListener("submit", function (ev) {
          ev.preventDefault();
          var key = catForm.elements.key.value.trim().toLowerCase();
          if (!key) return;
          var names = {};
          catForm.querySelectorAll("[data-cat-name]").forEach(function (i) { if (i.value.trim()) names[i.getAttribute("data-cat-name")] = i.value.trim(); });
          api("/catalog/categories/" + encodeURIComponent(key), { method: "PUT", body: {
            key: key, name_en: catForm.elements.name_en.value.trim(), names: names, icon: catForm.elements.icon.value.trim(),
            sort_order: Number(catForm.elements.sort_order.value || 100), is_active: !!catForm.elements.is_active.checked
          } }).then(function (d) {
            if (!d._ok) { toast((d.detail && (typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail))) || "Save failed"); return; }
            toast("Category saved"); loadAll(); editCategory(null);
          });
        });
        var cnew = document.getElementById("cat-new");
        if (cnew) cnew.addEventListener("click", function () { editCategory(null); });
        var cdel = document.getElementById("cat-delete");
        if (cdel) cdel.addEventListener("click", function () {
          var key = catForm.elements.key.value.trim();
          if (!key || !confirm("Delete category " + key + "? Only possible when no product uses it.")) return;
          api("/catalog/categories/" + encodeURIComponent(key), { method: "DELETE" }).then(function (d) {
            if (!d._ok) { toast(d.detail || "Cannot delete"); return; }
            toast("Category deleted"); loadAll(); editCategory(null);
          });
        });
        editCategory(null);
      }
      loadAll();
    }

    // ---------- business variables ----------
    var vars = document.getElementById("variables");
    if (vars) {
      var vstatus = document.getElementById("vars-status");
      var dirty = {};
      function vsay(m) { if (vstatus) vstatus.textContent = m; }
      function field(item, value) {
        var id = "v_" + item.key;
        var botTag = item.bot ? ' <span class="tag ice" title="The Telegram bot reads this">bot</span>' : "";
        if (item.kind === "bool") {
          return '<label class="switch"><span><b>' + esc(item.label) + "</b>" + botTag + (item.help ? '<div class="help">' + esc(item.help) + "</div>" : "") +
            '</span><input type="checkbox" id="' + id + '" data-key="' + esc(item.key) + '"' + (value ? " checked" : "") + "></label>";
        }
        var input;
        if (item.kind === "textarea") input = '<textarea id="' + id + '" data-key="' + esc(item.key) + '">' + esc(value == null ? "" : value) + "</textarea>";
        else if (item.kind === "select") input = '<select id="' + id + '" data-key="' + esc(item.key) + '">' + item.options.map(function (o) { return '<option value="' + esc(o) + '"' + (o === value ? " selected" : "") + ">" + esc(o) + "</option>"; }).join("") + "</select>";
        else if (item.kind === "list") input = '<input id="' + id + '" data-key="' + esc(item.key) + '" value="' + esc(Array.isArray(value) ? value.join(", ") : (value || "")) + '">';
        else if (item.kind === "number") input = '<input type="number" step="any" id="' + id + '" data-key="' + esc(item.key) + '" value="' + esc(value == null ? "" : value) + '"' + (item.min != null ? ' min="' + item.min + '"' : "") + (item.max != null ? ' max="' + item.max + '"' : "") + ">";
        else input = '<input id="' + id + '" data-key="' + esc(item.key) + '" value="' + esc(value == null ? "" : value) + '">';
        return '<div class="fld' + (item.kind === "textarea" ? " wide" : "") + '"><span>' + esc(item.label) + botTag + "</span>" + input + (item.help ? '<span class="help">' + esc(item.help) + "</span>" : "") + "</div>";
      }
      function paintVars(d) {
        var values = d.values || {};
        vars.innerHTML = (d.spec || []).map(function (g) {
          var bools = g.items.filter(function (i) { return i.kind === "bool"; });
          var others = g.items.filter(function (i) { return i.kind !== "bool"; });
          return '<section class="panel"><div class="panel-head"><span class="ph">' + esc(g.title) + '</span><span class="hint">' + esc(g.hint) + "</span></div>" +
            '<div class="panel-body">' + (others.length ? '<div class="form-grid">' + others.map(function (i) { return field(i, values[i.key]); }).join("") + "</div>" : "") +
            (bools.length ? '<div style="margin-top:' + (others.length ? "10px" : "0") + '">' + bools.map(function (i) { return field(i, values[i.key]); }).join("") + "</div>" : "") +
            "</div></section>";
        }).join("");
        var env = d.env || {};
        var envEl = document.getElementById("vars-env");
        if (envEl) {
          envEl.innerHTML = [
            ["Currency", env.currency], ["Tax rate", env.tax_rate], ["Quote validity", env.quote_valid_days + " days"],
            ["Support contact", env.support_contact], ["Timezone", env.timezone],
            ["Manager time-out", Math.round((env.hitl_timeout_seconds || 0) / 60) + " min · " + env.hitl_fallback],
            ["Telegram managers", env.telegram_admins], ["WhatsApp", env.whatsapp_enabled ? "on" : "off"], ["E-mail", env.email_enabled ? "on" : "off"], ["Brain", env.llm_mode]
          ].map(function (r) { return '<div class="sys-row"><span>' + esc(r[0]) + '</span><span class="sys-mode">' + esc(r[1] == null ? "—" : r[1]) + "</span></div>"; }).join("");
        }
        vars.querySelectorAll("[data-key]").forEach(function (el) {
          el.addEventListener("input", function () { dirty[el.getAttribute("data-key")] = true; vsay(Object.keys(dirty).length + " change(s) not saved"); });
          el.addEventListener("change", function () { dirty[el.getAttribute("data-key")] = true; vsay(Object.keys(dirty).length + " change(s) not saved"); });
        });
        dirty = {};
        vsay("");
      }
      function loadVars() {
        api("/settings/business").then(function (d) {
          if (d._status === 401) { window.location.href = "login.html"; return; }
          if (!d._ok) { vsay("Could not load (" + d._status + ")"); return; }
          paintVars(d);
        }).catch(function () { vsay("API unreachable"); });
      }
      var saveBtn = document.getElementById("vars-save");
      if (saveBtn) saveBtn.addEventListener("click", function () {
        var body = {};
        vars.querySelectorAll("[data-key]").forEach(function (el) {
          var k = el.getAttribute("data-key");
          if (!dirty[k]) return;
          body[k] = el.type === "checkbox" ? el.checked : el.value;
        });
        if (!Object.keys(body).length) { vsay("Nothing changed."); return; }
        vsay("Saving…");
        api("/settings/business", { method: "PUT", body: { values: body } }).then(function (d) {
          if (d._status === 403) { vsay("Your role cannot change variables."); return; }
          if (!d._ok) { vsay((d.detail && (typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail))) || "Save failed"); return; }
          toast("Saved · the bot uses it on the next message");
          paintVars({ values: d.values, spec: LAST_SPEC, env: LAST_ENV });
        }).catch(function () { vsay("API unreachable — nothing saved"); });
      });
      var LAST_SPEC = [], LAST_ENV = {};
      var _paint = paintVars;
      paintVars = function (d) { if (d.spec) LAST_SPEC = d.spec; if (d.env) LAST_ENV = d.env; _paint({ values: d.values, spec: LAST_SPEC, env: LAST_ENV }); };
      var reload = document.getElementById("vars-reload");
      if (reload) reload.addEventListener("click", loadVars);
      loadVars();
    }
  })();
})();
