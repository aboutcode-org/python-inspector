# -*- coding: utf-8 -*-
#
# This file is part of Requirements-Builder
# Further modified for python-inspector by nexB Inc.
# Copyright (C) 2015, 2016, 2017, 2018 CERN.
#
# Requirements-Builder is free software; you can redistribute it and/or
# modify it under the terms of the Revised BSD License;
# see setup_py_live_eval.py.LICENSE file for more details.
#

"""
Collect requirements from a setup.py file, by doing a live evaluation using AST
parsing and mocking.
"""

import ast
import os
import sys

import mock
from commoncode.command import pushd
from packvers.requirements import Requirement

################################################################################
# The order of these imports matters
try:
    import setuptools

    setuptools_name = setuptools.__name__
except ImportError:
    setuptools_name = "setuptools"

try:
    import distutils.core

    distutils_core_name = distutils.core.__name__
except ImportError:
    distutils_core_name = "distutils.core"
################################################################################


def build_pkg_name(pkg):
    """
    Return a package name from a ``pkg`` package including extras if present.
    """
    if pkg.extras:
        extras = ",".join(sorted(pkg.extras))
        return f"{pkg.name}[{extras}]"
    return str(pkg.name)


def iter_requirements(level, extras, setup_file, echo=print):
    """
    Iterate over setup.py requirements and yield requirement strings.
    """
    from pathlib import Path

    setup_file = str(Path(setup_file).absolute())
    requirement_by_package_name = {}

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

            elif (
                isinstance(elem, ast.Expr)
                and isinstance(elem.value, ast.Call)
                and isinstance(elem.value.func, ast.Attribute)
                and elem.value.func.attr == "setup"
            ):

                # for module imports, e.g. import setuptools; setuptools.setup(...)
                if isinstance(elem.value.func.value, ast.Name):
                    name = elem.value.func.value.id

                # for module imports, e.g. import distutils.core; distutils.core.setup(...)
                elif isinstance(elem.value.func.value, ast.Attribute):
                    name = f"{elem.value.func.value.value.id}.{elem.value.func.value.attr}"

                if name in asnames:
                    name = asnames[name]
                imports.append(name)

        setup_providers = [i for i in imports if i in [distutils_core_name, setuptools_name]]
        if not setup_providers:
            echo(
                f"Warning: unable to recognize setup provider in {setup_file}: "
                "defaulting to 'distutils.core'."
            )
            setup_provider = distutils_core_name

        elif len(setup_providers) == 1:
            setup_provider = setup_providers[0]

        else:
            echo(
                f"Warning: ambiguous setup provider in {setup_file}: candidates are {setup_providers}"
                "defaulting to 'distutils.core'."
            )
            setup_provider = distutils_core_name

        try:
            sys.path.append(os.path.dirname(setup_file))

            with mock.patch.object(eval(setup_provider), "setup") as mock_setup:  # NOQA
                mock_globals = {"__file__": setup_file, "__name__": "__main__"}
                exec(file_contents, mock_globals)
        finally:
            sys.path.pop()

    _mock_args, mock_kwargs = mock_setup.call_args
    install_requires = mock_kwargs.get("install_requires", install_requires)

    requires_extras = mock_kwargs.get("extras_require", requires_extras)
    test_requires = mock_kwargs.get("test_requires", test_requires)
    setup_requires = mock_kwargs.get("setup_requires", setup_requires)

    # FIXME: these do make any sense: we should add a test or setup extra to the install_requires instead
    # but test and setup requires are legacy
    for e, reqs in requires_extras.items():
        # Handle conditions on extras. See pkginfo_to_metadata function
        # in Wheel for details.
        condition = ""
        if ":" in e:
            e, _, condition = e.partition(":")
        if not e or e in extras:
            if condition:
                reqs = [f"{rq}; {condition}" for rq in reqs]
            install_requires.extend(reqs)

    # FIXME: these do not make any sense: we should add a test or setup extra to
    # the install_requires instead
    # but test and setup requires are legacy
    if "test" in extras:
        for reqs in test_requires:
            install_requires.extend(reqs)

    if "setup" in extras:
        for reqs in setup_requires:
            install_requires.extend(reqs)

    for req in install_requires:
        # skip things we already know
        # FIXME be smarter about merging things

        requirement = Requirement(req)

        # Evaluate environment markers skip if not applicable
        if hasattr(requirement, "marker") and requirement.marker is not None:
            # FIXME: we should pass a proepr environment to evaluate markers!!!
            if not requirement.marker.evaluate():
                continue
            else:
                # Remove markers from the output
                requirement.marker = None

        if requirement.name in requirement_by_package_name:
            continue

        pkg_name = build_pkg_name(requirement)

        specifier = requirement.specifier
        comparators = {s.operator: s.version for s in specifier._specs}

        if (">=" in comparators and ">" in comparators) or (
            "<=" in comparators and "<" in comparators
        ):
            raise Exception(f'ERROR: Inconsistent comparators! ("{requirement}")')

        if "==" in comparators:
            comp = comparators["=="]
            req_string = f"{pkg_name}=={comp}"

        elif ">=" in comparators:
            if level == "min":
                comp = comparators[">="]
                req_string = f"{pkg_name}=={comp}"
            else:
                req_string = requirement

        elif "~=" in comparators:
            comp = comparators["~="]
            if level == "min":
                req_string = f"{pkg_name}=={comp}"
            else:
                ver, _ = os.path.splitext(comp)
                req_string = f"{pkg_name}>={comp},=={ver}.*"

        elif ">" in comparators:
            if level == "min":
                raise Exception(
                    f"ERROR: specify minimal version of {build_pkg_name(requirement)!r} "
                    'using  comparators such as ">=" or "=="'
                )
            else:
                req_string = requirement

        else:
            if level == "min":
                raise Exception(
                    f"ERROR: specify minimal version of {pkg_name!r} "
                    'using  comparators such as ">=" or "=="'
                )
            else:
                req_string = pkg_name

        requirement_by_package_name[requirement.name] = req_string

    for _key, value in sorted(requirement_by_package_name.items()):
        yield str(value)
