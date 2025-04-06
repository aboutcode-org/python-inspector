#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """
    Reference: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    A settings object: use it with an .env file and/or environment variables all prefixed with
    PYTHON_INSPECTOR_
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PYTHON_INSPECTOR_",
        case_sensitive=True,
        extra="allow",
    )

    # the default Python version to use if none is provided
    DEFAULT_PYTHON_VERSION: str = "39"

    # the default OS to use if none is provided
    DEFAULT_OS: str = "linux"

    # a list of PyPI simple index URLs. Use a JSON array to represent multiple URLs
    INDEX_URL: tuple[str, ...] = ("https://pypi.org/simple",)

    # If True, only uses configured INDEX_URLs listed above and ignore other URLs found in requirements
    USE_ONLY_CONFIGURED_INDEX_URLS: bool = False

    # a path string where to store the cached downloads. Will be created if it does not exists.
    CACHE_THIRDPARTY_DIR: str = str(Path(Path.home() / ".cache/python_inspector"))

    @field_validator("INDEX_URL")
    @classmethod
    def validate_index_url(cls, value):
        if isinstance(value, str):
            return (value,)
        elif isinstance(value, (tuple, list)):
            return tuple(value)
        else:
            raise ValueError(f"INDEX_URL must be either a URL or list of URLs: {value!r}")


def create_cache_directory(cache_dir):
    cache_dir = Path(cache_dir).expanduser().resolve().absolute()
    if not cache_dir.exists():
        cache_dir.mkdir(exist_ok=True)
