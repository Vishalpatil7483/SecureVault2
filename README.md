# 🔒 SecureVault

**Encrypted file storage web application built with Flask.**

SecureVault is a production-oriented web app for storing files securely.
Every file is encrypted with **AES-256-GCM** before it touches disk, its
integrity is verified with a **SHA-256 checksum** on every download, and every
action is recorded in an immutable **audit log**. It was built as a portfolio
project to demonstrate professional software-engineering and cybersecurity
practices.

---

## Overview

Users register, log in, and manage their own private vault of files. Files are
never stored under their original name or in plaintext — they are encrypted
with a per-file key (itself wrapped by a master key) and stored under a random
identifier. Only the owning user can list, download, rename, or delete their
files.

## Features

- **Authentication** — registration, login, logout with hashed passwords
  (bcrypt), session hardening, and rate-limited login.
- **Secure upload** — extension whitelist, size limit, and empty-file
  rejection; files are encrypted in memory before being written to disk.
- **Encrypted storage** — AES-256-GCM envelope encryption (per-file data key
  wrapped by a master key).
- **Verified download** — files are decrypted on the fly and checked against a
  stored SHA-256 checksum; tampering is detected and rejected.
- **File management** — search, rename (display name only), and delete, all
  scoped to the current user.
- **Dashboard** — SaaS-style overview: statistics cards, storage-usage bar,
  a 14-day upload-trend chart (Chart.js), recent uploads and recent activity.
- **Activity Center** — dedicated, filterable, searchable, paginated timeline
  of the full audit trail, grouped by Today / Yesterday / Earlier.
- **Modern UX** — dark/light theme with system detection, drag-and-drop
  uploads, toast notifications, file-type icons, and responsive design.
- **Audit logging** — every upload, download, rename, and delete is recorded
  (including failures), with client IP and timestamp.
- **Hardened by default** — CSRF protection, strict Content-Security-Policy,
  secure cookies, and centralized, user-friendly error pages.

## Technology stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| Framework | Flask (application-factory pattern) |
| ORM / DB | SQLAlchemy 2.0, Flask-Migrate (Alembic), SQLite (Postgres-ready) |
| Auth | Flask-Login, Flask-Bcrypt |
| Forms / CSRF | Flask-WTF, WTForms |
| Rate limiting | Flask-Limiter |
| Cryptography | `cryptography` (AES-256-GCM), `hashlib` (SHA-256) |
| Frontend | Bootstrap 5, Bootstrap Icons, Chart.js (all self-hosted), Jinja2 |
| Server | Gunicorn |
| Packaging | Docker, docker-compose |

## Architecture

SecureVault uses the **application-factory** pattern with **feature blueprints**
and a **service layer** that isolates business logic from HTTP concerns.

```
SecureVault2/
├── app/
│   ├── __init__.py          # Application factory, extension + blueprint wiring
│   ├── config.py            # Env-based config (dev / testing / production)
│   ├── extensions.py        # Extension instances (db, login, csrf, limiter…)
│   ├── errors.py            # Centralized error handlers
│   ├── security.py          # Security headers (CSP, HSTS, etc.)
│   ├── logging_config.py    # Rotating file + console logging
│   ├── auth/                # Authentication blueprint
│   │   ├── models.py        # User
│   │   ├── forms.py         # Login / Register forms
│   │   ├── services.py      # register_user(), authenticate()
│   │   └── routes.py        # Thin views
│   ├── vault/               # File-management blueprint
│   │   ├── models.py        # File, AuditLog
│   │   ├── crypto.py        # AES-256-GCM envelope encryption engine
│   │   ├── services.py      # upload/download/delete/rename/stats + auditing
│   │   └── routes.py        # Thin views
│   ├── main/                # Landing page blueprint
│   ├── templates/           # Jinja2 templates (Bootstrap 5)
│   └── static/              # Self-hosted Bootstrap, app CSS/JS
├── migrations/              # Alembic migrations
├── tests/                   # Pytest scaffolding
├── Dockerfile, docker-compose.yml, render.yaml
├── requirements.txt, requirements-dev.txt
└── run.py                   # Entry point (exposes `app`)
```

**Request flow:** `route (thin)` → `service (business logic)` → `models / crypto`.
Routes never contain business logic; services never touch the request/response.

## Installation (local)

Requires **Python 3.10+** (3.12 recommended).

