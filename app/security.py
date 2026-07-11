"""
HTTP security headers for SecureVault 2.0.

A deliberately simple, dependency-free approach: a single `after_request` hook
sets sensible security headers on every response. This is easier to read,
audit and adjust than a full policy framework, which this app does not need.

Headers set:
  * Content-Security-Policy   — restrict resources to same-origin, block framing.
  * X-Content-Type-Options    — stop MIME-type sniffing.
  * X-Frame-Options           — legacy clickjacking protection.
  * Referrer-Policy           — limit referrer leakage.
  * Strict-Transport-Security — force HTTPS (production only, where cookies are
                                already marked Secure).
"""
from __future__ import annotations

from flask import Flask

# No inline styles or scripts are used in the templates, so a strict
# same-origin policy needs no 'unsafe-inline' escape hatch.
_CSP = "default-src 'self'; form-action 'self'; frame-ancestors 'none'"


def register_security_headers(app: Flask) -> None:
    """Attach an after_request hook that sets security headers."""

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("Content-Security-Policy", _CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Only advertise HSTS where we actually serve over HTTPS.
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
