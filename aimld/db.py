import sqlite3
from pathlib import Path
from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS admins (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS licenses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 key_hash TEXT NOT NULL UNIQUE,
 key_prefix TEXT NOT NULL,
 label TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','blocked','revoked')),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 expires_at TEXT NOT NULL,
 max_devices INTEGER NOT NULL DEFAULT 1 CHECK(max_devices >= 1),
 activated_at TEXT,
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS activations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 license_id INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
 device_id TEXT NOT NULL,
 device_label TEXT NOT NULL DEFAULT '',
 token_hash TEXT NOT NULL,
 activated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 deactivated_at TEXT,
 UNIQUE(license_id, device_id, deactivated_at)
);
CREATE INDEX IF NOT EXISTS idx_activations_license ON activations(license_id);
CREATE INDEX IF NOT EXISTS idx_licenses_status_expiry ON licenses(status, expires_at);
CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 admin_id INTEGER REFERENCES admins(id) ON DELETE SET NULL,
 action TEXT NOT NULL,
 target_type TEXT NOT NULL,
 target_id TEXT NOT NULL DEFAULT '',
 detail_json TEXT NOT NULL DEFAULT '{}',
 ip_address TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
"""

def get_db():
    if 'db' not in g:
        path = current_app.config['DATABASE_PATH']
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=15000')
        conn.execute('PRAGMA journal_mode=WAL')
        g.db = conn
    return g.db

def close_db(_=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(SCHEMA)

def register_db(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
