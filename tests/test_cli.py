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

import pytest
from click.testing import CliRunner

from python_inspector.resolve_cli import resolve_dependencies as cli


@pytest.mark.online
def test_cli_with_json_api():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--spec", "zipp==3.8.0", "--json", "-"],
    )
    assert result.exit_code == 0


@pytest.mark.online
def test_cli_with_single_index_url():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--spec", "zipp==3.8.0", "--index-url", "https://pypi.org/simple", "--json", "-"],
    )
    assert result.exit_code == 0


@pytest.mark.online
def test_cli_with_multiple_index_url_and_tilde_req():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--spec",
            "zipp~=3.8.0",
            "--index-url",
            "https://pypi.org/simple",
            "--index-url",
            "https://thirdparty.aboutcode.org/pypi/simple/",
            "--json",
            "-",
        ],
    )
    assert result.exit_code == 0
