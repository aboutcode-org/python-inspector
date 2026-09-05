# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/aboutcode-org/python-inspector for support or download.

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from python_inspector import resolution


@pytest.mark.parametrize("stem,extension", [("demo-1.0a", ".tar.gz"), ("demo-1.0+zip", ".zip")])
def test_sdist_extracted_directory_name(tmp_path, monkeypatch, stem, extension):
    monkeypatch.setattr(resolution.settings, "CACHE_THIRDPARTY_DIR", str(tmp_path))
    name = stem + extension
    member = stem + "/setup.py"
    if extension == ".tar.gz":
        with tarfile.open(tmp_path / name, "w:gz") as archive:
            info = tarfile.TarInfo(member)
            info.size = 4
            archive.addfile(info, io.BytesIO(b"pass"))
    else:
        with zipfile.ZipFile(tmp_path / name, "w") as archive:
            archive.writestr(member, "pass")
    result = Path(resolution.get_sdist_file_path_from_filename(name))
    assert result.name == stem
    assert (result / "setup.py").read_text() == "pass"
