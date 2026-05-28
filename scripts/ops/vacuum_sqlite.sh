#!/usr/bin/env bash
# OpenRHTV Cascade — weekly SQLite VACUUM.
#
# Usage: bash scripts/ops/vacuum_sqlite.sh [data_dir]
# Cron:  30 3 * * 0 /opt/cascade/scripts/ops/vacuum_sqlite.sh /opt/cascade/data >> /var/log/cascade-vacuum.log 2>&1

set -euo pipefail

DATA_DIR="${1:-${CASCADE_DATA_DIR:-/opt/cascade/data}}"

for db in events.db canvas.db checkpoints.db messages.db; do
  src="$DATA_DIR/$db"
  if [ ! -f "$src" ]; then
    echo "[skip] $src missing"
    continue
  fi
  before=$(stat -c %s "$src" 2>/dev/null || stat -f %z "$src")
  sqlite3 "$src" "VACUUM;"
  after=$(stat -c %s "$src" 2>/dev/null || stat -f %z "$src")
  echo "[ok] $db: ${before} -> ${after} bytes (saved $((before - after)))"
done
