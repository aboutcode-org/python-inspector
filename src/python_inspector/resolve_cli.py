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

from typing import Dict

import click

from python_inspector import utils_pypi
from python_inspector.api import resolve_dependencies as resolver_api
from python_inspector.cli_utils import FileOptionType
from python_inspector.utils import write_output_in_file

TRACE = False

__version__ = "0.9.5"

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
    type=click.Choice(utils_pypi.valid_python_versions),
    metavar="PYVER",
    show_default=True,
    required=True,
    help="Python version to use for dependency resolution.",
)
@click.option(
    "-o",
    "--operating-system",
    "operating_system",
    type=click.Choice(utils_pypi.PLATFORMS_BY_OS),
    metavar="OS",
    show_default=True,
    required=True,
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
    "--prefer-source",
    is_flag=True,
    help="Prefer source distributions over binary distributions"
    " if no source distribution is available then binary distributions are used",
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
    prefer_source=False,
    verbose=TRACE,
):
    """
    Resolve the dependencies for the package requirements listed in one or
    more REQUIREMENT-FILE file, one or more SPECIFIER and one setuptools
    SETUP-PY-FILE file and save the results as JSON to FILE.

    Resolve the dependencies for the requested ``--python-version`` PYVER and
    ``--operating_system`` OS combination.

    Download from the provided PyPI simple --index-url INDEX(s) URLs defaulting
    to PyPI.org.

    Provide source distributions over binary distributions with the --prefer-source
    option. If no source distribution is available then binary distributions are used.

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

    options = [f"--requirement {rf}" for rf in requirement_files]
    options += [f"--specifier {sp}" for sp in specifiers]
    options += [f"--index-url {iu}" for iu in index_urls]
    options += [f"--python-version {python_version}"]
    options += [f"--operating-system {operating_system}"]
    options += ["--json <file>"]

    notice = (
        "Dependency tree generated with python-inspector.\n"
        "python-inspector is a free software tool from nexB Inc. and others.\n"
        "Visit https://github.com/nexB/python-inspector/ for support and download."
    )

    headers = dict(
        tool_name="python-inspector",
        tool_homepageurl="https://github.com/nexB/python-inspector",
        tool_version=__version__,
        options=options,
        notice=notice,
        warnings=[],
        errors=[],
    )

    try:
        resolution_result: Dict = resolver_api(
            requirement_files=requirement_files,
            setup_py_file=setup_py_file,
            specifiers=specifiers,
            python_version=python_version,
            operating_system=operating_system,
            index_urls=index_urls,
            pdt_output=pdt_output,
            netrc_file=netrc_file,
            max_rounds=max_rounds,
            use_cached_index=use_cached_index,
            use_pypi_json_api=use_pypi_json_api,
            verbose=verbose,
            analyze_setup_py_insecurely=analyze_setup_py_insecurely,
            printer=click.secho,
            prefer_source=prefer_source,
        )
        output = dict(
            headers=headers,
            files=resolution_result.files,
            packages=resolution_result.packages,
            resolved_dependencies_graph=resolution_result.resolution,
        )
        write_output_in_file(
            output=output,
            location=json_output or pdt_output,
        )
    except Exception as exc:
        import traceback

        click.secho(traceback.format_exc(), err=True)
        ctx.exit(1)


if __name__ == "__main__":
    resolve_dependencies()
