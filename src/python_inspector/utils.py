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

import json
import os
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional

from urllib.parse import urlparse

import aiohttp
import requests


def get_netrc_auth(url, netrc):
    """
    Return login and password if either the hostname is in netrc or a default is set in netrc
    else return login and password as None
    """
    hostname = urlparse(url).hostname
    hosts = netrc.hosts
    if hostname in hosts:
        url_auth = hosts.get(hostname)
        # netrc returns a tuple of (login, account, password)
        return (url_auth[0], url_auth[2])

    if "default" in hosts:
        default_auth = hosts.get("default")
        return (default_auth[0], default_auth[2])

    return (None, None)


def contain_string(string: str, files: List) -> bool:
    """
    Return True if the ``string`` is contained in any of the ``files`` list of file paths.
    """
    for file in files:
        if not os.path.exists(file):
            continue
        with open(file, encoding="utf-8") as f:
            # TODO also consider other file names
            if string in f.read():
                return True
    return False


def write_output_in_file(output, location):
    """
    Write headers, requirements and resolved_dependencies as JSON to ``json_output``.
    Return the output data.
    """
    json.dump(output, location, indent=2)
    return output


class Candidate(NamedTuple):
    """
    A candidate is a package that can be installed.
    """

    name: str
    version: str
    extras: str


def get_response(url: str) -> Dict:
    """
    Return a mapping of the JSON response from fetching ``url``
    or None if the ``url`` cannot be fetched.
    """
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()


async def get_response_async(url: str) -> Optional[Dict]:
    """
    Return a mapping of the JSON response from fetching ``url``
    or None if the ``url`` cannot be fetched.
    """
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


def remove_test_data_dir_variable_prefix(path, placeholder="<file>"):
    """
    Return a clean path, removing variable test path prefix or using a ``placeholder``.
    Used for testing to ensure that results are stable across runs.
    """
    path = path.replace("\\", "/")
    if "tests/data/" in path:
        _junk, test_dir, cleaned = path.partition("tests/data/")
        cleaned = f"{test_dir}{cleaned}"
        return cleaned.replace("\\", "/")
    else:
        return placeholder


def unique(sequence):
    """
    Return a list of unique items found in sequence. Preserve the original sequence order.
    Items must be hashable.
    For example:
    >>> unique([1, 5, 3, 5])
    [1, 5, 3]
    """
    seen = set()
    deduped = []
    for item in sequence:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped
