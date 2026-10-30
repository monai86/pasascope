// PasaScope download page: language, the right download for this computer, the latest
// release's version and files, and the hero's signal-to-text playback.
(function () {
  "use strict";
  const REPO = "monai86/pasascope";
  const RELEASES = `https://github.com/${REPO}/releases/latest`;
  const root = document.documentElement;
  root.classList.add("js");

  // ---------------------------------------------------------------- language
  function setLanguage(code) {
    root.dataset.lang = code;
    root.lang = code;
    try { localStorage.setItem("pasascope-lang", code); } catch (_) { /* private mode */ }
  }
  let saved = null;
  try { saved = localStorage.getItem("pasascope-lang"); } catch (_) { /* private mode */ }
  const wanted = new URLSearchParams(location.search).get("lang");
  // ?lang= first, then the visitor's earlier choice, then Thai (English is one click away).
  const choice = [wanted, saved].find((code) => code === "th" || code === "en");
  setLanguage(choice || "th");
  document.querySelectorAll("[data-lang-toggle]").forEach((button) =>
    button.addEventListener("click", () => setLanguage(root.dataset.lang === "th" ? "en" : "th")));

  // ----------------------------------------------- which computer is this?
  const windows = /Windows/i.test(navigator.userAgent);
  if (windows) {
    document.querySelectorAll("[data-label-mac]").forEach((el) => (el.hidden = true));
    document.querySelectorAll("[data-label-win]").forEach((el) => (el.hidden = false));
  }
  const recommended = document.querySelector(`.download-card[data-platform="${windows ? "windows" : "mac"}"]`);
  if (recommended) recommended.classList.add("is-recommended");

  // ------------------------------------------- the latest release's files
  // The page ships with the current version written in; this replaces it with whatever
  // GitHub says is latest, so a new release needs no edit here.
  function megabytes(bytes) {
    return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.round(bytes / 1e6)} MB`;
  }
  function dayText(iso, locale) {
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(locale, { day: "numeric", month: "long", year: "numeric" });
  }
  fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" }, cache: "no-store" })
    .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
    .then((release) => {
      const version = String(release.tag_name || "").replace(/^v/, "");
      if (!version) return;
      document.querySelectorAll("[data-release-version]").forEach((el) => (el.textContent = version));
      document.querySelectorAll("[data-release-date]").forEach((el) => {
        const text = dayText(release.published_at, el.dataset.releaseDate);
        if (text) el.textContent = text;
      });
      const find = (pattern) => (release.assets || []).find((asset) => pattern.test(asset.name));
      const assets = { dmg: find(/\.dmg$/), exe: find(/windows-x64-setup\.exe$/) };
      for (const [kind, asset] of Object.entries(assets)) {
        const link = document.querySelector(`[data-asset="${kind}"]`);
        const meta = document.querySelector(`[data-asset-meta="${kind}"]`);
        if (asset && link) link.href = asset.browser_download_url;
        if (meta) {
          meta.innerHTML = asset
            ? `${version} · ${megabytes(asset.size)}`
            : '<span lang="th">กำลังเตรียมไฟล์ อีกสักครู่</span><span lang="en">Being prepared; back in a few minutes</span>';
        }
      }
      const primary = assets[windows ? "exe" : "dmg"];
      const primaryLink = document.querySelector('[data-download="primary"]');
      if (primary && primaryLink) primaryLink.href = primary.browser_download_url;
    })
    .catch(() => {
      document.querySelectorAll('[data-asset], [data-download="primary"]').forEach((link) => (link.href = RELEASES));
    });

  // ------------------------------------------------ signal → text playback
  const scope = document.querySelector(".scope");
  const canvas = scope && scope.querySelector(".wave");
  if (!scope || !canvas || !canvas.getContext) return;

  // The synthetic recording behind the sample: when each line is spoken, in seconds.
  const TOTAL = 16;
  const turns = [
    { s: 0.4, e: 1.8, child: false, syl: 6 },
    { s: 2.4, e: 3.6, child: true, syl: 3 },
    { s: 4.2, e: 5.4, child: false, syl: 4 },
    { s: 5.9, e: 7.2, child: true, syl: 4 },
    { s: 7.8, e: 9.0, child: false, syl: 4 },
    { s: 9.6, e: 11.0, child: true, syl: 4 },
    { s: 11.6, e: 13.0, child: false, syl: 6 },
    { s: 13.5, e: 15.4, child: true, syl: 5 },
  ];
  // What the readout shows after each child line is counted (CLAN rules, as in the app).
  const tallies = {
    1: { utt: 1, words: 3, mlu: 3.0, ndw: 3, echo: 1 },
    3: { utt: 2, words: 6, mlu: 3.0, ndw: 5, echo: 2 },
    5: { utt: 3, words: 9, mlu: 3.0, ndw: 8, echo: 3 },
    7: { utt: 4, words: 14, mlu: 3.5, ndw: 12, echo: 3 },
  };
  const lines = [...scope.querySelectorAll(".line")];
  const totals = {};
  scope.querySelectorAll("[data-total]").forEach((el) => (totals[el.dataset.total] = el));

  // A fixed seed, so the same waveform draws every time.
  let seed = 7;
  const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const BAR = 4;   // CSS px per bar, gap included
  let bars = [];   // amplitude 0..1 per bar, rebuilt on resize
  function buildBars(count) {
    seed = 7;
    const out = new Array(count).fill(0);
    for (const turn of turns) {
      const len = turn.e - turn.s;
      for (let k = 0; k < turn.syl; k++) {
        const centre = turn.s + (len * (k + 0.5)) / turn.syl;
        const width = (len / turn.syl) * (0.32 + random() * 0.12);
        const height = (turn.child ? 0.62 : 0.78) * (0.65 + random() * 0.35);
        for (let i = 0; i < count; i++) {
          const t = (i / count) * TOTAL;
          out[i] += height * Math.exp(-((t - centre) ** 2) / (2 * width * width));
        }
      }
    }
    return out.map((a) => Math.min(1, a * (0.86 + random() * 0.28) + 0.035 + random() * 0.025));
  }
  const css = getComputedStyle(root);
  const colour = {
    idle: "#c9d5ec",
    adult: "#8796b8",
    child: css.getPropertyValue("--azure").trim() || "#1c4fff",
    head: css.getPropertyValue("--azure-deep").trim() || "#1238d4",
  };
  function turnAt(t) { return turns.find((turn) => t >= turn.s - 0.15 && t <= turn.e + 0.15); }
  function draw(played) {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    const count = Math.floor(width / BAR);
    if (bars.length !== count) bars = buildBars(count);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const mid = height / 2;
    for (let i = 0; i < count; i++) {
      const t = (i / count) * TOTAL;
      const half = Math.max(1, bars[i] * (mid - 4));
      const turn = turnAt(t);
      ctx.fillStyle = t > played ? colour.idle : turn ? (turn.child ? colour.child : colour.adult) : colour.idle;
      const x = i * BAR + 0.5;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, mid - half, BAR - 1.5, half * 2, 1.25);
      else ctx.rect(x, mid - half, BAR - 1.5, half * 2);
      ctx.fill();
    }
    if (played > 0 && played < TOTAL) {
      const x = (played / TOTAL) * width;
      ctx.fillStyle = colour.head;
      ctx.fillRect(Math.round(x) - 0.75, 0, 1.5, height);
      ctx.beginPath();
      ctx.arc(x, 4, 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function showTally(index, animate) {
    const tally = tallies[index];
    if (!tally) return;
    for (const [key, el] of Object.entries(totals)) {
      const target = tally[key];
      const text = key === "mlu" ? target.toFixed(2) : String(target);
      if (!animate) { el.textContent = text; continue; }
      el.classList.add("is-ticking");
      const from = parseFloat(el.textContent) || 0;
      const start = performance.now();
      const step = (now) => {
        const k = Math.min(1, (now - start) / 420);
        const value = from + (target - from) * (1 - (1 - k) ** 3);
        el.textContent = key === "mlu" ? value.toFixed(2) : String(Math.round(value));
        if (k < 1) requestAnimationFrame(step);
        else { el.textContent = text; el.classList.remove("is-ticking"); }
      };
      requestAnimationFrame(step);
    }
  }

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let played = TOTAL;
  let running = false;
  const redraw = () => draw(played);
  if ("ResizeObserver" in window) new ResizeObserver(redraw).observe(canvas);
  else window.addEventListener("resize", redraw);

  if (reduce || !("IntersectionObserver" in window)) {
    redraw(); // the finished state: every line counted, numbers as written in the page
    return;
  }

  const replay = document.createElement("button");
  replay.type = "button";
  replay.className = "replay";
  replay.hidden = true;
  replay.innerHTML = '<span lang="th">เล่นอีกครั้ง</span><span lang="en">Play again</span>';
  scope.querySelector(".signal").append(replay);

  function arm() {
    scope.classList.add("is-armed");
    lines.forEach((line) => line.classList.remove("is-done", "is-live"));
    for (const [key, el] of Object.entries(totals)) el.textContent = key === "mlu" ? "0.00" : "0";
    played = 0;
    redraw();
  }
  function run() {
    if (running) return;
    running = true;
    replay.hidden = true;
    arm();
    const SPEED = 2.1; // recording seconds per screen second
    let last = performance.now();
    const counted = new Set();
    const frame = (now) => {
      played = Math.min(TOTAL, played + ((now - last) / 1000) * SPEED);
      last = now;
      turns.forEach((turn, index) => {
        const line = lines[index];
        if (!line) return;
        line.classList.toggle("is-live", played >= turn.s && played < turn.e + 0.2);
        if (played >= turn.e && !counted.has(index)) {
          counted.add(index);
          line.classList.add("is-done");
          showTally(index, true);
        }
      });
      draw(played);
      if (played < TOTAL) requestAnimationFrame(frame);
      else { running = false; lines.forEach((line) => line.classList.remove("is-live")); replay.hidden = false; }
    };
    requestAnimationFrame(frame);
  }
  replay.addEventListener("click", run);

  // Start once the panel is on screen and the fonts have settled, but not wait for long.
  const fonts = Promise.race([
    document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve(),
    new Promise((resolve) => setTimeout(resolve, 1500)),
  ]);
  arm();
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      observer.disconnect();
      fonts.then(() => setTimeout(run, 350));
    }
  }, { threshold: 0.35 });
  observer.observe(scope);
})();
