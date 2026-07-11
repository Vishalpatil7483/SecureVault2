"""
Application Factory for SecureVault 2.0.

The application-factory pattern is the Flask-recommended way to structure a
non-trivial app. Instead of a global `app` object, we build one on demand.

Why this matters for a production-quality project:
  * Testability   — each test can build an isolated app with a test config.
  * Multiple envs — dev / testing / production share one codebase.
  * No circular imports — extensions are instantiated in `extensions.py`
    and only *bound* to the app inside the factory.
"""
from __future__ import annotations

import os

from flask import Flask

from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import bcrypt, csrf, db, limiter, login_manager, migrate
from app.logging_config import configure_logging
from app.security import register_security_headers


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure a Flask application instance.

    Args:
        config_name: Optional config key ("development", "testing",
            "production"). Falls back to the FLASK_CONFIG env var, then
            "development".

    Returns:
        A fully configured Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Flask does not auto-create the instance folder; ensure it exists so the
    # default SQLite database (and other runtime artifacts) have a home.
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Configuration -----------------------------------------------------
    app.config.from_object(get_config(config_name))

    # --- Logging (configure early so later steps can log) ------------------
    configure_logging(app)

    # --- Extensions --------------------------------------------------------
    register_extensions(app)

    # --- Blueprints --------------------------------------------------------
    register_blueprints(app)

    # --- Cross-cutting concerns -------------------------------------------
    register_error_handlers(app)
    register_security_headers(app)

    app.logger.info("SecureVault 2.0 initialised (config=%s)", app.config["ENV_NAME"])
    return app


def register_extensions(app: Flask) -> None:
    """Bind Flask extensions to the application instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # login_manager needs to know where the login view lives. The endpoint is
    # namespaced by the auth blueprint; it is safe to set now even though the
    # view itself is implemented in a later milestone.
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints.

    Blueprints are imported locally to avoid import-time side effects and to
    keep the dependency graph clean.
    """
    from app.auth import auth_bp
    from app.main import main_bp
    from app.vault import vault_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(vault_bp, url_prefix="/vault")
