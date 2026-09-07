/* Zenovix Ops 1.6.0 — Database page: browse / add / edit / delete rows and
   move whole tables around as versioned JSON. Talks to /admin/api/database. */
(function () {
  "use strict";
  var root = document.getElementById("database");
  if (!root) return;

  var API = "/admin/api/database";
  var state = { table: "", key: "id", columns: [], rows: [], total: 0, limit: 25, offset: 0, q: "", editing: null };
  var listEl = document.getElementById("db-table-list");
  var rowsEl = document.getElementById("db-rows");
  var titleEl = document.getElementById("db-title");
  var countEl = document.getElementById("db-count");
  var pageEl = document.getElementById("db-page");
  var statusEl = document.getElementById("db-status");
  var searchEl = document.getElementById("db-search");
  var modal = document.getElementById("db-modal");
  var modalBody = document.getElementById("db-modal-body");
  var modalTitle = document.getElementById("db-modal-title");
  var modalStatus = document.getElementById("db-modal-status");

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function say(m) { if (statusEl) statusEl.textContent = m || ""; }
  function api(path, opts) {
    opts = opts || {};
    var headers = {};
    var body = opts.body;
    if (body && !(body instanceof FormData)) { headers["Content-Type"] = "application/json"; body = JSON.stringify(body); }
    return fetch(API + path, { method: opts.method || "GET", credentials: "same-origin", headers: headers, body: body })
      .then(function (r) {
        var ct = r.headers.get("content-type") || "";
        if (ct.indexOf("application/json") === -1) return r.text().then(function (t) { return { _status: r.status, _ok: r.ok, _text: t }; });
        return r.json().catch(function () { return {}; }).then(function (d) { d._status = r.status; d._ok = r.ok; return d; });
      });
  }
  function download(path, fallbackName) {
    say("Preparing export…");
    fetch(API + path, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) { say("Export failed (" + r.status + ")."); return null; }
      var cd = r.headers.get("content-disposition") || "";
      var m = /filename="([^"]+)"/.exec(cd);
      return r.blob().then(function (b) {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        a.download = (m && m[1]) || fallbackName;
        document.body.appendChild(a); a.click(); a.remove();
        say("Exported " + a.download);
      });
    }).catch(function () { say("Export failed."); });
  }
  function fmt(v) {
    if (v == null) return "";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }
  function short(v, n) { var s = fmt(v); return s.length > n ? s.slice(0, n - 1) + "…" : s; }

  // ---- tables ----------------------------------------------------------
  function loadTables() {
    return api("/tables").then(function (d) {
      if (d._status === 401) { listEl.innerHTML = '<div class="empty">Sign in required.</div>'; return; }
      var v = document.getElementById("db-version");
      if (v) v.textContent = "v" + (d.version || "") + " · " + (d.format || "");
      var groups = {};
      (d.tables || []).forEach(function (t) { (groups[t.group] = groups[t.group] || []).push(t); });
      listEl.innerHTML = Object.keys(groups).map(function (g) {
        return '<div class="db-group">' + esc(g) + "</div>" + groups[g].map(function (t) {
          return '<button class="db-tab' + (t.table === state.table ? " on" : "") + '" type="button" data-table="' + esc(t.table) + '"><span>' + esc(t.table) + "</span><b>" + (t.rows == null ? "?" : t.rows) + "</b></button>";
        }).join("");
      }).join("");
      listEl.querySelectorAll(".db-tab").forEach(function (b) {
        b.addEventListener("click", function () { open(b.getAttribute("data-table")); });
      });
    });
  }
  function open(table) {
    state.table = table; state.offset = 0; state.q = ""; if (searchEl) searchEl.value = "";
    listEl.querySelectorAll(".db-tab").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-table") === table); });
    return loadRows();
  }
  function loadRows() {
    if (!state.table) return Promise.resolve();
    titleEl.textContent = state.table;
    rowsEl.innerHTML = '<tbody><tr><td class="empty">Loading…</td></tr></tbody>';
    var qs = "?limit=" + state.limit + "&offset=" + state.offset + (state.q ? "&q=" + encodeURIComponent(state.q) : "");
    return api("/" + encodeURIComponent(state.table) + qs).then(function (d) {
      if (!d._ok) { rowsEl.innerHTML = '<tbody><tr><td class="empty">' + esc(d.detail || ("HTTP " + d._status)) + "</td></tr></tbody>"; return; }
      state.key = d.key || "id"; state.columns = d.columns || []; state.rows = d.rows || []; state.total = d.total || 0;
      renderRows();
    });
  }
  function visibleColumns() {
    var cols = state.columns.map(function (c) { return c.name; });
    var first = [state.key, "code", "name_en", "question_en", "title_en", "key", "sku", "status", "channel", "subject", "role", "sender_role", "kind"];
    var picked = first.filter(function (c) { return cols.indexOf(c) !== -1; });
    cols.forEach(function (c) { if (picked.length < 7 && picked.indexOf(c) === -1 && ["created_at", "updated_at"].indexOf(c) === -1) picked.push(c); });
    if (cols.indexOf("updated_at") !== -1 && picked.length < 8) picked.push("updated_at");
    else if (cols.indexOf("created_at") !== -1 && picked.length < 8) picked.push("created_at");
    return picked;
  }
  function renderRows() {
    var cols = visibleColumns();
    countEl.textContent = state.total + " rows · key " + state.key;
    var head = "<thead><tr>" + cols.map(function (c) { return "<th>" + esc(c) + "</th>"; }).join("") + "<th></th></tr></thead>";
    var body = state.rows.length ? state.rows.map(function (r, i) {
      return '<tr data-i="' + i + '">' + cols.map(function (c) { return "<td title=\"" + esc(short(r[c], 400)) + "\">" + esc(short(r[c], 48)) + "</td>"; }).join("") +
        '<td class="db-act"><button class="btn ghost" type="button" data-edit="' + i + '">Edit</button></td></tr>';
    }).join("") : '<tr><td class="empty" colspan="' + (cols.length + 1) + '">No rows' + (state.q ? " for “" + esc(state.q) + "”" : "") + ".</td></tr>";
    rowsEl.innerHTML = head + "<tbody>" + body + "</tbody>";
    rowsEl.querySelectorAll("[data-edit]").forEach(function (b) {
      b.addEventListener("click", function () { edit(state.rows[parseInt(b.getAttribute("data-edit"), 10)]); });
    });
    var page = Math.floor(state.offset / state.limit) + 1;
    var pages = Math.max(1, Math.ceil(state.total / state.limit));
    pageEl.textContent = "page " + page + " / " + pages;
    document.getElementById("db-prev").disabled = state.offset <= 0;
    document.getElementById("db-next").disabled = state.offset + state.limit >= state.total;
  }

  // ---- editor ----------------------------------------------------------
  var AUTO = { created_at: 1, updated_at: 1 };
  function fieldFor(col, value, isNew) {
    var t = col.type || "text";
    var name = col.name;
    var ro = (!isNew && (name === state.key || name === "id")) || AUTO[name];
    var v = value == null ? "" : (typeof value === "object" ? JSON.stringify(value, null, 1) : String(value));
    var ctl;
    if (t === "boolean") {
      ctl = '<select name="' + esc(name) + '"' + (ro ? " disabled" : "") + '><option value=""' + (value == null ? " selected" : "") + '>—</option><option value="true"' + (value === true ? " selected" : "") + '>true</option><option value="false"' + (value === false ? " selected" : "") + '>false</option></select>';
    } else if (t === "jsonb" || t === "json" || t === "ARRAY" || v.length > 80 || v.indexOf("\n") !== -1) {
      ctl = '<textarea name="' + esc(name) + '" data-type="' + esc(t) + '"' + (ro ? " readonly" : "") + ">" + esc(v) + "</textarea>";
    } else {
      ctl = '<input name="' + esc(name) + '" data-type="' + esc(t) + '" value="' + esc(v) + '"' + (ro ? " readonly" : "") + ">";
    }
    return '<label class="db-field' + (ro ? " ro" : "") + '"><span>' + esc(name) + ' <em>' + esc(t) + (col.nullable ? "" : " · required") + "</em></span>" + ctl + "</label>";
  }
  function edit(row) {
    state.editing = row || null;
    modalTitle.textContent = row ? state.table + " · " + short(row[state.key], 40) : "New row in " + state.table;
    modalBody.innerHTML = state.columns.map(function (c) { return fieldFor(c, row ? row[c.name] : null, !row); }).join("");
    document.getElementById("db-modal-delete").hidden = !row;
    modalStatus.textContent = "";
    modal.hidden = false;
  }
  function collect() {
    var out = {};
    modalBody.querySelectorAll("[name]").forEach(function (el) {
      if (el.disabled || el.readOnly) return;
      var name = el.getAttribute("name"), t = el.getAttribute("data-type") || "";
      var raw = el.value;
      if (el.tagName === "SELECT") { if (raw === "") { out[name] = null; return; } out[name] = raw === "true"; return; }
      if (raw === "" ) { if (state.editing) out[name] = null; return; }
      if (t === "jsonb" || t === "json" || t === "ARRAY") {
        try { out[name] = JSON.parse(raw); } catch (e) { throw new Error(name + ": invalid JSON"); }
        return;
      }
      if (["integer", "bigint", "smallint", "numeric", "double precision", "real"].indexOf(t) !== -1) { out[name] = Number(raw); return; }
      out[name] = raw;
    });
    return out;
  }
  function closeModal() { modal.hidden = true; state.editing = null; }
  document.getElementById("db-modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
  document.getElementById("db-modal-save").addEventListener("click", function () {
    var data;
    try { data = collect(); } catch (err) { modalStatus.textContent = err.message; return; }
    modalStatus.textContent = "Saving…";
    var p = state.editing
      ? api("/" + encodeURIComponent(state.table) + "/" + encodeURIComponent(fmt(state.editing[state.key])), { method: "PUT", body: { row: data } })
      : api("/" + encodeURIComponent(state.table), { method: "POST", body: { row: data } });
    p.then(function (d) {
      if (!d._ok) { modalStatus.textContent = "Not saved: " + (typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail || ("HTTP " + d._status))); return; }
      modalStatus.textContent = "Saved.";
      say((state.editing ? "Updated " : "Added ") + "row in " + state.table + ".");
      closeModal(); loadRows(); loadTables();
    });
  });
  document.getElementById("db-modal-delete").addEventListener("click", function () {
    if (!state.editing) return;
    if (!window.confirm("Delete this row from " + state.table + "? This cannot be undone.")) return;
    api("/" + encodeURIComponent(state.table) + "/" + encodeURIComponent(fmt(state.editing[state.key])), { method: "DELETE" }).then(function (d) {
      if (!d._ok) { modalStatus.textContent = d._status === 403 ? "Only a superadmin can delete." : (d._status === 409 ? "Not deleted — " + d.detail : "Not deleted: " + (d.detail || d._status)); return; }
      say("Deleted row from " + state.table + ".");
      closeModal(); loadRows(); loadTables();
    });
  });

  // ---- toolbar ---------------------------------------------------------
  document.getElementById("db-add").addEventListener("click", function () { if (state.table) edit(null); });
  document.getElementById("db-refresh").addEventListener("click", function () { loadRows(); loadTables(); });
  document.getElementById("db-prev").addEventListener("click", function () { state.offset = Math.max(0, state.offset - state.limit); loadRows(); });
  document.getElementById("db-next").addEventListener("click", function () { state.offset += state.limit; loadRows(); });
  var timer = null;
  searchEl.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(function () { state.q = searchEl.value.trim(); state.offset = 0; loadRows(); }, 260);
  });
  document.getElementById("db-export").addEventListener("click", function () {
    if (state.table) download("/" + encodeURIComponent(state.table) + "/export", state.table + ".json");
  });
  document.getElementById("db-export-all").addEventListener("click", function () { download("/export/all", "zenovix-db.json"); });
  function importFile(path, input) {
    var f = input.files && input.files[0];
    if (!f) return;
    var fd = new FormData(); fd.append("file", f, f.name);
    say("Importing " + f.name + "…");
    api(path, { method: "POST", body: fd }).then(function (d) {
      if (!d._ok) { say("Import failed: " + (d.detail || ("HTTP " + d._status))); return; }
      if (d.report) {
        var parts = Object.keys(d.report).map(function (t) { var r = d.report[t]; return t + ": " + (r.skipped === true ? "skipped" : (r.upserted + "/" + r.rows)); });
        say("Imported — " + parts.join(" · "));
      } else {
        say("Imported " + d.upserted + " of " + d.rows + " rows into " + d.table + (d.skipped ? " (" + d.skipped + " skipped)" : "") + (d.errors && d.errors.length ? " · first error: " + d.errors[0] : ""));
      }
      loadRows(); loadTables();
    }).catch(function () { say("Import failed."); }).then(function () { input.value = ""; });
  }
  document.getElementById("db-import-file").addEventListener("change", function () {
    if (!state.table) { say("Pick a table first."); this.value = ""; return; }
    importFile("/" + encodeURIComponent(state.table) + "/import", this);
  });
  document.getElementById("db-import-all-file").addEventListener("change", function () { importFile("/import", this); });

  loadTables().then(function () {
    var first = listEl.querySelector(".db-tab");
    if (first) open(first.getAttribute("data-table"));
  });
})();
