"""
SecureVault 2.0 — Application entry point.

This module is intentionally thin: its only job is to build an application
instance via the factory and expose it for the WSGI server / `flask` CLI.

Usage:
    python run.py                # run the dev server
    flask --app run:app run      # alternative via Flask CLI
    flask --app run:app db init  # Flask-Migrate commands
"""
from app import create_app

# The `flask` CLI and WSGI servers (gunicorn/uwsgi) look for a module-level
# `app` object by convention. The config is selected from FLASK_CONFIG.
app = create_app()


if __name__ == "__main__":
    # Debug + host/port are driven by config so behaviour is identical
    # whether launched via `python run.py` or a production WSGI server.
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
