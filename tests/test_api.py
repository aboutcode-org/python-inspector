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

import json
import os

import pytest
from commoncode.testcase import FileDrivenTesting
from test_cli import check_json_results

from python_inspector.resolve_cli import resolver_api

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


def test_api_with_specifier():
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("test-api-expected.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    specifiers=["flask==2.1.2"],
                    python_version="3.10",
                    operating_system="linux",
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_specifier_pdt():
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("test-api-pdt-expected.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    specifiers=["flask==2.1.2"],
                    python_version="3.10",
                    operating_system="linux",
                    pdt_output=True,
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_requirement_file():
    result_file = test_env.get_temp_file("json")
    requirement_file = test_env.get_test_loc("frozen-requirements.txt")
    expected_file = test_env.get_test_loc("test-api-with-requirement-file.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    python_version="3.10",
                    operating_system="linux",
                    requirement_files=[requirement_file],
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_prefer_source():
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("test-api-with-prefer-source.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    specifiers=["flask==2.1.2"],
                    python_version="3.10",
                    operating_system="linux",
                    prefer_source=True,
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_recursive_requirement_file():
    result_file = test_env.get_temp_file("json")
    requirement_file = test_env.get_test_loc("recursive_requirements/r.txt")
    expected_file = test_env.get_test_loc(
        "test-api-with-recursive-requirement-file.json", must_exist=False
    )
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    python_version="3.8",
                    operating_system="linux",
                    requirement_files=[requirement_file],
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_no_os():
    with pytest.raises(Exception) as e:
        resolver_api(
            specifiers=["flask==2.1.2"],
            python_version="3.10",
        )


def test_api_with_no_pyver():
    with pytest.raises(Exception) as e:
        resolver_api(
            specifiers=["flask==2.1.2"],
            operating_system="linux",
        )


def test_api_with_unsupported_os():
    with pytest.raises(ValueError) as e:
        resolver_api(
            specifiers=["flask==2.1.2"],
            python_version="3.10",
            operating_system="foo-bar",
        )


def test_api_with_wrong_pyver():
    with pytest.raises(ValueError) as e:
        resolver_api(
            specifiers=["flask==2.1.2"],
            python_version="3.12",
            operating_system="linux",
        )


def test_api_with_python_311():
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("test-api-with-python-311.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    specifiers=["flask==2.1.2"],
                    python_version="3.11",
                    operating_system="linux",
                    prefer_source=True,
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )


def test_api_with_partial_setup_py():
    result_file = test_env.get_temp_file("json")
    setup_py_file = test_env.get_test_loc("partial-setup.py")
    expected_file = test_env.get_test_loc("test-api-with-partial-setup-py.json", must_exist=False)
    with open(result_file, "w") as result:
        result.write(
            json.dumps(
                resolver_api(
                    python_version="3.11",
                    operating_system="linux",
                    setup_py_file=setup_py_file,
                    prefer_source=True,
                    analyze_setup_py_insecurely=True,
                ).to_dict()
            )
        )
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        clean=True,
    )
