#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import sys

import click

from python_inspector import utils_pypi
from python_inspector.cli_utils import FileOptionType
from python_inspector import dependencies

TRACE = False
TRACE_DEEP = False


@click.command()
@click.option(
    "-r",
    "--requirement",
    "requirement_files",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    metavar="REQUIREMENT-FILE",
    multiple=True,
    required=False,
    help="Path to pip requirements file listing thirdparty packages. "
         "This option can be used multiple times.",
)
@click.option(
    "--spec",
    "--specifier",
    "specifiers",
    type=str,
    metavar="SPECIFIER",
    multiple=True,
    required=False,
    help="Package specifier such as django==1.2.3. "
         "This option can be used multiple times.",
)
@click.option(
    "-p",
    "--python-version",
    "python_version",
    type=click.Choice(utils_pypi.PYTHON_VERSIONS),
    metavar="PYVER",
    # TODO: Make default the current Python version
    default="38", #utils_pypi.PYTHON_VERSIONS,
    show_default=True,
    help="Python version to use for dependency resolution.",
)
@click.option(
    "-o",
    "--operating-system",
    "operating_system",
    type=click.Choice(utils_pypi.PLATFORMS_BY_OS),
    metavar="OS",
    default="linux",
    show_default=True,
    help="OS to use for dependency resolution. ",
)
@click.option(
    "--index-url",
    "index_urls",
    type=str,
    metavar="INDEX",
    default=utils_pypi.PYPI_INDEX_URLS,
    show_default=True,
    multiple=True,
    help="PyPI index URL(s) to use in order of preference. ",
         "This option can be used multiple times.",
)
@click.option(
    "--json",
    "json_output",
    type=FileOptionType(mode='w', encoding='utf-8', lazy=True),
    metavar="FILE",
    help="Write output as pretty-printed JSON to FILE. ",
         "Use the special " - " file name to print results on screen/stdout.",
)
@click.option(
    "--use-cached-index",
    is_flag=True,
    help="Use cached on-disk PyPI package indexes and do not refetch if present.",
)
@click.help_option("-h", "--help")
def fetch_thirdparty(
    requirement_files,
    specifiers,
    python_version,
    operating_system,
    index_urls,
    json_output,
    use_cached_index,
):
    """
    Resolve the dependencies of the packages listed in REQUIREMENT-FILE(s) file
    and SPECIFIER(s) and save the results as JSON to FILE.

    Resolve the dependencies for the requested ``--python-version`` PYVER and
    ``--operating_system`` OS combination defaulting to the current version and OS.

    Download from the provided PyPI simple --index-url INDEX(s) URLs.
    Error and progress are printed to stderr.
    """

    # FIXME: Use stderr and click.secho
    print(f"Resolving dependencies...")

    required_dependent_packages = set()

    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        required_dependent_packages.update(deps)

    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        required_dependent_packages.add(dep)

    if not required_dependent_packages:
        print("Error: no requirements requested.")
        sys.exit(1)

    if TRACE_DEEP:
        print("required_dependent_packages:")
        for dep in required_dependent_packages:
            print(dep)

    # create a resolution environments
    environment = utils_pypi.Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system)

    # Collect PyPI repos
    repos = []
    for index_url in index_urls:
        index_url = index_url.strip("/")
        existing = utils_pypi.DEFAULT_PYPI_REPOS_BY_URL.get(index_url)
        if existing:
            existing.use_cached_index = use_cached_index
            repos.append(existing)
        else:
            repo = utils_pypi.PypiSimpleRepository(
                index_url=index_url,
                use_cached_index=use_cached_index,
            )
            repos.append(repo)

    # resolve dependencies proper

if __name__ == "__main__":
    fetch_thirdparty()
