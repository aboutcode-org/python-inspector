#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from python_inspector import settings

# Initialize global settings
pyinspector_settings = settings.Settings()

settings.create_cache_directory(pyinspector_settings.CACHE_THIRDPARTY_DIR)
