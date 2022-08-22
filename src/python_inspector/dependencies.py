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
from packaging.requirements import Requirement
from pip_requirements_parser import InstallRequirement

from _packagedcode import models
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import PythonSetupPyHandler
from python_inspector.resolution import get_requirements_from_distribution

"""
Utilities to resolve dependencies .
"""

TRACE = False


def get_dependencies_from_requirements(requirements_file="requirements.txt"):
    """
    Yield DependentPackage for each requirement in a `requirement`
    file.
    """
    for package_data in PipRequirementsFileHandler.parse(location=requirements_file):
        for dependent_package in package_data.dependencies:
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

    # TODO: use new InstallRequirement.from_specifier constructor when available
    ir = InstallRequirement(
        req=requirement,
        requirement_line=specifier,
    )

    scope = "install"
    is_runtime = True
    is_optional = False

    if ir.name:
        # will be None if not pinned
        version = ir.get_pinned_version
        purl = PackageURL(type="pypi", name=ir.name, version=version).to_string()

    return models.DependentPackage(
        purl=purl,
        scope=scope,
        is_runtime=is_runtime,
        is_optional=is_optional,
        is_resolved=ir.is_pinned or False,
        extracted_requirement=specifier,
    )
