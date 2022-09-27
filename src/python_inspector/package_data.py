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

from typing import List

from packageurl import PackageURL

from _packagedcode import models
from _packagedcode.models import PackageData
from python_inspector import utils_pypi
from python_inspector.resolution import get_python_version_from_env_tag
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository


def get_pypi_bugtracker_url(project_urls):
    bug_tracking_url = project_urls.get("Tracker")
    if not (bug_tracking_url):
        bug_tracking_url = project_urls.get("Issue Tracker")
    if not (bug_tracking_url):
        bug_tracking_url = project_urls.get("Bug Tracker")
    return bug_tracking_url


def get_pypi_codeview_url(project_urls):
    code_view_url = project_urls.get("Source")
    if not (code_view_url):
        code_view_url = project_urls.get("Code")
    if not (code_view_url):
        code_view_url = project_urls.get("Source Code")
    return code_view_url


def get_wheel_download_urls(
    purl: PackageURL,
    repos: List[PypiSimpleRepository],
    environment: Environment,
    python_version: str,
) -> List[str]:
    """
    Return a list of download urls for the given purl.
    """
    for repo in repos:
        for wheel in utils_pypi.get_supported_and_valid_wheels(
            repo=repo,
            name=purl.name,
            version=purl.version,
            environment=environment,
            python_version=python_version,
        ):
            yield wheel.download_url


def get_sdist_download_url(
    purl: PackageURL, repos: List[PypiSimpleRepository], python_version: str
) -> str:
    """
    Return a list of download urls for the given purl.
    """
    for repo in repos:
        sdist = utils_pypi.get_valid_sdist(
            repo=repo,
            name=purl.name,
            version=purl.version,
            python_version=python_version,
        )
        if sdist:
            return sdist.download_url


def get_pypi_data_from_purl(
    purl: str, environment: Environment, repos: List[PypiSimpleRepository]
) -> PackageData:
    """
    Generate `Package` object from the `purl` string of npm type
    """
    purl = PackageURL.from_string(purl)
    name = purl.name
    version = purl.version
    if not version:
        raise Exception("Version is not specified in the purl")
    base_path = "https://pypi.org/pypi"
    api_url = f"{base_path}/{name}/{version}/json"
    from python_inspector.resolution import get_response

    response = get_response(api_url)
    if not response:
        return []
    info = response.get("info") or {}
    homepage_url = info.get("home_page")
    license = info.get("license")
    project_urls = info.get("project_urls") or {}
    code_view_url = get_pypi_codeview_url(project_urls)
    bug_tracking_url = get_pypi_bugtracker_url(project_urls)
    python_version = get_python_version_from_env_tag(python_version=environment.python_version)
    valid_distribution_urls = []
    valid_distribution_urls.extend(
        list(
            get_wheel_download_urls(
                purl=purl,
                repos=repos,
                environment=environment,
                python_version=python_version,
            )
        )
    )
    valid_distribution_urls.append(
        get_sdist_download_url(
            purl=purl,
            repos=repos,
            python_version=python_version,
        )
    )
    urls = response.get("urls") or []
    for url in urls:
        dist_url = url.get("url")
        if dist_url not in valid_distribution_urls:
            continue
        digests = url.get("digests") or {}
        yield PackageData(
            primary_language="Python",
            description=info.get("description"),
            homepage_url=homepage_url,
            api_data_url=api_url,
            bug_tracking_url=bug_tracking_url,
            code_view_url=code_view_url,
            declared_license=license,
            download_url=dist_url,
            size=url.get("size"),
            md5=digests.get("md5") or url.get("md5_digest"),
            sha256=digests.get("sha256"),
            release_date=url.get("upload_time"),
            keywords=info.get("keywords") or [],
            parties=[
                models.Party(
                    type=models.party_person,
                    name=info.get("author"),
                    role="author",
                    email=info.get("author_email"),
                ),
                models.Party(
                    type=models.party_person,
                    name=info.get("maintainer"),
                    role="maintainer",
                    email=info.get("maintainer_email"),
                ),
            ],
            **purl.to_dict(),
        ).to_dict()
