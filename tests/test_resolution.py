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

from _packagedcode import models
from python_inspector.resolution import get_requirements_from_dependencies
from python_inspector.resolution import get_resolved_dependencies
from python_inspector.resolution import is_valid_version
from python_inspector.utils_pypi import PYPI_PUBLIC_REPO
from python_inspector.utils_pypi import Environment


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310():
    req = Requirement("flask==2.1.2")
    req.is_requirement_resolved = True
    results = get_resolved_dependencies(
        requirements=[req],
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
        "pkg:pypi/werkzeug@2.2.1",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310_windows():
    req = Requirement("flask==2.1.2")
    req.is_requirement_resolved = True
    results = get_resolved_dependencies(
        requirements=[req],
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
        "pkg:pypi/werkzeug@2.2.1",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_36():
    req = Requirement("flask")
    req.is_requirement_resolved = False
    results = get_resolved_dependencies(
        requirements=[req],
        environment=Environment(
            python_version="36",
            operating_system="linux",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    as_list = [p["package"] for p in results]

    assert as_list == [
        "pkg:pypi/click@8.0.4",
        "pkg:pypi/dataclasses@0.8",
        "pkg:pypi/flask@2.0.3",
        "pkg:pypi/importlib-metadata@4.8.3",
        "pkg:pypi/itsdangerous@2.0.1",
        "pkg:pypi/jinja2@3.0.3",
        "pkg:pypi/markupsafe@2.0.1",
        "pkg:pypi/typing-extensions@4.1.1",
        "pkg:pypi/werkzeug@2.0.3",
        "pkg:pypi/zipp@3.6.0",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_tilde_requirement_using_json_api():
    req = Requirement("flask~=2.1.2")
    req.is_requirement_resolved = False
    results = get_resolved_dependencies(
        requirements=[req],
        as_tree=False,
        environment=Environment(
            python_version="38",
            operating_system="linux",
        ),
    )
    as_list = [p["package"] for p in results]
    assert as_list == [
        "pkg:pypi/click@8.1.3",
        "pkg:pypi/flask@2.1.3",
        "pkg:pypi/importlib-metadata@4.12.0",
        "pkg:pypi/itsdangerous@2.1.2",
        "pkg:pypi/jinja2@3.1.2",
        "pkg:pypi/markupsafe@2.1.1",
        "pkg:pypi/werkzeug@2.2.1",
        "pkg:pypi/zipp@3.8.1",
    ]


@pytest.mark.online
def test_without_supported_wheels():
    req = Requirement("autobahn==22.3.2")
    req.is_requirement_resolved = True
    results = get_resolved_dependencies(
        requirements=[req],
        as_tree=False,
        repos=[PYPI_PUBLIC_REPO],
        environment=Environment(
            python_version="38",
            operating_system="linux",
        ),
    )
    as_list = [p["package"] for p in results]

    assert as_list == [
        "pkg:pypi/autobahn@22.3.2",
        "pkg:pypi/cffi@1.15.1",
        "pkg:pypi/cryptography@37.0.4",
        "pkg:pypi/hyperlink@21.0.0",
        "pkg:pypi/idna@3.3",
        "pkg:pypi/pycparser@2.21",
        "pkg:pypi/setuptools@63.4.1",
        "pkg:pypi/txaio@22.2.1",
    ]


def test_is_valid_version():
    parsed_version = packaging.version.parse("2.1.2")
    requirements = {"flask": [Requirement("flask>2.0.0")]}
    bad_versions = []
    identifier = "flask"
    assert is_valid_version(parsed_version, requirements, identifier, bad_versions)


def test_get_requirements_from_dependencies():
    dependencies = [
        models.DependentPackage(
            purl="pkg:pypi/django",
            scope="install",
            is_runtime=True,
            is_optional=False,
            is_resolved=False,
            extracted_requirement="django>=1.11.11",
            extra_data=dict(
                is_editable=False,
                link=None,
                hash_options=[],
                is_constraint=False,
                is_archive=False,
                is_wheel=False,
                is_url=False,
                is_vcs_url=False,
                is_name_at_url=False,
                is_local_path=False,
            ),
        )
    ]

    requirements = [str(r) for r in get_requirements_from_dependencies(dependencies)]

    assert requirements == ["django>=1.11.11"]


def test_get_requirements_from_dependencies_with_empty_list():
    assert list(get_requirements_from_dependencies(dependencies=[])) == []


def test_get_requirements_from_dependencies_with_editable_requirements():
    dependencies = [
        models.DependentPackage(
            purl="pkg:pypi/django",
            scope="install",
            is_runtime=True,
            is_optional=False,
            is_resolved=False,
            extracted_requirement="django>=1.11.11",
            extra_data=dict(
                is_editable=True,
                link=None,
                hash_options=[],
                is_constraint=False,
                is_archive=False,
                is_wheel=False,
                is_url=False,
                is_vcs_url=False,
                is_name_at_url=False,
                is_local_path=False,
            ),
        )
    ]

    requirements = [str(r) for r in get_requirements_from_dependencies(dependencies)]

    assert requirements == []
