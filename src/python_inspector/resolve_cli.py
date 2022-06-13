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

import json
import sys

import click
from packaging.requirements import Requirement

from python_inspector import dependencies
from python_inspector import utils_pypi
from python_inspector.cli_utils import FileOptionType
from python_inspector.resolution import resolution

TRACE = False


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
    help="Package specifier such as django==1.2.3. " "This option can be used multiple times.",
)
@click.option(
    "-p",
    "--python-version",
    "python_version",
    type=click.Choice(utils_pypi.PYTHON_VERSIONS),
    metavar="PYVER",
    # TODO: Make default the current Python version
    default="38",  # utils_pypi.PYTHON_VERSIONS,
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
    show_default=True,
    multiple=True,
    help="PyPI index URL(s) to use in order of preference. "
    "This option can be used multiple times.",
)
@click.option(
    "--json",
    "json_output",
    type=FileOptionType(mode="w", encoding="utf-8", lazy=True),
    required=True,
    metavar="FILE",
    help="Write output as pretty-printed JSON to FILE. "
    "Use the special '-' file name to print results on screen/stdout.",
)
@click.option(
    "--use-cached-index",
    is_flag=True,
    help="Use cached on-disk PyPI package indexes and do not refetch if present.",
)
@click.option(
    "--debug",
    is_flag=True,
    hidden=True,
    help="Enable debug output.",
)
@click.help_option("-h", "--help")
def resolve_dependencies(
    requirement_files,
    specifiers,
    python_version,
    operating_system,
    index_urls,
    json_output,
    use_cached_index,
    debug=TRACE,
):
    """
    Resolve the dependencies of the packages listed in REQUIREMENT-FILE(s) file
    and SPECIFIER(s) and save the results as JSON to FILE.

    Resolve the dependencies for the requested ``--python-version`` PYVER and
    ``--operating_system`` OS combination defaulting to the current version and OS.

    Download from the provided PyPI simple --index-url INDEX(s) URLs.
    Error and progress are printed to stderr.

    Default environment is the Python version - 3.8 and OS - linux.

    1) If no index_url is provided, the PyPI JSON API is used and environment will be ignored in that case.

    For example:
        dad --spec "flask==2.1.2" --json -

    2) If an index_url is provided, the environment will be used to resolve the dependencies.
    (If no environment is provided default environment will be used.)

    For example:
        dad --spec "flask==2.1.2" --index-url https://pypi.org/simple --json -

    For example::
        dad --spec "flask" --requirement etc/scripts/requirements.txt --json -
    """

    # FIXME: Use stderr and click.secho
    print(f"Resolving dependencies...")

    # TODO: deduplicate me
    direct_dependencies = []

    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        direct_dependencies.extend(deps)

    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        direct_dependencies.append(dep)

    if not direct_dependencies:
        print("Error: no requirements requested.")
        sys.exit(1)

    if debug:
        print("direct_dependencies:")
        for dep in direct_dependencies:
            print(" ", dep)

    # create a resolution environments
    environment = utils_pypi.Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system
    )

    if debug:
        print("environment:", environment)

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

    if debug:
        print("repos:")
        for repo in repos:
            print(" ", repo)

    # resolve dependencies proper
    resolved_dependencies = resolve(direct_dependencies, environment, repos)
    write_output(results=resolved_dependencies, json_output=json_output)

    if debug:
        print("done!")


def resolve(direct_dependencies, environment, repos):
    """
    Resolve dependencies given a ``direct_dependencies`` list of
    DependentPackage and return SOMETHING TBD.
    """

    reqs = [Requirement(d.extracted_requirement) for d in direct_dependencies]
    as_parent_children = resolution(reqs, environment, repos)

    return dict(
        headers=[dict(tool="dad")],
        requirements=[d.to_dict() for d in direct_dependencies],
        resolved_dependencies=dict(
            as_parent_children=as_parent_children,
        ),
    )


def write_output(results, json_output):
    """
    Write headers, and resolved dependency results to ``output_file``
    """
    # TODO : create tree, add headers
    json.dump(results, json_output, indent=2)


if __name__ == "__main__":
    resolve_dependencies()
