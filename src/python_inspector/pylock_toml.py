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

from typing import Iterable
from typing import Mapping

from packvers.markers import Marker

from _packagedcode import models
from python_inspector.dependencies import get_dependency
from python_inspector.resolution import get_environment_marker_from_environment
from python_inspector.resolution import get_python_version_from_env_tag
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import valid_python_version

SUPPORTED_LOCK_VERSION_MAJOR = 1


def load_toml(location: str) -> dict:
    """
    Return a mapping parsed from the TOML file at ``location``.
    """
    try:
        import tomllib

        with open(location, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        import toml

        return toml.load(location)


def parse_pylock_toml(location: str) -> models.PackageData:
    """
    Return PackageData parsed from a PEP 751 pylock.toml file at ``location``.
    """
    data = load_toml(location)
    lock_version = str(data.get("lock-version") or "")
    if lock_version:
        major = lock_version.split(".", 1)[0]
        if major != str(SUPPORTED_LOCK_VERSION_MAJOR):
            raise ValueError(
                f"Unsupported pylock.toml lock-version {lock_version!r}. "
                f"Only {SUPPORTED_LOCK_VERSION_MAJOR}.x is supported."
            )

    extra_index_urls = []
    dependent_packages = []
    for package in data.get("packages") or []:
        name = package.get("name")
        if not name:
            continue
        version = package.get("version")
        if not version:
            continue
        specifier = f"{name}=={version}"
        marker = package.get("marker")
        if marker:
            specifier = f"{specifier}; {marker}"
        dependent_packages.append(get_dependency(specifier=specifier))
        index_url = package.get("index")
        if index_url and index_url not in extra_index_urls:
            extra_index_urls.append(index_url)

    extra_data = {}
    for key in (
        "lock-version",
        "created-by",
        "requires-python",
        "environments",
        "extras",
        "dependency-groups",
        "default-groups",
    ):
        value = data.get(key)
        if value:
            extra_data[key] = value
    if extra_index_urls:
        extra_data["extra_index_urls"] = extra_index_urls

    return models.PackageData(
        datasource_id="pypi_pylock_toml",
        type="pypi",
        primary_language="Python",
        dependencies=dependent_packages,
        extra_data=extra_data,
    )


def get_dependencies_from_pylock(pylock_file: str) -> Iterable[models.DependentPackage]:
    """
    Yield DependentPackage for each locked package in a pylock.toml file.
    """
    yield from parse_pylock_toml(location=pylock_file).dependencies


def get_extra_data_from_pylock(pylock_file: str) -> Iterable[Mapping]:
    """
    Yield extra_data parsed from a pylock.toml file.
    """
    yield parse_pylock_toml(location=pylock_file).extra_data


def validate_pylock_for_environment(extra_data, python_version, operating_system):
    """
    Raise ValueError if the pylock metadata does not apply to ``python_version``
    and ``operating_system``.
    """
    extra_data = extra_data or {}
    python_dot_version = get_python_version_from_env_tag(python_version=python_version)
    requires_python = extra_data.get("requires-python")
    if requires_python and not valid_python_version(python_dot_version, requires_python):
        raise ValueError(
            f"Python version {python_dot_version} is not compatible with "
            f"pylock.toml requires-python {requires_python}"
        )

    environments = extra_data.get("environments") or []
    if not environments:
        return

    environment = Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system
    )
    environment_marker = get_environment_marker_from_environment(environment)
    for expression in environments:
        try:
            if Marker(expression).evaluate(environment_marker):
                return
        except Exception:
            continue
    raise ValueError(
        f"No pylock.toml environments marker matches python {python_dot_version} "
        f"on {operating_system}: {environments}"
    )
