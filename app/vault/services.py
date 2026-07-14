"""
File upload service layer.

All business logic for accepting an uploaded file lives here, decoupled from
HTTP concerns so it can be unit-tested and reused. The route layer only passes
in a Werkzeug ``FileStorage`` and the owning user.

Security properties enforced here:
  * Extension whitelist  — only configured types are accepted.
  * Size limits          — empty files and oversized files are rejected.
  * Randomised storage   — files are written under a server-generated random
                           name, never the user-supplied filename, preventing
                           path traversal, collisions and name-based leakage.
  * Atomic-ish metadata  — if the database write fails, the on-disk file is
                           removed so we never leak orphaned bytes.
"""
from __future__ import annotations

import mimetypes
import os
import secrets
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.auth.models import User
from app.extensions import db
from app.vault.models import File

# Length of the random token (bytes) used for on-disk filenames. 16 bytes of
# entropy (32 hex chars) makes collisions effectively impossible.
_STORED_NAME_ENTROPY_BYTES = 16

_DEFAULT_MIME_TYPE = "application/octet-stream"


class UploadError(Exception):
    """Base error for a failed upload."""


class FileValidationError(UploadError):
    """Raised when an uploaded file fails validation (type, size, emptiness)."""


class FileAccessError(Exception):
    """Raised when a requested file does not exist or is not owned by the user.

    A single error for both "missing" and "not yours" deliberately avoids
    leaking whether another user's file id exists (no resource enumeration).
    """


class PhysicalFileMissingError(Exception):
    """Raised when a file's metadata exists but its bytes are gone from disk."""


