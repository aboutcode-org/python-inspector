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

from typing import NamedTuple

import pytest

from python_inspector import utils_pypi
from python_inspector.utils_pypi import Distribution
from python_inspector.utils_pypi import PypiPackage
from python_inspector.utils_pypi import Sdist
from python_inspector.utils_pypi import Wheel


class DistTest(NamedTuple):
    filename: str
    expected_class: type
    expected_name: str
    expected_version: str

    def check(self, using=Distribution):
        dist = using.from_filename(self.filename)
        assert dist.name == self.expected_name
        assert dist.version == self.expected_version


wheel_tests = [
    DistTest(
        filename="package.repo/SomeProject-1.2.3-py33-none-any.whl",
        expected_class=Wheel,
        expected_name="SomeProject",
        expected_version="1.2.3",
    ),
    DistTest(
        filename="SomeProject-1.2.3+cpu-py33-none-any.whl",
        expected_class=Wheel,
        expected_name="SomeProject",
        expected_version="1.2.3+cpu",
    ),
    DistTest(
        filename="/scancode_toolkit_mini-32.0.6-cp311-none-any.whl",
        expected_class=Wheel,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="example/torch-2.0.0+cpu.cxx11.abi-cp310-cp310-linux_x86_64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="2.0.0+cpu.cxx11.abi",
    ),
    DistTest(
        filename="torch-1.10.2+cpu-cp39-cp39-win_amd64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="1.10.2+cpu",
    ),
    DistTest(
        filename="torch-2.0.0+cpu.cxx11.abi-cp310-cp310-linux_x86_64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="2.0.0+cpu.cxx11.abi",
    ),
    DistTest(
        filename="/torch-1.10.2+cpu-cp39-cp39-win_amd64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="1.10.2+cpu",
    ),
    DistTest(
        filename="example/torch-2.0.0%2Bcpu.cxx11.abi-cp310-cp310-linux_x86_64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="2.0.0+cpu.cxx11.abi",
    ),
    DistTest(
        filename="torch-1.10.2%2Bcpu-cp39-cp39-win_amd64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="1.10.2+cpu",
    ),
    DistTest(
        filename="torch-2.0.0%2Bcpu.cxx11.abi-cp310-cp310-linux_x86_64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="2.0.0+cpu.cxx11.abi",
    ),
    DistTest(
        filename="/torch-1.10.2%2Bcpu-cp39-cp39-win_amd64.whl",
        expected_class=Wheel,
        expected_name="torch",
        expected_version="1.10.2+cpu",
    ),
]

sdist_tests = [
    DistTest(
        filename="scancode-toolkit-mini-32.0.6.tar.gz",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="/scancode-toolkit-mini-32.0.6.tar.gz",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="foo/bar/scancode-toolkit-mini-32.0.6.tar.gz",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="scancode-toolkit-mini-32.0.6.zip",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="/scancode-toolkit-mini-32.0.6.zip",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
    DistTest(
        filename="foo/bar/scancode-toolkit-mini-32.0.6.zip",
        expected_class=Sdist,
        expected_name="scancode-toolkit-mini",
        expected_version="32.0.6",
    ),
]

linux_platforms = [
    "linux_x86_64",
    "manylinux1_x86_64",
    "manylinux2010_x86_64",
    "manylinux2014_x86_64",
    "manylinux_2_27_x86_64",
    "manylinux_2_28_x86_64",
]


@pytest.mark.parametrize("dist_test", sdist_tests + wheel_tests)
def test_Distribution_from_filename(dist_test):
    dist_test.check()


@pytest.mark.parametrize("dist_test", sdist_tests)
def test_Sdist_from_filename(dist_test):
    dist_test.check(using=Sdist)


@pytest.mark.parametrize("dist_test", wheel_tests)
def test_Wheel_from_filename(dist_test):
    dist_test.check(using=Wheel)


@pytest.mark.parametrize("linux_platform", linux_platforms)
def test_PypiPackage_get_supported_wheels(linux_platform):
    whl = Wheel.from_filename(f"onnxruntime-1.19.2-cp311-cp311-{linux_platform}.whl")
    pkg = PypiPackage.package_from_dists(dists=[whl])
    env = utils_pypi.Environment.from_pyver_and_os(python_version="311", operating_system="linux")

    supported_wheels = list(pkg.get_supported_wheels(environment=env))

    assert supported_wheels == [whl]
