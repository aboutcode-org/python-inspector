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
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting

from python_inspector.resolve_cli import resolve_dependencies

# Used for tests to regenerate fixtures with regen=True
REGEN_TEST_FIXTURES = os.getenv("PYINSP_REGEN_TEST_FIXTURES", False)

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.online
def test_cli_with_default_urls():
    expected_file = test_env.get_test_loc("default-url-expected.json", must_exist=False)
    specifier = "zipp==3.8.0"
    extra_options = [
        "--use-pypi-json-api",
    ]
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_single_index_url():
    expected_file = test_env.get_test_loc("single-url-expected.json", must_exist=False)
    specifier = "zipp==3.8.0"
    extra_options = [
        "--index-url",
        "https://pypi.org/simple",
    ]
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_multiple_index_url_and_tilde_req():
    expected_file = test_env.get_test_loc("tilde_req-expected.json", must_exist=False)
    specifier = "zipp~=3.8.0"
    extra_options = [
        "--index-url",
        "https://pypi.org/simple",
        "--index-url",
        "https://thirdparty.aboutcode.org/pypi/simple/",
    ]
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_pinned_requirements_file():
    requirements_file = test_env.get_test_loc("pinned-requirements.txt")
    expected_file = test_env.get_test_loc("pinned-requirements.txt-expected.json", must_exist=False)
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
    )


def check_specs_resolution(
    specifier,
    expected_file,
    extra_options=tuple(),
    regen=REGEN_TEST_FIXTURES,
):
    result_file = test_env.get_temp_file("json")
    options = ["--specifier", specifier, "--json", result_file]
    options.extend(extra_options)
    run_cli(options=options)
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        regen=regen,
    )


def check_requirements_resolution(
    requirements_file,
    expected_file,
    extra_options=tuple(),
    regen=REGEN_TEST_FIXTURES,
):
    result_file = test_env.get_temp_file("json")
    options = ["--requirement", requirements_file, "--json", result_file]
    options.extend(extra_options)
    run_cli(options=options)
    check_json_results(
        result_file=result_file,
        expected_file=expected_file,
        regen=regen,
    )


def check_json_results(result_file, expected_file, clean=True, regen=REGEN_TEST_FIXTURES):
    """
    Check the ``result_file`` JSON results against the ``expected_file``
    expected JSON results.

    If ``clean`` is True, remove headers data that can change across runs to
    provide stable test resultys.

    If ``regen`` is True the expected_file WILL BE overwritten with the new
    results from ``results_file``. This is convenient for updating tests
    expectations.
    """
    with open(result_file) as res:
        results = json.load(res)

    if clean:
        clean_results(results)

    if regen:
        with open(expected_file, "w") as reg:
            json.dump(results, reg, indent=2, separators=(",", ": "))
        expected = results
    else:
        with open(expected_file) as res:
            expected = json.load(res)

            if clean:
                clean_results(expected)

    assert results == expected


def clean_results(results):
    """
    Return cleaned results removing transient values that can change across test
    runs.
    """
    headers = results.get("headers", {})
    options = headers.get("options", [])
    headers["options"] = [o for o in options if not o.startswith("--requirement")]
    return results


def run_cli(options, cli=resolve_dependencies, expected_rc=0, env=None):
    """
    Run a command line resolution. Return a click.testing.Result object.
    """

    if not env:
        env = dict(os.environ)

    runner = CliRunner()
    result = runner.invoke(cli, options, catch_exceptions=False, env=env)

    if result.exit_code != expected_rc:
        output = result.output
        error = f"""
Failure to run:
rc: {result.exit_code}
python-inspector {options}
output:
{output}
"""
        assert result.exit_code == expected_rc, error
    return result
