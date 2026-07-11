# SecureVault 2.0

A secure file-storage web application built with Flask, designed to demonstrate
professional software-engineering and cybersecurity practices.

> **Status:** Milestone 1 — project scaffold. Authentication, models, routes,
> file upload and encryption are implemented in later milestones.

---

## Overview

SecureVault 2.0 is structured around Flask best practices:

- **Application Factory** — the app is built on demand, enabling isolated
  testing and multiple runtime environments from a single codebase.
- **Configuration by environment** — `development`, `testing` and `production`
  configs, with all secrets and environment-specific values injected via
  environment variables (`.env` / the host platform).
- **Blueprint architecture** — the app is split into cohesive feature modules
  (`main`, `auth`, `vault`) so it stays modular and scalable.
- **Rotating, level-aware logging** — console + rotating file handlers wired up
  at startup, essential for a security-focused application.
- **Extension isolation** — SQLAlchemy, Flask-Migrate, Flask-Login and
  Flask-Bcrypt are instantiated separately and bound in the factory, avoiding
  circular imports.

## Project structure

```
SecureVault2/
├── app/
│   ├── __init__.py          # Application factory + registration
│   ├── config.py            # Config classes (dev / testing / production)
│   ├── extensions.py        # Flask extension instances
│   ├── logging_config.py    # Logging setup (console + rotating file)
│   ├── main/                # Public pages blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/                # Authentication blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   └── vault/               # Secure file vault blueprint
│       ├── __init__.py
│       └── routes.py
├── instance/                # Local DB / runtime artifacts (git-ignored)
├── logs/                    # Rotating log files (git-ignored)
├── migrations/              # Alembic migrations (created via `flask db init`)
├── .env.example             # Template for environment variables
├── .gitignore
├── requirements.txt
├── run.py                   # Application entry point
└── README.md
```

## Getting started

### 1. Prerequisites
- Python 3.10+ (3.11 recommended)

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows (Git Bash / PowerShell)
source .venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# then generate a strong secret key:
python -c "import secrets; print(secrets.token_hex(32))"
# paste the result into SECRET_KEY in .env
```

### 5. Initialise the database

```bash
flask --app run:app db init      # first time only — creates migrations/
flask --app run:app db migrate   # generate a migration (once models exist)
flask --app run:app db upgrade   # apply migrations
```

> In Milestone 1 there are no models yet, so `db migrate` will produce an empty
> migration. The commands are shown here so the workflow is documented.

### 6. Run the development server

```bash
python run.py
# or
flask --app run:app run
```

The app starts on `http://127.0.0.1:5000` by default.

## Dependencies

| Package            | Purpose                                                    |
| ------------------ | ---------------------------------------------------------- |
| Flask              | Core web framework.                                        |
| Flask-SQLAlchemy   | ORM / database access layer.                               |
| Flask-Migrate      | Alembic-based database migrations (`flask db ...`).        |
| SQLAlchemy         | Underlying ORM engine (pinned for reproducibility).        |
| Flask-Login        | Session-based user authentication.                         |
| Flask-Bcrypt       | Secure password hashing.                                   |
| python-dotenv      | Loads environment variables from `.env`.                   |
| gunicorn           | Production WSGI server.                                     |

## Configuration reference

| Variable       | Description                                    | Default              |
| -------------- | ---------------------------------------------- | -------------------- |
| `FLASK_CONFIG` | Config to load: development/testing/production | `development`        |
| `SECRET_KEY`   | Session-signing secret (set a strong value)    | insecure placeholder |
| `HOST`         | Bind address                                   | `127.0.0.1`          |
| `PORT`         | Bind port                                      | `5000`               |
| `DATABASE_URL` | SQLAlchemy connection string                   | local SQLite         |
| `LOG_LEVEL`    | Logging verbosity                              | `INFO` (`DEBUG` dev) |

## License

This project is provided for educational and portfolio purposes.
