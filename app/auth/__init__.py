"""
Auth blueprint — registration, login, logout, session management.

Routes are intentionally not implemented in this milestone. This package only
establishes the blueprint so the application factory can register it.
"""
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# Import routes at the bottom so their decorators register against the
# blueprint. Placed here (not at the top) to avoid a circular import.
from app.auth import routes  # noqa: E402,F401
