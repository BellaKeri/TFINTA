# SPDX-FileCopyrightText: 2026 BellaKeri (BellaKeri@github.com) & D. Balparda <balparda@github.com>
# SPDX-License-Identifier: Apache-2.0
"""pytest configurations."""

from __future__ import annotations

import pytest
from typeguard import install_import_hook


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config) -> None:  # type:ignore  # pylint: disable=unused-argument
  """Configure pytest to use typeguard for type checking."""
  install_import_hook('src.tfinta')
