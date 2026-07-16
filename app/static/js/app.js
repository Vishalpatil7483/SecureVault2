// SecureVault 2.1 — progressive enhancement.
// Self-hosted and CSP-compliant (no inline scripts/styles in templates;
// dynamic styling happens here via the DOM API).
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
    // --- Storage progress bar (width set from data attribute, not inline CSS)
    document.querySelectorAll(".progress-bar[data-width-pct]").forEach(function (bar) {
      var pct = parseFloat(bar.dataset.widthPct);
      if (!isNaN(pct)) {
        bar.style.width = Math.min(Math.max(pct, 0), 100) + "%";
      }
    });

    // --- Upload trend chart (data supplied via a JSON data island) --------
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

    new Chart(canvas, {
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
            ticks: { precision: 0 },
            grid: { color: "rgba(0,0,0,0.05)" }
          },
          x: {
            grid: { display: false },
            ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 10 }
          }
        }
      }
    });
  });
})();
