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

import pytest
from commoncode.testcase import FileDrivenTesting

from python_inspector.api import resolver_api
from python_inspector.pylock_toml import get_dependencies_from_pylock
from python_inspector.pylock_toml import parse_pylock_toml
from python_inspector.pylock_toml import validate_pylock_for_environment

test_env = FileDrivenTesting()
test_env.test_data_dir = os.path.join(os.path.dirname(__file__), "data")


def test_parse_pylock_toml():
    location = test_env.get_test_loc("pylock.toml")
    package_data = parse_pylock_toml(location=location)
    assert package_data.datasource_id == "pypi_pylock_toml"
    assert package_data.extra_data["lock-version"] == "1.0"
    assert package_data.extra_data["created-by"] == "python-inspector-tests"
    assert package_data.extra_data["requires-python"] == ">=3.8"
    assert package_data.extra_data["extra_index_urls"] == ["https://pypi.org/simple"]
    purls = [dep.purl for dep in package_data.dependencies]
    assert purls == ["pkg:pypi/zipp@3.8.0", "pkg:pypi/windows-only@1.0.0"]
    windows_only = package_data.dependencies[1]
    assert "sys_platform" in windows_only.extracted_requirement
    assert windows_only.is_resolved is True


def test_get_dependencies_from_pylock_skips_packages_without_version():
    location = test_env.get_test_loc("pylock.toml")
    deps = list(get_dependencies_from_pylock(pylock_file=location))
    assert all(dep.is_resolved for dep in deps)
    assert "local-src" not in " ".join(dep.purl for dep in deps)


def test_parse_pylock_toml_rejects_unsupported_lock_version(tmpdir):
    lock_file = tmpdir.join("pylock.toml")
    lock_file.write('lock-version = "2.0"\n[[packages]]\nname = "zipp"\nversion = "3.8.0"\n')
    with pytest.raises(ValueError, match="Unsupported pylock.toml lock-version"):
        parse_pylock_toml(location=str(lock_file))


def test_validate_pylock_for_environment_rejects_incompatible_python():
    extra_data = {"requires-python": ">=3.12"}
    with pytest.raises(ValueError, match="requires-python"):
        validate_pylock_for_environment(
            extra_data=extra_data,
            python_version="38",
            operating_system="linux",
        )


def test_validate_pylock_for_environment_rejects_unmatched_environments():
    extra_data = {"environments": ["sys_platform == 'does-not-exist'"]}
    with pytest.raises(ValueError, match="environments marker"):
        validate_pylock_for_environment(
            extra_data=extra_data,
            python_version="38",
            operating_system="linux",
        )


def test_api_with_incompatible_pylock_requires_python():
    location = test_env.get_test_loc("pylock-requires-python.toml")
    with pytest.raises(ValueError, match="requires-python"):
        resolver_api(
            pylock_files=[location],
            python_version="38",
            operating_system="linux",
        )
