// SecureVault 2.3 — progressive enhancement.
// Self-hosted and CSP-compliant (no inline scripts/styles in templates;
// dynamic behaviour lives here).
(function () {
  "use strict";

  // --- Loading indicator on form submit (prevents double-submits) ---------
  document.addEventListener(
    "submit",
    function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;

      var button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;

      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Working…';
    },
    true
  );

  document.addEventListener("DOMContentLoaded", function () {
    // --- Theme toggle ------------------------------------------------------
    var toggle = document.getElementById("theme-toggle");
    var toggleIcon = document.getElementById("theme-toggle-icon");

    function syncToggleIcon() {
      if (!toggleIcon || !window.svTheme) return;
      var dark = window.svTheme.current() === "dark";
      toggleIcon.className = dark ? "bi bi-sun" : "bi bi-moon-stars";
      if (toggle) {
        toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
        toggle.title = dark ? "Switch to light mode" : "Switch to dark mode";
      }
    }

    if (toggle && window.svTheme) {
      toggle.addEventListener("click", function () {
        window.svTheme.set(window.svTheme.current() === "dark" ? "light" : "dark");
      });
      document.addEventListener("sv:theme-changed", syncToggleIcon);
      syncToggleIcon();
    }

    // --- Toast notifications (from server-rendered flash data) -------------
    var TOAST_META = {
      success: { icon: "check-circle-fill", cls: "text-bg-success" },
      danger: { icon: "exclamation-triangle-fill", cls: "text-bg-danger" },
      warning: { icon: "exclamation-circle-fill", cls: "text-bg-warning" },
      info: { icon: "info-circle-fill", cls: "text-bg-info" }
    };

    function showToast(message, category) {
      var container = document.getElementById("toast-container");
      if (!container || typeof bootstrap === "undefined") return;

      var meta = TOAST_META[category] || { icon: "info-circle-fill", cls: "text-bg-secondary" };
      var toastEl = document.createElement("div");
      toastEl.className = "toast align-items-center border-0 " + meta.cls;
      toastEl.setAttribute("role", "alert");
      toastEl.setAttribute("aria-live", "assertive");
      toastEl.setAttribute("aria-atomic", "true");

      var flex = document.createElement("div");
      flex.className = "d-flex";

      var body = document.createElement("div");
      body.className = "toast-body d-flex align-items-center gap-2";
      var icon = document.createElement("i");
      icon.className = "bi bi-" + meta.icon;
      icon.setAttribute("aria-hidden", "true");
      var text = document.createElement("span");
      text.textContent = message; // textContent — never innerHTML for user data
      body.appendChild(icon);
      body.appendChild(text);

      var close = document.createElement("button");
      close.type = "button";
      close.className = "btn-close btn-close-white me-2 m-auto";
      close.setAttribute("data-bs-dismiss", "toast");
      close.setAttribute("aria-label", "Close");

      flex.appendChild(body);
      flex.appendChild(close);
      toastEl.appendChild(flex);
      container.appendChild(toastEl);

      var toast = new bootstrap.Toast(toastEl, { delay: 5000, autohide: true });
      toastEl.addEventListener("hidden.bs.toast", function () { toastEl.remove(); });
      toast.show();
    }

    document.querySelectorAll(".sv-flash").forEach(function (el) {
      showToast(el.textContent.trim(), el.dataset.category || "info");
      el.remove();
    });

    // --- Drag & drop upload -------------------------------------------------
    var dropzone = document.getElementById("dropzone");
    var fileInput = document.getElementById("file");
    var dropzoneLabel = document.getElementById("dropzone-filename");

    if (dropzone && fileInput) {
      function setFilename() {
        if (!dropzoneLabel) return;
        if (fileInput.files && fileInput.files.length) {
          dropzoneLabel.textContent = fileInput.files[0].name;
          dropzone.classList.add("has-file");
        } else {
          dropzoneLabel.textContent = "";
          dropzone.classList.remove("has-file");
        }
      }

      // The invisible input overlays the whole zone, so clicking it opens the
      // picker natively; we only need highlight + label behaviour.
      ["dragenter", "dragover"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.add("dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.remove("dragover");
        });
      });
      dropzone.addEventListener("drop", function (e) {
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
          fileInput.files = e.dataTransfer.files;
          setFilename();
        }
      });
      fileInput.addEventListener("change", setFilename);
    }

    // --- Storage progress bar (width from data attribute, not inline CSS) --
    document.querySelectorAll(".progress-bar[data-width-pct]").forEach(function (bar) {
      var pct = parseFloat(bar.dataset.widthPct);
      if (!isNaN(pct)) {
        bar.style.width = Math.min(Math.max(pct, 0), 100) + "%";
      }
    });

    // --- Upload trend chart (data via JSON data island; theme-aware) --------
    var canvas = document.getElementById("uploadTrendChart");
    var dataEl = document.getElementById("upload-trend-data");
    if (!canvas || !dataEl || typeof Chart === "undefined") return;

    var trend;
    try {
      trend = JSON.parse(dataEl.textContent);
    } catch (err) {
      return; // malformed data — skip the chart rather than break the page
    }
    if (!Array.isArray(trend) || trend.length === 0) return;

    function chartColors() {
      var dark = document.documentElement.getAttribute("data-bs-theme") === "dark";
      return {
        grid: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)",
        ticks: dark ? "#adb5bd" : "#6c757d"
      };
    }

    var colors = chartColors();
    var chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: trend.map(function (d) { return d.label; }),
        datasets: [{
          label: "Uploads",
          data: trend.map(function (d) { return d.count; }),
          backgroundColor: "rgba(13, 110, 253, 0.55)",
          borderColor: "rgba(13, 110, 253, 1)",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 26
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { displayColors: false }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: colors.ticks },
            grid: { color: colors.grid }
          },
          x: {
            grid: { display: false },
            ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 10, color: colors.ticks }
          }
        }
      }
    });

    // Re-skin the chart when the theme changes.
    document.addEventListener("sv:theme-changed", function () {
      var c = chartColors();
      chart.options.scales.y.grid.color = c.grid;
      chart.options.scales.y.ticks.color = c.ticks;
      chart.options.scales.x.ticks.color = c.ticks;
      chart.update();
    });
  });
})();
