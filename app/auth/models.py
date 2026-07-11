"""
Authentication data model.

Holds the `User` entity and the Flask-Login `user_loader`. Password material
is never stored in plaintext — only a bcrypt hash, via `set_password`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import bcrypt, db, login_manager


class User(UserMixin, db.Model):
    """A registered account.

    `UserMixin` supplies the properties Flask-Login expects
    (`is_authenticated`, `get_id`, etc.), keeping this class focused on data.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, password: str) -> None:
        """Hash and store a plaintext password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Return True if `password` matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Reload a user from the session (used by Flask-Login on each request)."""
    return db.session.get(User, int(user_id))
