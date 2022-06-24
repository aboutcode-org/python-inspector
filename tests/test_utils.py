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

from commoncode.testcase import FileDrivenTesting
from tinynetrc import Netrc

from python_inspector.utils import get_netrc_auth

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


def test_get_netrc_auth():
    netrc_file = test_env.get_test_loc("test.netrc")
    netrc = Netrc(netrc_file)
    assert get_netrc_auth(url="https://pyp1.org/simple", netrc=netrc) == ("test", "test123")


def test_get_netrc_auth_with_no_matching_url():
    netrc_file = test_env.get_test_loc("test.netrc")
    netrc = Netrc(netrc_file)
    assert get_netrc_auth(url="https://pypi2.org/simple", netrc=netrc) == (None, None)
