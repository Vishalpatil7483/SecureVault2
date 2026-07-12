"""
Authentication service layer.

Business logic lives here, decoupled from HTTP concerns. Views call these
functions; the functions know nothing about requests, sessions or templates,
which makes them straightforward to unit-test.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.extensions import db


class RegistrationError(Exception):
    """Raised when a new account cannot be created."""


def register_user(username: str, email: str, password: str) -> User:
    """Create and persist a new user.

    Raises:
        RegistrationError: if the username or email is already taken.
    """
    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing is not None:
        raise RegistrationError("That username or email is already registered.")

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # A concurrent request registered the same username/email between the
        # pre-check and commit. The unique constraint is the source of truth;
        # roll back so the session is reusable and surface a clean error.
        db.session.rollback()
        raise RegistrationError(
            "That username or email is already registered."
        ) from None
    return user


def authenticate(username: str, password: str) -> User | None:
    """Return the matching user for valid credentials, else None.

    A single generic outcome (None) is returned whether the username is unknown
    or the password is wrong, so callers cannot leak which one failed.
    """
    user = User.query.filter_by(username=username).first()
    if user is not None and user.check_password(password):
        return user
    return None
