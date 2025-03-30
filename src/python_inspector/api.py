#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://aboutcode-orgnexB/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from netrc import netrc
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Sequence

from packageurl import PackageURL
from packvers.requirements import Requirement
from resolvelib import BaseReporter
from resolvelib import Resolver

from _packagedcode.models import DependentPackage
from _packagedcode.models import PackageData
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import PythonSetupPyHandler
from _packagedcode.pypi import can_process_dependent_package
from python_inspector import DEFAULT_PYTHON_VERSION
from python_inspector import dependencies
from python_inspector import utils
from python_inspector import utils_pypi
from python_inspector.package_data import get_pypi_data_from_purl
from python_inspector.resolution import PythonInputProvider
from python_inspector.resolution import format_pdt_tree
from python_inspector.resolution import format_resolution
from python_inspector.resolution import get_environment_marker_from_environment
from python_inspector.resolution import get_package_list
from python_inspector.resolution import get_python_version_from_env_tag
from python_inspector.resolution import get_reqs_insecurely
from python_inspector.resolution import get_requirements_from_python_manifest
from python_inspector.utils_pypi import PLATFORMS_BY_OS
from python_inspector.utils_pypi import PYPI_SIMPLE_URL
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import valid_python_versions


class Resolution(NamedTuple):
    """
    Return a dependency resolution returned from the ``resolver_api``.

    ``resolution`` is a graph of resolved dependencies.
    ``packages`` is a list of ``PackageData`` objects.
    ``files`` is a parsed list of input file data.
    """

    resolution: Dict
    packages: List[PackageData]
    files: List[Dict]

    def to_dict(self, generic_paths=False):
        files = self.files
        if generic_paths:
            # clean file paths
            for file in files:
                path = file["path"]
                file["path"] = utils.remove_test_data_dir_variable_prefix(path=path)
        return {
            "files": files,
            "packages": [package for package in self.packages],
            "resolution": self.resolution,
        }


def resolve_dependencies(
    requirement_files=tuple(),
    setup_py_file=None,
    specifiers=tuple(),
    python_version=None,
    operating_system=None,
    index_urls=tuple([PYPI_SIMPLE_URL]),
    pdt_output=None,
    netrc_file=None,
    max_rounds=200000,
    use_cached_index=False,
    use_pypi_json_api=False,
    verbose=False,
    analyze_setup_py_insecurely=False,
    prefer_source=False,
    printer=print,
    generic_paths=False,
    ignore_errors=False,
):
    """
    Resolve the dependencies for the package requirements listed in one or
    more ``requirement_files``, one or more ``specifiers`` and one setuptools
    ``setup_py_file`` file.

    Resolve the dependencies for the requested ``python_version`` PYVER and
    ``operating_system`` OS combination defaulting Python version 3.8 and
    linux OS.

    Download from the provided PyPI simple index_urls INDEX(s) URLs defaulting
    to PyPI.org
    """

    if not operating_system:
        raise Exception(f"No operating system provided.")
    if operating_system not in PLATFORMS_BY_OS:
        raise ValueError(
            f"Invalid operating system: {operating_system}. "
            f"Must be one of: {', '.join(PLATFORMS_BY_OS.keys())}"
        )

    if not python_version:
        raise Exception(f"No python version provided.")
    if python_version not in valid_python_versions:
        raise ValueError(
            f"Invalid python version: {python_version}. "
            f"Must be one of: {', '.join(valid_python_versions)}"
        )

    if verbose:
        printer("Resolving dependencies...")

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
            printer(f"Using netrc file {netrc_file}")
        parsed_netrc = netrc(netrc_file)
    else:
        parsed_netrc = None

    # TODO: deduplicate me
    direct_dependencies = []

    files = []

    if PYPI_SIMPLE_URL not in index_urls:
        index_urls = tuple([PYPI_SIMPLE_URL]) + tuple(index_urls)

    # requirements
    for req_file in requirement_files:
        deps = dependencies.get_dependencies_from_requirements(requirements_file=req_file)
        for extra_data in dependencies.get_extra_data_from_requirements(requirements_file=req_file):
            index_urls = (*index_urls, *tuple(extra_data.get("extra_index_urls") or []))
            index_urls = (*index_urls, *tuple(extra_data.get("index_url") or []))
        direct_dependencies.extend(deps)
        package_data = [
            pkg_data.to_dict() for pkg_data in PipRequirementsFileHandler.parse(location=req_file)
        ]
        if generic_paths:
            req_file = utils.remove_test_data_dir_variable_prefix(path=req_file)

        files.append(
            dict(
                type="file",
                path=req_file,
                package_data=package_data,
            )
        )

    # specs
    for specifier in specifiers:
        dep = dependencies.get_dependency(specifier=specifier)
        direct_dependencies.append(dep)

    # setup.py
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
            raise Exception(
                f"Python version {get_python_version_from_env_tag(python_version)} "
                f"is not compatible with setup.py {setup_py_file} "
                f"python_requires {python_requires}",
            )
        if analyze_setup_py_insecurely:
            reqs = list(
                get_reqs_insecurely(
                    setup_py_location=setup_py_file,
                )
            )
            setup_py_file_deps = list(get_dependent_packages_from_reqs(reqs))
            direct_dependencies.extend(setup_py_file_deps)
        else:
            setup_py_file_deps = package_data.dependencies
            for dep in package_data.dependencies:
                # TODO : we need to handle to all the scopes
                if dep.scope == "install":
                    direct_dependencies.append(dep)

            if not package_data.dependencies:
                reqs = get_requirements_from_python_manifest(
                    sdist_location=os.path.dirname(setup_py_file),
                    setup_py_location=setup_py_file,
                    files=[setup_py_file],
                    analyze_setup_py_insecurely=analyze_setup_py_insecurely,
                )
                setup_py_file_deps = list(get_dependent_packages_from_reqs(reqs))
                direct_dependencies.extend(setup_py_file_deps)

        package_data.dependencies = setup_py_file_deps
        file_package_data = [package_data.to_dict()]
        if generic_paths:
            setup_py_file = utils.remove_test_data_dir_variable_prefix(path=setup_py_file)
        files.append(
            dict(
                type="file",
                path=setup_py_file,
                package_data=file_package_data,
            )
        )

    if not direct_dependencies:
        return Resolution(
            packages=[],
            resolution=[],
            files=files,
        )

    if verbose:
        printer("direct_dependencies:")
        for dep in direct_dependencies:
            printer(f" {dep}")

    # create a resolution environments
    environment = utils_pypi.Environment.from_pyver_and_os(
        python_version=python_version, operating_system=operating_system
    )

    if verbose:
        printer(f"environment: {environment}")

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
                if parsed_netrc:
                    login, password = utils.get_netrc_auth(index_url, parsed_netrc)
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
        printer("repos:")
        for repo in repos:
            printer(f" {repo}")

    # resolve dependencies proper
    resolution, purls = resolve(
        direct_dependencies=direct_dependencies,
        environment=environment,
        repos=repos,
        as_tree=False,
        max_rounds=max_rounds,
        pdt_output=pdt_output,
        analyze_setup_py_insecurely=analyze_setup_py_insecurely,
        ignore_errors=ignore_errors,
    )

    packages = []

    for package in purls:
        packages.extend(
            [
                pkg.to_dict()
                for pkg in list(
                    get_pypi_data_from_purl(
                        package, repos=repos, environment=environment, prefer_source=prefer_source
                    )
                )
            ],
        )

    if verbose:
        printer("done!")

    return Resolution(
        packages=packages,
        resolution=resolution,
        files=files,
    )


