// SecureVault 2.0 — minimal progressive enhancement.
// Self-hosted so it complies with the app's strict Content-Security-Policy
// (no inline scripts). Shows a loading indicator on form submission and
// prevents accidental double-submits.
(function () {
  "use strict";

  document.addEventListener(
    "submit",
    function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;

      var button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;

      // Preserve the label, then swap in a spinner. The form submits normally;
      // disabling the button only guards against a second click.
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Working…';
    },
    true
  );
})();
