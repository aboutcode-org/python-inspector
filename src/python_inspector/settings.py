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

from enum import Enum
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Reference: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

class TraceLevel(int, Enum):
    TRACE = 1
    TRACE_DEEP = 2
    TRACE_ULTRA_DEEP = 3

class Settings(BaseSettings, case_sensitive=True):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', env_prefix="PYTHON_INSPECTOR",)
    DEFAULT_PYTHON_VERSION: str = "38"
    INDEX_URL: str = "https://pypi.org/simple"
    EXTRA_INDEX_URLS: Optional[List[str]] = None
    TRACE: Optional[TraceLevel] = None
