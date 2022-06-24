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
def get_netrc_auth(url, netrc):
    """
    Return login and password if url is in netrc
    else return login and password as None
    """
    if netrc.get(url):
        return (netrc[url].get("login"), netrc[url].get("password"))
    return (None, None)
