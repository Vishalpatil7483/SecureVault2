"""
Flask extension instances.

Each extension is instantiated here *without* an app. They are bound to a
concrete app later inside the application factory via `init_app()`.

Keeping these in a dedicated, import-light module is what prevents the classic
Flask circular-import problem: any part of the app can `from app.extensions
import db` without importing the factory.
"""
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# ORM / database access layer.
db = SQLAlchemy()

# Alembic-backed database migrations (`flask db ...`).
migrate = Migrate()

# Password hashing.
bcrypt = Bcrypt()

# Session-based user authentication.
login_manager = LoginManager()

# Global CSRF protection for all POST/PUT/PATCH/DELETE requests.
csrf = CSRFProtect()

# Rate limiting, keyed by client IP. Storage backend is configured per-env
# (in-memory for dev, Redis in production) via RATELIMIT_STORAGE_URI.
limiter = Limiter(key_func=get_remote_address)
