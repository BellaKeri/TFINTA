#!/usr/bin/env bash
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# https://coverage.readthedocs.io/
#

poetry run python3 -m coverage run --omit=__init__.py,*_test.py,*_tests.py,*/dist-packages/*,*/site-packages/*,*/tests/* -m pytest
poetry run python3 -m coverage report -m
poetry run python3 -m coverage html
