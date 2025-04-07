#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import subprocess
import sys
import unittest

import pytest


class BaseTests(unittest.TestCase):
    @pytest.mark.skipif(sys.version_info[:2] == (3, 12), reason="Skipping test for Python 3.12")
    def test_codestyle(self):
        """
        This test shouldn't run in proliferated repositories.
        """
        args = "make check"
        try:
            subprocess.check_output(args.split())
        except subprocess.CalledProcessError as e:
            print("===========================================================")
            print(e.output)
            print("===========================================================")
            raise Exception(
                "Code style check failed!",
                e.output,
            ) from e
