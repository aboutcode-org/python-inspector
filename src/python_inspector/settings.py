#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

# Reference: https://docs.pydantic.dev/latest/concepts/pydantic_settings/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PYTHON_INSPECTOR_",
        case_sensitive=True,
        extra="allow",
    )
    DEFAULT_PYTHON_VERSION: str = "39"
    INDEX_URL: tuple[str, ...] = ("https://pypi.org/simple",)
    CACHE_THIRDPARTY_DIR: Path = Path.home() / ".cache/python_inspector"

    @field_validator("INDEX_URL")
    def validate_index_url(cls, value):
        if isinstance(value, str):
            return (value,)
        elif isinstance(value, tuple):
            return value
        else:
            raise ValueError("INDEX_URL must be either a string or a tuple of strings.")