```bash
# 1. Clone and enter the project
git clone <your-repo-url> SecureVault2 && cd SecureVault2

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash);  .venv/bin/activate on macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt          # runtime
pip install -r requirements-dev.txt      # + pytest (optional)

# 4. Configure environment
cp .env.example .env                     # dev works with built-in fallbacks

# 5. Apply database migrations
flask --app run:app db upgrade

# 6. Run the development server
python run.py                            # http://127.0.0.1:5000
```

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `FLASK_CONFIG` | no | `development` (default), `testing`, or `production`. |
| `SECRET_KEY` | prod | Session-signing secret. Must be ≥ 32 chars in production. |
| `ENCRYPTION_KEY` | prod | AES master key: 64-char hex, base64 of 32 bytes, or a 32-char string. |
| `DATABASE_URL` | no | SQLAlchemy URL. Defaults to local SQLite in `instance/`. |
| `RATELIMIT_STORAGE_URI` | no | Rate-limit backend (`memory://` default; use Redis in prod). |
| `MAX_FILE_SIZE` | no | Max upload size in bytes (default 16 MB). |
| `STORAGE_QUOTA_BYTES` | no | Display-only quota for the dashboard usage bar (default 1 GB). |
| `HOST` / `PORT` | no | Bind address / port. |
| `LOG_LEVEL` | no | `DEBUG` / `INFO` / `WARNING` / … |

In **development** and **testing**, throwaway `SECRET_KEY` and `ENCRYPTION_KEY`
values are used automatically if unset. In **production** the app refuses to
start unless both are set to valid values.

Generate strong values:

```bash
python -c "import secrets; print(secrets.token_hex(32))"                              # SECRET_KEY
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())" # ENCRYPTION_KEY
```

## Database migrations

Schema changes are managed with Flask-Migrate (Alembic):

```bash
flask --app run:app db migrate -m "describe change"   # generate a migration
flask --app run:app db upgrade                         # apply migrations
flask --app run:app db downgrade                       # roll back one revision
```

Migrations are committed to the repo; the Docker entry point runs
`flask db upgrade` automatically on start.

## Security features

- **Encryption at rest:** AES-256-GCM envelope encryption; plaintext is never
  written to disk. Each file has a unique data key wrapped by the master key.
- **Integrity:** GCM authentication tag + independent SHA-256 checksum verified
  on every download.
- **Key management:** master key supplied via environment/config; production
  startup validation rejects a missing or malformed key.
- **Authentication & authorization:** bcrypt password hashing; all file access
  is scoped to the owning user (a file you don't own is indistinguishable from
  one that doesn't exist).
- **CSRF protection:** enabled globally via Flask-WTF.
- **Rate limiting:** login endpoint throttled to mitigate brute-force attacks.
- **Secure sessions:** `HttpOnly`, `SameSite=Lax`, and `Secure` (in production)
  cookies with a bounded lifetime.
- **Security headers:** strict Content-Security-Policy (`default-src 'self'`,
  no CDNs), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
  HSTS in production.
- **Safe uploads:** extension whitelist, size cap, randomised on-disk names,
  and `secure_filename` sanitisation.
- **Audit trail:** append-only log of all file actions, retained across deletes.

## Screenshots

> _Placeholder — add screenshots here._

| Landing | Dashboard | Login |
| --- | --- | --- |
| `docs/screenshots/landing.png` | `docs/screenshots/dashboard.png` | `docs/screenshots/login.png` |

## Deployment

### Docker (local, production-style)

```bash
# Create .env with a strong SECRET_KEY and a valid 32-byte ENCRYPTION_KEY.
docker compose up --build
# App available at http://localhost:8000
```

The named `vault-data` volume persists the SQLite database and encrypted
uploads across restarts.

### Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and point it at the repo; Render reads
   [`render.yaml`](render.yaml).
3. Render generates `SECRET_KEY` automatically. Set `ENCRYPTION_KEY` manually in
   the service's **Environment** tab (generate one with the command above).
4. Deploy. The Docker entry point runs migrations, then starts Gunicorn. The
   attached disk (`/app/instance`) persists data.

> For multi-instance / high-traffic production, point `DATABASE_URL` at Postgres
> and `RATELIMIT_STORAGE_URI` at Redis.

## Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Future improvements

- Move object storage to S3-compatible cloud storage with server-side streaming.
- Postgres + Redis in the default production compose file.
- Per-user storage quotas and file-type previews.
- Optional two-factor authentication and OAuth login.
- Background virus scanning of uploads.
- Key rotation tooling for the encryption master key.
- Admin dashboard surfacing the audit log.

## License

Released under the [MIT License](LICENSE).
