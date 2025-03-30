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
import os
from unittest.mock import patch

import packvers
import pytest
from commoncode.system import on_mac
from commoncode.testcase import FileDrivenTesting
from packvers.requirements import Requirement

from _packagedcode import models
from python_inspector.api import get_resolved_dependencies
from python_inspector.error import NoVersionsFound
from python_inspector.resolution import PythonInputProvider
from python_inspector.resolution import get_requirements_from_dependencies
from python_inspector.resolution import get_requirements_from_python_manifest
from python_inspector.resolution import is_valid_version
from python_inspector.resolution import parse_reqs_from_setup_py_insecurely
from python_inspector.utils_pypi import PYPI_PUBLIC_REPO
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository

setup_test_env = FileDrivenTesting()
setup_test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310():
    req = Requirement("flask==2.1.2")
    req.is_requirement_resolved = True
    _, plist = get_resolved_dependencies(
        requirements=[req],
        environment=Environment(
            python_version="310",
            operating_system="linux",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    assert plist == [
        "pkg:pypi/click@8.1.8",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/itsdangerous@2.2.0",
        "pkg:pypi/jinja2@3.1.6",
        "pkg:pypi/markupsafe@3.0.2",
        "pkg:pypi/werkzeug@3.1.3",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_310_windows():
    req = Requirement("flask==2.1.2")
    req.is_requirement_resolved = True
    _, plist = get_resolved_dependencies(
        requirements=[req],
        environment=Environment(
            python_version="310",
            operating_system="windows",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )
    assert plist == [
        "pkg:pypi/click@8.1.8",
        "pkg:pypi/colorama@0.4.6",
        "pkg:pypi/flask@2.1.2",
        "pkg:pypi/itsdangerous@2.2.0",
        "pkg:pypi/jinja2@3.1.6",
        "pkg:pypi/markupsafe@3.0.2",
        "pkg:pypi/werkzeug@3.1.3",
    ]


@pytest.mark.online
def test_get_resolved_dependencies_with_flask_and_python_36():
    req = Requirement("flask")
    req.is_requirement_resolved = False
    _, plist = get_resolved_dependencies(
        requirements=[req],
        environment=Environment(
            python_version="36",
            operating_system="linux",
        ),
        repos=[PYPI_PUBLIC_REPO],
        as_tree=False,
    )

    assert plist == [
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
    _, plist = get_resolved_dependencies(
        requirements=[req],
        as_tree=False,
        environment=Environment(
            python_version="38",
            operating_system="linux",
        ),
    )
    assert plist == [
        "pkg:pypi/click@8.1.8",
        "pkg:pypi/flask@2.1.3",
        "pkg:pypi/importlib-metadata@8.6.1",
        "pkg:pypi/itsdangerous@2.2.0",
        "pkg:pypi/jinja2@3.1.6",
        "pkg:pypi/markupsafe@3.0.2",
        "pkg:pypi/werkzeug@3.1.3",
        "pkg:pypi/zipp@3.21.0",
    ]


@pytest.mark.online
@pytest.mark.skipif(on_mac, reason="torch is only available for linux and windows.")
def test_get_resolved_dependencies_for_version_containing_local_version_identifier():
    req = Requirement("torch==2.0.0+cpu")
    req.is_requirement_resolved = True
    _, plist = get_resolved_dependencies(
        requirements=[req],
        environment=Environment(
            python_version="310",
            operating_system="linux",
        ),
        repos=[
            PypiSimpleRepository(index_url="https://download.pytorch.org/whl/cpu", credentials=None)
        ],
        as_tree=False,
    )

    assert plist == [
        "pkg:pypi/filelock@3.13.1",
        "pkg:pypi/jinja2@3.1.4",
        "pkg:pypi/markupsafe@2.1.5",
        "pkg:pypi/mpmath@1.3.0",
        "pkg:pypi/networkx@3.3",
        "pkg:pypi/sympy@1.13.1",
        "pkg:pypi/torch@2.0.0%2Bcpu",
        "pkg:pypi/typing-extensions@4.12.2",
    ]


@pytest.mark.online
def test_without_supported_wheels():
    req = Requirement("autobahn==22.3.2")
    req.is_requirement_resolved = True
    _, plist = get_resolved_dependencies(
        requirements=[req],
        as_tree=False,
        repos=[PYPI_PUBLIC_REPO],
        environment=Environment(
            python_version="38",
            operating_system="linux",
        ),
    )

    assert plist == [
        "pkg:pypi/autobahn@22.3.2",
        "pkg:pypi/cffi@1.17.1",
        "pkg:pypi/cryptography@44.0.2",
        "pkg:pypi/hyperlink@21.0.0",
        "pkg:pypi/idna@3.10",
        "pkg:pypi/pycparser@2.22",
        "pkg:pypi/setuptools@75.3.2",
        "pkg:pypi/txaio@23.1.1",
    ]


def test_is_valid_version():
    parsed_version = packvers.version.parse("2.1.2")
    requirements = {"flask": [Requirement("flask>2.0.0")]}
    bad_versions = []
    identifier = "flask"
    assert is_valid_version(parsed_version, requirements, identifier, bad_versions)


def test_is_valid_version_with_no_specifier():
    parsed_version = packvers.version.parse("2.1.2")
    requirements = {"flask": [Requirement("flask")]}
    bad_versions = []
    identifier = "flask"
    assert is_valid_version(parsed_version, requirements, identifier, bad_versions)


def test_is_valid_version_with_no_specifier_and_pre_release():
    parsed_version = packvers.version.parse("1.0.0b4")
    requirements = {"flask": [Requirement("flask")]}
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


def test_get_requirements_from_python_manifest_securely():
    sdist_location = "tests/data/secure-setup"
    setup_py_emptyrequires = "setup-emptyrequires.py"
    setup_py_norequires = "setup-norequires.py"
    setup_py_requires = "setup-requires.py"
    analyze_setup_py_insecurely = False
    try:
        ret = list(
            get_requirements_from_python_manifest(
                sdist_location,
                sdist_location + "/" + setup_py_norequires,
                [sdist_location + "/" + setup_py_norequires],
                analyze_setup_py_insecurely,
            )
        )
        assert ret == []
    except Exception:
        pytest.fail("Failure parsing setup.py where requirements are not provided.")
    try:
        ret = list(
            get_requirements_from_python_manifest(
                sdist_location,
                sdist_location + "/" + setup_py_emptyrequires,
                [sdist_location + "/" + setup_py_emptyrequires],
                analyze_setup_py_insecurely,
            )
        )
        assert ret == []
    except Exception:
        pytest.fail("Failure getting empty requirements securely from setup.py.")
    with pytest.raises(Exception):
        ret = list(
            get_requirements_from_python_manifest(
                sdist_location,
                sdist_location + "/" + setup_py_requires,
                [sdist_location + "/" + setup_py_requires],
                analyze_setup_py_insecurely,
            ).next()
        )


def test_setup_py_parsing_insecure():
    setup_py_file = setup_test_env.get_test_loc("insecure-setup/setup.py")
    reqs = [str(req) for req in list(parse_reqs_from_setup_py_insecurely(setup_py=setup_py_file))]
    assert reqs == ["isodate", "pyparsing", "six"]


def test_setup_py_parsing_insecure_testpkh():
    setup_py_file = setup_test_env.get_test_loc("insecure-setup-2/setup.py")
    reqs = [str(req) for req in list(parse_reqs_from_setup_py_insecurely(setup_py=setup_py_file))]
    assert reqs == [
        "CairoSVG<2.0.0,>=1.0.20",
        "click>=5.0.0",
        "invenio[auth,base,metadata]>=3.0.0",
        "invenio-records==1.0.*,>=1.0.0",
        "mock>=1.3.0",
    ]


@patch("python_inspector.resolution.PythonInputProvider.get_versions_for_package")
def test_iter_matches(mock_versions):
    mock_versions.return_value = []
    provider = PythonInputProvider()
    with pytest.raises(NoVersionsFound):
        list(provider._iter_matches("foo-bar", {"foo-bar": []}, {"foo-bar": []}))
