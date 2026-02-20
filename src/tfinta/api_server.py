# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Convenience entry-point for ``realtime-api`` console script.

Usage (via poetry):

    poetry run realtime-api run          # starts on 0.0.0.0:8080
    poetry run realtime-api run --port 9000

Or directly:

    uvicorn tfinta.api:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import dataclasses

import click
import typer
import uvicorn
from rich import console as rich_console
from transcrypto.cli import clibase
from transcrypto.utils import config as app_config
from transcrypto.utils import logging as tc_logging

from . import __version__
from . import tfinta_base as base


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class APIServerConfig(clibase.CLIConfig):
  """CLI global context, storing the configuration."""


_VERBOSITY_NAMES: dict[int, str] = {
  0: 'error',
  1: 'warning',
  2: 'info',
  3: 'debug',
}


# CLI app setup, this is an important object and can be imported elsewhere and called
app = typer.Typer(
  add_completion=True,
  no_args_is_help=True,
  help='realtime-api: Launch the TFINTA Realtime API server.',  # keep in sync with Main().help
  epilog=(
    'Example:\n\n\n\n'
    '# --- Run API ---\n\n'
    'poetry run realtime-api run  # starts on 0.0.0.0:8080\n'
    'poetry run realtime-api run --port 9000\n\n\n\n'
    '# --- Generate documentation ---\n\n'
    'poetry run realtime-api markdown > realtime-api.md\n\n'
  ),
)


def Run() -> None:  # pragma: no cover
  """Run the CLI."""
  app()


@app.callback(
  invoke_without_command=True,  # have only one; this is the "constructor"
  help='realtime-api: Launch the TFINTA Realtime API server.',  # keep message in sync with app.help
)
@clibase.CLIErrorGuard
def Main(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: click.Context,  # global context
  version: bool = typer.Option(False, '--version', help='Show version and exit.'),
  verbose: int = typer.Option(
    0,
    '-v',
    '--verbose',
    count=True,
    help='Verbosity (nothing=ERROR, -v=WARNING, -vv=INFO, -vvv=DEBUG).',
    min=0,
    max=3,
  ),
  color: bool | None = typer.Option(
    None,
    '--color/--no-color',
    help=(
      'Force enable/disable colored output (respects NO_COLOR env var if not provided). '
      'Defaults to having colors.'  # state default because None default means docs don't show it
    ),
  ),
) -> None:
  if version:
    typer.echo(__version__)
    raise typer.Exit(0)
  # initialize logging and get console
  console: rich_console.Console
  console, verbose, color = tc_logging.InitLogging(
    verbose,
    color=color,
    include_process=False,
  )
  # create context with the arguments we received.
  ctx.obj = APIServerConfig(
    console=console,
    verbose=verbose,
    color=color,
    appconfig=app_config.InitConfig(base.APP_NAME, base.CONFIG_FILE_NAME),
  )


@app.command(
  'run',
  help='Run the TFINTA Realtime API server.',
  epilog=('Example:\n\n\n\n$ poetry run realtime-api run\n\n<<starts the API server>>'),
)
@clibase.CLIErrorGuard
def APIRun(  # noqa: D103
  *,
  ctx: click.Context,
  host: str = typer.Option('0.0.0.0', '-h', '--host', help='Bind address, default "0.0.0.0"'),  # noqa: S104
  port: int = typer.Option(8080, '-p', '--port', help='Port, default 8080'),
  reload: bool = typer.Option(
    False, '--reload/--no-reload', help='Development auto-reload? (default: False)'
  ),
) -> None:  # documentation is help/epilog/args
  config: APIServerConfig = ctx.obj
  uvicorn.run(
    'tfinta.api:app',
    host=host,
    port=port,
    reload=reload,
    log_level=_VERBOSITY_NAMES[config.verbose],
  )


@app.command(
  'markdown',
  help='Emit Markdown docs for the CLI (see README.md section "Creating a New Version").',
  epilog=(
    'Example:\n\n\n\n$ poetry run realtime-api markdown > realtime-api.md\n\n<<saves CLI doc>>'
  ),
)
@clibase.CLIErrorGuard
def Markdown(*, ctx: click.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: APIServerConfig = ctx.obj
  config.console.print(clibase.GenerateTyperHelpMarkdown(app, prog_name='realtime-api'))
