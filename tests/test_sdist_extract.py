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
import io
import os
import tarfile
import zipfile

import pytest

from python_inspector.resolution import _restrictive_tar_filter
from python_inspector.resolution import _tarfile_extract_supports_filter
from python_inspector.resolution import get_requirements_from_python_manifest
from python_inspector.resolution import get_sdist_file_path_from_filename
from python_inspector.resolution import get_setup_requirements

SETUP_CFG = """\
[metadata]
name = pkg
version = 1.0

[options]
install_requires =
    six
"""


def _use_cache(monkeypatch, cache):
    os.makedirs(cache, exist_ok=True)
    monkeypatch.setattr(
        "python_inspector.resolution.settings.CACHE_THIRDPARTY_DIR",
        str(cache),
    )


def _add_bytes(tar, name, payload):
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def _add_link(tar, name, linkname, symbolic):
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.SYMTYPE if symbolic else tarfile.LNKTYPE
    info.linkname = linkname
    tar.addfile(info)


def _write_sdist(cache, members):
    """
    Build a tar.gz whose member names are stored as given, including absolute paths.
    """
    archive_name = "pkg-1.0.tar.gz"
    archive_path = os.path.join(cache, archive_name)
    with tarfile.open(archive_path, "w:gz") as tar:
        for member in members:
            kind = member[0]
            if kind == "file":
                _add_bytes(tar, member[1], member[2])
            else:
                _add_link(tar, member[1], member[2], symbolic=kind == "symlink")
    return archive_name


def _metadata_members():
    return [
        ("file", "pkg-1.0/PKG-INFO", "Name: pkg\nVersion: 1.0\n"),
        ("file", "pkg-1.0/setup.cfg", SETUP_CFG),
    ]


