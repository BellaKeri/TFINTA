-- SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
-- SPDX-License-Identifier: Apache-2.0
--
-- 001_initial_schema.sql
-- TFINTA Realtime DB - initial schema.
--
-- Run with:
--   psql -U tfinta -d tfinta -f db/migrations/001_initial_schema.sql
-- ---------------------------------------------------------------------------

BEGIN;

-- ===== schema_version tracking =============================================

CREATE TABLE IF NOT EXISTS schema_version (
  version   INTEGER PRIMARY KEY,
  applied   TIMESTAMPTZ NOT NULL DEFAULT now(),
  description TEXT
);

-- Guard: skip if this migration was already applied.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM schema_version WHERE version = 1) THEN
    RAISE NOTICE 'Migration 001 already applied - skipping.';
    RETURN;
  END IF;

  -- ===== stations ==========================================================

  CREATE TABLE stations (
    id          INTEGER       NOT NULL,
    code        VARCHAR(10)   NOT NULL,
    description TEXT          NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    alias       TEXT,
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
  );

  CREATE UNIQUE INDEX idx_stations_id ON stations (id);
  CREATE INDEX idx_stations_description ON stations (LOWER(description));
  CREATE INDEX idx_stations_alias ON stations (LOWER(alias)) WHERE alias IS NOT NULL;

  -- ===== running_trains ====================================================

  CREATE TABLE running_trains (
    code        VARCHAR(20)   NOT NULL,
    status      SMALLINT      NOT NULL,   -- 0=TERMINATED 1=NOT_YET_RUNNING 2=RUNNING
    day         DATE          NOT NULL,
    direction   TEXT          NOT NULL,
    message     TEXT          NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (code)
  );

  -- ===== station_board_lines ===============================================

  CREATE TABLE station_board_lines (
    station_code                VARCHAR(10)   NOT NULL,
    train_code                  TEXT          NOT NULL,
    origin_code                 VARCHAR(10)   NOT NULL,
    origin_name                 TEXT          NOT NULL,
    destination_code            VARCHAR(10)   NOT NULL,
    destination_name            TEXT          NOT NULL,
    trip_arrival_seconds        INTEGER,
    trip_departure_seconds      INTEGER,
    direction                   TEXT          NOT NULL,
    due_in_seconds              INTEGER,
    late                        INTEGER       NOT NULL,
    location_type               SMALLINT      NOT NULL,   -- 0=STOP 1=ORIGIN 2=DEST 3=TIMING 4=CREW
    status                      TEXT,
    train_type                  SMALLINT      NOT NULL DEFAULT 0,  -- 0=UNKNOWN 1=DMU 2=DART 3=ICR 4=LOCO
    last_location               TEXT,
    scheduled_arrival_seconds   INTEGER,
    scheduled_departure_seconds INTEGER,
    expected_arrival_seconds    INTEGER,
    expected_departure_seconds  INTEGER,
    updated_at                  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (station_code, train_code)
  );

  CREATE INDEX idx_sbl_station_code ON station_board_lines (station_code);

  -- ===== train_stops =======================================================

  CREATE TABLE train_stops (
    train_code                  TEXT          NOT NULL,
    station_order               INTEGER       NOT NULL,
    day                         DATE          NOT NULL,
    station_code                VARCHAR(10)   NOT NULL,
    station_name                TEXT,
    location_type               SMALLINT      NOT NULL,   -- same enum as station_board_lines
    stop_type                   SMALLINT      NOT NULL DEFAULT 0,  -- 0=UNKNOWN 1=CURRENT 2=NEXT
    auto_arrival                BOOLEAN       NOT NULL,
    auto_depart                 BOOLEAN       NOT NULL,
    scheduled_arrival_seconds   INTEGER,
    scheduled_departure_seconds INTEGER,
    expected_arrival_seconds    INTEGER,
    expected_departure_seconds  INTEGER,
    actual_arrival_seconds      INTEGER,
    actual_departure_seconds    INTEGER,
    updated_at                  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (train_code, station_order)
  );

  -- ===== record the migration ==============================================

  INSERT INTO schema_version (version, description)
  VALUES (1, 'Initial schema: stations, running_trains, station_board, train_movements');

END $$;

COMMIT;
