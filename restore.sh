#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then echo "Usage: $0 path/to/backup.sqlite3" >&2; exit 2; fi
DB_PATH="${AIMLD_DATABASE_PATH:-./instance/aimld.sqlite3}"
mkdir -p "$(dirname "$DB_PATH")"
if [ -f "$DB_PATH" ]; then cp "$DB_PATH" "$DB_PATH.before-restore-$(date -u +%Y%m%dT%H%M%SZ)"; fi
python - "$1" "$DB_PATH" <<'PY'
import sqlite3, sys
src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2])
with dst: src.backup(dst)
print('Restore completed:',sys.argv[2])
dst.close(); src.close()
PY
