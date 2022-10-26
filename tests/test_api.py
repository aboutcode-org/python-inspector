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

from commoncode.testcase import FileDrivenTesting

from python_inspector.resolve_cli import resolver_api
from tests.test_cli import check_json_results

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
