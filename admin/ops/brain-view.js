/* Three.js nucleus + canvas HUD. Falls back to canvas-only if THREE is missing. */
(function () {
  "use strict";

  var atom = KnowledgeAtom.seed();
  var selected = { kind: "nucleus", node: atom.nucleus };
  var t0 = performance.now();
  var rotY = 0.35;
  var rotX = 0.42;
  var dragging = false;
  var lastX = 0;
  var lastY = 0;
  var three = null;

  var gl = document.getElementById("gl");
  var hud = document.getElementById("hud");
  var hctx = hud.getContext("2d");
  var dock = document.getElementById("dock-body");
  var statsEl = document.getElementById("atom-stats");

  var COLORS = {
    public: 0x00ffa8,
    internal: 0x00f0ff,
    confidential: 0xff2bd6,
    future: 0xb6ff3b,
    nucleus: 0x00f0ff,
  };

  function colorOf(e) {
    if (e.status === "inactive" || e.domain === "future") return COLORS.future;
    return COLORS[e.sensitivity] || COLORS.internal;
  }

  function hexCss(n) {
    return "#" + n.toString(16).padStart(6, "0");
  }

  function resize() {
    var stage = document.getElementById("brain-stage");
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
    target.addEventListener("pointerup", function () {
      dragging = false;
    });
    target.addEventListener("pointermove", function (ev) {
      if (!dragging) return;
      rotY += (ev.clientX - lastX) * 0.005;
      rotX += (ev.clientY - lastY) * 0.005;
      rotX = Math.max(-0.9, Math.min(0.9, rotX));
      lastX = ev.clientX;
      lastY = ev.clientY;
    });
    target.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      if (three) {
        three.camera.position.z = Math.max(8, Math.min(42, three.camera.position.z + ev.deltaY * 0.02));
      }
    }, { passive: false });
  }

  function initThree() {
    if (typeof THREE === "undefined") return null;
    var renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
    camera.position.set(0, 2.4, 16);

    scene.add(new THREE.AmbientLight(0x1a3a66, 0.55));
    var key = new THREE.PointLight(0x00f0ff, 2.6, 80);
    key.position.set(6, 8, 10);
    scene.add(key);
    var rim = new THREE.PointLight(0xff2bd6, 1.6, 70);
    rim.position.set(-8, -4, 4);
    scene.add(rim);

    var root = new THREE.Group();
    scene.add(root);

    var nucleusMat = new THREE.MeshStandardMaterial({
      color: COLORS.nucleus,
      emissive: 0x003a44,
      metalness: 0.35,
      roughness: 0.22,
    });
    var nucleus = new THREE.Mesh(new THREE.IcosahedronGeometry(1.15, 2), nucleusMat);
    nucleus.userData = { id: atom.nucleus.id };
    root.add(nucleus);
    var glow = new THREE.Mesh(
      new THREE.SphereGeometry(1.55, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.14 })
    );
    root.add(glow);

    var shellGroups = [];
    var electronMeshes = [];

    function rebuildShells() {
      shellGroups.forEach(function (g) {
        root.remove(g);
      });
      shellGroups = [];
      electronMeshes = [];
      atom.shells.forEach(function (shell) {
        var g = new THREE.Group();
        g.rotation.x = 0.18 * shell.n;
        g.rotation.z = 0.11 * shell.n;
        var radius = 2.1 + shell.n * 1.55;
        var ring = new THREE.Mesh(
          new THREE.TorusGeometry(radius, 0.012, 8, 128),
          new THREE.MeshBasicMaterial({ color: 0x3a3f4c, transparent: true, opacity: 0.7 })
        );
        g.add(ring);
        shell.electrons.forEach(function (e, i) {
          var m = new THREE.Mesh(
            new THREE.SphereGeometry(0.18, 16, 16),
            new THREE.MeshStandardMaterial({
              color: colorOf(e),
              emissive: colorOf(e),
              emissiveIntensity: 0.35,
              metalness: 0.2,
              roughness: 0.4,
            })
          );
          m.userData = { id: e.id, radius: radius, electron: e, index: i, count: shell.electrons.length };
          g.add(m);
          electronMeshes.push(m);
        });
        root.add(g);
        shellGroups.push(g);
      });
    }

    rebuildShells();

    var ray = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    gl.addEventListener("click", function (ev) {
      if (dragging) return;
      var rect = gl.getBoundingClientRect();
      mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      ray.setFromCamera(mouse, camera);
      var hits = ray.intersectObjects(electronMeshes.concat([nucleus]));
      if (hits.length) select(hits[0].object.userData.id);
    });

    return {
      renderer: renderer,
      scene: scene,
      camera: camera,
      root: root,
      rebuildShells: rebuildShells,
      electronMeshes: function () {
        return electronMeshes;
      },
    };
  }

  function select(id) {
    selected = atom.find(id) || selected;
    renderDock();
  }

  function renderDock() {
    var s = atom.stats();
    statsEl.textContent =
      s.shells + " shells · " + s.electrons + " electrons · next orbit holds " + s.nextCapacity + " · infinite";
    var n = selected.node;
    if (selected.kind === "nucleus") {
      dock.innerHTML =
        "<h3>Nucleus</h3><p><b>" +
        n.title +
        "</b></p><p class='mini'>" +
        n.charter +
        "</p><p class='mini'>The nucleus never splits. New knowledge only adds shells.</p>";
      return;
    }
    dock.innerHTML =
      "<h3>" +
      selected.shell.label +
      " · n=" +
      selected.shell.n +
      "</h3><p><b>" +
      n.title +
      "</b></p><p class='mini'>" +
      n.domain +
      " · " +
      n.sensitivity +
      " · " +
      n.status +
      " · v" +
      n.version +
      "</p><p>" +
      n.text +
      "</p>";
  }

  function drawHud(now) {
    var w = hud.clientWidth;
    var h = hud.clientHeight;
    hctx.clearRect(0, 0, w, h);
    hctx.fillStyle = "rgba(238,241,246,0.55)";
    hctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    hctx.fillText("Atomic knowledge brain · drag to orbit · click an electron", 16, 22);
    var legend = [
      ["Nucleus", COLORS.nucleus],
      ["Public", COLORS.public],
      ["Internal", COLORS.internal],
      ["Confidential", COLORS.confidential],
      ["Future shell", COLORS.future],
    ];
    legend.forEach(function (row, i) {
      var x = 16;
      var y = h - 18 - i * 16;
      hctx.fillStyle = hexCss(row[1]);
      hctx.beginPath();
      hctx.arc(x, y, 4, 0, Math.PI * 2);
      hctx.fill();
      hctx.fillStyle = "rgba(238,241,246,0.7)";
      hctx.fillText(row[0], x + 10, y + 4);
    });
    if (!three) drawCanvasAtom(now, w, h);
  }

  function drawCanvasAtom(now, w, h) {
    var ctx = gl.getContext("2d");
    if (!ctx) return;
    gl.width = hud.width;
    gl.height = hud.height;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    ctx.clearRect(0, 0, w, h);
    var cx = w / 2;
    var cy = h / 2;
    var t = now * 0.001;
    ctx.save();
    ctx.translate(cx, cy);
    var g = ctx.createRadialGradient(0, 0, 4, 0, 0, 28);
    g.addColorStop(0, "#00f0ff");
    g.addColorStop(1, "rgba(0,240,255,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#00f0ff";
    ctx.beginPath();
    ctx.arc(0, 0, 10, 0, Math.PI * 2);
    ctx.fill();
    atom.shells.forEach(function (shell) {
      var r = 42 + shell.n * 28;
      ctx.strokeStyle = "rgba(58,63,76,0.9)";
      ctx.beginPath();
      ctx.ellipse(0, 0, r, r * (0.45 + 0.08 * Math.sin(rotX)), rotY + shell.n * 0.2, 0, Math.PI * 2);
      ctx.stroke();
      shell.electrons.forEach(function (e, i) {
        var a = e.phase + t * e.speed + (i / Math.max(shell.electrons.length, 1)) * Math.PI * 2;
        var x = Math.cos(a + rotY) * r;
        var y = Math.sin(a) * r * (0.45 + 0.08 * Math.sin(rotX));
        ctx.fillStyle = hexCss(colorOf(e));
        ctx.beginPath();
        ctx.arc(x, y, 4.5, 0, Math.PI * 2);
        ctx.fill();
      });
    });
    ctx.restore();
  }

  function tick(now) {
    var t = (now - t0) / 1000;
    if (three) {
      three.root.rotation.y = rotY;
      three.root.rotation.x = rotX;
      three.electronMeshes().forEach(function (m) {
        var r = m.userData.radius;
        var a = m.userData.electron.phase + t * m.userData.electron.speed;
        m.position.set(Math.cos(a) * r, Math.sin(a * 0.35) * 0.35, Math.sin(a) * r);
      });
      three.renderer.render(three.scene, three.camera);
    }
    drawHud(now);
    requestAnimationFrame(tick);
  }

  function addParticle() {
    var n = atom.stats().electrons + 1;
    atom.addElectron({
      title: "New particle " + n,
      sensitivity: n % 5 === 0 ? "confidential" : n % 2 ? "internal" : "public",
      domain: ["email", "website", "social", "sales", "support", "ops"][n % 6],
      status: "approved",
      text: "Added at runtime. Overflow created a new Bohr shell if needed.",
    });
    if (three) three.rebuildShells();
    renderDock();
  }

  function addOrbit() {
    atom.addShell();
    if (three) three.rebuildShells();
    renderDock();
  }

  document.getElementById("btn-add-e").addEventListener("click", addParticle);
  document.getElementById("btn-add-shell").addEventListener("click", addOrbit);
  document.getElementById("btn-nucleus").addEventListener("click", function () {
    select(atom.nucleus.id);
  });

  three = initThree();
  bindDrag(gl);
  bindDrag(hud);
  window.addEventListener("resize", resize);
  resize();
  renderDock();
  requestAnimationFrame(tick);
})();
