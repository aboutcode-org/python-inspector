#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import create_dependency_for_python_requires


def test_create_dependency_for_python_requires():
    assert create_dependency_for_python_requires(
        python_requires_specifier=">=3.6"
    ) == DependentPackage(
        purl="pkg:generic/python", extracted_requirement="python_requires>=3.6", scope="python"
    )
