# -*- coding: utf-8 -*-
#
# This file is part of Requirements-Builder
# Copyright (C) 2015, 2016, 2017, 2018 CERN.
#
# Requirements-Builder is free software; you can redistribute it and/or
# modify it under the terms of the Revised BSD License; see LICENSE
# file for more details.
#
"""Generate requirements from `setup.py` and `requirements-devel.txt`."""

import ast
import os
import sys

try:
    import configparser
except ImportError:  # pragma: no cover
    import ConfigParser as configparser

import distutils.core

import mock
import setuptools
from commoncode.command import pushd
from packvers.requirements import Requirement


def minver_error(pkg_name):
    """Report error about missing minimum version constraint and exit."""
    print(
        'ERROR: specify minimal version of "{0}" using ' '">=" or "=="'.format(pkg_name),
        file=sys.stderr,
    )
    sys.exit(1)


def build_pkg_name(pkg):
    """Build package name, including extras if present."""
    if pkg.extras:
        return "{0}[{1}]".format(str(pkg.name), ",".join(sorted(pkg.extras)))
    return str(pkg.name)


def iter_requirements(level, extras, setup_file):
    """Iterate over requirements."""
    from pathlib import Path

    setup_file = str(Path(setup_file).absolute())
    result = dict()
    requires = []
    stuff = []
    install_requires = []
    requires_extras = {}
    test_requires = {}
    setup_requires = {}
    # change directory to setup.py path
    with pushd(os.path.dirname(setup_file)):
        with open(setup_file) as sf:
            file_contents = sf.read()
            node = ast.parse(file_contents)
            asnames = {}
            imports = []
            for elem in ast.walk(node):
                # save the asnames to parse aliases later
                if isinstance(elem, ast.Import):
                    for n in elem.names:
                        asnames[(n.asname if n.asname is not None else n.name)] = n.name
            for elem in ast.walk(node):
                # for function imports, e.g. from setuptools import setup; setup()
                if isinstance(elem, ast.ImportFrom) and "setup" in [e.name for e in elem.names]:
                    imports.append(elem.module)
                # for module imports, e.g. import setuptools; setuptools.setup(...)
                elif (
                    isinstance(elem, ast.Expr)
                    and isinstance(elem.value, ast.Call)
                    and isinstance(elem.value.func, ast.Attribute)
                    and isinstance(elem.value.func.value, ast.Name)
                    and elem.value.func.attr == "setup"
                ):
                    name = elem.value.func.value.id
                    if name in asnames.keys():
                        name = asnames[name]
                    imports.append(name)
                # for module imports, e.g. import disttools.core; disttools.core.setup(...)
                elif (
                    isinstance(elem, ast.Expr)
                    and isinstance(elem.value, ast.Call)
                    and isinstance(elem.value.func, ast.Attribute)
                    and isinstance(elem.value.func.value, ast.Attribute)
                    and elem.value.func.attr == "setup"
                ):
                    name = (
                        str(elem.value.func.value.value.id) + "." + str(elem.value.func.value.attr)
                    )
                    if name in asnames.keys():
                        name = asnames[name]
                    imports.append(name)
            setup_providers = [i for i in imports if i in ["distutils.core", "setuptools"]]
            if len(setup_providers) == 0:
                print(
                    f"Warning: unable to recognize setup provider in {setup_file}: "
                    "defaulting to 'distutils.core'."
                )
                setup_provider = "distutils.core"
            elif len(setup_providers) == 1:
                setup_provider = setup_providers[0]
            else:
                print(
                    f"Warning: ambiguous setup provider in {setup_file}: candidates are {setup_providers}"
                    "defaulting to 'distutils.core'."
                )
                setup_provider = "distutils.core"
            with mock.patch.object(eval(setup_provider), "setup") as mock_setup:
                sys.path.append(os.path.dirname(setup_file))
                g = {"__file__": setup_file, "__name__": "__main__"}
                exec(file_contents, g)
            sys.path.pop()
            # removing the assertion `assert g["setup"]`` since this is not true for all cases
            # for example when setuptools.setup() is called instead of setup()

    mock_args, mock_kwargs = mock_setup.call_args
    install_requires = mock_kwargs.get("install_requires", install_requires)

    requires_extras = mock_kwargs.get("extras_require", requires_extras)
    test_requires = mock_kwargs.get("test_requires", test_requires)
    setup_requires = mock_kwargs.get("setup_requires", setup_requires)

    for e, reqs in requires_extras.items():
        # Handle conditions on extras. See pkginfo_to_metadata function
        # in Wheel for details.
        condition = ""
        if ":" in e:
            e, condition = e.split(":", 1)
        if not e or e in extras:
            if condition:
                reqs = ["{0}; {1}".format(r, condition) for r in reqs]
            install_requires.extend(reqs)

    for reqs in test_requires:
        if "test" in extras:
            install_requires.extend(reqs)

    for reqs in setup_requires:
        if "setup" in extras:
            install_requires.extend(reqs)

    for req in install_requires:
        # skip things we already know
        # FIXME be smarter about merging things
        pkg = Requirement(req)
        # Evaluate environment markers skip if not applicable
        if hasattr(pkg, "marker") and pkg.marker is not None:
            if not pkg.marker.evaluate():
                continue
            else:
                # Remove markers from the output
                pkg.marker = None

        if pkg.name in result:
            continue

        specs = pkg.specifier
        specs = {s.operator: s.version for s in specs._specs}
        if ((">=" in specs) and (">" in specs)) or (("<=" in specs) and ("<" in specs)):
            print(
                "ERROR: Do not specify such weird constraints! " '("{0}")'.format(pkg),
                file=sys.stderr,
            )
            sys.exit(1)

        if "==" in specs:
            result[pkg.name] = "{0}=={1}".format(build_pkg_name(pkg), specs["=="])

        elif ">=" in specs:
            if level == "min":
                result[pkg.name] = "{0}=={1}".format(build_pkg_name(pkg), specs[">="])
            else:
                result[pkg.name] = pkg

        elif ">" in specs:
            if level == "min":
                minver_error(build_pkg_name(pkg))
            else:
                result[pkg.name] = pkg

        elif "~=" in specs:
            if level == "min":
                result[pkg.name] = "{0}=={1}".format(build_pkg_name(pkg), specs["~="])
            else:
                ver, _ = os.path.splitext(specs["~="])
                result[pkg.name] = "{0}>={1},=={2}.*".format(build_pkg_name(pkg), specs["~="], ver)

        else:
            if level == "min":
                minver_error(build_pkg_name(pkg))
            else:
                result[pkg.name] = build_pkg_name(pkg)

    for s in stuff:
        yield s

    for k in sorted(result.keys()):
        yield str(result[k])
