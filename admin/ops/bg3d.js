/* Zenovix Ops 1.6.0 — 3D background for the manager console (admin only).
   A slow field of glass cubes + particles rendered with three.js behind the
   UI. Follows the four themes (light / dark / gray / neon), pauses when the
   tab is hidden, respects prefers-reduced-motion, and degrades to a soft 2D
   canvas gradient when WebGL or three.js is unavailable. Toggle: Ctrl+Shift+B
   (stored in localStorage "zenovix-bg3d"). */
(function () {
  "use strict";
  if (window.__zxBg) return;
  window.__zxBg = true;
  var KEY = "zenovix-bg3d";
  var enabled = true;
  try { enabled = localStorage.getItem(KEY) !== "off"; } catch (e) {}
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var wrap = document.createElement("div");
  wrap.id = "bg3d";
  wrap.setAttribute("aria-hidden", "true");
  var canvas = document.createElement("canvas");
  wrap.appendChild(canvas);
  document.body.insertBefore(wrap, document.body.firstChild);

  var THEMES = {
    dark: { bg: 0x0b0f1a, a: 0x8a3fe6, b: 0x3b8df5, c: 0x38bdf8, fog: 0x0b0f1a, glass: 0.16, particles: 0.55 },
    light: { bg: 0xf4f6fb, a: 0x8a3fe6, b: 0x2563eb, c: 0x7c3aed, fog: 0xf4f6fb, glass: 0.10, particles: 0.35 },
    gray: { bg: 0x1c1f26, a: 0x9ca3af, b: 0x60a5fa, c: 0xa78bfa, fog: 0x1c1f26, glass: 0.12, particles: 0.4 },
    neon: { bg: 0x05060c, a: 0xf472b6, b: 0x38bdf8, c: 0xa3e635, fog: 0x05060c, glass: 0.22, particles: 0.8 },
  };
  function theme() {
    var t = document.documentElement.getAttribute("data-theme") || "dark";
    return THEMES[t] || THEMES.dark;
  }

  // ---- 2D fallback --------------------------------------------------------
  function fallback2d() {
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    function paint() {
      var w = canvas.width = window.innerWidth, h = canvas.height = window.innerHeight;
      var t = theme();
      function hex(n) { return "#" + ("000000" + n.toString(16)).slice(-6); }
      ctx.fillStyle = hex(t.bg); ctx.fillRect(0, 0, w, h);
      var g1 = ctx.createRadialGradient(w * 0.85, h * 0.1, 0, w * 0.85, h * 0.1, w * 0.5);
      g1.addColorStop(0, hex(t.a) + "55"); g1.addColorStop(1, "transparent");
      ctx.fillStyle = g1; ctx.fillRect(0, 0, w, h);
      var g2 = ctx.createRadialGradient(w * 0.1, h * 0.95, 0, w * 0.1, h * 0.95, w * 0.45);
      g2.addColorStop(0, hex(t.b) + "44"); g2.addColorStop(1, "transparent");
      ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
    }
    paint();
    window.addEventListener("resize", paint);
    new MutationObserver(paint).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  // Pages whose *content* is already a full-screen three.js scene (Ecosystem,
  // Knowledge brain) keep one WebGL context: a second animated scene behind
  // them costs battery on laptops and phones and adds nothing visible.
  if (document.querySelector(".brain-stage")) {
    fallback2d();
    return;
  }

  var T = window.THREE;
  var gl = null;
  try { gl = canvas.getContext("webgl2") || canvas.getContext("webgl"); } catch (e) { gl = null; }
  if (!T || !gl || !enabled) {
    if (!enabled) wrap.classList.add("off");
    fallback2d();
    return;
  }

  // ---- three.js scene -----------------------------------------------------
  var renderer;
  try {
    renderer = new T.WebGLRenderer({ canvas: canvas, context: gl, antialias: true, alpha: false, powerPreference: "low-power" });
  } catch (e) { fallback2d(); return; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  var scene = new T.Scene();
  var camera = new T.PerspectiveCamera(50, 1, 0.1, 200);
  camera.position.set(0, 2.5, 26);

  var group = new T.Group();
  scene.add(group);
  var cubes = [];
  var glassMat = new T.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0.1, roughness: 0.25, transparent: true, opacity: 0.16, transmission: 0.0, clearcoat: 0.6, side: T.DoubleSide });
  var edgeMat = new T.LineBasicMaterial({ color: 0x8a3fe6, transparent: true, opacity: 0.35 });
  var geo = new T.BoxGeometry(1, 1, 1);
  var edges = new T.EdgesGeometry(geo);
  var N = reduce ? 28 : 54;
  for (var i = 0; i < N; i++) {
    var s = 0.6 + Math.random() * 2.2;
    var m = new T.Mesh(geo, glassMat.clone());
    m.scale.setScalar(s);
    m.position.set((Math.random() - 0.5) * 60, (Math.random() - 0.5) * 30 - 2, (Math.random() - 0.5) * 40 - 8);
    m.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
    var e = new T.LineSegments(edges, edgeMat.clone());
    m.add(e);
    m.userData = { rx: (Math.random() - 0.5) * 0.004, ry: (Math.random() - 0.5) * 0.004, vy: 0.002 + Math.random() * 0.006, ph: Math.random() * Math.PI * 2 };
    group.add(m);
    cubes.push(m);
  }
  // particles
  var P = reduce ? 200 : 600;
  var pos = new Float32Array(P * 3);
  for (var k = 0; k < P; k++) { pos[k * 3] = (Math.random() - 0.5) * 90; pos[k * 3 + 1] = (Math.random() - 0.5) * 50; pos[k * 3 + 2] = (Math.random() - 0.5) * 60 - 10; }
  var pgeo = new T.BufferGeometry();
  pgeo.setAttribute("position", new T.BufferAttribute(pos, 3));
  var pmat = new T.PointsMaterial({ color: 0x3b8df5, size: 0.12, transparent: true, opacity: 0.55, sizeAttenuation: true, depthWrite: false });
  var points = new T.Points(pgeo, pmat);
  scene.add(points);

  var ambient = new T.AmbientLight(0xffffff, 0.6);
  var l1 = new T.PointLight(0x8a3fe6, 2.2, 90);
  var l2 = new T.PointLight(0x3b8df5, 2.0, 90);
  l1.position.set(-18, 12, 10); l2.position.set(20, -8, 6);
  scene.add(ambient, l1, l2);

  function applyTheme() {
    var t = theme();
    scene.background = new T.Color(t.bg);
    scene.fog = new T.FogExp2(t.fog, 0.022);
    l1.color.setHex(t.a); l2.color.setHex(t.b);
    pmat.color.setHex(t.c); pmat.opacity = t.particles;
    cubes.forEach(function (c, idx) {
      c.material.opacity = t.glass;
      c.material.color.setHex(idx % 3 === 0 ? t.a : idx % 3 === 1 ? t.b : 0xffffff);
      c.children[0].material.color.setHex(idx % 2 ? t.a : t.b);
      c.children[0].material.opacity = document.documentElement.getAttribute("data-theme") === "light" ? 0.25 : 0.4;
    });
  }
  applyTheme();
  new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  function resize() {
    var w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  var mouse = { x: 0, y: 0 };
  window.addEventListener("pointermove", function (e) {
    mouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
    mouse.y = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  var running = true, last = 0, frame = 0;
  function tick(now) {
    if (!running) return;
    requestAnimationFrame(tick);
    if (reduce && frame++ % 3) return;                 // ~20 fps when motion is reduced
    var dt = Math.min(0.05, (now - last) / 1000 || 0.016); last = now;
    var t = now * 0.001;
    cubes.forEach(function (c) {
      c.rotation.x += c.userData.rx; c.rotation.y += c.userData.ry;
      c.position.y += c.userData.vy * dt * 20;
      if (c.position.y > 18) c.position.y = -18;
    });
    group.rotation.y = Math.sin(t * 0.05) * 0.15 + mouse.x * 0.05;
    points.rotation.y = t * 0.01;
    camera.position.x += ((mouse.x * 1.5) - camera.position.x) * 0.02;
    camera.position.y += ((2.5 - mouse.y * 1.0) - camera.position.y) * 0.02;
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }
  requestAnimationFrame(tick);

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { running = false; }
    else if (!running && enabled) { running = true; last = 0; requestAnimationFrame(tick); }
  });

  function setEnabled(on) {
    enabled = on;
    try { localStorage.setItem(KEY, on ? "on" : "off"); } catch (e) {}
    wrap.classList.toggle("off", !on);
    if (on && !running) { running = true; last = 0; requestAnimationFrame(tick); }
    if (!on) running = false;
  }
  window.addEventListener("keydown", function (e) {
    if (e.ctrlKey && e.shiftKey && (e.key === "B" || e.key === "b")) { e.preventDefault(); setEnabled(!enabled); }
  });
  window.zenovixBackground = { enable: function () { setEnabled(true); }, disable: function () { setEnabled(false); } };
})();
