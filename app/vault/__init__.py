"""
Vault blueprint — secure file upload, storage, listing and download.

Routes are intentionally not implemented in this milestone. This package only
establishes the blueprint so the application factory can register it.
"""
from flask import Blueprint

vault_bp = Blueprint("vault", __name__)

# Import models at the bottom so their SQLAlchemy mappers register when the
# blueprint package loads (the factory imports this package). Placed here, not
# at the top, to avoid a circular import. Routes are added in a later batch.
from app.vault import models  # noqa: E402,F401
