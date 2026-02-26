-- SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
-- SPDX-License-Identifier: Apache-2.0
--
-- 000_create_database.sql
-- Bootstrap: create the tfinta database and role.
--
-- Run ONCE as a Postgres superuser (e.g. postgres):
--   psql -U postgres -f db/migrations/000_create_database.sql
-- ---------------------------------------------------------------------------

-- Create the application role (if it doesn't exist).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tfinta') THEN
    CREATE ROLE tfinta WITH LOGIN PASSWORD 'tfinta';
  END IF;
END $$;

-- Create the database (if it doesn't exist).
-- NOTE: CREATE DATABASE cannot run inside a transaction block, so this file
-- must be executed outside a BEGIN/COMMIT wrapper.
SELECT 'CREATE DATABASE tfinta OWNER tfinta'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'tfinta')
\gexec
