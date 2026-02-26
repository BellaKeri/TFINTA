#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
#
# migrate.sh – apply all numbered SQL migrations in order.
#
# Usage:
#   ./db/migrate.sh                         # uses defaults (localhost / tfinta / tfinta)
#   PGHOST=10.0.0.2 ./db/migrate.sh        # override host
#   PGPASSWORD=secret ./db/migrate.sh      # override password
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"

# Connection defaults (override with env vars)
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-tfinta}"
export PGUSER="${PGUSER:-tfinta}"
export PGPASSWORD="${PGPASSWORD:-tfinta}"

echo "==> Connecting to ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"

# Ensure schema_version table exists (idempotent)
psql -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS schema_version (
  version     INTEGER PRIMARY KEY,
  applied     TIMESTAMPTZ NOT NULL DEFAULT now(),
  description TEXT
);
SQL

# Apply each migration file in order
for migration in "${MIGRATIONS_DIR}"/[0-9]*.sql; do
  filename="$(basename "$migration")"
  version="${filename%%_*}"  # e.g. "001" from "001_initial_schema.sql"
  version_int=$((10#$version))  # strip leading zeros

  # Skip 000 (database bootstrap – must be run separately as superuser)
  if [ "$version_int" -eq 0 ]; then
    continue
  fi

  already=$(psql -tAc "SELECT 1 FROM schema_version WHERE version = ${version_int}" 2>/dev/null || true)
  if [ "$already" = "1" ]; then
    echo "    [skip] ${filename} (already applied)"
  else
    echo "    [apply] ${filename}"
    psql -v ON_ERROR_STOP=1 -f "$migration"
  fi
done

echo "==> Migrations complete."