resolver_api = resolve_dependencies


def resolve(
    direct_dependencies,
    environment,
    repos=tuple(),
    as_tree=False,
    max_rounds=200000,
    pdt_output=False,
    analyze_setup_py_insecurely=False,
    ignore_errors=False,
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
        pdt_output=pdt_output,
        analyze_setup_py_insecurely=analyze_setup_py_insecurely,
        ignore_errors=ignore_errors,
    )

    return resolved_dependencies, packages


def get_resolved_dependencies(
    requirements: List[Requirement],
    environment: Environment = None,
    repos: Sequence[utils_pypi.PypiSimpleRepository] = tuple(),
    as_tree: bool = False,
    max_rounds: int = 200000,
    pdt_output: bool = False,
    analyze_setup_py_insecurely: bool = False,
    ignore_errors: bool = False,
):
    """
    Return resolved dependencies of a ``requirements`` list of Requirement for
    an ``enviroment`` Environment. The resolved dependencies are formatted as
    parent/children or a nested tree if ``as_tree`` is True.

    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively instead
    """
    resolver = Resolver(
        provider=PythonInputProvider(
            environment=environment,
            repos=repos,
            analyze_setup_py_insecurely=analyze_setup_py_insecurely,
            ignore_errors=ignore_errors,
        ),
        reporter=BaseReporter(),
    )
    resolver_results = resolver.resolve(requirements=requirements, max_rounds=max_rounds)
    package_list = get_package_list(results=resolver_results)
    if pdt_output:
        return (format_pdt_tree(resolver_results), package_list)
    return (
        format_resolution(resolver_results, as_tree=as_tree),
        package_list,
    )


def get_requirements_from_direct_dependencies(
    direct_dependencies: List[DependentPackage], environment_marker: Dict
) -> List[Requirement]:
    """
    Yield Requirements from a list of DependentPackages.
    """
    for dependency in direct_dependencies:
        # FIXME We are skipping editable requirements
        # and other pip options for now
        # https://github.com/aboutcode-org/python-inspector/issues/41
        if not can_process_dependent_package(dependency):
            continue
        req = Requirement(requirement_string=dependency.extracted_requirement)
        if req.marker is None:
            yield req
        else:
            if req.marker.evaluate(environment_marker):
                yield req


def get_dependent_packages_from_reqs(requirements: List[Requirement]):
    for req in requirements:
        yield DependentPackage(
            purl=str(
                PackageURL(
                    type="pypi",
                    name=req.name,
                )
            ),
            extracted_requirement=str(req),
            scope="install",
            is_runtime=False,
        )
