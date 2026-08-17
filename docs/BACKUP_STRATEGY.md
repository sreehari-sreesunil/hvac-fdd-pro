# Postgres Backup Strategy

## What this covers

`scripts/backup_postgres.sh` dumps each of the 6 service databases
(`auth_db`, `asset_db`, `telemetry_db`, `ml_service_db`,
`notification_db`, `copilot_service_db`) individually, in Postgres's
custom format (`-Fc`) - compressed, and restorable selectively or in
parallel, unlike a plain-SQL dump.

**Per-database, not a single `pg_dumpall`** - this matches the
project's own per-service-database architecture
(`init-scripts/init-multiple-dbs.sh`): if one service's data needs to
be restored (e.g. after a bad migration), the other 5 databases don't
need to be touched. A single `pg_dumpall` would only ever let you
restore everything at once.

Backups land in `backups/<timestamp>/<db_name>.dump`, gitignored -
these are real (or real-shaped) data dumps and must never be
committed, the same reasoning as `.env` already being gitignored for
secrets.

`scripts/restore_postgres.sh` restores one database from one backup.
**Defaults to a safe target**: restoring `auth_db` from a backup
creates and restores into `auth_db_restore_test`, leaving the real
`auth_db` untouched - overwriting the real database requires an
explicit `--overwrite-original` flag AND typing the database name to
confirm. This is a deliberate choice: a backup/restore script is
exactly the kind of thing someone runs during a stressful real
incident, and the easy, default path should not be the destructive
one.

## What this does NOT cover (real, stated gaps)

- **No off-site/redundant storage.** Backups land on the same machine
  running the database (`~/hvac-fdd-pro/backups/` on the production
  VM). A real disaster (disk failure, the whole machine being lost)
  would take the backups down with the database they're meant to
  protect. Deliberately deferred, not overlooked: real off-site
  storage (object storage, a separate host) is a legitimate next step
  for a production business with real customer data at stake, but
  isn't proportionate to add for this project's current stage.
- **No encryption at rest for the backup files themselves.** They
  contain the same data as the live database - anyone with filesystem
  access to `backups/` has the same access a database breach would
  give them.
- **Not tested under real production load/size.** This has been
  tested against this project's actual current data (see the
  verification log below), which is real but small. Restore time and
  dump size at real production data volumes are unverified.

These are honestly out of scope for this project's current stage -
listed here so they're a known, deliberate gap, not a silent one.

## Real deployment status

As of the first live deployment (`plenumcontrol.in`, see
`docs/DEPLOYMENT_RUNBOOK.md`), this script runs on a real cron
schedule on the production server - daily at 03:00 server time,
logging to `backup.log`:

```bash
0 3 * * * cd /home/<user>/hvac-fdd-pro && ./scripts/backup_postgres.sh >> /home/<user>/hvac-fdd-pro/backup.log 2>&1
```

Verified working: ran manually against the real production database
before scheduling, confirmed all 6 real database dumps were created
successfully.

## How to back up

```bash
./scripts/backup_postgres.sh
```

Dumps all 6 databases into a new timestamped directory under
`backups/`, and prunes old backup directories beyond the last 5 kept.

## How to restore

**Safe (default) - restores into a new test database, real data untouched:**
```bash
./scripts/restore_postgres.sh 20260806_143000 auth_db
```

**Destructive - overwrites the real database, requires confirmation:**
```bash
./scripts/restore_postgres.sh 20260806_143000 auth_db --overwrite-original
```
