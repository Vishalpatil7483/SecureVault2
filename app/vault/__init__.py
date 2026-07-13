"""
Vault blueprint — secure file upload, storage, listing and download.

Routes are intentionally not implemented in this milestone. This package only
establishes the blueprint so the application factory can register it.
"""
from flask import Blueprint

vault_bp = Blueprint("vault", __name__)

# Import models and routes at the bottom so the SQLAlchemy mappers register and
# the route decorators bind to the blueprint when this package loads (the
# factory imports it). Placed here, not at the top, to avoid a circular import.
from app.vault import models  # noqa: E402,F401
from app.vault import routes  # noqa: E402,F401
