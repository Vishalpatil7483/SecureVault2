"""
Route handlers for the `vault` blueprint.

Views are intentionally thin: they gather the request input, delegate to the
service layer, translate the outcome into a flash message, and render/redirect.
All access requires an authenticated user.
"""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.vault import vault_bp
from app.vault.models import File
from app.vault.services import FileValidationError, UploadError, save_upload


@vault_bp.app_template_filter("filesizeformat_iec")
def filesizeformat_iec(num_bytes: int) -> str:
    """Render a byte count as a human-readable size (e.g. 1.2 MB)."""
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@vault_bp.route("/dashboard")
@login_required
def dashboard():
    """Show the current user's files and the upload form."""
    files = (
        File.query.filter_by(user_id=current_user.id)
        .order_by(File.upload_timestamp.desc())
        .all()
    )
    return render_template("vault/dashboard.html", files=files)


@vault_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """Accept a single uploaded file and store it via the service layer."""
    file_storage = request.files.get("file")
    if file_storage is None or not file_storage.filename:
        flash("Please choose a file to upload.", "warning")
        return redirect(url_for("vault.dashboard"))

    try:
        record = save_upload(file_storage, current_user)
    except FileValidationError as exc:
        flash(str(exc), "danger")
    except UploadError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"'{record.original_filename}' uploaded successfully.", "success")

    return redirect(url_for("vault.dashboard"))