def test_extract_sdist_rejects_absolute_tar_member(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    members = _metadata_members() + [("file", str(marker), "changed")]
    archive_name = _write_sdist(cache, members)

    with pytest.raises(ValueError, match="outside the extraction directory"):
        get_sdist_file_path_from_filename(archive_name)

    assert marker.read_text() == "unchanged"
    extracted = cache / "extracted_sdists"
    if extracted.exists():
        for dirpath, _dirnames, filenames in os.walk(extracted):
            for filename in filenames:
                with open(os.path.join(dirpath, filename), "rb") as extracted_file:
                    assert b"changed" not in extracted_file.read()


def test_extract_sdist_rejects_parent_path_member(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    extraction_dir = cache / "extracted_sdists" / "pkg-1.0"
    relative_escape = os.path.relpath(marker, extraction_dir)
    members = _metadata_members() + [("file", relative_escape, "changed")]
    archive_name = _write_sdist(cache, members)

    with pytest.raises(ValueError, match="outside the extraction directory"):
        get_sdist_file_path_from_filename(archive_name)

    assert marker.read_text() == "unchanged"


def test_extract_sdist_rejects_symlink_and_hardlink_outside(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    for kind in ("symlink", "hardlink"):
        members = _metadata_members() + [(kind, "pkg-1.0/escape", str(marker))]
        archive_name = _write_sdist(cache, members)
        with pytest.raises(ValueError, match="unsafe link"):
            get_sdist_file_path_from_filename(archive_name)
        assert marker.read_text() == "unchanged"
        assert not os.path.lexists(cache / "extracted_sdists" / "pkg-1.0" / "pkg-1.0" / "escape")


def test_extract_sdist_rejects_file_through_escaping_symlink(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    marker_dir = tmp_path / "marker-dir"
    marker_dir.mkdir()
    marker = marker_dir / "marker"
    marker.write_text("unchanged")
    members = _metadata_members() + [
        ("symlink", "pkg-1.0/escape", str(marker_dir)),
        ("file", "pkg-1.0/escape/marker", "changed"),
    ]
    archive_name = _write_sdist(cache, members)

    with pytest.raises(ValueError, match="unsafe link"):
        get_sdist_file_path_from_filename(archive_name)

    assert marker.read_text() == "unchanged"


def test_extract_sdist_keeps_internal_metadata_and_links(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    members = _metadata_members() + [
        ("symlink", "pkg-1.0/setup.cfg.link", "setup.cfg"),
        ("hardlink", "pkg-1.0/setup.cfg.hard", "pkg-1.0/setup.cfg"),
    ]
    archive_name = _write_sdist(cache, members)

    package_dir = get_sdist_file_path_from_filename(archive_name)

    assert os.path.basename(package_dir) == "pkg-1.0"
    assert not os.path.islink(package_dir)
    assert os.path.isdir(package_dir)
    extraction_dir = os.path.dirname(package_dir)
    assert os.path.realpath(package_dir).startswith(os.path.realpath(extraction_dir) + os.sep)
    with open(os.path.join(package_dir, "setup.cfg")) as manifest:
        assert "install_requires" in manifest.read()
    assert os.path.islink(os.path.join(package_dir, "setup.cfg.link"))
    assert os.path.isfile(os.path.join(package_dir, "setup.cfg.hard"))


def test_extract_sdist_replaces_symlinked_extraction_directory(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "planted").write_text("planted")
    extraction_link = cache / "extracted_sdists" / "pkg-1.0"
    extraction_link.parent.mkdir(parents=True)
    extraction_link.symlink_to(outside, target_is_directory=True)
    archive_name = _write_sdist(cache, _metadata_members())

    package_dir = get_sdist_file_path_from_filename(archive_name)

    assert not os.path.islink(package_dir)
    assert os.path.isfile(os.path.join(package_dir, "setup.cfg"))
    assert (outside / "planted").read_text() == "planted"
    assert not (outside / "pkg-1.0").exists()
    assert not (outside / "setup.cfg").exists()


def test_extract_without_filter_argument_still_rejects_absolute_member(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    monkeypatch.setattr(
        "python_inspector.resolution._tarfile_extract_supports_filter",
        lambda: False,
    )
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    members = _metadata_members() + [("file", str(marker), "changed")]
    archive_name = _write_sdist(cache, members)

    with pytest.raises(ValueError, match="outside the extraction directory"):
        get_sdist_file_path_from_filename(archive_name)

    assert marker.read_text() == "unchanged"


def test_extract_passes_explicit_restrictive_filter(tmp_path, monkeypatch):
    if not _tarfile_extract_supports_filter():
        pytest.skip("this interpreter has no tar extract filter argument")
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    filters = []
    real_extract = tarfile.TarFile.extract

    def spy(self, member, path="", set_attrs=True, *, numeric_owner=False, filter=None):
        filters.append(filter)
        return real_extract(
            self,
            member,
            path,
            set_attrs,
            numeric_owner=numeric_owner,
            filter=filter,
        )

    monkeypatch.setattr(tarfile.TarFile, "extract", spy)
    archive_name = _write_sdist(cache, _metadata_members())

    get_sdist_file_path_from_filename(archive_name)

    assert filters
    assert all(extract_filter is _restrictive_tar_filter for extract_filter in filters)


def test_extract_sdist_rejects_absolute_zip_member(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    _use_cache(monkeypatch, cache)
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    archive_name = "pkg-1.0.zip"
    archive_path = cache / archive_name
    with zipfile.ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("pkg-1.0/PKG-INFO", "Name: pkg\nVersion: 1.0\n")
        zip_file.writestr("pkg-1.0/setup.cfg", SETUP_CFG)
        zip_file.writestr(str(marker), "changed")

    with pytest.raises(ValueError, match="outside the extraction directory"):
        get_sdist_file_path_from_filename(archive_name)

    assert marker.read_text() == "unchanged"


def test_manifest_read_rejects_symlink_outside_package(tmp_path):
    package_dir = tmp_path / "pkg-1.0"
    package_dir.mkdir()
    outside = tmp_path / "outside-setup.py"
    outside.write_text(
        "from setuptools import setup\nsetup(name='pkg', install_requires=['leaked'])\n"
    )
    setup_py = package_dir / "setup.py"
    setup_py.symlink_to(outside)

    with pytest.raises(ValueError, match="resolves outside"):
        list(
            get_requirements_from_python_manifest(
                str(package_dir),
                str(setup_py),
                [str(setup_py)],
                False,
            )
        )
    with pytest.raises(ValueError, match="resolves outside"):
        list(
            get_setup_requirements(
                str(package_dir),
                str(setup_py),
                str(package_dir / "setup.cfg"),
            )
        )
