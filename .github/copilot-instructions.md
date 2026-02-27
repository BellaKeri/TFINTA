# Copilot Instructions

This is `tfinta` (Transport for Ireland Data), a Python/Poetry toolkit for parsing and displaying
Irish public-transport datasets — GTFS schedules (bus, rail, ferry, Luas), Irish Rail DART
schedules, and live train movements. It includes 5 CLI tools and 2 FastAPI REST APIs (one live,
one PostgreSQL-backed) deployed to Google Cloud Run. Published on PyPI.

## Running Code and Tests

- All non-`make` commands should be run from the Poetry environment: `poetry run <command>`
- Five CLI apps:
  - `poetry run gtfs <command>` — GTFS schedule parsing
  - `poetry run dart <command>` — DART-specific schedule queries
  - `poetry run realtime <command>` — live Irish Rail XML feed
  - `poetry run realtime-api <command>` — FastAPI server (live data, port 8080)
  - `poetry run realtime-apidb <command>` — FastAPI server (DB-backed, port 8081)
- To run tests on a file: `poetry run pytest tests/<file>_test.py`

## Code Standards

### Required Before Each Commit

- Run `make test` to ensure all tests pass
- Run `make ci` runs everything, to ensure integration tests and linters pass, also to generate auto-generated code
- When adding new functionality, make sure you update the `README.md` and `CHANGELOG.md` files
- It is very important that the cloud deployment and maintenance instructions in `README.md` are always up to date, since this project is not only a library but also a live service

### Styling

- Zero lint errors or warnings
- Try to always keep line length under 100 characters
- All files must have a license header (e.g., `# SPDX-License-Identifier: Apache-2.0` for Python files, `<!-- SPDX-License-Identifier: Apache-2.0 -->` for Markdown files, etc)

- Use Python conventions, but note that:
  - Use 2 spaces for indentation
  - Always prefer single quotes (`'`) but use double quotes in docstrings (`"""`)
  - Google-style docstrings with complete type annotations in the `Args` and `Returns` sections
  - Methods and Classes must be named in CamelCase; test methods can be snake_case but must start with `test_`, but I prefer test methods to be in CamelCase as well as `testSomething`
  - Start private Classes, Methods, and fields with an underscore (`_`). Only make public what is strictly necessary, the rest keep private
  - Always use `from __future__ import annotations`
  - MyPy strict + Pyright strict + typeguard everywhere. Always add complete type annotations. Avoid creating typeguard exceptions in tests as much as possible.
  - Testfiles are `<module>_test.py`, NOT `test_<module>.py` and tests mirror source structure
  - Project selects `"ALL"` Ruff rules and adds just a few exceptions
  - Never import except at the top, not even for tests, not even for type checking: ALL imports at the top always (only acceptable exception is CLI modules imports to register commands)

### CLI Architecture

- Five independent Typer apps, each self-contained in its own module (flat structure, NO `cli/` subdirectory):
  - `gtfs` (gtfs.py): Parse national GTFS bundle. Commands: `read`, `print {basics,routes,stops,shapes,calendars,trips}`, `markdown`
  - `dart` (dart.py): DART-specific schedule queries. Commands: `read`, `print {calendars,stops,trips,station,trip,all}`, `markdown`
  - `realtime` (realtime.py): Live Irish Rail XML feed. Commands: `print {stations,running,station,train}`, `markdown`
  - `realtime-api` (api_server.py): Launch FastAPI live-data server. Commands: `run`, `markdown`
  - `realtime-apidb` (apidb_server.py): Launch FastAPI DB-backed server. Commands: `run`, `markdown`
- Each has a global callback (`@app.callback`) handling `--version`, `--verbose`, `--color`
- Every command receives `ctx: click.Context` and reads config via `config = ctx.obj`
- Every command is decorated with `@clibase.CLIErrorGuard` (from `transcrypto.cli.clibase`)

### FastAPI REST APIs

- `api.py`: Wraps live Irish Rail XML feed. Endpoints: `/health`, `/stations`, `/running`, `/station/{code}`, `/train/{code}`
- `apidb.py`: Same endpoints, backed by PostgreSQL. Uses Pydantic response models for OpenAPI docs
- Both use FastAPI lifespan for setup/teardown
- Deployed to Google Cloud Run (`europe-west1`)

### PostgreSQL Database

- `docker-compose.yml`: Local dev PostgreSQL 17
- `db/migrations/`: Numbered SQL migration files, applied via `db/migrate.sh`
- `db.py`: Connection pool (`psycopg` + `psycopg_pool`), all SQL queries
- Tables: `stations`, `running_trains`, `station_board_lines`, `train_stops`, `schema_version`
- Env vars: `TFINTA_DB_HOST`, `TFINTA_DB_PORT`, `TFINTA_DB_NAME`, `TFINTA_DB_USER`, `TFINTA_DB_PASSWORD`, `TFINTA_DB_MIN_CONN`, `TFINTA_DB_MAX_CONN`

### `transcrypto`

We try to use `transcrypto` utilities and helpers as much as possible:

