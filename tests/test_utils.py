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
import collections
import json
import os
import sys
from netrc import netrc
from unittest import mock

import pytest
from commoncode.testcase import FileDrivenTesting
from test_cli import check_json_file_results

from _packagedcode.pypi import SetupCfgHandler
from python_inspector.resolution import fetch_and_extract_sdist
from python_inspector.utils import get_netrc_auth
from python_inspector.utils_pypi import PypiSimpleRepository
from python_inspector.utils_pypi import valid_python_version

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")

Candidate = collections.namedtuple("Candidate", "name version extras")


def test_get_netrc_auth():
    netrc_file = test_env.get_test_loc("test.netrc")
    parsed_netrc = netrc(netrc_file)
    assert get_netrc_auth(url="https://pyp1.org/simple", netrc=parsed_netrc) == ("test", "test123")
    assert get_netrc_auth(url="https://pyp1.org/different/path", netrc=parsed_netrc) == (
        "test",
        "test123",
    )
    assert get_netrc_auth(url="https://pyp1.org", netrc=parsed_netrc) == ("test", "test123")


def test_get_netrc_auth_with_ports_and_schemes():
    netrc_file = test_env.get_test_loc("test.netrc")
    parsed_netrc = netrc(netrc_file)

    assert get_netrc_auth(url="https://pyp1.org:443/path", netrc=parsed_netrc) == (
        "test",
        "test123",
    )
    assert get_netrc_auth(url="http://pyp1.org:80/simple", netrc=parsed_netrc) == (
        "test",
        "test123",
    )


def test_get_commented_netrc_auth():
    netrc_file = test_env.get_test_loc("test-commented.netrc")
    parsed_netrc = netrc(netrc_file)
    assert get_netrc_auth(url="https://pyp2.org/simple", netrc=parsed_netrc) == ("test", "test123")


def test_get_netrc_auth_with_no_matching_url():
    netrc_file = test_env.get_test_loc("test.netrc")
    parsed_netrc = netrc(netrc_file)
    assert get_netrc_auth(url="https://pypi2.org/simple", netrc=parsed_netrc) == (None, None)


def test_get_netrc_auth_with_with_subdomains():
    netrc_file = test_env.get_test_loc("test.netrc")
    parsed_netrc = netrc(netrc_file)

    assert get_netrc_auth(url="https://subdomain.example.com/simple", netrc=parsed_netrc) == (
        "subdomain-user",
        "subdomain-secret",
    )
    assert get_netrc_auth(url="https://another.example.com/simple", netrc=parsed_netrc) == (
        None,
        None,
    )


def test_get_netrc_auth_with_default():
    netrc_file = test_env.get_test_loc("test-default.netrc")
    parsed_netrc = netrc(netrc_file)

    assert get_netrc_auth(url="https://example.com/simple", netrc=parsed_netrc) == (
        "test",
        "test123",
    )
    assert get_netrc_auth(url="https://non-existing.org/simple", netrc=parsed_netrc) == (
        "defaultuser",
        "defaultpass",
    )


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
@mock.patch("python_inspector.utils_pypi.CACHE.get")
async def test_fetch_links(mock_get):
    file_name = test_env.get_test_loc("psycopg2.html")
    with open(file_name) as file:
        mock_get.return_value = file.read(), file_name
    links = await PypiSimpleRepository().fetch_links(normalized_name="psycopg2")
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("psycopg2-links-expected.json", must_exist=False)
    with open(result_file, "w") as file:
        json.dump(links, file, indent=4)
    check_json_file_results(result_file, expected_file)
    # Testing relative links
    relative_links_file = test_env.get_test_loc("fetch_links_test.html")
    with open(relative_links_file) as relative_file:
        mock_get.return_value = relative_file.read(), relative_links_file
    relative_links = await PypiSimpleRepository().fetch_links(normalized_name="sources.whl")
    relative_links_result_file = test_env.get_temp_file("json")
    relative_links_expected_file = test_env.get_test_loc(
        "relative-links-expected.json", must_exist=False
    )
    with open(relative_links_result_file, "w") as file:
        json.dump(relative_links, file, indent=4)
    check_json_file_results(relative_links_result_file, relative_links_expected_file)


def test_parse_reqs():
    results = [
        package.to_dict() for package in SetupCfgHandler.parse(test_env.get_test_loc("setup.cfg"))
    ]
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc("parse-reqs.json", must_exist=False)
    with open(result_file, "w") as file:
        json.dump(results, file, indent=4)
    check_json_file_results(result_file, expected_file)


@pytest.mark.online
@pytest.mark.asyncio
async def test_get_sdist_file():
    sdist_file = await fetch_and_extract_sdist(
        repos=tuple([PypiSimpleRepository()]),
        candidate=Candidate(name="psycopg2", version="2.7.5", extras=None),
        python_version="3.8",
    )
    assert os.path.basename(os.path.normpath(sdist_file)) == "psycopg2-2.7.5"


def test_parse_reqs_with_setup_requires_and_python_requires():
    results = [
        package.to_dict()
        for package in SetupCfgHandler.parse(
            test_env.get_test_loc("setup_with_setup_requires_and_python_requires.cfg")
        )
    ]
    result_file = test_env.get_temp_file("json")
    expected_file = test_env.get_test_loc(
        "parse-reqs-with-setup_requires-and-python-requires.json", must_exist=False
    )
    with open(result_file, "w") as file:
        json.dump(results, file, indent=4)
    check_json_file_results(result_file, expected_file)


def test_valid_python_version():
    assert valid_python_version("3.8", ">3.1")
    assert not valid_python_version("3.8.1", ">3.9")