def ensure_upload_dir() -> Path:
    """Return the uploads directory, creating it if necessary."""
    upload_dir: Path = current_app.config["UPLOAD_DIR"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _extract_extension(filename: str) -> str:
    """Return the normalised, lower-case extension (no dot) or "" if none."""
    return Path(filename).suffix.lower().lstrip(".")


def _measure_size(file_storage: FileStorage) -> int:
    """Return the byte length of the upload stream without consuming it."""
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


def _validate(file_storage: FileStorage, extension: str, size: int) -> None:
    """Validate a candidate upload, raising FileValidationError on any failure."""
    config = current_app.config

    # A missing filename means no file was actually selected/sent.
    if not file_storage or not file_storage.filename:
        raise FileValidationError("No file was provided.")

    if not extension:
        raise FileValidationError("The file has no extension and cannot be accepted.")

    if extension not in config["ALLOWED_UPLOAD_EXTENSIONS"]:
        raise FileValidationError(f"Files of type '.{extension}' are not allowed.")

    # Empty-file detection.
    if size == 0:
        raise FileValidationError("The file is empty.")

    if size > config["MAX_FILE_SIZE"]:
        max_mb = config["MAX_FILE_SIZE"] / (1024 * 1024)
        raise FileValidationError(f"The file exceeds the {max_mb:.0f} MB limit.")


def _generate_stored_filename(extension: str) -> str:
    """Build a collision-resistant random on-disk name preserving the extension."""
    token = secrets.token_hex(_STORED_NAME_ENTROPY_BYTES)
    return f"{token}.{extension}" if extension else token


def _resolve_mime_type(file_storage: FileStorage, original_filename: str) -> str:
    """Best-effort MIME type from the client hint, then filename, then default."""
    if file_storage.mimetype:
        return file_storage.mimetype
    guessed, _ = mimetypes.guess_type(original_filename)
    return guessed or _DEFAULT_MIME_TYPE


def save_upload(file_storage: FileStorage, user: User) -> File:
    """Validate, store on disk, and persist metadata for an uploaded file.

    Args:
        file_storage: The incoming Werkzeug file from ``request.files``.
        user: The authenticated owner of the file.

    Returns:
        The persisted ``File`` metadata record.

    Raises:
        FileValidationError: if the file fails validation.
        UploadError: if the file cannot be written or its metadata persisted.
    """
    # Keep a sanitised copy of the original name for display; the on-disk name
    # is random regardless, so this is defensive rather than load-bearing.
    original_filename = secure_filename(file_storage.filename or "")
    extension = _extract_extension(original_filename)
    size = _measure_size(file_storage)

    _validate(file_storage, extension, size)

    upload_dir = ensure_upload_dir()
    stored_filename = _generate_stored_filename(extension)
    storage_path = upload_dir / stored_filename

    # Write the bytes to disk first so we never persist metadata for a file
    # that failed to save.
    try:
        file_storage.save(str(storage_path))
    except OSError as exc:
        current_app.logger.exception("Failed to write uploaded file to disk")
        raise UploadError("The file could not be saved.") from exc

    record = File(
        user_id=user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_extension=extension,
        mime_type=_resolve_mime_type(file_storage, original_filename),
        file_size=size,
        storage_path=str(storage_path),
    )

    try:
        db.session.add(record)
        db.session.commit()
    except Exception as exc:
        # Roll back and remove the orphaned file so disk and DB stay consistent.
        db.session.rollback()
        storage_path.unlink(missing_ok=True)
        current_app.logger.exception("Failed to persist file metadata")
        raise UploadError("The file could not be saved.") from exc

    current_app.logger.info(
        "Stored upload id=%s user=%s size=%s", record.id, user.id, size
    )
    return record


# Maximum length accepted for a (renamed) display filename.
_MAX_DISPLAY_NAME_LENGTH = 255


def get_owned_file(file_id: int, user: User) -> File:
    """Return the user's file by id, or raise FileAccessError.

    Scoping the query by ``user_id`` is the authorization boundary: a file that
    belongs to someone else is indistinguishable from one that doesn't exist.
    """
    file = File.query.filter_by(id=file_id, user_id=user.id).first()
    if file is None:
        raise FileAccessError("File not found.")
    return file


def get_download_target(file_id: int, user: User) -> tuple[Path, str]:
    """Resolve an owned file to its on-disk path and original download name.

    Returns:
        A ``(storage_path, original_filename)`` tuple.

    Raises:
        FileAccessError: if the file is missing or not owned by the user.
        PhysicalFileMissingError: if the record exists but the bytes are gone.
    """
    file = get_owned_file(file_id, user)
    storage_path = Path(file.storage_path)
    if not storage_path.is_file():
        current_app.logger.error(
            "Missing physical file for id=%s user=%s path=%s",
            file.id, user.id, file.storage_path,
        )
        raise PhysicalFileMissingError("The stored file is no longer available.")
    return storage_path, file.original_filename


def delete_file(file_id: int, user: User) -> str:
    """Delete an owned file's record and its bytes on disk.

    The database row is the source of truth: it is removed first, then the file
    on disk. A physical file that is already gone is not an error.

    Returns:
        The original filename of the deleted file (for the flash message).

    Raises:
        FileAccessError: if the file is missing or not owned by the user.
        UploadError: if the metadata could not be removed.
    """
    file = get_owned_file(file_id, user)
    original_filename = file.original_filename
    storage_path = Path(file.storage_path)

    try:
        db.session.delete(file)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Failed to delete file metadata id=%s", file_id)
        raise UploadError("The file could not be deleted.") from exc

    # Metadata is gone; now remove the bytes. `missing_ok=True` makes an
    # already-absent file a no-op rather than a failure.
    try:
        storage_path.unlink(missing_ok=True)
    except OSError:
        # The record is already deleted; a leftover file is logged, not fatal.
        current_app.logger.warning(
            "Deleted record but could not remove file on disk: %s", storage_path
        )

    current_app.logger.info("Deleted file id=%s user=%s", file_id, user.id)
    return original_filename


def rename_file(file_id: int, user: User, new_name: str) -> File:
    """Rename the display (original) filename only; the on-disk name is untouched.

    Raises:
        FileAccessError: if the file is missing or not owned by the user.
        FileValidationError: if the new name is empty or too long.
        UploadError: if the change could not be persisted.
    """
    file = get_owned_file(file_id, user)

    # Strip any path components a client might inject; this is a display label,
    # never a filesystem path.
    cleaned = os.path.basename((new_name or "").strip())
    if not cleaned:
        raise FileValidationError("Please provide a new filename.")
    if len(cleaned) > _MAX_DISPLAY_NAME_LENGTH:
        raise FileValidationError("The filename is too long.")

    file.original_filename = cleaned
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Failed to rename file id=%s", file_id)
        raise UploadError("The file could not be renamed.") from exc

    current_app.logger.info("Renamed file id=%s user=%s", file_id, user.id)
    return file


def list_files(user: User, query: str | None = None) -> list[File]:
    """Return the user's files, newest first, optionally filtered by name.

    Search is scoped to the user and matches ``original_filename`` with a
    case-insensitive substring. The ``ix_files_user_id`` index keeps the
    per-user filter efficient.
    """
    stmt = File.query.filter_by(user_id=user.id)
    if query:
        term = query.strip()
        if term:
            stmt = stmt.filter(File.original_filename.ilike(f"%{term}%"))
    return stmt.order_by(File.upload_timestamp.desc()).all()
