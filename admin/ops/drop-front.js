(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) {
    return Number(n || 0).toLocaleString("en-US");
  }

  /* ── Live gauges (DropAgent /live, English neon) ── */
  function gauge(canvasId, ratio, color, sub) {
    var cv = $(canvasId);
    if (!cv) return;
    var ctx = cv.getContext("2d");
    var w = cv.width;
    var h = cv.height;
    var cx = w / 2;
    var cy = h / 2;
    var r = w / 2 - 16;
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 12;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1c2a55";
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI * 0.75, Math.PI * 2.25);
    ctx.stroke();
    ratio = Math.max(0, Math.min(1, ratio));
    if (ratio > 0) {
      var grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, color);
      grad.addColorStop(1, "#ff2bd6");
      ctx.strokeStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, r, Math.PI * 0.75, Math.PI * 0.75 + Math.PI * 1.5 * ratio);
      ctx.stroke();
    }
    ctx.fillStyle = "#eaf6ff";
    ctx.font = "bold 28px ui-sans-serif, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(Math.round(ratio * 100) + "%", cx, cy - 8);
    ctx.fillStyle = "#7f9ec7";
    ctx.font = "13px ui-sans-serif, system-ui, sans-serif";
    ctx.fillText(sub || "", cx, cy + 20);
  }

  function liveApply(d) {
    gauge("gInbound", (d.inbound || 0) / 200, "#00f0ff", fmt(d.inbound));
    gauge("gQueue", (d.queue || 0) / 20, d.queue > 6 ? "#ff3d7a" : "#ffb020", fmt(d.queue));
    gauge("gAuto", (d.auto || 0) / 150, "#00ffa8", fmt(d.auto));
    gauge("gTickets", (d.tickets || 0) / 30, "#b6ff3b", fmt(d.tickets));
    if ($("vInbound")) $("vInbound").textContent = fmt(d.inbound);
    if ($("vQueue")) $("vQueue").textContent = fmt(d.queue);
    if ($("vAuto")) $("vAuto").textContent = fmt(d.auto);
    if ($("vTickets")) $("vTickets").textContent = fmt(d.tickets);
    var map = {
      rLeads: d.leads,
      rQuotes: d.quotes,
      rPay: d.payments,
      rWd: d.withdrawals,
      rPend: d.products,
      rTik: d.tickets_open,
    };
    Object.keys(map).forEach(function (id) {
      if ($(id)) $(id).textContent = fmt(map[id]);
    });
  }

  function startLive() {
    if (!$("gInbound")) return;
    var base = {
      inbound: 128,
      queue: 4,
      auto: 84,
      tickets: 9,
      leads: 7,
      quotes: 3,
      payments: 1,
      withdrawals: 0,
      products: 2,
      tickets_open: 9,
    };
    var mode = $("liveMode");
    var dot = $("liveDot");
    function tick() {
      var jitter = function (n, a) {
        return Math.max(0, n + Math.round((Math.random() - 0.5) * a));
      };
      liveApply({
        inbound: jitter(base.inbound, 4),
        queue: base.queue,
        auto: jitter(base.auto, 2),
        tickets: base.tickets,
        leads: base.leads,
        quotes: base.quotes,
        payments: base.payments,
        withdrawals: base.withdrawals,
        products: base.products,
        tickets_open: base.tickets_open,
      });
      if (dot) {
        dot.className = "dot live";
      }
      if (mode) mode.textContent = "Mock stream · 3s (no backend)";
    }
    tick();
    setInterval(tick, 3000);
  }

  /* ── Insights SVG (DropAgent /insights) ── */
  function lineChart(el, labels, s1, s2, c1, c2) {
    var node = $(el);
    if (!node) return;
    var W = 560,
      H = 200,
      P = 28;
    var max = Math.max(1, Math.max.apply(null, s1.concat(s2)));
    var X = function (i) {
      return P + i * ((W - 2 * P) / Math.max(1, labels.length - 1));
    };
    var Y = function (v) {
      return H - P - (v / max) * (H - 2 * P);
    };
    var path = function (s) {
      return s
        .map(function (v, i) {
          return (i ? "L" : "M") + X(i).toFixed(1) + "," + Y(v).toFixed(1);
        })
        .join(" ");
    };
    var grid = "";
    for (var g = 0; g <= 3; g++) {
      var y = P + g * ((H - 2 * P) / 3);
      grid +=
        '<line x1="' +
        P +
        '" y1="' +
        y +
        '" x2="' +
        (W - P) +
        '" y2="' +
        y +
        '" stroke="rgba(0,240,255,.12)"/>' +
        '<text x="' +
        (W - P + 4) +
        '" y="' +
        (y + 4) +
        '" fill="#7f9ec7" font-size="9">' +
        Math.round(max * (1 - g / 3)) +
        "</text>";
    }
    var lbls = labels
      .map(function (d, i) {
        return i % Math.ceil(labels.length / 7) === 0
          ? '<text x="' +
              X(i) +
              '" y="' +
              (H - 6) +
              '" fill="#7f9ec7" font-size="9" text-anchor="middle">' +
              esc(d) +
              "</text>"
          : "";
      })
      .join("");
    node.innerHTML =
      '<svg viewBox="0 0 ' +
      W +
      " " +
      H +
      '" preserveAspectRatio="none">' +
      grid +
      '<path d="' +
      path(s2) +
      '" fill="none" stroke="' +
      c2 +
      '" stroke-width="2.2" opacity=".85"/>' +
      '<path d="' +
      path(s1) +
      '" fill="none" stroke="' +
      c1 +
      '" stroke-width="2.2"/>' +
      s1
        .map(function (v, i) {
          return '<circle cx="' + X(i) + '" cy="' + Y(v) + '" r="2.6" fill="' + c1 + '"/>';
        })
        .join("") +
      lbls +
      "</svg>";
  }

  function barChart(el, labels, vals, color) {
    var node = $(el);
    if (!node) return;
    var W = 560,
      H = 200,
      P = 28;
    var max = Math.max(1, Math.max.apply(null, vals));
    var bw = (W - 2 * P) / vals.length;
    var bars = vals
      .map(function (v, i) {
        var h = (v / max) * (H - 2 * P);
        return (
          '<rect x="' +
          (P + i * bw + bw * 0.18).toFixed(1) +
          '" y="' +
          (H - P - h).toFixed(1) +
          '" width="' +
          (bw * 0.64).toFixed(1) +
          '" height="' +
          Math.max(h, 1).toFixed(1) +
          '" rx="3" fill="' +
          color +
          '" opacity=".88"><title>' +
          esc(labels[i]) +
          ": " +
          fmt(v) +
          "</title></rect>"
        );
      })
      .join("");
    var grid = "";
    for (var g = 0; g <= 3; g++) {
      var y = P + g * ((H - 2 * P) / 3);
      grid +=
        '<line x1="' +
        P +
        '" y1="' +
        y +
        '" x2="' +
        (W - P) +
        '" y2="' +
        y +
        '" stroke="rgba(0,240,255,.12)"/>';
    }
    node.innerHTML =
      '<svg viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none">' + grid + bars + "</svg>";
  }

  function startInsights() {
    if (!$("chartUsers")) return;
    var days = ["22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "1", "2", "3", "4"];
    var neu = [2, 1, 4, 3, 2, 5, 1, 3, 6, 2, 4, 3, 7, 4];
    var act = [18, 20, 19, 22, 21, 24, 16, 23, 28, 25, 27, 26, 30, 29];
    var gmv = [1200, 800, 2100, 900, 1600, 2400, 400, 1800, 3200, 1100, 1900, 2200, 4100, 2500];
    lineChart("chartUsers", days, neu, act, "#00f0ff", "#ff2bd6");
    barChart("chartGmv", days, gmv, "#b6ff3b");
    var products = [
      { title: "PET-001 base oil", n: 12 },
      { title: "200L drums", n: 9 },
      { title: "Circulating pump", n: 6 },
      { title: "TDS pack", n: 4 },
    ];
    var cats = [
      { title: "Lubricants", n: 18 },
      { title: "Equipment", n: 7 },
      { title: "Docs", n: 5 },
      { title: "Training", n: 3 },
    ];
    function bars(id, items) {
      var el = $(id);
      if (!el) return;
      var max = Math.max.apply(
        null,
        items.map(function (i) {
          return i.n;
        })
      );
      el.innerHTML = items
        .map(function (p) {
          return (
            '<div class="bar-row"><span class="lbl" title="' +
            esc(p.title) +
            '">' +
            esc(p.title) +
            '</span><span class="bar" style="width:' +
            (p.n / max) * 70 +
            '%"></span><b class="num">' +
            fmt(p.n) +
            "</b></div>"
          );
        })
        .join("");
    }
    bars("topProducts", products);
    bars("topCats", cats);
  }

  /* ── Market catalog (DropAgent storefront) ── */
  var PRODUCTS = [
    { id: 1, title: "PET-001 group II base oil", cat: "lubricants", price: 99, featured: true, sales: 12, icon: "🛢" },
    { id: 2, title: "200L industrial drum", cat: "packaging", price: 48, featured: false, sales: 9, icon: "🛢" },
    { id: 3, title: "Circulating pump PMP-4400", cat: "equipment", price: 1840, featured: true, sales: 6, icon: "⚙" },
    { id: 4, title: "Technical data sheet pack", cat: "docs", price: 0, featured: false, sales: 40, icon: "📄" },
    { id: 5, title: "MOQ & warranty FAQ", cat: "docs", price: 0, featured: false, sales: 22, icon: "📘" },
    { id: 6, title: "Brand voice SOP v2", cat: "docs", price: 0, featured: false, sales: 8, icon: "🗂" },
    { id: 7, title: "Sales psychology skill", cat: "training", price: 29, featured: false, sales: 15, icon: "🎓" },
    { id: 8, title: "Pricing strategy skill", cat: "training", price: 19, featured: false, sales: 11, icon: "🎓" },
    { id: 9, title: "Content calendar skill", cat: "training", price: 15, featured: false, sales: 7, icon: "📅" },
    { id: 10, title: "Nordic Oils quote pack", cat: "sales", price: 4200, featured: true, sales: 1, icon: "💶" },
  ];

  function startMarket() {
    var grid = $("marketGrid");
    if (!grid) return;
    var chips = $("marketChips");
    var qEl = $("marketQ");
    var cnt = $("marketCnt");
    var sortSel = $("marketSort");
    var modalWrap = $("modalWrap");
    var modal = $("modal");
    var toastEl = $("toast");
    var cur = { cat: "", q: "", sort: "new" };

    function toast(m) {
      if (!toastEl) return;
      toastEl.textContent = m;
      toastEl.classList.add("show");
      setTimeout(function () {
        toastEl.classList.remove("show");
      }, 2200);
    }

    function filtered() {
      var list = PRODUCTS.filter(function (p) {
        if (cur.cat && p.cat !== cur.cat) return false;
        if (cur.q && (p.title + " " + p.cat).toLowerCase().indexOf(cur.q) === -1) return false;
        return true;
      });
      if (cur.sort === "cheap") list.sort(function (a, b) { return a.price - b.price; });
      else if (cur.sort === "exp") list.sort(function (a, b) { return b.price - a.price; });
      else if (cur.sort === "sold") list.sort(function (a, b) { return b.sales - a.sales; });
      else list.sort(function (a, b) { return b.id - a.id; });
      return list;
    }

    function render() {
      var items = filtered();
      grid.innerHTML = items
        .map(function (p) {
          return (
            '<article class="m-card" tabindex="0" data-id="' +
            p.id +
            '"><div class="m-thumb">' +
            p.icon +
            (p.featured ? '<span class="m-badge">Featured</span>' : "") +
            '</div><div class="m-body"><div class="m-title">' +
            esc(p.title) +
            '</div><div class="m-meta"><span class="m-price">' +
            (p.price ? "€" + fmt(p.price) : "Free / internal") +
            "</span><span>" +
            p.sales +
            " sales</span></div></div></article>"
          );
        })
        .join("");
      if (cnt) cnt.textContent = items.length + " items";
      grid.querySelectorAll(".m-card").forEach(function (card) {
        card.addEventListener("click", function () {
          openProduct(+card.getAttribute("data-id"));
        });
      });
    }

    function openProduct(id) {
      var p = PRODUCTS.filter(function (x) {
        return x.id === id;
      })[0];
      if (!p || !modal || !modalWrap) return;
      var hold = p.price >= 500;
      modal.innerHTML =
        '<button class="close btn ghost" type="button" style="float:right">✕</button>' +
        "<h2>" +
        esc(p.title) +
        "</h2>" +
        '<p class="mini">' +
        esc(p.cat) +
        " · " +
        p.sales +
        " sales</p>" +
        '<p class="m-price" style="font-size:24px;margin:12px 0">' +
        (p.price ? "€" + fmt(p.price) : "Internal knowledge") +
        "</p>" +
        "<p>Demo catalog only. Quotes and payments still go through Kia HITL — never auto.</p>" +
        '<div class="actions">' +
        (hold
          ? '<a class="btn good" href="queue.html">Send to Approvals</a>'
          : '<button class="btn primary" type="button" id="keepAuto">Keep automatic lead</button>') +
        '<a class="btn" href="sales.html">Open sales flow</a></div>';
      modalWrap.classList.add("open");
      var keep = $("keepAuto");
      if (keep)
        keep.onclick = function () {
          toast("Lead logged · create_lead (auto)");
          modalWrap.classList.remove("open");
        };
    }

    if (chips) {
      var cats = ["", "lubricants", "equipment", "packaging", "docs", "training", "sales"];
      chips.innerHTML = cats
        .map(function (c, i) {
          return (
            '<button class="chip-btn' +
            (i === 0 ? " on" : "") +
            '" data-c="' +
            c +
            '" type="button">' +
            (c || "All") +
            "</button>"
          );
        })
        .join("");
      chips.addEventListener("click", function (e) {
        var b = e.target.closest(".chip-btn");
        if (!b) return;
        cur.cat = b.getAttribute("data-c");
        chips.querySelectorAll(".chip-btn").forEach(function (x) {
          x.classList.toggle("on", x === b);
        });
        render();
      });
    }
    if (qEl) {
      qEl.addEventListener("input", function () {
        cur.q = qEl.value.trim().toLowerCase();
        render();
      });
    }
    if (sortSel) {
      sortSel.addEventListener("change", function () {
        cur.sort = sortSel.value;
        render();
      });
    }
    if (modalWrap) {
      modalWrap.addEventListener("click", function (e) {
        if (e.target === modalWrap || e.target.closest(".close")) modalWrap.classList.remove("open");
      });
    }
    render();
  }

  startLive();
  startInsights();
  startMarket();
})();
