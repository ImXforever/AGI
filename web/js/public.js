(function () {
  "use strict";
  var tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }
  var notice = document.getElementById("notice");
  var view = document.getElementById("view");

  function show(message) {
    if (!notice) return;
    notice.textContent = message;
    notice.style.display = "block";
    window.setTimeout(function () {
      notice.style.display = "none";
    }, 4200);
  }

  function actionPayload(action, code) {
    var payload = { v: 1, action: String(action || "") };
    if (code) payload.code = String(code);
    return JSON.stringify(payload);
  }

  function renderView(action) {
    if (!view || document.getElementById("catalog-panel")) return;
    var copy = {
      products: {
        h: "Products",
        p: "Ask the bot for the approved catalog. Prices on the site are not changed here."
      },
      support: {
        h: "Support",
        p: "Describe the issue in Telegram. Safety cases go to a person. You will see ticket status as open, waiting, resolved, or escalated — never the internal queue."
      },
      quote: {
        h: "Quote",
        p: "A draft is prepared from the catalog. Sending waits for a manager record. Payment is never taken in this app."
      }
    };
    var item = copy[action];
    if (!item) return;
    view.innerHTML =
      "<div class=\"card\"><h2>" +
      item.h +
      "</h2><p>" +
      item.p +
      "</p></div>" +
      "<p style=\"color:var(--dim)\">Nothing here reads admin settings, env vars, or bot tokens.</p>";
  }

  var ALLOWED = { products: true, support: true, quote: true };

  function sendAction(action, code) {
    if (!ALLOWED[action]) return;
    if (tg && typeof tg.sendData === "function") {
      try {
        tg.sendData(actionPayload(action, code));
        show(code ? "Sent to the bot — pick a quantity there." : "Request sent. Quotes and sensitive mail wait for a manager.");
      } catch (err) {
        show("Could not send. Open this page inside Telegram.");
      }
      return;
    }
    renderView(action);
    if (location.pathname.indexOf("/app") === 0) {
      show("Open the customer app from Telegram to send this to the bot.");
      return;
    }
    location.href = "/app?action=" + encodeURIComponent(action);
  }

  // The Login button is always visible on the landing page: it opens the
  // manager sign-in form. Inside Telegram, admins get one-tap TWA login instead.
  var LOGIN_PAGE = "/admin/ops/login.html";

  function openOps() {
    window.location.href = "/admin/ops/ecosystem.html";
  }

  function twaLoginThenOps(ev) {
    if (ev) ev.preventDefault();
    if (!tg || !tg.initData) {
      window.location.href = LOGIN_PAGE;
      return;
    }
    fetch("/admin/api/twa/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ initData: tg.initData, init_data: tg.initData })
    })
      .then(function (r) {
        if (r.ok) openOps();
        else window.location.href = LOGIN_PAGE;
      })
      .catch(function () {
        window.location.href = LOGIN_PAGE;
      });
  }

  if (tg && tg.initData && document.querySelector("[data-admin-login]")) {
    fetch("/admin/api/twa/probe", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ initData: tg.initData, init_data: tg.initData })
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.admin) {
          document.querySelectorAll("[data-admin-login]").forEach(function (el) {
            el.addEventListener("click", twaLoginThenOps);
          });
        }
      })
      .catch(function () {});
  }

  // ---- 1.4.0: live catalog in the customer's language (public, no secrets) ----
  var catList = document.getElementById("cat-list");
  if (catList) {
    var lang = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) ||
      new URLSearchParams(location.search).get("lang") || (navigator.language || "en").slice(0, 2);
    var CATALOG = null;
    var CURRENT = "";
    function escapeHtml(s) {
      return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    }
    function paintCatalog() {
      if (!CATALOG) return;
      var chips = document.getElementById("cat-chips");
      if (chips) {
        chips.innerHTML = CATALOG.categories.map(function (c) {
          return '<button type="button" class="chip' + (c.key === CURRENT ? " on" : "") + '" data-cat="' + escapeHtml(c.key) + '">' +
            escapeHtml((c.icon ? c.icon + " " : "") + c.name) + " (" + c.count + ")</button>";
        }).join("");
        chips.querySelectorAll("[data-cat]").forEach(function (b) {
          b.addEventListener("click", function () { CURRENT = CURRENT === b.getAttribute("data-cat") ? "" : b.getAttribute("data-cat"); paintCatalog(); });
        });
      }
      var items = CATALOG.items.filter(function (p) { return !CURRENT || p.category === CURRENT; });
      catList.innerHTML = items.length ? items.map(function (p) {
        return '<div class="prod">' +
          (p.image ? '<img src="' + escapeHtml(p.image) + '" alt="" loading="lazy">' : '<span class="ph-img"></span>') +
          '<div><div class="code">' + escapeHtml(CATALOG.labels.code) + " " + escapeHtml(p.code) + '</div><div class="name">' + escapeHtml(p.name) + "</div>" +
          (p.title ? '<div class="title">' + escapeHtml(p.title) + "</div>" : "") + "</div>" +
          '<div class="price">' + escapeHtml(p.price_text) + (p.price && p.unit ? "<br>/ " + escapeHtml(p.unit) : "") +
          '<button type="button" class="order" data-order="' + escapeHtml(p.code) + '">' + escapeHtml(CATALOG.labels.order) + "</button></div></div>";
      }).join("") : '<div class="empty">—</div>';
      catList.querySelectorAll("[data-order]").forEach(function (b) {
        b.addEventListener("click", function () { sendAction("products", b.getAttribute("data-order")); });
      });
    }
    fetch("/api/public/catalog?lang=" + encodeURIComponent(lang), { credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) { catList.innerHTML = '<div class="empty">Catalog unavailable</div>'; return; }
        CATALOG = d;
        if (d.rtl) document.documentElement.setAttribute("dir", "rtl");
        var t = document.getElementById("cat-title");
        if (t && d.labels && d.labels.title) t.textContent = d.labels.title;
        var h = document.getElementById("cat-hint");
        if (h) h.textContent = d.items.length + " · " + (d.language || "en").toUpperCase();
        paintCatalog();
      })
      .catch(function () { catList.innerHTML = '<div class="empty">Catalog unavailable</div>'; });
    var conn = document.getElementById("conn");
    if (conn) {
      window.addEventListener("offline", function () { conn.textContent = "offline"; });
      window.addEventListener("online", function () { conn.textContent = "online"; });
    }
  }

  document.querySelectorAll("[data-action]").forEach(function (button) {
    button.addEventListener("click", function () {
      sendAction(button.getAttribute("data-action"));
    });
  });

  var pending = new URLSearchParams(location.search).get("action");
  if (pending && location.pathname.indexOf("/app") === 0) {
    sendAction(pending);
  }

  var menu = document.getElementById("menu");
  var links = document.getElementById("links");
  if (menu && links) {
    menu.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }
})();
