#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import PythonSetupPyHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_setup_py_parsing():
    setup_py_file = os.path.join(BASE_DIR, "data", "setup", "simple-setup.py")
    package_data = list(PythonSetupPyHandler.parse(location=setup_py_file))
    deps = []
    for pkg in package_data:
        deps.extend(pkg.dependencies)
    assert deps == [
        DependentPackage(
            purl="pkg:pypi/license-expression",
            extracted_requirement="license-expression<1.2,>=0.1",
            scope="install",
        ),
    ]
