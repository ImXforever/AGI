/* 3D Kia ecosystem simulator. THREE if present, canvas fallback otherwise. English only. */
(function () {
  "use strict";

  var gl = document.getElementById("eco-gl");
  var hud = document.getElementById("eco-hud");
  var hctx = hud.getContext("2d");
  var dock = document.getElementById("eco-dock");
  var logEl = document.getElementById("eco-log");
  var statsEl = document.getElementById("eco-stats");
  var stage = document.getElementById("eco-stage");

  var rotY = 0.4;
  var rotX = 0.28;
  var dragging = false;
  var lastX = 0;
  var lastY = 0;
  var three = null;
  var paused = false;
  var burst = 1;
  var t0 = performance.now();
  var packets = [];
  var selected = "core";
  var counters = { in: 0, auto: 0, hold: 0, out: 0 };

  var NODES = [
    { id: "core", label: "Orchestrator", ring: 0, color: 0x00f0ff, href: "index.html", kind: "core",
      text: "Intent classification, skill routing, memory. Every inbound message lands here first." },
    { id: "hitl", label: "HITL gate", ring: 0.55, color: 0xff2bd6, href: "queue.html", kind: "gate",
      text: "Payment, contract, price, delete, access never auto-run. Manager record required." },
    { id: "tg", label: "Telegram", ring: 1, color: 0x6ea8ff, href: "inbox.html", kind: "channel",
      text: "Executive bot, webhooks, inline approvals." },
    { id: "wa", label: "WhatsApp", ring: 1, color: 0x00ffa8, href: "inbox.html", kind: "channel",
      text: "Meta Cloud / Twilio inbound and templates." },
    { id: "em", label: "Email", ring: 1, color: 0x7af6ff, href: "inbox.html", kind: "channel",
      text: "IMAP capture · classify · reply_common or escalate." },
    { id: "ig", label: "Instagram", ring: 1, color: 0xff2bd6, href: "social.html", kind: "channel",
      text: "Calendar posts auto. Guarantee claims held." },
    { id: "x", label: "X / Twitter", ring: 1, color: 0xeaf6ff, href: "social.html", kind: "channel",
      text: "Publish, mentions, character limits before send." },
    { id: "web", label: "Website", ring: 1, color: 0xb6ff3b, href: "website.html", kind: "channel",
      text: "Forms become leads. Price edits hit the policy gate." },
    { id: "sales", label: "Sales agent", ring: 0.72, color: 0xffb020, href: "sales.html", kind: "agent",
      text: "Lead → qualify → quote. Sending a quote is HITL." },
    { id: "support", label: "Support agent", ring: 0.72, color: 0x00ffa8, href: "support.html", kind: "agent",
      text: "Tickets and first-line. Safety issues escalate now." },
    { id: "know", label: "Knowledge", ring: 0.72, color: 0x00f0ff, href: "brain.html", kind: "agent",
      text: "Approved docs only. Confidential stays hidden." },
    { id: "ops", label: "Ops agent", ring: 0.72, color: 0x6ea8ff, href: "operations.html", kind: "agent",
      text: "Reminders, digest, coordination. Observes, does not bypass." },
    { id: "pg", label: "Postgres", ring: 1.28, color: 0x4169e1, href: "audit.html", kind: "store",
      text: "Customers, messages, approvals ledger. Durable before AI work." },
    { id: "rd", label: "Redis", ring: 1.28, color: 0xff3d7a, href: "live.html", kind: "store",
      text: "Streams, locks, rate limits, prompt cache." },
    { id: "rag", label: "RAG store", ring: 1.28, color: 0xb6ff3b, href: "knowledge.html", kind: "store",
      text: "Indexed chunks. Unapproved drafts never answer." }
  ];

  var EDGES = [
    ["tg", "core"], ["wa", "core"], ["em", "core"], ["ig", "core"], ["x", "core"], ["web", "core"],
    ["core", "sales"], ["core", "support"], ["core", "know"], ["core", "ops"],
    ["core", "hitl"], ["hitl", "core"],
    ["core", "pg"], ["core", "rd"], ["know", "rag"]
  ];

  function nodeById(id) {
    for (var i = 0; i < NODES.length; i++) if (NODES[i].id === id) return NODES[i];
    return NODES[0];
  }

  function hexCss(n) {
    return "#" + n.toString(16).padStart(6, "0");
  }

  function posOf(n, t) {
    if (n.kind === "core") return { x: 0, y: 0, z: 0 };
    var ringR = n.kind === "gate" ? 2.4 : n.kind === "agent" ? 4.4 : n.kind === "store" ? 6.6 : 7.4;
    var peers = NODES.filter(function (x) { return x.kind === n.kind; });
    var i = peers.indexOf(n);
    var a = (i / Math.max(peers.length, 1)) * Math.PI * 2 + (n.kind === "channel" ? t * 0.05 : 0);
    var y = n.kind === "store" ? -1.6 : n.kind === "gate" ? 0.4 : n.kind === "agent" ? 0.2 : 0.15 * Math.sin(a * 2);
    return { x: Math.cos(a) * ringR, y: y, z: Math.sin(a) * ringR };
  }

  function logLine(kind, msg) {
    if (!logEl) return;
    var row = document.createElement("div");
    row.className = "eco-l eco-" + kind;
    var ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    row.textContent = "[" + ts + "] " + msg;
    logEl.insertBefore(row, logEl.firstChild);
    while (logEl.children.length > 40) logEl.removeChild(logEl.lastChild);
  }

  function spawnPacket() {
    var ch = ["tg", "wa", "em", "ig", "x", "web"][Math.floor(Math.random() * 6)];
    var hold = Math.random() < 0.15;
    packets.push({
      from: ch,
      via: "core",
      to: hold ? "hitl" : ["sales", "support", "know", "ops"][Math.floor(Math.random() * 4)],
      t: 0,
      hold: hold,
      speed: 0.55 + Math.random() * 0.45
    });
    counters.in += 1;
    var src = nodeById(ch).label;
    logLine("in", src + " → orchestrator · ingest");
  }

  function renderDock() {
    var n = nodeById(selected);
    dock.innerHTML =
      "<h3>" + n.label + "</h3>" +
      "<p class='mini'>" + n.kind.toUpperCase() + "</p>" +
      "<p>" + n.text + "</p>" +
      "<p class='mini'>Inbound " + counters.in + " · auto " + counters.auto +
      " · held " + counters.hold + " · out " + counters.out + "</p>" +
      '<a class="btn primary" href="' + n.href + '" style="margin-top:10px;display:inline-block">Open module</a>';
  }

  function resize() {
    var w = stage.clientWidth;
    var h = stage.clientHeight;
    hud.width = w * devicePixelRatio;
    hud.height = h * devicePixelRatio;
    hud.style.width = w + "px";
    hud.style.height = h + "px";
    hctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    if (three) {
      three.renderer.setSize(w, h, false);
      three.camera.aspect = w / Math.max(h, 1);
      three.camera.updateProjectionMatrix();
    } else {
      gl.width = hud.width;
      gl.height = hud.height;
      gl.style.width = w + "px";
      gl.style.height = h + "px";
    }
  }

  function bindDrag(target) {
    target.addEventListener("pointerdown", function (ev) {
      dragging = true;
      lastX = ev.clientX;
      lastY = ev.clientY;
      target.setPointerCapture(ev.pointerId);
    });
    target.addEventListener("pointerup", function () { dragging = false; });
    target.addEventListener("pointermove", function (ev) {
      if (!dragging) return;
      rotY += (ev.clientX - lastX) * 0.005;
      rotX += (ev.clientY - lastY) * 0.004;
      rotX = Math.max(-0.85, Math.min(0.85, rotX));
      lastX = ev.clientX;
      lastY = ev.clientY;
    });
    target.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      if (three) {
        three.camera.position.z = Math.max(10, Math.min(48, three.camera.position.z + ev.deltaY * 0.025));
      }
    }, { passive: false });
  }

  function initThree() {
    if (typeof THREE === "undefined") return null;
    var renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(46, 1, 0.1, 200);
    camera.position.set(0, 4.2, 18);
    scene.add(new THREE.AmbientLight(0x14305a, 0.7));
    var key = new THREE.PointLight(0x00f0ff, 2.8, 90);
    key.position.set(8, 10, 12);
    scene.add(key);
    var rim = new THREE.PointLight(0xff2bd6, 1.8, 80);
    rim.position.set(-10, -2, 6);
    scene.add(rim);
    var root = new THREE.Group();
    scene.add(root);

    var meshes = {};
    NODES.forEach(function (n) {
      var size = n.kind === "core" ? 1.35 : n.kind === "gate" ? 0.72 : 0.42;
      var geo = n.kind === "core"
        ? new THREE.IcosahedronGeometry(size, 2)
        : n.kind === "gate"
          ? new THREE.OctahedronGeometry(size, 0)
          : new THREE.SphereGeometry(size, 18, 18);
      var mat = new THREE.MeshStandardMaterial({
        color: n.color,
        emissive: n.color,
        emissiveIntensity: n.kind === "core" ? 0.55 : 0.35,
        metalness: 0.35,
        roughness: 0.28
      });
      var m = new THREE.Mesh(geo, mat);
      m.userData = { id: n.id };
      root.add(m);
      if (n.kind === "core") {
        var glow = new THREE.Mesh(
          new THREE.SphereGeometry(1.85, 32, 32),
          new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.12 })
        );
        root.add(glow);
      }
      meshes[n.id] = m;
    });

    var lineMat = new THREE.LineBasicMaterial({ color: 0x1c3a88, transparent: true, opacity: 0.55 });
    var lines = [];
    EDGES.forEach(function () {
      var g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(6), 3));
      var ln = new THREE.Line(g, lineMat);
      root.add(ln);
      lines.push(ln);
    });

    var pktGeo = new THREE.SphereGeometry(0.09, 8, 8);
    var pktGroup = new THREE.Group();
    root.add(pktGroup);

    var ray = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    gl.addEventListener("click", function (ev) {
      if (dragging) return;
      var rect = gl.getBoundingClientRect();
      mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      ray.setFromCamera(mouse, camera);
      var hits = ray.intersectObjects(Object.keys(meshes).map(function (k) { return meshes[k]; }));
      if (hits.length) {
        selected = hits[0].object.userData.id;
        renderDock();
      }
    });

    return { renderer: renderer, scene: scene, camera: camera, root: root, meshes: meshes, lines: lines, pktGroup: pktGroup, pktGeo: pktGeo };
  }

  function lerp(a, b, t) {
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t };
  }

  function drawCanvas(now, w, h) {
    var ctx = gl.getContext("2d");
    if (!ctx) return;
    gl.width = hud.width;
    gl.height = hud.height;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    ctx.clearRect(0, 0, w, h);
    var cx = w / 2;
    var cy = h / 2;
    var t = now * 0.001;
    function proj(p) {
      var x = p.x * Math.cos(rotY) - p.z * Math.sin(rotY);
      var z = p.x * Math.sin(rotY) + p.z * Math.cos(rotY);
      var y = p.y * Math.cos(rotX) - z * Math.sin(rotX);
      var zz = p.y * Math.sin(rotX) + z * Math.cos(rotX);
      var s = 220 / (14 + zz);
      return { x: cx + x * s, y: cy + y * s, s: s };
    }
    ctx.strokeStyle = "rgba(0,240,255,0.18)";
    EDGES.forEach(function (e) {
      var a = proj(posOf(nodeById(e[0]), t));
      var b = proj(posOf(nodeById(e[1]), t));
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });
    NODES.forEach(function (n) {
      var p = proj(posOf(n, t));
      ctx.fillStyle = hexCss(n.color);
      ctx.beginPath();
      ctx.arc(p.x, p.y, n.kind === "core" ? 16 : 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(234,246,255,0.85)";
      ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
      ctx.fillText(n.label, p.x + 10, p.y + 4);
    });
  }

  function tick(now) {
    var t = (now - t0) / 1000;
    if (!paused) {
      var rate = 0.018 * burst;
      if (Math.random() < rate) spawnPacket();
      packets.forEach(function (p) { p.t += 0.016 * p.speed * burst; });
      packets = packets.filter(function (p) {
        if (p.t < 1) return true;
        if (p.hold) {
          counters.hold += 1;
          logLine("hold", "HITL hold · " + nodeById(p.from).label + " · manager gate");
        } else {
          counters.auto += 1;
          counters.out += 1;
          logLine("ok", "auto · " + nodeById(p.to).label + " executed");
        }
        return false;
      });
    }
    if (statsEl) {
      statsEl.textContent =
        "10k-member model · " + counters.in + " ingest · " + counters.auto + " auto · " +
        counters.hold + " HITL · burst ×" + burst;
    }
    if (three) {
      three.root.rotation.y = rotY;
      three.root.rotation.x = rotX;
      NODES.forEach(function (n) {
        var p = posOf(n, t);
        var m = three.meshes[n.id];
        m.position.set(p.x, p.y, p.z);
      });
      EDGES.forEach(function (e, i) {
        var a = three.meshes[e[0]].position;
        var b = three.meshes[e[1]].position;
        var arr = three.lines[i].geometry.attributes.position.array;
        arr[0] = a.x; arr[1] = a.y; arr[2] = a.z;
        arr[3] = b.x; arr[4] = b.y; arr[5] = b.z;
        three.lines[i].geometry.attributes.position.needsUpdate = true;
      });
      while (three.pktGroup.children.length < packets.length) {
        var pm = new THREE.Mesh(
          three.pktGeo,
          new THREE.MeshBasicMaterial({ color: 0xb6ff3b })
        );
        three.pktGroup.add(pm);
      }
      while (three.pktGroup.children.length > packets.length) {
        three.pktGroup.remove(three.pktGroup.children[three.pktGroup.children.length - 1]);
      }
      packets.forEach(function (p, i) {
        var a = three.meshes[p.from].position;
        var mid = three.meshes.core.position;
        var b = three.meshes[p.to].position;
        var pt = p.t < 0.5
          ? lerp(a, mid, p.t * 2)
          : lerp(mid, b, (p.t - 0.5) * 2);
        var mesh = three.pktGroup.children[i];
        mesh.position.set(pt.x, pt.y, pt.z);
        mesh.material.color.setHex(p.hold ? 0xff2bd6 : 0xb6ff3b);
      });
      three.renderer.render(three.scene, three.camera);
    } else {
      drawCanvas(now, hud.clientWidth, hud.clientHeight);
    }
    var w = hud.clientWidth;
    var h = hud.clientHeight;
    hctx.clearRect(0, 0, w, h);
    hctx.fillStyle = "rgba(234,246,255,0.7)";
    hctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    hctx.fillText("Ecosystem · drag to orbit · click a node · packets = live sim", 16, 22);
    requestAnimationFrame(tick);
  }

  document.getElementById("eco-burst").addEventListener("click", function () {
    burst = burst === 1 ? 8 : burst === 8 ? 24 : 1;
    logLine("sys", "Traffic burst set to ×" + burst + " (10k-member model)");
    this.textContent = burst === 1 ? "Burst ×1" : "Burst ×" + burst;
  });
  document.getElementById("eco-pause").addEventListener("click", function () {
    paused = !paused;
    this.textContent = paused ? "Resume" : "Pause";
  });
  document.getElementById("eco-core").addEventListener("click", function () {
    selected = "core";
    renderDock();
  });

  three = initThree();
  bindDrag(gl);
  bindDrag(hud);
  window.addEventListener("resize", resize);
  resize();
  renderDock();
  logLine("sys", "Ecosystem online · English · neon · HITL locked");
  logLine("sys", "Channels: Telegram · WhatsApp · Email · Instagram · X · Website");
  requestAnimationFrame(tick);
})();
