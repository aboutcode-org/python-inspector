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

from typing import List

from packageurl import PackageURL

from _packagedcode.models import PackageData
from _packagedcode.pypi import get_declared_license
from _packagedcode.pypi import get_description
from _packagedcode.pypi import get_keywords
from _packagedcode.pypi import get_parties
from python_inspector import utils_pypi
from python_inspector.resolution import get_python_version_from_env_tag
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository


def get_pypi_data_from_purl(
    purl: str, environment: Environment, repos: List[PypiSimpleRepository], prefer_source: bool
) -> PackageData:
    """
    Generate `Package` object from the `purl` string of pypi type

    ``purl`` is a package-url of pypi type
    ``environment`` is a `Environment` object defaulting Python version 3.8 and linux OS
    ``repos`` is a list of `PypiSimpleRepository` objects
    ``prefer_source`` is a boolean value to prefer source distribution over wheel,
    if no source distribution is available then wheel is used
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
    project_urls = info.get("project_urls") or {}
    code_view_url = get_pypi_codeview_url(project_urls)
    bug_tracking_url = get_pypi_bugtracker_url(project_urls)
    python_version = get_python_version_from_env_tag(python_version=environment.python_version)
    valid_distribution_urls = []

    valid_distribution_urls.append(
        get_sdist_download_url(
            purl=purl,
            repos=repos,
            python_version=python_version,
        )
    )

    valid_distribution_urls = [url for url in valid_distribution_urls if url]

    # if prefer_source is True then only source distribution is used
    # in case of no source distribution available then wheel is used
    if not valid_distribution_urls or not prefer_source:
        wheel_urls = list(
            get_wheel_download_urls(
                purl=purl,
                repos=repos,
                environment=environment,
                python_version=python_version,
            )
        )
        wheel_url = choose_single_wheel(wheel_urls)
        if wheel_url:
            valid_distribution_urls.append(wheel_url)

    urls = response.get("urls") or []
    for url in urls:
        dist_url = url.get("url")
        if dist_url not in valid_distribution_urls:
            continue
        digests = url.get("digests") or {}

        yield PackageData(
            primary_language="Python",
            description=get_description(info),
            homepage_url=homepage_url,
            api_data_url=api_url,
            bug_tracking_url=bug_tracking_url,
            code_view_url=code_view_url,
            license_expression=info.get("license_expression"),
            declared_license=get_declared_license(info),
            download_url=dist_url,
            size=url.get("size"),
            md5=digests.get("md5") or url.get("md5_digest"),
            sha256=digests.get("sha256"),
            release_date=url.get("upload_time"),
            keywords=get_keywords(info),
            parties=get_parties(
                info,
                author_key="author",
                author_email_key="author_email",
                maintainer_key="maintainer",
                maintainer_email_key="maintainer_email",
            ),
            **purl.to_dict(),
        )


def choose_single_wheel(wheel_urls):
    """
    Sort wheel urls descendingly and return the first one
    """
    wheel_urls.sort(reverse=True)
    if wheel_urls:
        return wheel_urls[0]


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