- `from transcrypto.utils import logging as cli_logging` — Rich console singleton, `InitLogging()`, `Console()`, `ResetConsole()`
  - After this initialization, use `cli_logging.Console().print(...)` for all console output and plain `import logging; logging.info(...)` for all logging output
- `from transcrypto.utils import config as app_config` — config management, `InitConfig()`, `ResetConfig()`
- `from transcrypto.cli import clibase` — `CLIErrorGuard`, `CLIConfig`, `GenerateTyperHelpMarkdown()`

- Try to use `transcrypto` when possible, including for:
  - Base (`transcrypto.utils.base`): lots of conversions bytes/int/hex/str/etc
  - Human-friendly outputs: `transcrypto.utils.human`
  - Saving/loading configs, including encrypted: `transcrypto.utils.config`
  - Random: `transcrypto.utils.saferandom`
  - Simple statistical results: `transcrypto.utils.stats`
  - Timing: `transcrypto.utils.timer`
  - Encryption: `transcrypto.core.key` and `transcrypto.core.aes` are good starting points

### Key Domain Concepts

- `gtfs_data_model.py`: Full GTFS data model — `GTFSData` container, frozen dataclasses for Agency, Route, Trip, Stop, Calendar, Schedule, etc.
- `realtime_data_model.py`: Realtime data model — Station, RunningTrain, StationLine, TrainStop dataclasses + Pydantic models for API responses
- `tfinta_base.py`: Base constants (`APP_NAME`, `CONFIG_FILE_NAME`), custom types (`DayTime`, `DayRange`, `Point`), error classes
- Data sources: TFI GTFS CSV files (downloaded/cached), Irish Rail XML API (`api.irishrail.ie/realtime/`)

## Testing Patterns

- Test files are flat under `tests/` (no subdirectories), mirroring the flat source structure
- Shared test helpers (`FakeHTTPStream`, `FakeHTTPFile`, `AssertTable()`, `AssertPrettyPrint()`) live in `tests/util.py`
- Large pre-built test data fixtures in `tests/gtfs_data.py` and `tests/realtime_data.py`
- Test fixture files (GTFS CSVs, realtime XML) in `tests/data/`
- Use `@pytest.fixture(autouse=True)` to reset singletons (`cli_logging.ResetConsole()`, `app_config.ResetConfig()`) before each test
- CLI tests use `typer.testing.CliRunner().invoke(app, args)` for real CLI wiring
- API tests use `fastapi.testclient.TestClient` with `httpx`
- Use `unittest.mock.patch` to mock GTFS/DART constructors, HTTP requests, DB connections
- Mark tests with `@pytest.mark.slow`, `@pytest.mark.stochastic`, `@pytest.mark.integration` as appropriate
- Integration tests (`tests_integration/`) build a wheel, install into a temp venv, and run all 5 CLIs including API server smoke tests

## Repository Structure

- `CHANGELOG.md`: latest changes/releases
- `Makefile`: commands for testing, linting, Docker, DB, generating code, etc
- `gtfs.md` / `dart.md` / `realtime.md` / `realtime-api.md` / `realtime-apidb.md`: auto-generated CLI docs
- `pyproject.toml`: most important configurations live here
- `README.md`: main documentation
- `requirements.txt`: auto-generated file (by `make req` or `make ci`)
- `Dockerfile.api` / `Dockerfile.apidb`: Docker images for API servers
- `docker-compose.yml`: Local PostgreSQL dev stack
- `.github/`: Github configs and pipelines
- `.vscode/`: VSCode configs
- `db/`: Database migrations and PostgreSQL config
  - `db/migrations/`: Numbered SQL migration files
  - `db/migrate.sh`: Migration runner script
  - `db/postgresql-tfinta.conf`: PostgreSQL tuning config
- `deploy/gce/`: GCP Compute Engine deployment scripts
- `src/tfinta/`: Main source code (flat structure, no sub-packages)
  - `src/tfinta/__init__.py`: Version lives here (e.g., `__version__ = "2.2.0"`) and in `pyproject.toml` both
  - `src/tfinta/tfinta_base.py`: Base constants, types, error classes
  - `src/tfinta/gtfs_data_model.py`: GTFS data model (dataclasses + TypedDicts)
  - `src/tfinta/realtime_data_model.py`: Realtime data model (dataclasses + Pydantic)
  - `src/tfinta/gtfs.py`: GTFS CLI app
  - `src/tfinta/dart.py`: DART CLI app
  - `src/tfinta/realtime.py`: Realtime CLI app
  - `src/tfinta/api.py` / `src/tfinta/apidb.py`: FastAPI apps
  - `src/tfinta/api_server.py` / `src/tfinta/apidb_server.py`: Typer wrappers for API servers
  - `src/tfinta/db.py`: PostgreSQL connection pool and queries
- `tests/`: Unit tests (flat) + `util.py` + `gtfs_data.py` / `realtime_data.py` fixtures + `data/` fixture files
- `tests_integration/`: Integration tests (wheel build + install + smoke tests)
