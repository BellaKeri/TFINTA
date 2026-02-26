# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0

.PHONY: install fmt lint type test integration cov flakes api docker docker-run apidb docker-apidb docker-apidb-run db-up db-down db-migrate precommit docs req ci

install:
	poetry install

fmt:
	poetry run ruff format .

lint:
	poetry run ruff check .

type:
	poetry run mypy src tests tests_integration

test:
	poetry run pytest -q tests

integration:
	poetry run pytest -q tests_integration

cov:
	poetry run pytest --typeguard-packages=tfinta --cov=src --cov-report=term-missing -q tests

flakes:
	poetry run pytest --flake-finder --flake-runs=100 -q tests

api:
	poetry run realtime-api run

docker:
	docker build  -f Dockerfile.api -t tfinta-api .

docker-run:
	docker run --rm -p 8080:8080 tfinta-api

apidb:
	poetry run uvicorn tfinta.apidb:app --reload --port 8081

docker-apidb:
	docker build -f Dockerfile.apidb -t tfinta-apidb .

docker-apidb-run:
	docker run --rm -p 8081:8081 -e TFINTA_DB_HOST=host.docker.internal tfinta-apidb

db-up:
	docker compose up -d

db-down:
	docker compose down

db-migrate:
	./db/migrate.sh

precommit:
	poetry run pre-commit run --all-files

# TODO: generate openapi.json automatically from realtime-api code, e.g. using FastAPI's built-in OpenAPI generation, instead of maintaining it manually
# https://tfinta-api-157394351650.europe-west1.run.app/openapi.json

docs:
	@echo "Generating gtfs.md & dart.md & realtime*.md..."
	poetry run gtfs markdown > gtfs.md
	poetry run dart markdown > dart.md
	poetry run realtime markdown > realtime.md
	poetry run realtime-api markdown > realtime-api.md

req:
	poetry export --format requirements.txt --without-hashes --output requirements.txt

ci: cov integration precommit docs req docker docker-apidb
	@echo "CI checks passed! Generated docs & requirements.txt & built docker images."
