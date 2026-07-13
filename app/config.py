"""
Configuration system for SecureVault 2.0.

Design:
  * A `BaseConfig` holds sane, shared defaults.
  * Environment-specific subclasses override only what changes.
  * Secrets and environment-dependent values come from environment variables
    (loaded from a local `.env` file via python-dotenv) — never hard-coded.

This keeps the same codebase deployable across dev, test and prod while
following the 12-factor-app principle of config-in-the-environment.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Project root = one level above the `app` package.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file if present. Real environment variables
# always take precedence over the file, which is the desired behaviour in
# production where secrets are injected by the platform.
load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    """Settings shared by every environment."""

    ENV_NAME = "base"

    # --- Security ----------------------------------------------------------
    # No insecure default here. Dev/testing provide a throwaway fallback in
    # their own subclasses; production requires a real, strong key from the
    # environment (enforced by ProductionConfig.validate()).
    SECRET_KEY = os.getenv("SECRET_KEY")

    # --- Networking --------------------------------------------------------
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))

    # --- Database ----------------------------------------------------------
    # Default to a local SQLite file inside the instance folder. Any other
    # backend (Postgres, MySQL) can be supplied via DATABASE_URL.
    # `.as_posix()` yields forward slashes so the SQLite URI is valid on
    # Windows as well as POSIX systems (avoids backslashes inside the URI).
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'instance' / 'securevault.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session cookie hardening -----------------------------------------
    # Sensible security defaults for a session-based app. SECURE is left off
    # in the base/dev config (no HTTPS locally) and switched on in production.
    SESSION_COOKIE_HTTPONLY = True  # JS cannot read the session cookie (XSS)
    SESSION_COOKIE_SAMESITE = "Lax"  # mitigates CSRF on cross-site requests
    SESSION_COOKIE_SECURE = False  # overridden to True in production

    # Session + "remember me" lifetimes. Short-lived sessions limit the window
    # of a stolen cookie; the remember cookie is hardened the same way.
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False  # overridden to True in production

    # --- Rate limiting -----------------------------------------------------
    # In-memory storage suits a single-process dev server. Point this at Redis
    # (e.g. redis://localhost:6379) for multi-worker production deployments.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # --- File uploads ------------------------------------------------------
    # Uploaded files live on disk under the (git-ignored) instance folder and
    # are never served directly; only their metadata is stored in the database.
    UPLOAD_DIR = BASE_DIR / "instance" / "uploads"

    # Maximum accepted upload size in bytes (default 16 MB). MAX_CONTENT_LENGTH
    # lets Flask reject oversized request bodies before they reach the service,
    # guarding against memory exhaustion; the service enforces the same limit.
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(16 * 1024 * 1024)))
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE

    # Allowed extensions (lower-case, no leading dot). The whitelist is the
    # primary control over what may be stored — the on-disk name is randomised.
    ALLOWED_UPLOAD_EXTENSIONS = {
        "pdf", "txt", "csv", "md",
        "png", "jpg", "jpeg", "gif",
        "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "zip",
    }

    # --- Logging -----------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = BASE_DIR / "logs"

    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    """Local development: verbose logging, debugger on."""

    ENV_NAME = "development"
    DEBUG = True
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

    # Fixed throwaway key so local sessions survive server restarts. Clearly
    # labelled as insecure; production never inherits this.
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-insecure-secret-not-for-production"


class TestingConfig(BaseConfig):
    """Automated tests: in-memory DB, testing hooks enabled."""

    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = os.getenv("SECRET_KEY") or "testing-insecure-secret"
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False  # disabled so tests can POST without a token
    RATELIMIT_ENABLED = False  # disabled so tests are not throttled/flaky


class ProductionConfig(BaseConfig):
    """Production: strict, secret-driven, no debugger."""

    ENV_NAME = "production"
    DEBUG = False

    # Only send session / remember cookies over HTTPS in production.
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    # Minimum acceptable length for a production secret key (bytes/chars).
    MIN_SECRET_KEY_LENGTH = 32

    # Fail loudly, at startup, if the secret key is missing or weak. Checking
    # presence + length (not a single hardcoded placeholder) means a copied
    # dev key or an empty value is still rejected.
    @classmethod
    def validate(cls) -> None:
        if not cls.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )
        if len(cls.SECRET_KEY) < cls.MIN_SECRET_KEY_LENGTH:
            raise RuntimeError(
                "SECRET_KEY is too weak; use a strong random value of at least "
                f"{cls.MIN_SECRET_KEY_LENGTH} characters "
                '(e.g. `python -c "import secrets; print(secrets.token_hex(32))"`).'
            )


_CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> type[BaseConfig]:
    """Resolve a config class from an explicit name or the environment.

    Resolution order: explicit argument -> FLASK_CONFIG env var -> development.
    """
    name = (config_name or os.getenv("FLASK_CONFIG", "development")).lower()
    config = _CONFIG_MAP.get(name, DevelopmentConfig)
    if config is ProductionConfig:
        config.validate()
    return config
