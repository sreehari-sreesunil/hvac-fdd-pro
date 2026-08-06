#!/bin/bash
set -euo pipefail

# Restores ONE database from a specific backup. Defaults to restoring
# into a DIFFERENT database name (a "_restore_test" suffix), never the
# real one, without an explicit override - overwriting a live database
# is a genuinely destructive, high-stakes action, and shouldn't be the
# easy/default path for a script someone might run half-awake during a
# real incident.

usage() {
    echo "Usage: $0 <backup_timestamp> <database_name> [--overwrite-original]"
    echo "Example (safe, restores into auth_db_restore_test):"
    echo "  $0 20260806_143000 auth_db"
    echo "Example (DESTRUCTIVE, overwrites the real auth_db):"
    echo "  $0 20260806_143000 auth_db --overwrite-original"
    exit 1
}

[ $# -lt 2 ] && usage

TIMESTAMP="$1"
DB_NAME="$2"
OVERWRITE_FLAG="${3:-}"
DUMP_FILE="backups/${TIMESTAMP}/${DB_NAME}.dump"

[ -f "$DUMP_FILE" ] || { echo "Backup file not found: $DUMP_FILE"; exit 1; }

if [ "$OVERWRITE_FLAG" == "--overwrite-original" ]; then
    TARGET_DB="$DB_NAME"
    echo "WARNING: this will overwrite the REAL database '${TARGET_DB}' with the"
    echo "backup from ${TIMESTAMP}. Current data in it will be lost."
    read -p "Type the database name to confirm: " CONFIRM
    [ "$CONFIRM" == "$DB_NAME" ] || { echo "Confirmation did not match - aborting."; exit 1; }
else
    TARGET_DB="${DB_NAME}_restore_test"
    echo "Restoring into a NEW test database: ${TARGET_DB} (the real '${DB_NAME}' is untouched)"
    docker compose exec -T postgres psql -U hvac -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};"
    docker compose exec -T postgres psql -U hvac -d postgres -c "CREATE DATABASE ${TARGET_DB};"
fi

cat "$DUMP_FILE" | docker compose exec -T postgres pg_restore -U hvac -d "$TARGET_DB" --clean --if-exists --no-owner

echo "Restore complete into: ${TARGET_DB}"
