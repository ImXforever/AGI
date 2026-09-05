/* Knowledge atom — infinitely expandable Bohr architecture.
 *
 * Nucleus  = company charter (immutable core)
 * Shell n  = orbit with capacity 2n² (K, L, M, N, … forever)
 * Electron = one knowledge particle (document, SOP, FAQ, future domain)
 *
 * Adding knowledge never mutates the nucleus. Overflow creates shell n+1.
 */
(function (root) {
  "use strict";

  function bohrCapacity(n) {
    return 2 * n * n;
  }

  function uid(prefix) {
    return prefix + "-" + Math.random().toString(36).slice(2, 8);
  }

  function Nucleus(data) {
    this.id = data.id || "nucleus";
    this.title = data.title || "Company core";
    this.charter = data.charter || "";
    this.mass = data.mass || 1;
  }

  function Electron(data) {
    this.id = data.id || uid("e");
    this.title = data.title || "Untitled";
    this.sensitivity = data.sensitivity || "internal";
    this.domain = data.domain || "ops";
    this.status = data.status || "approved";
    this.version = data.version || 1;
    this.text = data.text || "";
    this.phase = data.phase || 0;
    this.speed = 0.35 + Math.random() * 0.55;
  }

  function Shell(n, label) {
    this.n = n;
    this.label = label || "n=" + n;
    this.capacity = bohrCapacity(n);
    this.electrons = [];
  }
  Shell.prototype.isFull = function () {
    return this.electrons.length >= this.capacity;
  };

  function KnowledgeAtom(nucleusData) {
    this.nucleus = new Nucleus(nucleusData || {});
    this.shells = [];
  }

  KnowledgeAtom.prototype.ensureShell = function (n, label) {
    while (this.shells.length < n) {
      var next = this.shells.length + 1;
      this.shells.push(new Shell(next, label && next === n ? label : shellName(next)));
    }
    return this.shells[n - 1];
  };

  KnowledgeAtom.prototype.addShell = function (label) {
    var n = this.shells.length + 1;
    var shell = new Shell(n, label || shellName(n));
    this.shells.push(shell);
    return shell;
  };

  KnowledgeAtom.prototype.addElectron = function (data) {
    var e = data instanceof Electron ? data : new Electron(data);
    var shell = null;
    for (var i = 0; i < this.shells.length; i++) {
      if (!this.shells[i].isFull()) {
        shell = this.shells[i];
        break;
      }
    }
    if (!shell) shell = this.addShell();
    e.phase = (shell.electrons.length / Math.max(shell.capacity, 1)) * Math.PI * 2;
    shell.electrons.push(e);
    return { electron: e, shell: shell };
  };

  KnowledgeAtom.prototype.eachElectron = function (fn) {
    this.shells.forEach(function (shell) {
      shell.electrons.forEach(function (e) {
        fn(e, shell);
      });
    });
  };

  KnowledgeAtom.prototype.find = function (id) {
    if (id === this.nucleus.id) return { kind: "nucleus", node: this.nucleus };
    var found = null;
    this.eachElectron(function (e, shell) {
      if (e.id === id) found = { kind: "electron", node: e, shell: shell };
    });
    return found;
  };

  KnowledgeAtom.prototype.stats = function () {
    var electrons = 0;
    this.shells.forEach(function (s) {
      electrons += s.electrons.length;
    });
    var nextN = this.shells.length + 1;
    return {
      shells: this.shells.length,
      electrons: electrons,
      nextCapacity: bohrCapacity(nextN),
      infinite: true,
    };
  };

  KnowledgeAtom.prototype.toJSON = function () {
    return {
      nucleus: this.nucleus,
      shells: this.shells.map(function (s) {
        return {
          n: s.n,
          label: s.label,
          capacity: s.capacity,
          electrons: s.electrons,
        };
      }),
    };
  };

  function shellName(n) {
    var letters = "KLMNOQRTUVWXYZ";
    if (n <= letters.length) return letters.charAt(n - 1) + " shell";
    return "n=" + n + " shell";
  }

  KnowledgeAtom.seed = function () {
    var atom = new KnowledgeAtom({
      id: "nucleus",
      title: "Kia charter",
      mass: 4,
      charter:
        "You are the company's digital operations manager. You handle email, the website, social, day-to-day work, knowledge, follow-up and reporting. High-risk actions need a manager record.",
    });
    atom.addShell("Public · K");
    atom.addShell("Internal · L");
    atom.addShell("Confidential · M");
    atom.addShell("Domain specialists · N");

    var particles = [
      { title: "Product catalog v4", sensitivity: "public", domain: "sales", status: "approved", version: 4, text: "Approved commercial catalog used by common replies." },
      { title: "Brand voice SOP v2", sensitivity: "internal", domain: "ops", status: "approved", version: 2, text: "Tone, greeting, and refusal patterns." },
      { title: "Warranty & MOQ FAQ v3", sensitivity: "internal", domain: "support", status: "approved", version: 3, text: "First-line warranty and quantity answers." },
      { title: "Shipping windows", sensitivity: "internal", domain: "ops", status: "review", version: 1, text: "Not yet approved — agents must not quote it." },
      { title: "Distribution contract terms", sensitivity: "confidential", domain: "legal", status: "approved", version: 1, text: "Manager-only. Hidden from email_agent." },
      { title: "2026 price list", sensitivity: "internal", domain: "sales", status: "draft", version: 0, text: "Draft. Quotes cannot invent prices from this." },
      { title: "Email templates", sensitivity: "internal", domain: "email", status: "approved", version: 3, text: "Catalog, MOQ, samples, warranty, meeting." },
      { title: "Social claim rules", sensitivity: "internal", domain: "social", status: "approved", version: 1, text: "No guaranteed, medical, or return-on-investment claims." },
      { title: "Website CMS policy", sensitivity: "internal", domain: "website", status: "approved", version: 1, text: "Price, legal, delete stay behind HITL." },
      { title: "Access matrix §5", sensitivity: "internal", domain: "ops", status: "approved", version: 1, text: "Auto vs manager-only actions." },
      { title: "Support SLA", sensitivity: "internal", domain: "support", status: "approved", version: 1, text: "4h / 24h / 48h by priority." },
      { title: "Future: accounting", sensitivity: "internal", domain: "future", status: "inactive", version: 0, text: "Declared, not activated." },
    ];
    particles.forEach(function (p) {
      atom.addElectron(p);
    });
    return atom;
  };

  root.KnowledgeAtom = KnowledgeAtom;
  root.KnowledgeElectron = Electron;
  root.bohrCapacity = bohrCapacity;
})(typeof window !== "undefined" ? window : globalThis);
