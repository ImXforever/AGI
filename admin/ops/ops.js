(function () {
  "use strict";

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
      var policy = mail.getAttribute("data-policy");
      var tag = policy === "hold" ? "hold" : "auto";
      var label = policy === "hold" ? "Held for manager" : "Automatic under rules";
      reader.innerHTML =
        '<div style="color:var(--dim)">Email · ' +
        mail.getAttribute("data-cat") +
        " · proposed action</div>" +
        "<h2>" +
        mail.getAttribute("data-title") +
        "</h2>" +
        '<p style="color:var(--dim);margin:0 0 14px">' +
        mail.getAttribute("data-from") +
        "</p>" +
        "<p>" +
        mail.getAttribute("data-body") +
        "</p>" +
        '<p><span class="tag ' +
        tag +
        '">' +
        label +
        '</span> <span class="tag">' +
        mail.getAttribute("data-action") +
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

  document.querySelectorAll("[data-decide]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-id");
      var status = btn.getAttribute("data-decide");
      if (!id) {
        toast("Demo card — wire a real approval id from the API");
        return;
      }
      api("/approvals/" + encodeURIComponent(id) + "/decide", {
        method: "POST",
        body: { status: status, note: "ops console" },
      }).then(function (d) {
        if (d._status === 401) {
          toast("Sign in required — /admin/api/auth/login");
          return;
        }
        if (!d._ok) {
          toast((d.detail || "Decide failed") + " (" + d._status + ")");
          return;
        }
        toast((status === "approved" ? "Approved" : "Rejected") + " · " + (d.execution && d.execution.executed ? "executed" : "recorded"));
        btn.closest(".card") && btn.closest(".card").setAttribute("data-decided", status);
      }).catch(function () {
        toast("API unreachable — demo mode");
      });
    });
  });

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
})();
