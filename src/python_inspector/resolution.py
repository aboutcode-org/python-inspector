#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import collections
import operator
import os
from typing import List

import packaging.markers
import packaging.requirements
import packaging.specifiers
import packaging.utils
import packaging.version
import requests
from packageurl import PackageURL
from packaging.requirements import Requirement
from resolvelib import AbstractProvider
from resolvelib import Resolver
from resolvelib.reporters import BaseReporter

from _packagedcode.pypi import PypiWheelHandler
from python_inspector.utils_pypi import CACHE_THIRDPARTY_DIR
from python_inspector.utils_pypi import PYPI_PUBLIC_REPO
from python_inspector.utils_pypi import PYPI_SIMPLE_URL
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository
from python_inspector.utils_pypi import download_wheel

Candidate = collections.namedtuple("Candidate", "name version extras")


def get_response(url):
    """
    Return a response for the given url.
    """
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None


def is_valid_version(parsed_version, requirements, identifier, bad_versions):
    """
    Return True if the parsed_version is valid for the given identifier.
    """
    if (
        any(parsed_version not in r.specifier for r in requirements[identifier])
        or parsed_version in bad_versions
    ):
        return False
    return True


class PythonInputProvider(AbstractProvider):
    def __init__(self, environment=None, repos=[]):
        self.environment = environment
        self.repos = repos
        self.versions_by_package = {}
        self.dependencies_by_purl = {}

    def identify(self, requirement_or_candidate):
        name = packaging.utils.canonicalize_name(requirement_or_candidate.name)
        if requirement_or_candidate.extras:
            extras_str = ",".join(sorted(requirement_or_candidate.extras))
            return "{}[{}]".format(name, extras_str)
        return name

    def get_preference(
        self,
        identifier,
        resolutions,
        candidates,
        information,
        backtrack_causes,
    ):
        transitive = all(p is not None for _, p in information[identifier])
        return (transitive, identifier)

    def get_versions_for_package(self, name, repo=None):
        """
        Return a list of versions for a package.
        """
        versions = []
        if repo and self.environment:
            for version, package in repo._get_package_versions_map(name).items():
                wheels = package.get_supported_wheels(environment=self.environment)
                if list(wheels):
                    versions.append(version)
        else:
            if name not in self.versions_by_package:
                api_url = f"https://pypi.org/pypi/{name}/json"
                resp = get_response(api_url)
                if not resp:
                    self.versions_by_package[name] = []
                releases = resp.get("releases") or {}
                self.versions_by_package[name] = releases.keys() or []
            versions = self.versions_by_package[name]
        return versions

    def get_requirements_for_package(self, purl, candidate):
        """
        Yield requirements for a package.
        """
        if self.repos and self.environment:
            wheels = download_wheel(
                name=candidate.name,
                version=str(candidate.version),
                environment=self.environment,
                repos=self.repos,
            )
            for wheel in wheels:
                deps = list(PypiWheelHandler.parse(os.path.join(CACHE_THIRDPARTY_DIR, wheel)))
                assert len(deps) == 1
                deps = deps[0].dependencies
                for dep in deps:
                    if dep.scope == "install":
                        yield packaging.requirements.Requirement(str(dep.extracted_requirement))
        else:
            if str(purl) not in self.dependencies_by_purl:
                api_url = f"https://pypi.org/pypi/{purl.name}/{purl.version}/json"
                resp = get_response(api_url)
                if not resp:
                    self.dependencies_by_purl[str(purl)] = []
                info = resp.get("info") or {}
                requires_dist = info.get("requires_dist") or []
                self.dependencies_by_purl[str(purl)] = requires_dist
            for dependency in self.dependencies_by_purl[str(purl)]:
                yield packaging.requirements.Requirement(dependency)

    def get_candidates(self, all_versions, requirements, identifier, bad_versions, name, extras):
        """
        Generate candidates for the given identifier.
        """
        for version in all_versions:
            parsed_version = packaging.version.parse(version)
            if not is_valid_version(parsed_version, requirements, identifier, bad_versions):
                continue
            yield Candidate(name=name, version=parsed_version, extras=extras)

    def _iter_matches(self, identifier, requirements, incompatibilities):
        """
        Return a list of candidates for the given identifier.
        """
        name, _, _ = identifier.partition("[")
        bad_versions = {c.version for c in incompatibilities[identifier]}
        extras = {e for r in requirements[identifier] for e in r.extras}
        if not self.repos:
            all_versions = self.get_versions_for_package(name)
            yield from self.get_candidates(
                all_versions, requirements, identifier, bad_versions, name, extras
            )
        else:
            for repo in self.repos:
                all_versions = self.get_versions_for_package(name, repo)
                yield from self.get_candidates(
                    all_versions, requirements, identifier, bad_versions, name, extras
                )

    def find_matches(self, identifier, requirements, incompatibilities):
        candidates = sorted(
            self._iter_matches(identifier, requirements, incompatibilities),
            key=operator.attrgetter("version"),
            reverse=True,
        )
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        return candidate.version in requirement.specifier

    def _iter_dependencies(self, candidate):
        """
        Yield dependencies for the given candidate.
        """
        name = packaging.utils.canonicalize_name(candidate.name)
        if candidate.extras:
            r = f"{name}=={candidate.version}"
            yield packaging.requirements.Requirement(r)
        purl = PackageURL(
            type="pypi",
            name=name,
            version=str(candidate.version),
        )
        for r in self.get_requirements_for_package(purl, candidate):
            if r.marker is None:
                yield r
            else:
                if r.marker.evaluate({"extra": ""}):
                    yield r

    def get_dependencies(self, candidate):
        return list(self._iter_dependencies(candidate))


