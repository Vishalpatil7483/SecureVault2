// SecureVault 2.3 — theme bootstrap.
// Loaded synchronously in <head> (self-hosted, CSP-compliant) so the correct
// theme is applied before first paint, avoiding a flash of the wrong theme.
// Preference order: localStorage -> OS preference (prefers-color-scheme).
(function () {
  "use strict";

  function preferredTheme() {
    try {
      var stored = localStorage.getItem("sv-theme");
      if (stored === "light" || stored === "dark") return stored;
    } catch (err) { /* storage unavailable — fall through to OS preference */ }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
  }

  applyTheme(preferredTheme());

  // Shared helper for the toggle button in app.js.
  window.svTheme = {
    current: function () {
      return document.documentElement.getAttribute("data-bs-theme") || "light";
    },
    set: function (theme) {
      applyTheme(theme);
      try { localStorage.setItem("sv-theme", theme); } catch (err) { /* ignore */ }
      document.dispatchEvent(new CustomEvent("sv:theme-changed", { detail: { theme: theme } }));
    }
  };

  // Follow OS changes live, but only when the user hasn't chosen explicitly.
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
      var stored = null;
      try { stored = localStorage.getItem("sv-theme"); } catch (err) { /* ignore */ }
      if (!stored) {
        applyTheme(e.matches ? "dark" : "light");
        document.dispatchEvent(new CustomEvent("sv:theme-changed", { detail: { theme: e.matches ? "dark" : "light" } }));
      }
    });
  }
})();
