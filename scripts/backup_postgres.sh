#!/bin/bash
set -euo pipefail

# Real Postgres backup script - per-database custom-format (-Fc) dumps,
# not a single pg_dumpall. Matches this project's own per-service-DB
# architecture (see init-scripts/init-multiple-dbs.sh): a per-database
# dump lets one service's database be restored independently during a
# partial recovery, without touching the other 5 - a single pg_dumpall
# would only ever restore everything at once. Custom format (not plain
# SQL) is also compressed and supports selective-table and parallel
# restore, not just "replay this whole SQL file top to bottom."
#
# -T is required on `docker compose exec` here, not optional - it
# disables pseudo-TTY allocation. Without it, TTY allocation can
# corrupt binary output when piped to a file - a real, easy-to-miss
# mistake with a custom-format (binary) dump specifically; a plain-SQL
# dump would "work" without -T and mask the same underlying problem.

DATABASES=(auth_db asset_db telemetry_db ml_service_db notification_db copilot_service_db)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}"
KEEP_LAST_N=5

mkdir -p "$BACKUP_DIR"

for db in "${DATABASES[@]}"; do
    echo "Backing up ${db}..."
    docker compose exec -T postgres pg_dump -U hvac -Fc "$db" > "${BACKUP_DIR}/${db}.dump"
done

echo "Backup complete: ${BACKUP_DIR}"
du -sh "${BACKUP_DIR}"/*.dump

# Simple retention: keep only the last N backup directories, delete
# older ones. Real, working rotation for a solo/local-dev setup - NOT
# a substitute for automated scheduling or off-site storage before any
# real deployment (see docs/BACKUP_STRATEGY.md's explicitly stated,
# honest gaps - this script has to be run manually, it isn't on a cron
# or CI schedule).
cd backups
ls -1d */ 2>/dev/null | sort -r | tail -n +$((KEEP_LAST_N + 1)) | xargs -r rm -rf
cd ..
