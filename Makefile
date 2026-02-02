# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0

.PHONY: install fmt lint type test integration cov flakes precommit docs req ci

install:
	poetry install

fmt:
	poetry run ruff format .

lint:
	poetry run ruff check .

type:
	poetry run mypy src

test:
	poetry run pytest -q tests

integration:
	poetry run pytest -q tests_integration

cov:
	poetry run pytest --typeguard-packages=tfinta --cov=src --cov-report=term-missing -q tests

flakes:
	poetry run pytest --flake-finder --flake-runs=100 -q tests

precommit:
	poetry run pre-commit run --all-files

docs:
	@echo "Generating dart.md"
	poetry run dart markdown > dart.md

req:
	poetry export --format requirements.txt --without-hashes --output requirements.txt

ci: cov integration precommit docs req
	@echo "CI checks passed! Generated docs & requirements.txt."
