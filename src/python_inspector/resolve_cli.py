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

from typing import Dict

import click

from python_inspector import utils_pypi
from python_inspector.cli_utils import FileOptionType
from python_inspector.utils import write_output_in_file

TRACE = False

__version__ = "0.13.0"

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
    multiple=False,
    required=False,
    help="Path to setuptools setup.py file listing dependencies and metadata.",
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
    help="Python version to use for dependency resolution. One of "
    + ", ".join(utils_pypi.PYTHON_DOT_VERSIONS_BY_VER.values()),
)
@click.option(
    "-o",
    "--operating-system",
    "operating_system",
    type=click.Choice(utils_pypi.PLATFORMS_BY_OS),
    metavar="OS",
    show_default=True,
    required=True,
    help="OS to use for dependency resolution. One of " + ", ".join(utils_pypi.PLATFORMS_BY_OS),
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
    help="Netrc file to use for authentication.",
)
@click.option(
    "--max-rounds",
    "max_rounds",
    hidden=True,
    type=int,
    default=200000,
    help="Increase the maximum number of resolution rounds. "
    "Use in the rare cases where the resolution graph is very deep.",
)
@click.option(
    "--use-cached-index",
    is_flag=True,
    hidden=True,
    help="Use cached on-disk PyPI simple package indexes "
    "and do not refetch package index if cache is present.",
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
    help="Enable collection of requirements in setup.py that compute these "
    "dynamically. This is an insecure operation as it can run arbitrary code.",
)
@click.option(
    "--prefer-source",
    is_flag=True,
    help="Prefer source distributions over binary distributions if no source "
    "distribution is available then binary distributions are used",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose debug output.",
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
@click.option(
    "--ignore-errors", is_flag=True, default=False, help="Ignore errors and continue execution."
)
@click.help_option("-h", "--help")
@click.option(
    "--generic-paths",
    is_flag=True,
    hidden=True,
    help="Use generic or truncated paths in the JSON output header and files sections. "
    "Used only for testing to avoid absolute paths and paths changing at each run.",
)
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
    generic_paths=False,
    ignore_errors=False,
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
    from python_inspector.api import resolve_dependencies as resolver_api

    if not (json_output or pdt_output):
        click.secho("No output file specified. Use --json or --json-pdt.", err=True)
        ctx.exit(1)

    if json_output and pdt_output:
        click.secho("Only one of --json or --json-pdt can be used.", err=True)
        ctx.exit(1)

    options = get_pretty_options(ctx, generic_paths=generic_paths)

    notice = (
        "Dependency tree generated with python-inspector.\n"
        "python-inspector is a free software tool from nexB Inc. and others.\n"
        "Visit https://github.com/aboutcode-org/python-inspector/ for support and download."
    )

    headers = dict(
        tool_name="python-inspector",
        tool_homepageurl="https://github.com/aboutcode-org/python-inspector",
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
            ignore_errors=ignore_errors,
            generic_paths=generic_paths,
        )

        files = resolution_result.files or []
        output = dict(
            headers=headers,
            files=files,
            packages=resolution_result.packages,
            resolved_dependencies_graph=resolution_result.resolution,
        )
        write_output_in_file(
            output=output,
            location=json_output or pdt_output,
        )
    except Exception:
        import traceback

        click.secho(traceback.format_exc(), err=True)
        ctx.exit(1)


def get_pretty_options(ctx, generic_paths=False):
    """
    Return a sorted list of formatted strings for the selected CLI options of
    the `ctx` Click.context, putting arguments first then options:

        ["~/some/path", "--license", ...]

    Skip options that are hidden or flags that are not set.
    If ``generic_paths`` is True, click.File and click.Path parameters are made
    "generic" replacing their value with a placeholder. This is used mostly for
    testing.
    """

    args = []
    options = []

    param_values = ctx.params
    for param in ctx.command.params:
        name = param.name
        value = param_values.get(name)

        if param.is_eager:
            continue

        if getattr(param, "hidden", False):
            continue

        if value == param.default:
            continue

        if value in (None, False):
            continue

        if value in (tuple(), []):
            # option with multiple values, the value is a emoty tuple
            continue

        # opts is a list of CLI options as in "--verbose": the last opt is
        # the CLI option long form by convention
        cli_opt = param.opts[-1]

        if not isinstance(value, (tuple, list)):
            value = [value]

        for val in value:
            val = get_pretty_value(param_type=param.type, value=val, generic_paths=generic_paths)

            if isinstance(param, click.Argument):
                args.append(val)
            else:
                # an option
                if val is True:
                    # mere flag... do not add the "true" value
                    options.append(f"{cli_opt}")
                else:
                    options.append(f"{cli_opt} {val}")

    return sorted(args) + sorted(options)


def get_pretty_value(param_type, value, generic_paths=False):
    """
    Return pretty formatted string extracted from a parameter ``value``.
    Make paths generic (by using a placeholder or truncating the path) if
    ``generic_paths`` is True.
    """
    if isinstance(param_type, (click.Path, click.File)):
        return get_pretty_path(param_type, value, generic_paths)

    elif not (value is None or isinstance(value, (str, bytes, tuple, list, dict, bool))):
        # coerce to string for non-basic types
        return repr(value)

    else:
        return value


def get_pretty_path(param_type, value, generic_paths=False):
    """
    Return a pretty path value for a Path or File option. Truncate the path or
    use a placeholder as needed if ``generic_paths`` is True. Used for testing.
    """
    from python_inspector.utils import remove_test_data_dir_variable_prefix

    if value == "-":
        return value

    if isinstance(param_type, click.Path):
        if generic_paths:
            return remove_test_data_dir_variable_prefix(path=value)
        return value

    elif isinstance(param_type, click.File):
        # the value cannot be displayed as-is as this may be an opened file-
        # like object
        vname = getattr(value, "name", None)
        if not vname:
            return "<file>"
        else:
            value = vname

        if generic_paths:
            return remove_test_data_dir_variable_prefix(path=value, placeholder="<file>")

    return value


if __name__ == "__main__":
    resolve_dependencies()
