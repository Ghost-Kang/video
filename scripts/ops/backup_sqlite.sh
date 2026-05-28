#!/usr/bin/env bash
# OpenRHTV Cascade — SQLite hot backup (cron daily 03:00).
#
# Why: backend writes to data/*.db continuously. cp during write can corrupt;
# sqlite3 .backup is atomic. Keep last 7 days locally + push to OSS if configured.
#
# Usage: bash scripts/ops/backup_sqlite.sh [data_dir] [backup_dir]
# Cron:  0 3 * * * /opt/cascade/scripts/ops/backup_sqlite.sh

set -euo pipefail

DATA_DIR="${1:-${CASCADE_DATA_DIR:-/opt/cascade/data}}"
BACKUP_DIR="${2:-${CASCADE_BACKUP_DIR:-/opt/cascade/backups}}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%d_%H%M%S)

for db in events.db canvas.db checkpoints.db messages.db; do
  src="$DATA_DIR/$db"
  if [ ! -f "$src" ]; then
    echo "[skip] $src missing"
    continue
  fi
  dst="$BACKUP_DIR/${db%.db}_${STAMP}.db"
  sqlite3 "$src" ".backup '$dst'"
  gzip -9 "$dst"
  echo "[ok] $src → ${dst}.gz"
done

# Prune older than RETENTION_DAYS
find "$BACKUP_DIR" -name "*.db.gz" -mtime "+$RETENTION_DAYS" -delete

# Optional OSS push (uncomment + configure):
# ossutil cp -r "$BACKUP_DIR" oss://your-bucket/cascade-backups/ --include "*${STAMP}*"

echo "[done] backup_sqlite ${STAMP}"
