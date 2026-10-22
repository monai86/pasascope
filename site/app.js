// PasaScope download page: language, the right download for this computer,
// the latest release's files and sizes, and the hero sheet's counting marks.
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
  // ?lang= first, then the visitor's earlier choice, then English (Thai is one click away).
  const choice = [wanted, saved].find((code) => code === "th" || code === "en");
  setLanguage(choice || "en");
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
  function megabytes(bytes) {
    return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.round(bytes / 1e6)} MB`;
  }
  function dayText(iso, locale) {
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(locale, { day: "numeric", month: "long", year: "numeric" });
  }
  fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
    .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
    .then((release) => {
      const version = String(release.tag_name || "").replace(/^v/, "");
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
      const secondary = assets[windows ? "dmg" : "exe"];
      const primaryLink = document.querySelector('[data-download="primary"]');
      const secondaryLink = document.querySelector('[data-download="secondary"]');
      if (primary && primaryLink) primaryLink.href = primary.browser_download_url;
      if (secondaryLink) secondaryLink.href = "#download";
      const metaLine = document.querySelector("[data-release-meta]");
      if (metaLine && version) {
        metaLine.insertAdjacentHTML("afterbegin",
          `<span lang="th">รุ่น ${version} · ${dayText(release.published_at, "th-TH")} · </span>` +
          `<span lang="en">Version ${version} · ${dayText(release.published_at, "en-GB")} · </span>`);
      }
    })
    .catch(() => {
      document.querySelectorAll('[data-asset], [data-download="primary"]').forEach((link) => (link.href = RELEASES));
    });

  // ------------------------- the sheet marks itself once it comes into view
  // Marks are visible by default; with motion allowed, CSS hides them until
  // this adds .is-marked, then they draw in word by word.
  const sheet = document.querySelector(".sheet");
  if (!sheet) return;
  const mark = () => sheet.classList.add("is-marked");
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    mark();
    return;
  }
  // Wait for the fonts so the marks draw under the final word widths, but not for long.
  const fonts = Promise.race([
    document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve(),
    new Promise((resolve) => setTimeout(resolve, 1500)),
  ]);
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      observer.disconnect();
      fonts.then(() => requestAnimationFrame(mark));
    }
  }, { threshold: 0.3 });
  observer.observe(sheet);
})();
