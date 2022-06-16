#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import packaging
import pytest
from packaging.requirements import Requirement

from python_inspector.resolution import get_resolved_dependencies
from python_inspector.resolution import is_valid_version
from python_inspector.utils_pypi import PYPI_PUBLIC_REPO
from python_inspector.utils_pypi import Environment


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310():
    req = [Requirement("flask==2.1.2")]
    results = get_resolved_dependencies(
        requirements=req,
        environment=Environment(
            python_version="310",
            operating_system="linux",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    as_list = [p["package"] for p in results]
    assert as_list == [
        "pkg:pypi/click@8.1.3",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/itsdangerous@2.1.2",
        "pkg:pypi/jinja2@3.1.2",
        "pkg:pypi/markupsafe@2.1.1",
        "pkg:pypi/werkzeug@2.1.2",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310_windows():
    req = [Requirement("flask==2.1.2")]
    results = get_resolved_dependencies(
        requirements=req,
        environment=Environment(
            python_version="310",
            operating_system="windows",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    as_list = [p["package"] for p in results]
    assert as_list == [
        "pkg:pypi/click@8.1.3",
        "pkg:pypi/colorama@0.4.5",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/itsdangerous@2.1.2",
        "pkg:pypi/jinja2@3.1.2",
        "pkg:pypi/markupsafe@2.1.1",
        "pkg:pypi/werkzeug@2.1.2",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_36():
    req = [Requirement("flask==2.1.2")]
    results = get_resolved_dependencies(
        requirements=req,
        environment=Environment(
            python_version="36",
            operating_system="linux",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    as_list = [p["package"] for p in results]

    assert as_list == [
        "pkg:pypi/click@8.1.3",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/importlib-metadata@4.11.4",
        "pkg:pypi/itsdangerous@2.1.2",
        "pkg:pypi/jinja2@3.1.2",
        "pkg:pypi/markupsafe@2.0.1",
        "pkg:pypi/typing-extensions@4.2.0",
        "pkg:pypi/werkzeug@2.1.2",
        "pkg:pypi/zipp@3.8.0",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_tilde_requirement_using_json_api():
    req = [Requirement("flask~=2.1.2")]
    results = get_resolved_dependencies(
        requirements=req,
        as_tree=False,
        environment=Environment(
            python_version="38",
            operating_system="linux",
        ),
    )
    as_list = [p["package"] for p in results]
    assert as_list == [
        "pkg:pypi/click@8.1.3",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/importlib-metadata@4.11.4",
        "pkg:pypi/itsdangerous@2.1.2",
        "pkg:pypi/jinja2@3.1.2",
        "pkg:pypi/markupsafe@2.1.1",
        "pkg:pypi/werkzeug@2.1.2",
        "pkg:pypi/zipp@3.8.0",
    ]


def test_is_valid_version():
    parsed_version = packaging.version.parse("2.1.2")
    requirements = {"flask": [Requirement("flask>2.0.0")]}
    bad_versions = []
    identifier = "flask"
    assert is_valid_version(parsed_version, requirements, identifier, bad_versions)
