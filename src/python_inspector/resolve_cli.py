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
from python_inspector.resolution import get_resolved_dependencies

TRACE = False

__version__ = "0.5.0"

DEFAULT_PYTHON_VERSION = "38"
PYPI_SIMPLE_URL = "https://pypi.org/simple"


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
    help="Package specifier such as django==1.2.3. This option can be used multiple times.",
)
@click.option(
    "-p",
    "--python-version",
    "python_version",
    type=click.Choice(utils_pypi.PYTHON_VERSIONS),
    metavar="PYVER",
    default=DEFAULT_PYTHON_VERSION,
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
    help="OS to use for dependency resolution.",
)
@click.option(
    "--index-url",
    "index_urls",
    type=str,
    metavar="INDEX",
    show_default=True,
    default=tuple([PYPI_SIMPLE_URL]),
    multiple=True,
    help="PyPI simple index URL(s) to use in order of preference. "
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
    hidden=True,
    help="Use cached on-disk PyPI simple package indexes and do not refetch if present.",
)
@click.option(
    "--use-pypi-json-api",
    is_flag=True,
    help="Use PyPI JSON API to fetch dependency data. Faster but not always correct. "
    "--index-url are ignored when this option is active.",
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
    use_cached_index=False,
    use_pypi_json_api=False,
    debug=TRACE,
):
    """
    Resolve the dependencies of the packages listed in REQUIREMENT-FILE(s) file
    and SPECIFIER(s) and save the results as JSON to FILE.

    Resolve the dependencies for the requested ``--python-version`` PYVER and
    ``--operating_system`` OS combination defaulting Python version 3.8 and
    linux OS.

    Download from the provided PyPI simple --index-url INDEX(s) URLs defaulting
    to PyPI.org

    Error and progress are printed to stderr.

    For example, display the results of resolving the dependencies for flask==2.1.2
    on screen::

        dad --spec "flask==2.1.2" --json -
    """

    click.secho(f"Resolving dependencies...")

    # TODO: deduplicate me
    direct_dependencies = []

    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        direct_dependencies.extend(deps)

    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        direct_dependencies.append(dep)

    if not direct_dependencies:
        click.secho("Error: no requirements requested.")
        sys.exit(1)

    if debug:
        click.secho("direct_dependencies:")
        for dep in direct_dependencies:
            click.secho(f" {dep}")

    # create a resolution environments
    environment = utils_pypi.Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system
    )

    if debug:
        click.secho(f"environment: {environment}")

    repos = []
    if not use_pypi_json_api:
        # Collect PyPI repos
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
        click.secho("repos:")
        for repo in repos:
            click.secho(f" {repo}")

    # resolve dependencies proper
    requirements, resolved_dependencies = resolve(
        direct_dependencies=direct_dependencies,
        environment=environment,
        repos=repos,
        as_tree=False,
    )

    cli_options = [f"--requirement {rf}" for rf in requirement_files]
    cli_options += [f"--specifier {sp}" for sp in specifiers]
    cli_options += [f"--index-url {iu}" for iu in index_urls]
    cli_options += [f"--python-version {python_version}"]
    cli_options += [f"--operating-system {operating_system}"]
    cli_options += ["--json <file>"]

    notice = (
        "Dependency tree generated with python-inspector.\n"
        "python-inspector is a free software tool from nexB Inc. and others.\n"
        "Visit https://github.com/nexB/scancode-toolkit/ for support and download."
    )

    headers = dict(
        tool_name="dad",
        tool_homepageurl="https://github.com/nexB/python-inspector",
        tool_version=__version__,
        options=cli_options,
        notice=notice,
        warnings=[],
        errors=[],
    )

    write_output(
        headers=headers,
        requirements=requirements,
        resolved_dependencies=resolved_dependencies,
        json_output=json_output,
    )

    if debug:
        click.secho("done!")


def resolve(direct_dependencies, environment, repos=tuple(), as_tree=False):
    """
    Resolve dependencies given a ``direct_dependencies`` list of
    DependentPackage and return a tuple of (initial_requirements,
    resolved_dependencies).
    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively.
    """

    requirements = [
        Requirement(requirement_string=d.extracted_requirement) for d in direct_dependencies
    ]
    resolved_dependencies = get_resolved_dependencies(
        requirements=requirements,
        environment=environment,
        repos=repos,
        as_tree=as_tree,
    )

    initial_requirements = [d.to_dict() for d in direct_dependencies]

    return initial_requirements, resolved_dependencies


def write_output(headers, requirements, resolved_dependencies, json_output):
    """
    Write headers, requirements and resolved_dependencies as JSON to ``json_output``.
    Return the output data.
    """
    output = dict(
        headers=headers,
        requirements=requirements,
        resolved_dependencies=resolved_dependencies,
    )

    json.dump(output, json_output, indent=2)
    return output


if __name__ == "__main__":
    resolve_dependencies()
