/* Zenovix Ops 1.6.0 — bot simulator (WhatsApp clone inside the console).
   Talks to /admin/api/simulator/*. Files are dropped on the chat, kept per
   session on the server, and travel with the next message as DATA. */
(function () {
  "use strict";
  var root = document.getElementById("simulator");
  if (!root) return;

  var API = "/admin/api/simulator";
  var KEY = "zenovix-sim-session";
  var log = document.getElementById("sim-log");
  var form = document.getElementById("sim-form");
  var input = document.getElementById("sim-text");
  var sendBtn = document.getElementById("sim-send");
  var status = document.getElementById("sim-status");
  var filesBox = document.getElementById("sim-files");
  var filesHint = document.getElementById("sim-files-hint");
  var debug = document.getElementById("sim-debug");
  var drop = document.getElementById("sim-drop");
  var dropzone = document.getElementById("sim-dropzone");
  var fileInput = document.getElementById("sim-file");
  var langSel = document.getElementById("sim-lang");
  var sessionEl = document.getElementById("sim-session");
  var busy = false;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function newSession() {
    var id = "s" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    try { localStorage.setItem(KEY, id); } catch (e) {}
    return id;
  }
  var session = "";
  try { session = localStorage.getItem(KEY) || ""; } catch (e) {}
  if (!session) session = newSession();
  if (sessionEl) sessionEl.textContent = session;

  function say(msg) { if (status) status.textContent = msg || ""; }
  function api(path, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    var body = opts.body;
    if (body && !(body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }
    return fetch(API + path, { method: opts.method || "GET", credentials: "same-origin", headers: headers, body: body })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) { d._status = r.status; d._ok = r.ok; return d; });
      });
  }
  function timeNow() {
    var d = new Date();
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
  }
  function bubble(kind, text, meta) {
    if (log.querySelector(".empty")) log.innerHTML = "";
    var el = document.createElement("div");
    el.className = "sim-msg " + kind;
    el.innerHTML = '<div class="sim-body">' + esc(text) + '</div><div class="sim-meta">' + esc(meta || timeNow()) + "</div>";
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }
  function typing() {
    var el = document.createElement("div");
    el.className = "sim-msg bot typing";
    el.innerHTML = '<div class="sim-body"><span></span><span></span><span></span></div>';
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  // ---- files -------------------------------------------------------------
  function renderFiles(files) {
    if (filesHint) filesHint.textContent = files.length + " / 8";
    if (!files.length) {
      filesBox.innerHTML = '<div class="empty">No files. Drop one on the chat or press ＋.</div>';
      return;
    }
    filesBox.innerHTML = files.map(function (f) {
      var kb = Math.max(1, Math.round((f.size || 0) / 1024));
      return '<div class="sim-file" data-id="' + esc(f.id) + '">' +
        '<div class="sim-file-ic">' + (String(f.content_type || "").indexOf("image/") === 0 ? "🖼" : "📄") + "</div>" +
        '<div class="sim-file-main"><b>' + esc(f.name) + "</b><span>" + esc(f.content_type || "") + " · " + kb + " KB · " + (f.chars || 0) + " chars read</span>" +
        (f.preview ? '<em>' + esc(f.preview) + "…</em>" : '<em class="warn">no readable text — the bot will only know the file name</em>') + "</div>" +
        '<button class="btn bad sim-file-del" type="button" title="Remove">✕</button></div>';
    }).join("");
    filesBox.querySelectorAll(".sim-file-del").forEach(function (b) {
      b.addEventListener("click", function () {
        var id = b.closest(".sim-file").getAttribute("data-id");
        api("/files/" + encodeURIComponent(id) + "?session=" + encodeURIComponent(session), { method: "DELETE" }).then(function (d) {
          say(d._ok ? "File removed." : "Could not remove: " + (d.detail || d._status));
          loadFiles();
        });
      });
    });
  }
  function loadFiles() {
    return api("/files?session=" + encodeURIComponent(session)).then(function (d) {
      if (d._status === 401) { say("Sign in required."); return; }
      renderFiles(d.files || []);
    });
  }
  function upload(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    if (!files.length) return;
    var chain = Promise.resolve();
    files.forEach(function (f) {
      chain = chain.then(function () {
        var fd = new FormData();
        fd.append("file", f, f.name);
        say("Uploading " + f.name + "…");
        return api("/files?session=" + encodeURIComponent(session), { method: "POST", body: fd }).then(function (d) {
          if (d._ok) {
            say("Attached " + f.name + " (" + ((d.file && d.file.chars) || 0) + " chars read).");
            bubble("sys", "📎 " + f.name + " attached — it goes with your next message.", "file");
          } else {
            var why = d.detail || ("HTTP " + d._status);
            if (String(why).indexOf("mime_not_allowed") === 0) why = "file type not allowed";
            if (String(why).indexOf("max_files") === 0) why = "session already has 8 files";
            say("Rejected " + f.name + ": " + why);
            bubble("sys", "⛔ " + f.name + " rejected — " + why, "file");
          }
        });
      });
    });
    chain.then(loadFiles);
  }

  // drag & drop on the whole phone screen
  ["dragenter", "dragover"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("over"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("over"); });
  });
  drop.addEventListener("drop", function (e) { if (e.dataTransfer && e.dataTransfer.files) upload(e.dataTransfer.files); });
  document.getElementById("sim-attach").addEventListener("click", function () { fileInput.click(); });
  dropzone.addEventListener("click", function () { fileInput.click(); });
  fileInput.addEventListener("change", function () { upload(fileInput.files); fileInput.value = ""; });
  // paste an image/file straight into the chat
  document.addEventListener("paste", function (e) {
    if (!e.clipboardData || !e.clipboardData.files || !e.clipboardData.files.length) return;
    upload(e.clipboardData.files);
  });

  // ---- messages ----------------------------------------------------------
  function renderDebug(d) {
    var r = d.result || {};
    var rows = [
      ["handled", r.handled ? "yes" : "no"],
      ["guard", r.guard_rejected ? "rejected" : "passed"],
      ["held by manager", r.held ? "yes" : "no"],
      ["approval id", r.approval_id || "—"],
      ["classification", r.classification ? (r.classification.skill || "") + " / " + (r.classification.intent || "") + " (" + Math.round((r.classification.confidence || 0) * 100) + "%)" : "—"],
      ["files used", (d.files_used || []).map(function (f) { return f.name; }).join(", ") || "—"],
      ["latency", (d.latency_ms || 0) + " ms"],
      ["conversation", d.conversation_id || "—"],
    ];
    debug.innerHTML = '<table class="table">' + rows.map(function (x) {
      return "<tr><td class=\"mini\">" + esc(x[0]) + "</td><td>" + esc(x[1]) + "</td></tr>";
    }).join("") + "</table>";
  }
  function send(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    busy = true; sendBtn.disabled = true; say("Sending…");
    var pending = filesBox.querySelectorAll(".sim-file").length;
    bubble("me", text + (pending ? "\n📎 " + pending + (pending === 1 ? " file" : " files") + " attached" : ""));
    input.value = "";
    var t = typing();
    api("/message", { method: "POST", body: { text: text, session: session, language: langSel ? langSel.value : "" } })
      .then(function (d) {
        t.remove();
        if (d._status === 401) { bubble("sys", "Sign in required.", "auth"); say("Sign in required."); return; }
        if (!d._ok) { bubble("sys", "Error: " + (d.detail || ("HTTP " + d._status)), "error"); say("Failed."); return; }
        var replies = d.replies || [];
        if (!replies.length) bubble("sys", "(no reply — the bot stayed silent for this input)", "pipeline");
        replies.forEach(function (r) { bubble("bot", r.text); });
        if (d.result && d.result.guard_rejected) bubble("sys", "Security layer rejected this input — same as production.", "guard");
        if (d.result && d.result.held) bubble("sys", "A manager holds this conversation — the bot stays quiet until it is released.", "hold");
        renderDebug(d);
        say("Reply in " + (d.latency_ms || 0) + " ms" + ((d.result && d.result.approval_id) ? " · waiting for a manager (Approvals)" : ""));
        if (d.files_used && d.files_used.length) loadFiles();
      })
      .catch(function () { t.remove(); bubble("sys", "Network problem.", "error"); say("Network problem."); })
      .then(function () { busy = false; sendBtn.disabled = false; input.focus(); });
  }
  form.addEventListener("submit", function (e) { e.preventDefault(); send(input.value); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input.value); }
  });
  root.querySelectorAll("[data-sim]").forEach(function (b) {
    b.addEventListener("click", function () { send(b.getAttribute("data-sim")); });
  });

  function loadHistory() {
    return api("/history?session=" + encodeURIComponent(session)).then(function (d) {
      var turns = d.turns || [];
      if (!turns.length) return;
      log.innerHTML = "";
      turns.forEach(function (m) {
        var kind = (m.role === "agent" || m.role === "assistant" || m.role === "bot") ? "bot" : "me";
        var text = String(m.content || "");
        var cut = text.indexOf("\n\nATTACHED FILE ");
        if (kind === "me" && cut > 0) text = text.slice(0, cut) + "\n📎 (files attached)";
        bubble(kind, text, (m.created_at || "").slice(11, 16) || "");
      });
    });
  }

  document.getElementById("sim-new").addEventListener("click", function () {
    session = newSession();
    if (sessionEl) sessionEl.textContent = session;
    log.innerHTML = '<div class="empty">New session. Say hello — or press a quick command below.</div>';
    debug.innerHTML = '<div class="empty">Send a message to see classification, guard and HITL results.</div>';
    say("New session " + session);
    loadFiles();
  });
  document.getElementById("sim-reset").addEventListener("click", function () {
    if (!window.confirm("Forget this session? Files, saved language and stored turns are deleted.")) return;
    api("/session?session=" + encodeURIComponent(session), { method: "DELETE" }).then(function (d) {
      say(d._ok ? "Session forgotten (" + (d.messages || 0) + " turns, " + (d.files || 0) + " files)." : "Could not reset.");
      log.innerHTML = '<div class="empty">Session cleared. Say hello.</div>';
      loadFiles();
    });
  });

  loadFiles();
  loadHistory();
})();
