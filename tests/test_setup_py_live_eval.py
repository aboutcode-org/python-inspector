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

import pytest

from python_inspector.setup_py_live_eval import iter_requirements

REQ = abspath(join(dirname(__file__), "./data/requirements.devel.txt"))


@pytest.mark.parametrize(
    "setup_py",
    [
        abspath(join(dirname(__file__), "./data/setup.txt")),
        abspath(join(dirname(__file__), "./data/setup-qualifiedfct.txt")),
    ],
)
def test_iter_requirements_with_setup_py(setup_py):
    """Test requirements-builder."""
    # Min
    assert list(iter_requirements("min", [], setup_py)) == ["click==6.1.0", "mock==1.3.0"]

    # PyPI
    assert list(iter_requirements("pypi", [], setup_py)) == ["click>=6.1.0", "mock>=1.3.0"]

    # Dev
    assert list(iter_requirements("dev", [], setup_py)) == ["click>=6.1.0", "mock>=1.3.0"]


@pytest.mark.parametrize(
    "setup_py",
    [
        abspath(join(dirname(__file__), "./data/setup-distutils.txt")),
        abspath(join(dirname(__file__), "./data/setup-distutils-qualifiedfct.txt")),
        abspath(join(dirname(__file__), "./data/setup-distutils-asnames.txt")),
    ],
)
def test_iter_requirements_with_setup_py_noreqs(setup_py):
    """Test against setup.py files which import setup in different ways"""
    # Min
    assert list(iter_requirements("min", [], setup_py)) == []

    # PyPI
    assert list(iter_requirements("pypi", [], setup_py)) == []

    # Dev
    assert list(iter_requirements("dev", [], setup_py)) == []
