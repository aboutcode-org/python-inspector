#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from unittest import mock

import pytest
from commoncode.testcase import FileDrivenTesting
from test_cli import check_data_results

from python_inspector.package_data import get_pypi_data_from_purl
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.asyncio
@mock.patch("python_inspector.package_data.get_sdist_download_url")
@mock.patch("python_inspector.package_data.get_wheel_download_urls")
@mock.patch("python_inspector.utils.get_response_async")
async def test_get_pypi_data_from_purl_tries_repos_in_order(
    mock_get_response, mock_get_wheels, mock_get_sdist
):
    mock_get_sdist.return_value = None
    mock_get_wheels.return_value = []

    call_urls = []

    async def track_calls(url):
        call_urls.append(url)
        return None

    mock_get_response.side_effect = track_calls

    repo1 = PypiSimpleRepository(index_url="https://repo1.example.com/simple")
    repo2 = PypiSimpleRepository(index_url="https://repo2.example.com/simple")
    env = Environment(python_version="310", operating_system="linux")

    await get_pypi_data_from_purl(
        purl="pkg:pypi/requests@2.28.0",
        environment=env,
        repos=[repo1, repo2],
        prefer_source=False,
    )

    assert call_urls == [
        "https://repo1.example.com/pypi/requests/2.28.0/json",
        "https://repo2.example.com/pypi/requests/2.28.0/json",
        "https://pypi.org/pypi/requests/2.28.0/json",
    ]


@pytest.mark.asyncio
@mock.patch("python_inspector.package_data.get_sdist_download_url")
@mock.patch("python_inspector.package_data.get_wheel_download_urls")
@mock.patch("python_inspector.utils.get_response_async")
async def test_get_pypi_data_from_purl_stops_on_first_success(
    mock_get_response, mock_get_wheels, mock_get_sdist
):
    mock_get_sdist.return_value = None
    mock_get_wheels.return_value = []

    call_urls = []

    async def return_success_on_second(url):
        call_urls.append(url)
        if "repo2" in url:
            return {"info": {}, "urls": []}
        return None

    mock_get_response.side_effect = return_success_on_second

    repo1 = PypiSimpleRepository(index_url="https://repo1.example.com/simple")
    repo2 = PypiSimpleRepository(index_url="https://repo2.example.com/simple")
    env = Environment(python_version="310", operating_system="linux")

    await get_pypi_data_from_purl(
        purl="pkg:pypi/requests@2.28.0",
        environment=env,
        repos=[repo1, repo2],
        prefer_source=False,
    )

    assert call_urls == [
        "https://repo1.example.com/pypi/requests/2.28.0/json",
        "https://repo2.example.com/pypi/requests/2.28.0/json",
    ]


@pytest.mark.asyncio
@mock.patch("python_inspector.package_data.get_sdist_download_url")
@mock.patch("python_inspector.package_data.get_wheel_download_urls")
@mock.patch("python_inspector.utils.get_response_async")
async def test_get_pypi_data_from_purl_falls_back_to_pypi_org(
    mock_get_response, mock_get_wheels, mock_get_sdist
):
    mock_get_sdist.return_value = None
    mock_get_wheels.return_value = []

    call_urls = []

    async def track_calls(url):
        call_urls.append(url)
        return None

    mock_get_response.side_effect = track_calls

    env = Environment(python_version="310", operating_system="linux")

    await get_pypi_data_from_purl(
        purl="pkg:pypi/requests@2.28.0",
        environment=env,
        repos=[],
        prefer_source=False,
    )

    assert call_urls == ["https://pypi.org/pypi/requests/2.28.0/json"]


@pytest.mark.asyncio
@mock.patch("python_inspector.package_data.get_sdist_download_url")
@mock.patch("python_inspector.package_data.get_wheel_download_urls")
@mock.patch("python_inspector.utils.get_response_async")
async def test_get_pypi_data_from_purl_matches_by_filename(
    mock_get_response, mock_get_wheels, mock_get_sdist
):
    mock_get_sdist.return_value = None
    mock_get_wheels.return_value = [
        "https://repo.example.com/simple/../packages/ab/cd/requests-2.28.0-py3-none-any.whl"
    ]

    async def return_json_response(url):
        if "pypi" in url:
            return {
                "info": {
                    "name": "requests",
                    "version": "2.28.0",
                    "home_page": "https://requests.readthedocs.io",
                    "license_expression": "Apache-2.0",
                },
                "urls": [
                    {
                        "url": "../../packages/xy/zz/requests-2.28.0-py3-none-any.whl",
                        "digests": {"sha256": "abc123def456", "md5": "789xyz"},
                        "size": 62500,
                        "upload_time": "2022-06-29T15:30:00",
                    }
                ],
            }
        return None

    mock_get_response.side_effect = return_json_response

    repo = PypiSimpleRepository(index_url="https://repo.example.com/simple")
    env = Environment(python_version="310", operating_system="linux")

    result = await get_pypi_data_from_purl(
        purl="pkg:pypi/requests@2.28.0",
        environment=env,
        repos=[repo],
        prefer_source=False,
    )

    expected_file = test_env.get_test_loc(
        "test_get_pypi_data_from_purl_matches_by_filename-expected.json",
        must_exist=False,
    )
    check_data_results(results=result.to_dict(), expected_file=expected_file)
