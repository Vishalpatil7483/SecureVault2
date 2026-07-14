"""
File-metadata data model.

Holds the `File` entity: a database record describing an uploaded file. The
file's bytes live on disk (under the instance uploads directory); this table
stores only metadata plus the randomised on-disk name that locates it.

Files are never stored under their original filename — `stored_filename` is a
server-generated random token, which prevents path-traversal, collisions and
information leakage from user-controlled names.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


class File(db.Model):
    """Metadata for a single uploaded file, owned by a user."""

    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)

    # Owner. Indexed for efficient per-user lookups; cascade so a user's files
    # are removed with the user at the ORM level.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The name the user uploaded — retained for display/download only, never
    # used to build a filesystem path.
    original_filename = db.Column(db.String(255), nullable=False)

    # Server-generated random name actually used on disk. Unique so lookups by
    # stored name are unambiguous.
    stored_filename = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Normalised, lower-case extension without the leading dot (e.g. "pdf").
    file_extension = db.Column(db.String(32), nullable=False)

    # Detected MIME type (best-effort; defaults to a generic binary type).
    mime_type = db.Column(db.String(255), nullable=False)

    # Size in bytes.
    file_size = db.Column(db.Integer, nullable=False)

    upload_timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Absolute path to the stored file on disk.
    storage_path = db.Column(db.String(512), nullable=False)

    # --- Encryption metadata (Milestone 4) --------------------------------
    # Whether the on-disk blob is AES-256-GCM encrypted. New uploads are always
    # encrypted; the flag lets download handle any legacy plaintext gracefully.
    is_encrypted = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text("0")
    )

    # The per-file Data-Encryption-Key, wrapped with the master key
    # (wrap_nonce || wrapped_dek). The file nonce itself is prepended to the
    # on-disk blob, so it needs no column here.
    encrypted_key = db.Column(db.LargeBinary, nullable=True)

    # SHA-256 hex digest of the *plaintext*, for independent integrity checks.
    checksum_sha256 = db.Column(db.String(64), nullable=True)

    # Relationship back to the owning user. `back_populates` keeps both sides
    # in sync; the matching `files` collection is added to User for integration.
    owner = db.relationship("User", back_populates="files")

    def __repr__(self) -> str:
        return f"<File {self.stored_filename!r} owner={self.user_id}>"


class AuditLog(db.Model):
    """Append-only record of a security-relevant action on a file.

    Deliberately decoupled from ``files`` (plain ``file_id`` + a ``filename``
    snapshot rather than a hard foreign key) so the audit trail is retained
    even after a file is deleted or renamed.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    # The actor. SET NULL on user removal so history is never lost.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Reference to the file at action time; not a FK so deletes don't cascade.
    file_id = db.Column(db.Integer, nullable=True, index=True)

    # One of: upload, download, delete, rename.
    action = db.Column(db.String(32), nullable=False, index=True)

    # Snapshot of the file's display name at the time of the action.
    filename = db.Column(db.String(255), nullable=True)

    # Optional human-readable context (e.g. rename old->new, integrity status).
    detail = db.Column(db.String(255), nullable=True)

    # Client IP address the action originated from, when available.
    ip_address = db.Column(db.String(45), nullable=True)

    # Whether the action succeeded (failures are audited too).
    success = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.text("1")
    )

    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} user={self.user_id} file={self.file_id}>"
