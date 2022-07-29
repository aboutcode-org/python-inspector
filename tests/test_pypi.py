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

from _packagedcode import models
from _packagedcode.pypi import can_process_dependent_package


def test_can_process_dependent_package():
    dependency = models.DependentPackage(
        purl="pkg:pypi/django",
        scope="install",
        is_runtime=True,
        is_optional=False,
        is_resolved=False,
        extracted_requirement="django>=1.11.11",
        extra_data=dict(
            is_editable=False,
            link=None,
            hash_options=[],
            is_constraint=False,
            is_archive=False,
            is_wheel=False,
            is_url=False,
            is_vcs_url=False,
            is_name_at_url=False,
            is_local_path=False,
        ),
    )

    assert can_process_dependent_package(dependency)


def test_can_not_process_editable_dependent_package():
    dependency = models.DependentPackage(
        purl="pkg:pypi/django",
        scope="install",
        is_runtime=True,
        is_optional=False,
        is_resolved=False,
        extracted_requirement="django>=1.11.11",
        extra_data=dict(
            is_editable=True,
            link=None,
            hash_options=[],
            is_constraint=False,
            is_archive=False,
            is_wheel=False,
            is_url=False,
            is_vcs_url=False,
            is_name_at_url=False,
            is_local_path=False,
        ),
    )

    assert not can_process_dependent_package(dependency)


def test_can_process_dependent_package_without_extra_data():
    dependency = models.DependentPackage(
        purl="pkg:pypi/django",
        scope="install",
        is_runtime=True,
        is_optional=False,
        is_resolved=False,
        extracted_requirement="django>=1.11.11",
    )

    assert can_process_dependent_package(dependency)


def test_can_not_process_dependent_package_with_any_flags_set():
    dependency = models.DependentPackage(
        purl="pkg:pypi/django",
        scope="install",
        is_runtime=True,
        is_optional=False,
        is_resolved=False,
        extracted_requirement="django>=1.11.11",
        extra_data=dict(
            is_editable=True,
            link="http://example.com/django.tar.gz",
            hash_options=["--hash", "sha256:12345"],
            is_constraint=True,
            is_archive=True,
            is_wheel=True,
            is_url=True,
            is_vcs_url=True,
            is_name_at_url=True,
            is_local_path=True,
        ),
    )

    assert not can_process_dependent_package(dependency)
