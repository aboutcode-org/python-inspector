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

from python_inspector.dependencies import get_extra_data_from_requirements

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_get_extra_data_from_requirements():
    req_file = os.path.join(BASE_DIR, "data", "requirements-test.txt")
    expected = [
        {
            "extra_index_urls": [
                "https://pypi.python.org/simple/",
                "https://testpypi.python.org/simple/",
                "https://pypi1.python.org/simple/",
            ],
            "index_url": "https://pypi-index1.python.org/simple/",
        }
    ]
    result = list(get_extra_data_from_requirements(req_file))
    assert expected == result
