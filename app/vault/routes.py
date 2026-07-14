"""
Route handlers for the `vault` blueprint.

Views are intentionally thin: they gather the request input, delegate to the
service layer, translate the outcome into a flash message, and render/redirect.
All access requires an authenticated user.
"""
from __future__ import annotations

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app.vault import vault_bp
from app.vault.services import (
    FileAccessError,
    FileValidationError,
    PhysicalFileMissingError,
    UploadError,
    delete_file,
    get_download_target,
    list_files,
    rename_file,
    save_upload,
)


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
    """Show the current user's files, the upload form, and search results."""
    search_query = request.args.get("q", "").strip()
    files = list_files(current_user, search_query)
    return render_template(
        "vault/dashboard.html", files=files, search_query=search_query
    )


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


@vault_bp.route("/download/<int:file_id>")
@login_required
def download(file_id: int):
    """Stream an owned file back to the user under its original filename."""
    try:
        storage_path, original_filename = get_download_target(file_id, current_user)
    except FileAccessError:
        abort(404)
    except PhysicalFileMissingError:
        flash("The stored file is no longer available.", "danger")
        return redirect(url_for("vault.dashboard"))

    # download_name restores the user-facing name; as_attachment forces a
    # download rather than in-browser rendering.
    return send_file(
        storage_path, as_attachment=True, download_name=original_filename
    )


@vault_bp.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete(file_id: int):
    """Delete an owned file (metadata + bytes on disk)."""
    try:
        original_filename = delete_file(file_id, current_user)
    except FileAccessError:
        abort(404)
    except UploadError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"'{original_filename}' was deleted.", "success")

    return redirect(url_for("vault.dashboard"))


@vault_bp.route("/rename/<int:file_id>", methods=["POST"])
@login_required
def rename(file_id: int):
    """Rename an owned file's display name only."""
    new_name = request.form.get("new_name", "")
    try:
        record = rename_file(file_id, current_user, new_name)
    except FileAccessError:
        abort(404)
    except FileValidationError as exc:
        flash(str(exc), "danger")
    except UploadError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Renamed to '{record.original_filename}'.", "success")

    return redirect(url_for("vault.dashboard"))
