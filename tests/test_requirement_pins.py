# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/aboutcode-org/python-inspector for support or download.

import pytest

from packvers.requirements import Requirement
from python_inspector.dependencies import get_dependency
from python_inspector.dependencies import is_requirement_pinned


@pytest.mark.parametrize(
    "text,expected",
    [
        ("demo", False),
        ("demo==1.2.*", False),
        ("demo>=1", False),
        ("demo==1.2", True),
        ("demo===1.2", True),
        ("demo===1.2.*", True),
    ],
)
def test_requirement_pins(text, expected):
    assert is_requirement_pinned(Requirement(text)) is expected


def test_wildcard_dependency_has_no_exact_version():
    dependency = get_dependency("demo==1.2.*")
    assert dependency.purl == "pkg:pypi/demo"
    assert dependency.is_resolved is False
