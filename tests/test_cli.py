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
import sys

import pytest
from click.testing import CliRunner
from commoncode.testcase import FileDrivenTesting

from python_inspector.resolve_cli import resolve_dependencies

# Used for tests to regenerate fixtures with regen=True
REGEN_TEST_FIXTURES = os.getenv("PYINSP_REGEN_TEST_FIXTURES", False)

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")
setup_test_env = FileDrivenTesting()
setup_test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data", "setup")


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
def test_cli_with_requirements_and_ignore_errors():
    requirements_file = test_env.get_test_loc("error-requirements.txt")
    expected_file = test_env.get_test_loc(
        "example-requirements-ignore-errors-expected.json", must_exist=False
    )
    extra_options = [
        "--ignore-errors",
        "--operating-system",
        "linux",
        "--python-version",
        "310",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_pdt_output():
    requirements_file = test_env.get_test_loc("pdt-requirements.txt")
    expected_file = test_env.get_test_loc("pdt-requirements.txt-expected.json", must_exist=False)
    extra_options = []
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        pdt_output=True,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_pdt_output_with_pinned_requirements():
    requirements_file = test_env.get_test_loc("pinned-pdt-requirements.txt")
    expected_file = test_env.get_test_loc(
        "pinned-pdt-requirements.txt-expected.json", must_exist=False
    )
    extra_options = []
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        pdt_output=True,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_pdt_output_with_frozen_requirements():
    requirements_file = test_env.get_test_loc("frozen-requirements.txt")
    expected_file = test_env.get_test_loc("frozen-requirements.txt-expected.json", must_exist=False)
    extra_options = []
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        pdt_output=True,
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
def test_cli_with_single_index_url_except_pypi_simple():
    expected_file = test_env.get_test_loc(
        "single-url-except-simple-expected.json", must_exist=False
    )
    # using flask since it's not present in thirdparty
    specifier = "flask"
    extra_options = [
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
def test_cli_with_environment_marker_and_complex_ranges():
    requirements_file = test_env.get_test_loc("environment-marker-test-requirements.txt")
    expected_file = test_env.get_test_loc(
        "environment-marker-test-requirements.txt-expected.json", must_exist=False
    )
    extra_options = [
        "--operating-system",
        "linux",
        "--python-version",
        "37",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        pdt_output=True,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_azure_devops_with_python_310():
    requirements_file = test_env.get_test_loc("azure-devops.req.txt")
    expected_file = test_env.get_test_loc("azure-devops.req-310-expected.json", must_exist=False)
    extra_options = [
        "--operating-system",
        "linux",
        "--python-version",
        "310",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_azure_devops_with_python_312():
    requirements_file = test_env.get_test_loc("azure-devops.req.txt")
    expected_file = test_env.get_test_loc("azure-devops.req-312-expected.json", must_exist=False)
    extra_options = [
        "--operating-system",
        "linux",
        "--python-version",
        "312",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_azure_devops_with_python_313():
    requirements_file = test_env.get_test_loc("azure-devops.req.txt")
    expected_file = test_env.get_test_loc("azure-devops.req-313-expected.json", must_exist=False)
    extra_options = [
        "--operating-system",
        "linux",
        "--python-version",
        "313",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_azure_devops_with_python_38():
    requirements_file = test_env.get_test_loc("azure-devops.req.txt")
    expected_file = test_env.get_test_loc("azure-devops.req-38-expected.json", must_exist=False)
    extra_options = [
        "--operating-system",
        "linux",
        "--python-version",
        "38",
    ]
    check_requirements_resolution(
        requirements_file=requirements_file,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_multiple_index_url_and_tilde_req_with_max_rounds():
    expected_file = test_env.get_test_loc("tilde_req-expected.json", must_exist=False)
    specifier = "zipp~=3.8.0"
    extra_options = [
        "--index-url",
        "https://pypi.org/simple",
        "--index-url",
        "https://thirdparty.aboutcode.org/pypi/simple/",
        "--max-rounds",
        "100",
    ]
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_multiple_index_url_and_tilde_req_and_netrc_file_without_matching_url():
    expected_file = test_env.get_test_loc("tilde_req-expected.json", must_exist=False)
    netrc_file = test_env.get_test_loc("test-commented.netrc", must_exist=False)
    specifier = "zipp~=3.8.0"
    extra_options = [
        "--index-url",
        "https://pypi.org/simple",
        "--index-url",
        "https://thirdparty.aboutcode.org/pypi/simple/",
        "--netrc",
        netrc_file,
    ]
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=extra_options,
        regen=REGEN_TEST_FIXTURES,
    )


@pytest.mark.online
def test_cli_with_prefer_source():
    expected_file = test_env.get_test_loc("prefer-source-expected.json", must_exist=False)
    specifier = "zipp==3.8.0"
    extra_options = ["--prefer-source"]
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


@pytest.mark.online
def test_cli_with_setup_py_failure():
    setup_py_file = setup_test_env.get_test_loc("simple-setup.py")
    expected_file = setup_test_env.get_test_loc("simple-setup.py-expected.json", must_exist=False)
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        expected_rc=1,
        message=f"Python version 3.8 is not compatible with setup.py {setup_py_file} python_requires >2, <=3",
    )


@pytest.mark.online
def test_cli_with_insecure_option():
    setup_py_file = setup_test_env.get_test_loc("spdx-setup.py")
    expected_file = setup_test_env.get_test_loc("spdx-setup.py-expected.json", must_exist=False)
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        extra_options=["--python-version", "27", "--analyze-setup-py-insecurely"],
        pdt_output=True,
    )


@pytest.mark.skipif(sys.version_info[:2] == (3, 12), reason="Skipping test for Python 3.12")
@pytest.mark.online
def test_cli_with_insecure_option_testpkh():
    setup_py_file = test_env.get_test_loc("insecure-setup-2/setup.py")
    expected_file = test_env.get_test_loc(
        "insecure-setup-2/setup.py-expected.json", must_exist=False
    )
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        extra_options=["--python-version", "27", "--analyze-setup-py-insecurely"],
    )


@pytest.mark.online
def test_cli_with_insecure_option_testrdflib():
    setup_py_file = test_env.get_test_loc("insecure-setup/setup.py")
    expected_file = test_env.get_test_loc("insecure-setup/setup.py-expected.json", must_exist=False)
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        extra_options=["--python-version", "27", "--analyze-setup-py-insecurely"],
    )


@pytest.mark.online
def test_cli_with_setup_py():
    setup_py_file = setup_test_env.get_test_loc("simple-setup.py")
    expected_file = setup_test_env.get_test_loc("simple-setup.py-expected.json", must_exist=False)
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        extra_options=["--python-version", "27"],
    )


@pytest.mark.online
def test_cli_with_setup_py_no_direct_dependencies():
    setup_py_file = setup_test_env.get_test_loc("no-direct-dependencies-setup.py")
    expected_file = setup_test_env.get_test_loc(
        "no-direct-dependencies-setup.py-expected.json", must_exist=False
    )
    check_setup_py_resolution(
        setup_py=setup_py_file,
        expected_file=expected_file,
        regen=REGEN_TEST_FIXTURES,
        extra_options=["--python-version", "27", "--analyze-setup-py-insecurely"],
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
    check_json_file_results(
        result_file=result_file,
        expected_file=expected_file,
        regen=regen,
    )


def append_os_and_pyver_options(options):
    if "--python-version" not in options:
        options.extend(["--python-version", "38"])
    if "--operating-system" not in options:
        options.extend(["--operating-system", "linux"])
    return options


def test_passing_of_json_pdt_and_json_flags():
    result_file = test_env.get_temp_file("json")
    options = ["--specifier", "foo", "--json", result_file, "--json-pdt", result_file]
    run_cli(options=options, expected_rc=1)


def test_version_option():
    options = ["--version"]
    result = run_cli(options=options)
    assert "0.13.0" in result.output


def test_passing_of_netrc_file_that_does_not_exist():
    options = ["--specifier", "foo", "--netrc", "bar.txt", "--json", "-"]
    run_cli(options=options, expected_rc=2)


def test_passing_of_empty_requirements_file():
    test_file = test_env.get_temp_file(file_name="pdt.txt", extension="")
    with open(test_file, "w") as f:
        f.write("")
    test_file_2 = test_env.get_temp_file(file_name="setup.py", extension="")
    with open(test_file_2, "w") as f:
        f.write("")
    options = ["--requirement", test_file, "--json", "-", "--requirement", test_file_2]
    run_cli(options=options, expected_rc=0)


def test_passing_of_no_json_output_flag():
    options = ["--specifier", "foo"]
    run_cli(options=options, expected_rc=1)


def test_passing_of_no_os():
    options = ["--specifier", "foo", "--json", "-", "--python-version", "38"]
    run_cli(options=options, expected_rc=2, get_env=False)


def test_passing_of_no_pyver():
    options = ["--specifier", "foo", "--json", "-", "--operating-system", "linux"]
    run_cli(options=options, expected_rc=2, get_env=False)


def test_passing_of_wrong_pyver():
    options = ["--specifier", "foo", "--json", "-", "--python-version", "foo"]
    message = "Invalid value for '-p' / '--python-version'"
    result = run_cli(options=options, expected_rc=2, get_env=False)
    if message:
        assert message in result.output


def test_passing_of_unsupported_os():
    options = ["--specifier", "foo", "--json", "-", "--operating-system", "bar"]
    message = "Invalid value for '-o' / '--operating-system'"
    result = run_cli(options=options, expected_rc=2, get_env=False)
    if message:
        assert message in result.output


def check_requirements_resolution(
    requirements_file,
    expected_file,
    extra_options=tuple(),
    regen=REGEN_TEST_FIXTURES,
    pdt_output=False,
):
    result_file = test_env.get_temp_file("json")
    if pdt_output:
        options = ["--requirement", requirements_file, "--json-pdt", result_file]
    else:
        options = ["--requirement", requirements_file, "--json", result_file]
    options.extend(extra_options)
    run_cli(options=options)
    check_json_file_results(result_file=result_file, expected_file=expected_file, regen=regen)


def check_setup_py_resolution(
    setup_py,
    expected_file,
    extra_options=tuple(),
    regen=REGEN_TEST_FIXTURES,
    pdt_output=False,
    expected_rc=0,
    message="",
):
    result_file = setup_test_env.get_temp_file(file_name="json")
    if pdt_output:
        options = ["--setup-py", setup_py, "--json-pdt", result_file]
    else:
        options = ["--setup-py", setup_py, "--json", result_file]
    options.extend(extra_options)
    result = run_cli(options=options, expected_rc=expected_rc)
    if message:
        assert message in result.output
    if expected_rc == 0:
        check_json_file_results(result_file=result_file, expected_file=expected_file, regen=regen)


def check_json_file_results(result_file, expected_file, regen=REGEN_TEST_FIXTURES):
    """
    Check the ``result_file`` JSON results against the ``expected_file``
    expected JSON results.

    If ``regen`` is True the expected_file WILL BE overwritten with the new
    results from ``results_file``. This is convenient for updating tests
    expectations.
    """
    with open(result_file) as resi:
        results = json.load(resi)
    check_data_results(results, expected_file, regen)


def check_data_results(results, expected_file, regen=REGEN_TEST_FIXTURES):
    """
    Check the ``results`` data against the ``expected_file`` expected JSON results.

    If ``regen`` is True the expected_file WILL BE overwritten with the new
    results from ``results_file``. This is convenient for updating tests
    expectations.
    """
    if regen:
        with open(expected_file, "w") as exo:
            json.dump(results, exo, indent=2, separators=(",", ": "))
        expected = results
    else:
        with open(expected_file) as reso:
            expected = json.load(reso)
    assert results == expected


def run_cli(options, cli=resolve_dependencies, expected_rc=0, env=None, get_env=True):
    """
    Run a command line resolution. Return a click.testing.Result object.
    """

    if not env:
        env = dict(os.environ)

    runner = CliRunner()
    if get_env:
        options = append_os_and_pyver_options(options)

    if "--generic-paths" not in options:
        options.append("--generic-paths")

    result = runner.invoke(cli, options, catch_exceptions=False, env=env)

    if result.exit_code != expected_rc:
        output = result.output
        opts = " ".join(options)
        error = f"""
Failure to run:
rc: {result.exit_code}
python-inspector {opts}
output:
{output}
"""
        assert result.exit_code == expected_rc, error
    return result
