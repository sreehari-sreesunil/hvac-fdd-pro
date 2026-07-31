#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE asset_db;
    CREATE DATABASE telemetry_db;
    CREATE DATABASE ml_service_db;
    CREATE DATABASE notification_db;
    CREATE DATABASE copilot_service_db;
EOSQL
