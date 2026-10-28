#!/bin/sh
set -eu
DB_PATH="${AIMLD_DATABASE_PATH:-./instance/aimld.sqlite3}"
BACKUP_DIR="${AIMLD_BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# SQLite online backup API via Python handles WAL consistently.
python - "$DB_PATH" "$BACKUP_DIR/aimld-$STAMP.sqlite3" <<'PY'
import sqlite3, sys
src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2])
with dst: src.backup(dst)
dst.close(); src.close()
print('Backup written:',sys.argv[2])
PY
