"""
Vault blueprint — secure file upload, storage, listing and download.

Routes are intentionally not implemented in this milestone. This package only
establishes the blueprint so the application factory can register it.
"""
from flask import Blueprint

vault_bp = Blueprint("vault", __name__)

# Routes will be imported here in a later milestone, e.g.:
# from app.vault import routes  # noqa: E402,F401
