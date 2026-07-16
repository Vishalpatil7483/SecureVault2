"""
Centralized error handling for SecureVault 2.0.

Registering handlers in one place keeps error responses consistent across
every blueprint and prevents stack traces from leaking to clients in
production. Handlers render minimal templates so the UX degrades gracefully.
"""
from __future__ import annotations

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from app.extensions import db


def register_error_handlers(app: Flask) -> None:
    """Attach application-wide error handlers to the app."""

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        # Expired or missing CSRF token — treat as a bad request.
        return render_template("errors/400.html", reason=error.description), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        # Raised when an upload exceeds MAX_CONTENT_LENGTH.
        max_bytes = app.config.get("MAX_CONTENT_LENGTH") or 0
        max_mb = max_bytes / (1024 * 1024)
        return render_template("errors/413.html", max_mb=max_mb), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        # Raised by Flask-Limiter when a rate limit is exceeded.
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        # Roll back any half-completed transaction so the session is usable,
        # and log the full traceback for operators (never shown to the user).
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        return render_template("errors/500.html"), 500
