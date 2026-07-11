"""
Route handlers for the `main` blueprint.

Currently a single landing page. It doubles as the post-login/logout redirect
target and the destination Flask-Login uses after authentication.
"""
from flask import render_template

from app.main import main_bp


@main_bp.route("/")
def index():
    return render_template("main/index.html")
