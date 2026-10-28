# AIMLD License Platform

A deployable Flask web admin + REST license API + SQLite schema + SwiftUI sample. The provided `IOSViet.zip` was not copied into this project; this project is a standalone licensing service and does not contain or integrate game-modification code.


## Windows / VS Code quick start

This replacement ZIP includes a private local `.env` with randomly generated secrets, so you do not need to create those secrets manually. Do not upload or share `.env`.

1. Extract the ZIP into a new folder (keep the whole folder structure).
2. Open that extracted folder in VS Code.
3. Double-click `RUN_ON_WINDOWS.bat`, or in the VS Code terminal run:

```powershell
py -m pip install -r requirements.txt
py -m flask --app aimld.app create-admin
py -m flask --app aimld.app run --host 127.0.0.1 --port 9132
```

When prompted, enter an admin username and a unique password of at least 14 characters; confirm it. Then open `http://127.0.0.1:9132/admin/login`. For local HTTP, `COOKIE_SECURE=false` is set in the included `.env`. For public HTTPS hosting, set it to `true`.

## Source analysis

A static analysis of the supplied `IOSViet.zip` is included at `docs/ANALYSIS_IOSVIET.md`, with an inventory of the archive in `docs/iosviet_inventory.csv`. The original is a Theos iOS tweak/dylib project, not a complete Xcode app. AIMLD re-implements the lawful UI style and standalone licensing flow; game-interaction, injection, and anti-analysis code is not included. The source archive had five manifest mismatches and an embedded API token; the token was not copied into AIMLD.

## Architecture

- Flask serves the responsive admin UI and `/api/license/*` REST endpoints.
- SQLite stores admin hashes, HMAC hashes of license keys, activation records, and audit logs.
- Admin keys are generated with Python's cryptographic `secrets` module. The raw key is shown once after creation; only HMAC-SHA256 with a server-side pepper is stored.
- SwiftUI calls the server over HTTPS. No admin secret is shipped in the app.

## Local run

Python 3.11+ recommended.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export AIMLD_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AIMLD_LICENSE_PEPPER="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AIMLD_DATABASE_PATH="$PWD/instance/aimld.sqlite3"
export COOKIE_SECURE=false  # local HTTP only; set true behind HTTPS in production
flask --app aimld.app create-admin
flask --app aimld.app run --host 0.0.0.0 --port 9132
```

Open `/admin/login`. For production, do not use Flask's development server; run Gunicorn using `Procfile` or `Dockerfile`. Ensure `/data` (Docker) or `AIMLD_DATABASE_PATH` points to a persistent disk.

## Environment

Copy `.env.example` into your deployment's environment settings; do not commit a real `.env`. Generate independent values for `AIMLD_SESSION_SECRET` and `AIMLD_LICENSE_PEPPER`. Losing the pepper makes existing license hashes impossible to validate, so back it up separately in a secret manager. Never rotate the pepper without a planned key re-issuance/migration.

## Endpoints

See `docs/API.md` for requests and response codes. `GET /health` checks the DB connection. API request limits are applied per client IP with Flask-Limiter; default storage is process memory, so configure `RATELIMIT_STORAGE_URI` to Redis for multiple instances.

## Database and backups

Schema is in `migrations/001_initial.sql`; the app runs idempotent schema creation on startup. Use `AIMLD_DATABASE_PATH=/path/to/aimld.sqlite3 ./backup.sh`. Restore with `AIMLD_DATABASE_PATH=/path/to/aimld.sqlite3 ./restore.sh ./backups/your-backup.sqlite3`. Stop writes or put the service in maintenance mode before restore. Back up the pepper and session secret separately and securely.

## Tests

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Tests cover activation, token-based validation, device limits, unknown keys, expiration, and revocation. The current packaging environment could not run the suite because Flask dependencies are not installed and outbound package downloads are unavailable. Run `pip install -r requirements.txt` and then the command above in a Python environment with package access before production.

## Hosting and iPhone-only deployment

**Free-tier snapshot checked 2026-10-25 (provider terms can change):**

| Provider | Current free-tier caveat | Suitability for real license data |
|---|---|---|
| Render | Free web service sleeps after 15 minutes idle; cold start can take about a minute; local files are ephemeral and lost on restart/redeploy. Free Postgres expires after 30 days. | Demo only with SQLite. Do not store real license data on its ephemeral disk. |
| PythonAnywhere | Free account lists 100 CPU seconds, 512 MiB disk, one web app with one web worker, and one-month expiry; outbound internet is restricted. | Useful for a short trial, not a reliable permanent production license server. |
| Railway | Trial includes a one-time $5 credit for up to 30 days; after trial the Free plan provides $1/month credit. Volumes are limited on free resources. | Trial/demo only unless usage and persistence are confirmed for the account. |

Official references: https://render.com/docs/free · https://help.pythonanywhere.com/pages/FreeAccountsFeatures/ · https://docs.railway.com/pricing/free-trial

Choose a Python-capable host that supports persistent disk or a managed PostgreSQL service. Free-tier quotas, sleep behavior, retention, and pricing change frequently; verify current terms before deploying. A free web container without persistent disk can lose SQLite data on restart/redeploy. Do not assume any free tier is permanent. Upload this ZIP from Safari to a host that accepts GitHub repositories or ZIP deployments, set the environment variables in the host dashboard, attach persistent storage at `/data` (or set `AIMLD_DATABASE_PATH`), and configure HTTPS/domain in the host dashboard. Run `flask --app aimld.app create-admin` as a one-time release/start command or through the provider's shell. Do not run the create-admin command on every restart.

An iPhone can upload/configure a project through browser dashboards, but some hosts require a Git repository or terminal. For an actual signed IPA, Apple's Xcode/signing toolchain is needed, normally on a Mac or a hosted Mac build service. The ZIP contains Swift source, not a pre-signed IPA.

## Security boundaries

- License checks are server-authoritative, but client-side app features can still be patched by a determined attacker. For valuable functionality, enforce entitlements on the server wherever practical and consider App Attest/DeviceCheck.
- A device ID stored in Keychain is a practical device slot identifier, not an unforgeable hardware identity. A reinstall or compromised device may affect it.
- There is no offline grace cache in this sample; offline requests fail closed. If offline access is added, use short-lived signed entitlements and explicitly accept the revocation delay.
- `GET /api/license/status` accepts the key in query parameters for the requested endpoint shape; query strings may appear in proxy logs. Prefer POST `/validate` for normal app traffic.
