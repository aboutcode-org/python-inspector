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

from python_inspector.package_data import get_pypi_codeview_url
from python_inspector.package_data import get_sdist_from_urls


def test_get_pypi_codeview_url():
    assert (
        get_pypi_codeview_url({"Source": "https://github.com/psf/requests"})
        == "https://github.com/psf/requests"
    )
    assert (
        get_pypi_codeview_url({"Code": "https://github.com/psf/requests"})
        == "https://github.com/psf/requests"
    )
    assert (
        get_pypi_codeview_url({"Source Code": "https://github.com/psf/requests"})
        == "https://github.com/psf/requests"
    )
    assert get_pypi_codeview_url({}) is None


def test_get_sdist_from_urls():
    urls = [
        {"packagetype": "bdist_wheel", "url": "https://example.com/pkg-1.0.whl"},
        {
            "packagetype": "sdist",
            "url": "https://example.com/pkg-1.0.tar.gz",
            "digests": {"sha256": "abc123", "md5": "def456"},
            "size": 12345,
            "filename": "pkg-1.0.tar.gz",
        },
    ]
    result = get_sdist_from_urls(urls)
    assert result["url"] == "https://example.com/pkg-1.0.tar.gz"
    assert result["sha256"] == "abc123"
    assert result["filename"] == "pkg-1.0.tar.gz"


def test_get_sdist_from_urls_returns_none_when_missing():
    assert get_sdist_from_urls([]) is None
    assert get_sdist_from_urls(None) is None
    assert get_sdist_from_urls([{"packagetype": "bdist_wheel"}]) is None


def test_get_sdist_from_urls_md5_digest_fallback():
    urls = [{"packagetype": "sdist", "url": "x", "md5_digest": "old", "digests": {}}]
    assert get_sdist_from_urls(urls)["md5"] == "old"
