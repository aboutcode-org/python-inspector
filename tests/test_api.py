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

import pytest
from commoncode.testcase import FileDrivenTesting
from test_cli import check_data_results

from python_inspector.api import resolver_api

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


def test_api_with_specifier():
    expected_file = test_env.get_test_loc("test-api-expected.json", must_exist=False)
    results = resolver_api(
        specifiers=["flask==2.1.2"],
        python_version="3.10",
        operating_system="linux",
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_specifier_pdt():
    expected_file = test_env.get_test_loc("test-api-pdt-expected.json", must_exist=False)
    results = resolver_api(
        specifiers=["flask==2.1.2"],
        python_version="3.10",
        operating_system="linux",
        pdt_output=True,
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_requirement_file():
    expected_file = test_env.get_test_loc("test-api-with-requirement-file.json", must_exist=False)
    results = resolver_api(
        python_version="3.10",
        operating_system="linux",
        requirement_files=[test_env.get_test_loc("frozen-requirements.txt")],
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_prefer_source():
    expected_file = test_env.get_test_loc("test-api-with-prefer-source.json", must_exist=False)
    results = resolver_api(
        specifiers=["flask==2.1.2"],
        python_version="3.10",
        operating_system="linux",
        prefer_source=True,
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_recursive_requirement_file():
    requirement_file = test_env.get_test_loc("recursive_requirements/r.txt")
    expected_file = test_env.get_test_loc(
        "test-api-with-recursive-requirement-file.json", must_exist=False
    )
    results = resolver_api(
        python_version="3.8",
        operating_system="linux",
        requirement_files=[requirement_file],
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_no_os():
    with pytest.raises(Exception):
        resolver_api(specifiers=["flask==2.1.2"], python_version="3.10")


def test_api_with_no_pyver():
    with pytest.raises(Exception):
        resolver_api(specifiers=["flask==2.1.2"], operating_system="linux")


def test_api_with_unsupported_os():
    with pytest.raises(ValueError):
        resolver_api(specifiers=["flask==2.1.2"], python_version="3.10", operating_system="foo-bar")


def test_api_with_wrong_pyver():
    with pytest.raises(ValueError):
        resolver_api(specifiers=["flask==2.1.2"], python_version="3.14", operating_system="linux")


def test_api_with_python_311():
    expected_file = test_env.get_test_loc("test-api-with-python-311.json", must_exist=False)
    results = resolver_api(
        specifiers=["flask==2.1.2"],
        python_version="3.11",
        operating_system="linux",
        prefer_source=True,
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_lief_python_312():
    expected_file = test_env.get_test_loc("test-api-with-lief-python-312.json", must_exist=False)
    results = resolver_api(
        specifiers=["lief==0.15.1"],
        python_version="3.12",
        operating_system="linux",
        prefer_source=True,
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)


def test_api_with_partial_setup_py():
    expected_file = test_env.get_test_loc("test-api-with-partial-setup-py.json", must_exist=False)
    results = resolver_api(
        python_version="3.11",
        operating_system="linux",
        setup_py_file=test_env.get_test_loc("partial-setup.py"),
        prefer_source=True,
        analyze_setup_py_insecurely=True,
    )
    check_data_results(results=results.to_dict(generic_paths=True), expected_file=expected_file)
