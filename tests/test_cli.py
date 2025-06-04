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
import time
from os.path import dirname

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


def clear_environ():
    for k, v in os.environ.items():
        if k == "PYINSP_REGEN_TEST_FIXTURES":
            continue
        if "PYINSP" in k:
            print(f"deleting: {k}: {v}")
            os.unsetenv(k)


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
def test_cli_with_specs_with_no_install_requires():
    expected_file = test_env.get_test_loc("no-install-requires-expected.json", must_exist=False)
    specifier = "crontab==1.0.4"
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
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
        "--index-url",
        "https://pypi.org/simple/",
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
def test_cli_with_single_env_var_index_url_flag_override():
    # Click default is to override env vars via flag as shown here
    expected_file = test_env.get_test_loc("single-url-env-var-expected.json", must_exist=False)
    specifier = "zipp==3.8.0"
    os.environ["PYINSP_INDEX_URL"] = "https://thirdparty.aboutcode.org/pypi/simple/"
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
    os.unsetenv("PYINSP_INDEX_URL")


@pytest.mark.online
def test_cli_with_single_env_var_index_url_except_pypi_simple():
    expected_file = test_env.get_test_loc(
        "single-url-env-var-except-simple-expected.json", must_exist=False
    )
    # using flask since it's not present in thirdparty
    specifier = "flask"
    os.environ["PYINSP_INDEX_URL"] = "https://thirdparty.aboutcode.org/pypi/simple/"
    try:
        check_specs_resolution(
            specifier=specifier,
            expected_file=expected_file,
            extra_options=[],
            regen=REGEN_TEST_FIXTURES,
        )
    except Exception as e:
        assert "python_inspector.error.NoVersionsFound: This package does not exist: flask" in str(
            e
        )
    os.unsetenv("PYINSP_INDEX_URL")


@pytest.mark.online
def test_cli_with_multiple_env_var_index_url_and_tilde_req():
    expected_file = test_env.get_test_loc("tilde_req-expected-env.json", must_exist=False)
    specifier = "zipp~=3.8.0"
    os.environ["PYINSP_INDEX_URL"] = (
        "https://pypi.org/simple https://thirdparty.aboutcode.org/pypi/simple/"
    )
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=[],
        regen=REGEN_TEST_FIXTURES,
    )
    os.unsetenv("PYINSP_INDEX_URL")


@pytest.mark.online
def test_cli_with_single_env_var_index_url():
    expected_file = test_env.get_test_loc("single-url-env-var-expected.json", must_exist=False)
    specifier = "zipp==3.8.0"
    os.environ["PYINSP_INDEX_URL"] = "https://pypi.org/simple"
    check_specs_resolution(
        specifier=specifier,
        expected_file=expected_file,
        extra_options=[],
        regen=REGEN_TEST_FIXTURES,
    )
    os.unsetenv("PYINSP_INDEX_URL")


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
    expected_file = test_env.get_test_loc("tilde_req-expected-max-rounds.json", must_exist=False)
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
    expected_file = test_env.get_test_loc("tilde_req-expected-netrc.json", must_exist=False)
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


@pytest.mark.skipif(
    sys.version_info[:2] >= (3, 12),
    reason="Skipping test for Python 3.12+ because of "
    "https://github.com/aboutcode-org/python-inspector/issues/212"
    "to avoid error AttributeError: module 'configparser' has no attribute "
    "'SafeConfigParser'. Did you mean: 'RawConfigParser'?",
)
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
    rc, stdout, stderr = run_cli(options=options)
    assert "0.14.0" in stdout


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
    options = [
        "--specifier",
        "foo",
        "--json",
        "-",
        "--python-version",
        "38",
        "--operating-system",
        "",
    ]
    run_cli(options=options, expected_rc=2, get_env=False)


def test_passing_of_no_pyver():
    options = [
        "--specifier",
        "foo",
        "--json",
        "-",
        "--operating-system",
        "linux",
        "--python-version",
        "",
    ]
    run_cli(options=options, expected_rc=2, get_env=False)


def test_passing_of_wrong_pyver():
    options = ["--specifier", "foo", "--json", "-", "--python-version", "foo"]
    message = "Invalid value for '-p' / '--python-version'"
    rc, stdout, stderr = run_cli(options=options, expected_rc=2, get_env=False)
    assert message in stderr


def test_passing_of_unsupported_os():
    options = ["--specifier", "foo", "--json", "-", "--operating-system", "bar"]
    message = "Invalid value for '-o' / '--operating-system'"
    rc, stdout, stderr = run_cli(options=options, expected_rc=2, get_env=False)
    assert message in stderr


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
    rc, stdout, stderr = run_cli(options=options, expected_rc=expected_rc)
    if message:
        assert message in stderr
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
    results = clean_results(results)
    if regen:
        with open(expected_file, "w") as exo:
            json.dump(results, exo, indent=2, separators=(",", ": "))
        expected = results
    else:
        with open(expected_file) as reso:
            expected = json.load(reso)

    expected = clean_results(expected)

    assert results == expected


def clean_results(results):
    """
    Return cleaned data
    """
    if isinstance(results, dict) and "headers" in results:
        headers = results.get("headers", {}) or {}
        if "tool_version" in headers:
            del headers["tool_version"]
        options = headers.get("options", []) or []
        if "--verbose" in options:
            options.remove("--verbose")

    return results


def run_cli(
    options,
    expected_rc=0,
    env=None,
    get_env=True,
    retry=True,
):
    """
    Run a python-inspector command as a plain subprocess. Return results.
    """

    from commoncode.command import execute

    if not env:
        env = dict(os.environ)

    if get_env:
        options = append_os_and_pyver_options(options)

    if "--generic-paths" not in options:
        options.append("--generic-paths")

    root_dir = dirname(dirname(__file__))
    py_cmd = os.path.abspath(os.path.join(root_dir, "venv", "bin", "python-inspector"))
    rc, stdout, stderr = execute(
        cmd_loc=py_cmd,
        args=options,
        env=env,
    )

    if retry and rc != expected_rc:
        # wait and rerun in verbose mode to get more in the output
        time.sleep(1)
        if "--verbose" not in options:
            options.append("--verbose")
        rc, stdout, stderr = execute(
            cmd_loc=py_cmd,
            args=options,
            env=env,
        )

    if rc != expected_rc:
        opts = get_opts(options)
        error = f"""
Failure to run:
rc: {rc!r}
command: python-inspector {opts}
stdout:
{stdout}

stderr:
{stderr}
"""
        assert rc == expected_rc, error

    return rc, stdout, stderr


def get_opts(options):
    opts = [o if isinstance(o, str) else repr(o) for o in options]
    return " ".join(opts)
