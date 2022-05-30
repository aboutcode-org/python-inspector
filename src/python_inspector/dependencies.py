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

from _packagedcode import models
from _packagedcode.pypi import PipRequirementsFileHandler
from pip_requirements_parser import InstallRequirement
from packaging.requirements import Requirement
from packageurl import PackageURL

"""
Utilities to resolve dependencies .
"""


def get_dependencies_from_requirements(requirements_file="requirements.txt", *args, **kwargs):
    """
    Yield DependentPackage for each requirement in a `requirement`
    file.
    """
    for packages_data in PipRequirementsFileHandler.parse(location=requirements_file):
        for package_data in packages_data:
            for dependent_package in package_data.dependencies:
                yield dependent_package


def get_dependency(specifier, *args, **kwargs):
    """
    Return a DependentPackage given a requirement ``specifier`` string.

    For example:
    >>> assert get_dependency("foo==1.2.3") == ("foo", "1.2.3")
    >>> assert get_dependency("fooA==1.2.3.DEV1") == ("fooa", "1.2.3.dev1")
    """
    specifier = specifier and "".join(specifier.lower().split())
    assert specifier, f"specifier is required but empty:{specifier!r}"

    requirement = Requirement(requirement_string=specifier)

    # TODO: use new InstallRequirement.from_specifier constructor when available
    ir = InstallRequirement(
        req=requirement,
        requirement_line=specifier,
    )

    scope = 'install'
    is_runtime = True
    is_optional = False

    if ir.name:
        # will be None if not pinned
        version = ir.get_pinned_version
        purl = PackageURL(type='pypi', name=ir.name, version=version)

    return models.DependentPackage(
        purl=purl,
        scope=scope,
        is_runtime=is_runtime,
        is_optional=is_optional,
        is_resolved=ir.is_pinned or False,
        extracted_requirement=specifier,
    )
