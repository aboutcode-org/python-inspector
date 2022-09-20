# -*- coding: utf-8 -*-
#
# This file is part of Requirements-Builder
# Copyright (C) 2015 CERN.
#
# Requirements-Builder is free software; you can redistribute it and/or
# modify it under the terms of the Revised BSD License; see LICENSE
# file for more details.
#
"""Tests for `requirements-builder` module."""

from os.path import abspath
from os.path import dirname
from os.path import join

from python_inspector.setup_py_live_eval import iter_requirements

REQ = abspath(join(dirname(__file__), "./data/requirements.devel.txt"))
SETUP = abspath(join(dirname(__file__), "./data/setup.txt"))


def test_iter_requirements_with_setup_py():
    """Test requirements-builder."""
    # Min
    assert list(iter_requirements("min", [], SETUP)) == ["click==6.1.0", "mock==1.3.0"]

    # PyPI
    assert list(iter_requirements("pypi", [], SETUP)) == ["click>=6.1.0", "mock>=1.3.0"]

    # Dev
    assert list(iter_requirements("dev", [], SETUP)) == ["click>=6.1.0", "mock>=1.3.0"]