def get_all_srcs(mapping, graph):
    """
    Return a list of all sources in the graph.
    """
    for name in mapping.keys():
        if list(graph.iter_parents(name)) == [None]:
            yield name


def dfs(mapping, graph, src):
    """
    Return a recursive mapping of dependencies.
    """
    children = list(graph.iter_children(src))
    src_purl = PackageURL(
        type="pypi",
        name=src,
        version=str(mapping[src].version),
    )
    if not children:
        return dict(package=str(src_purl), dependencies=[])

    return dict(
        package=str(src_purl),
        dependencies=sorted([dfs(mapping, graph, c) for c in children], key=lambda d: d["package"]),
    )


def format_resolution(result):
    """
    Return a formatted resolution.
    """
    mapping = result.mapping
    graph = result.graph
    as_list = [
        str(
            PackageURL(
                type="pypi",
                name=name,
                version=str(candidate.version),
            )
        )
        for name, candidate in mapping.items()
    ]

    as_parent_children = []
    parents = mapping.keys()
    for parent in parents:
        parent_purl = PackageURL(
            type="pypi",
            name=parent,
            version=str(mapping[parent].version),
        )
        dependencies = []
        for dependency in graph.iter_children(parent):
            dep_purl = PackageURL(
                type="pypi",
                name=dependency,
                version=str(mapping[dependency].version),
            )
            dependencies.append(str(dep_purl))
        dependencies.sort()
        parent_children = dict(package=str(parent_purl), dependencies=dependencies)
        as_parent_children.append(parent_children)

    srcs = list(get_all_srcs(mapping=mapping, graph=graph))
    dependencies = []
    for src in srcs:
        dependencies.append(dfs(mapping=mapping, graph=graph, src=src))

    as_list.sort()
    as_parent_children.sort(key=lambda d: d["package"])
    dependencies.sort(key=lambda d: d["package"])
    as_tree = dict(dependencies=dependencies)
    return as_list, as_parent_children, as_tree


def pypi_simple_repo_in_repos(repos: PypiSimpleRepository):
    """
    Return True if simple pypi index_url is present in any of the repos
    """
    for repo in repos:
        if repo.index_url == PYPI_SIMPLE_URL:
            return True
    return False


def resolution(
    requirements: List[Requirement],
    environment: Environment = None,
    repos: List[PypiSimpleRepository] = [],
    return_as_parent_children: bool = True,
    return_as_tree: bool = False,
    return_as_list: bool = False,
):
    """
    Return a resolution for the given requirements.
    """
    if repos and not pypi_simple_repo_in_repos(repos):
        repos.append(PYPI_PUBLIC_REPO)
    resolver = Resolver(PythonInputProvider(environment, repos), BaseReporter())
    as_list, as_parent_children, as_tree = format_resolution(resolver.resolve(requirements))
    if return_as_parent_children:
        return as_parent_children
    if return_as_tree:
        return as_tree
    if return_as_list:
        return as_list
