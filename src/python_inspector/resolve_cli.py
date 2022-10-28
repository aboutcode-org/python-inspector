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
from typing import Dict
from typing import List

import click
from packaging.requirements import Requirement
from tinynetrc import Netrc

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import PythonSetupPyHandler
from _packagedcode.pypi import can_process_dependent_package
from python_inspector import dependencies
from python_inspector import utils
from python_inspector import utils_pypi
from python_inspector.cli_utils import FileOptionType
from python_inspector.package_data import get_pypi_data_from_purl
from python_inspector.resolution import contain_string
from python_inspector.resolution import get_deps_from_distribution
from python_inspector.resolution import get_environment_marker_from_environment
from python_inspector.resolution import get_python_version_from_env_tag
from python_inspector.resolution import get_resolved_dependencies
from python_inspector.resolution import parse_deps_from_setup_py_insecurely

TRACE = False

__version__ = "0.8.5"

DEFAULT_PYTHON_VERSION = "38"
PYPI_SIMPLE_URL = "https://pypi.org/simple"


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"Python-inspector version: {__version__}")
    ctx.exit()


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
    "-s",
    "--setup-py",
    "setup_py_file",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    metavar="SETUP-PY-FILE",
    required=False,
    help="Path to setuptools setup.py file listing dependencies and metadata. "
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
    "-n",
    "--netrc",
    "netrc_file",
    type=click.Path(exists=True, readable=True, path_type=str, dir_okay=False),
    metavar="NETRC-FILE",
    hidden=True,
    required=False,
    help="Netrc file to use for authentication. ",
)
@click.option(
    "--max-rounds",
    "max_rounds",
    hidden=True,
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
    "--analyze-setup-py-insecurely",
    is_flag=True,
    help="Enable collection of requirements in setup.py that compute these"
    " dynamically. This is an insecure operation as it can run arbitrary code.",
)
@click.option(
    "--verbose",
    is_flag=True,
    hidden=True,
    help="Enable debug output.",
)
@click.option(
    "-V",
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=print_version,
    help="Show the version and exit.",
)
@click.help_option("-h", "--help")
def resolve_dependencies(
    ctx,
    requirement_files,
    setup_py_file,
    specifiers,
    python_version,
    operating_system,
    index_urls,
    json_output,
    pdt_output,
    netrc_file,
    max_rounds,
    use_cached_index=False,
    use_pypi_json_api=False,
    analyze_setup_py_insecurely=False,
    verbose=TRACE,
):
    """
    Resolve the dependencies for the package requirements listed in one or
    more REQUIREMENT-FILE file, one or more SPECIFIER and one setuptools
    SETUP-PY-FILE file and save the results as JSON to FILE.

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

    files = []

    if PYPI_SIMPLE_URL not in index_urls:
        index_urls = tuple([PYPI_SIMPLE_URL]) + tuple(index_urls)

    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        for extra_data in dependencies.get_extra_data_from_requirements(requirements_file=req_file):
            index_urls = (*index_urls, *tuple(extra_data.get("extra_index_urls") or []))
        direct_dependencies.extend(deps)
        package_data = [
            pkg_data.to_dict() for pkg_data in PipRequirementsFileHandler.parse(location=req_file)
        ]
        files.append(
            dict(
                type="file",
                path=req_file,
                package_data=package_data,
            )
        )

    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        direct_dependencies.append(dep)

    if setup_py_file:
        package_data = list(PythonSetupPyHandler.parse(location=setup_py_file))
        assert len(package_data) == 1
        package_data = package_data[0]
        # validate if python require matches our current python version
        python_requires = package_data.extra_data.get("python_requires")
        if not utils_pypi.valid_python_version(
            python_version=get_python_version_from_env_tag(python_version),
            python_requires=python_requires,
        ):
            click.secho(
                f"Python version {get_python_version_from_env_tag(python_version)} "
                f"is not compatible with setup.py {setup_py_file} "
                f"python_requires {python_requires}",
                err=True,
            )
            ctx.exit(1)

        setup_py_file_deps = package_data.dependencies
        for dep in package_data.dependencies:
            # TODO : we need to handle to all the scopes
            if dep.scope == "install":
                direct_dependencies.append(dep)

        if not package_data.dependencies:
            has_deps = False
            if contain_string(string="requirements.txt", files=[setup_py_file]):
                # Look in requirements file if and only if thy are refered in setup.py or setup.cfg
                # And no deps have been yielded by requirements file.

                location = os.path.dirname(setup_py_file)
                requirement_location = os.path.join(
                    location,
                    "requirements.txt",
                )
                deps = get_deps_from_distribution(
                    handler=PipRequirementsFileHandler,
                    location=requirement_location,
                )
                if deps:
                    setup_py_file_deps = list(deps)
                    has_deps = True
                    direct_dependencies.extend(deps)

            if not has_deps and contain_string(string="_require", files=[setup_py_file]):
                if analyze_setup_py_insecurely:
                    insecure_setup_py_deps = list(
                        parse_deps_from_setup_py_insecurely(setup_py=setup_py_file)
                    )
                    setup_py_file_deps = insecure_setup_py_deps
                    direct_dependencies.extend(insecure_setup_py_deps)
                else:
                    raise Exception("Unable to collect setup.py dependencies securely")

        package_data.dependencies = setup_py_file_deps
        file_package_data = [package_data.to_dict()]
        files.append(
            dict(
                type="file",
                path=setup_py_file,
                package_data=file_package_data,
            )
        )

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
    resolved_dependencies, purls = resolve(
        direct_dependencies=direct_dependencies,
        environment=environment,
        repos=repos,
        as_tree=False,
        max_rounds=max_rounds,
        verbose=verbose,
        pdt_output=pdt_output,
        analyze_setup_py_insecurely=analyze_setup_py_insecurely,
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
        "Visit https://github.com/nexB/python-inspector/ for support and download."
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

    packages = []

    for package in purls:
        packages.extend(
            [
                pkg.to_dict()
                for pkg in list(
                    get_pypi_data_from_purl(package, repos=repos, environment=environment)
                )
            ],
        )

    output = dict(
        headers=headers,
        files=files,
        resolved_dependencies_graph=resolved_dependencies,
        packages=packages,
    )

    write_output(
        json_output=json_output or pdt_output,
        output=output,
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
    analyze_setup_py_insecurely=False,
):
    """
    Resolve dependencies given a ``direct_dependencies`` list of
    DependentPackage and return a tuple of (initial_requirements,
    resolved_dependencies).
    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively.
    """

    environment_marker = get_environment_marker_from_environment(environment)

    requirements = list(
        get_requirements_from_direct_dependencies(
            direct_dependencies=direct_dependencies, environment_marker=environment_marker
        )
    )

    resolved_dependencies, packages = get_resolved_dependencies(
        requirements=requirements,
        environment=environment,
        repos=repos,
        as_tree=as_tree,
        max_rounds=max_rounds,
        verbose=verbose,
        pdt_output=pdt_output,
        analyze_setup_py_insecurely=analyze_setup_py_insecurely,
    )

    return resolved_dependencies, packages


def get_requirements_from_direct_dependencies(
    direct_dependencies: List[DependentPackage], environment_marker: Dict
) -> List[Requirement]:
    for dependency in direct_dependencies:
        # FIXME We are skipping editable requirements
        # and other pip options for now
        # https://github.com/nexB/python-inspector/issues/41
        if not can_process_dependent_package(dependency):
            continue
        req = Requirement(requirement_string=dependency.extracted_requirement)
        if req.marker is None:
            yield req
        else:
            if req.marker.evaluate(environment_marker):
                yield req


def write_output(output, json_output):
    """
    Write headers, requirements and resolved_dependencies as JSON to ``json_output``.
    Return the output data.
    """
    json.dump(output, json_output, indent=2)
    return output


if __name__ == "__main__":
    resolve_dependencies()
