#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from packageurl import PackageURL
from packvers.requirements import Requirement
from pip_requirements_parser import InstallRequirement

from _packagedcode import models
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import get_requirements_txt_dependencies

"""
Utilities to resolve dependencies .
"""

TRACE = False


def get_dependencies_from_requirements(requirements_file="requirements.txt"):
    """
    Yield DependentPackage for each requirement in a `requirement`
    file.
    """
    dependent_packages, _ = get_requirements_txt_dependencies(
        location=requirements_file, include_nested=True
    )
    for dependent_package in dependent_packages:
        if TRACE:
            print(
                "dependent_package.extracted_requirement:",
                dependent_package.extracted_requirement,
            )
        yield dependent_package


def get_extra_data_from_requirements(requirements_file="requirements.txt"):
    """
    Yield extra_data for each requirement in a `requirement`
    file.
    """
    for package_data in PipRequirementsFileHandler.parse(location=requirements_file):
        yield package_data.extra_data


def is_requirement_pinned(requirement: Requirement):
    specifiers = requirement.specifier
    return specifiers and len(specifiers) == 1 and next(iter(specifiers)).operator in {"==", "==="}


def get_dependency(specifier):
    """
    Return a DependentPackage given a requirement ``specifier`` string.

    For example:
    >>> dep = get_dependency("foo==1.2.3")
    >>> assert dep.purl == "pkg:pypi/foo@1.2.3"
    """
    specifier = specifier and "".join(specifier.lower().split())
    assert specifier, f"specifier is required but empty:{specifier!r}"

    requirement = Requirement(requirement_string=specifier)

    scope = "install"
    is_runtime = True
    is_optional = False

    if requirement.name:
        # will be None if not pinned
        version = None
        if is_requirement_pinned(requirement):
            version = str(list(requirement.specifier)[0].version)
        purl = PackageURL(type="pypi", name=requirement.name, version=version).to_string()

    return models.DependentPackage(
        purl=purl,
        scope=scope,
        is_runtime=is_runtime,
        is_optional=is_optional,
        is_resolved=False or is_requirement_pinned(requirement),
        extracted_requirement=specifier,
    )
