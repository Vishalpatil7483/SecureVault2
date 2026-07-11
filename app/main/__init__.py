"""
Main blueprint — public / general pages (landing, health check, etc.).

Routes are intentionally not implemented in this milestone. This package only
establishes the blueprint so the application factory can register it.
"""
from flask import Blueprint

main_bp = Blueprint("main", __name__)

# Import routes at the bottom so their decorators register against the
# blueprint. Placed here (not at the top) to avoid a circular import.
from app.main import routes  # noqa: E402,F401
