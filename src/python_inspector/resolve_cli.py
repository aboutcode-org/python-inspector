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
import os
from typing import List

import click
from packaging.requirements import Requirement
from tinynetrc import Netrc

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import can_process_dependent_package
from python_inspector import dependencies
from python_inspector import utils
from python_inspector import utils_pypi
from python_inspector.cli_utils import FileOptionType
from python_inspector.resolution import get_resolved_dependencies

TRACE = False

__version__ = "0.5.0"

DEFAULT_PYTHON_VERSION = "38"
PYPI_SIMPLE_URL = "https://pypi.org/simple"


@click.command()
@click.pass_context
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
    "-n",
    "--netrc",
    "netrc_file",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    metavar="NETRC-FILE",
    required=False,
    help="Netrc file to use for authentication. ",
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
    required=False,
    metavar="FILE",
    help="Write output as pretty-printed JSON to FILE. "
    "Use the special '-' file name to print results on screen/stdout.",
)
@click.option(
    "--json-pdt",
    "pdt_output",
    type=FileOptionType(mode="w", encoding="utf-8", lazy=True),
    required=False,
    metavar="FILE",
    help="Write output as pretty-printed JSON to FILE as a tree in the style of pipdeptree. "
    "Use the special '-' file name to print results on screen/stdout.",
)
@click.option(
    "--max-rounds",
    "max_rounds",
    type=int,
    default=200000,
    help="Increase the max rounds whenever the resolution is too deep",
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
    "--verbose",
    is_flag=True,
    hidden=True,
    help="Enable debug output.",
)
@click.help_option("-h", "--help")
def resolve_dependencies(
    ctx,
    requirement_files,
    netrc_file,
    specifiers,
    python_version,
    operating_system,
    index_urls,
    json_output,
    pdt_output,
    max_rounds,
    use_cached_index=False,
    use_pypi_json_api=False,
    verbose=TRACE,
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

        python-inspector --spec "flask==2.1.2" --json -
    """
    if not (json_output or pdt_output):
        click.secho("No output file specified. Use --json or --json-pdt.", err=True)
        ctx.exit(1)

    if json_output and pdt_output:
        click.secho("Only one of --json or --json-pdt can be used.", err=True)
        ctx.exit(1)

    if verbose:
        click.secho(f"Resolving dependencies...")

    if netrc_file:
        if not os.path.exists(netrc_file):
            raise Exception(f"Missing netrc file {netrc_file}")

    if not netrc_file:
        netrc_file = os.path.join(os.path.expanduser("~"), ".netrc")
        if not os.path.exists(netrc_file):
            netrc_file = os.path.join(os.path.expanduser("~"), "_netrc")
            if not os.path.exists(netrc_file):
                netrc_file = None

    if netrc_file:
        if verbose:
            click.secho(f"Using netrc file {netrc_file}")
        netrc = Netrc(file=netrc_file)
    else:
        netrc = None

    # TODO: deduplicate me
    direct_dependencies = []

    if PYPI_SIMPLE_URL not in index_urls:
        index_urls = tuple([PYPI_SIMPLE_URL]) + tuple(index_urls)

    invalid_requirement_files = []

    for req_file in requirement_files:
        if not PipRequirementsFileHandler.is_datafile(location=req_file):
            invalid_requirement_files.append(req_file)

    if invalid_requirement_files:
        invalid_requirement_files = "\n".join(invalid_requirement_files)
        click.secho(
            "The following requirement files are not valid pip "
            f"requirement file names: \n{invalid_requirement_files}",
            err=True,
        )
        ctx.exit(1)

    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        for extra_data in dependencies.get_extra_data_from_requirements(requirements_file=req_file):
            index_urls = (*index_urls, *tuple(extra_data.get("extra_index_urls") or []))
        direct_dependencies.extend(deps)

    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        direct_dependencies.append(dep)

    if not direct_dependencies:
        click.secho("Error: no requirements requested.")
        ctx.exit(1)

    if verbose:
        click.secho("direct_dependencies:")
        for dep in direct_dependencies:
            click.secho(f" {dep}")

    # create a resolution environments
    environment = utils_pypi.Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system
    )

    if verbose:
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
                credentials = None
                if netrc:
                    login, password = utils.get_netrc_auth(index_url, netrc)
                    credentials = (
                        dict(login=login, password=password) if login and password else None
                    )
                repo = utils_pypi.PypiSimpleRepository(
                    index_url=index_url,
                    use_cached_index=use_cached_index,
                    credentials=credentials,
                )
                repos.append(repo)

    if verbose:
        click.secho("repos:")
        for repo in repos:
            click.secho(f" {repo}")

    # resolve dependencies proper
    requirements, resolved_dependencies = resolve(
        direct_dependencies=direct_dependencies,
        environment=environment,
        repos=repos,
        as_tree=False,
        max_rounds=max_rounds,
        verbose=verbose,
        pdt_output=pdt_output,
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
        tool_name="python-inspector",
        tool_homepageurl="https://github.com/nexB/python-inspector",
        tool_version=__version__,
        options=cli_options,
        notice=notice,
        warnings=[],
        errors=[],
    )

    if json_output:
        write_output(
            headers=headers,
            requirements=requirements,
            resolved_dependencies=resolved_dependencies,
            json_output=json_output,
        )

    else:
        write_output(
            headers=headers,
            requirements=requirements,
            resolved_dependencies=resolved_dependencies,
            json_output=pdt_output,
            pdt_output=True,
        )

    if verbose:
        click.secho("done!")


def resolve(
    direct_dependencies,
    environment,
    repos=tuple(),
    as_tree=False,
    max_rounds=200000,
    verbose=False,
    pdt_output=False,
):
    """
    Resolve dependencies given a ``direct_dependencies`` list of
    DependentPackage and return a tuple of (initial_requirements,
    resolved_dependencies).
    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively.
    """

    requirements = list(get_requirements_from_direct_dependencies(direct_dependencies))

    resolved_dependencies = get_resolved_dependencies(
        requirements=requirements,
        environment=environment,
        repos=repos,
        as_tree=as_tree,
        max_rounds=max_rounds,
        verbose=verbose,
        pdt_output=pdt_output,
    )

    initial_requirements = [d.to_dict() for d in direct_dependencies]

    return initial_requirements, resolved_dependencies


def get_requirements_from_direct_dependencies(
    direct_dependencies: List[DependentPackage],
) -> List[Requirement]:
    for dependency in direct_dependencies:
        # FIXME We are skipping editable requirements
        # and other pip options for now
        # https://github.com/nexB/python-inspector/issues/41
        if not can_process_dependent_package(dependency):
            continue
        yield Requirement(requirement_string=dependency.extracted_requirement)


def write_output(headers, requirements, resolved_dependencies, json_output, pdt_output=False):
    """
    Write headers, requirements and resolved_dependencies as JSON to ``json_output``.
    Return the output data.
    """
    if not pdt_output:
        output = dict(
            headers=headers,
            requirements=requirements,
            resolved_dependencies=resolved_dependencies,
        )
    else:
        output = resolved_dependencies

    json.dump(output, json_output, indent=2)
    return output


if __name__ == "__main__":
    resolve_dependencies()
