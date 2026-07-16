"""
Route handlers for the `auth` blueprint.

Views are intentionally thin: parse/validate the form, delegate to the service
layer, then translate the result into a response. Rate limiting protects the
login endpoint against brute-force attempts.
"""
from __future__ import annotations

from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterForm
from app.auth.services import RegistrationError, authenticate, register_user
from app.extensions import limiter


def _is_safe_next(target: str | None) -> bool:
    """Allow only local, path-only redirects to prevent open-redirect abuse."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and target.startswith("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            register_user(form.username.data, form.email.data, form.password.data)
        except RegistrationError as exc:
            flash(str(exc), "danger")
        else:
            flash("Account created. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate(form.username.data, form.password.data)
        if user is None:
            flash("Invalid username or password.", "danger")
        else:
            session.permanent = True  # apply PERMANENT_SESSION_LIFETIME
            login_user(user, remember=form.remember.data)
            # Audit trail only — does not alter authentication behaviour.
            # Imported here to keep auth importable without the vault package.
            from app.vault.services import ACTION_LOGIN, record_audit

            record_audit(ACTION_LOGIN, user, detail="session started")
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            if _is_safe_next(next_page):
                return redirect(next_page)
            return redirect(url_for("main.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    # Audit before the session is cleared so the acting user is still known.
    from app.vault.services import ACTION_LOGOUT, record_audit

    record_audit(ACTION_LOGOUT, current_user, detail="session ended")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
