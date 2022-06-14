#
# Copyright (c) Tzu-ping Chung <uranusjr@gmail.com>, nexB Inc. and others.
# SPDX-License-Identifier: ISC AND Apache-2.0
# derived and heavily modified from https://github.com/sarugaku/resolvelib

# See https://github.com/nexB/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import collections
import operator
import os
from typing import List
from typing import Sequence

import packaging.requirements
import packaging.utils
import packaging.version
import requests
from packageurl import PackageURL
from packaging.requirements import Requirement
from resolvelib import AbstractProvider
from resolvelib import Resolver
from resolvelib.reporters import BaseReporter

from _packagedcode.pypi import PypiWheelHandler
from python_inspector import utils_pypi

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


def get_python_version_from_env_tag(python_version: str):
    """
    >>> assert get_python_version_from_env_tag("310") == "3.10"
    >>> assert get_python_version_from_env_tag("39") == "3.9"
    """
    elements = list(python_version)
    elements.insert(1, ".")
    python_version = "".join(elements)
    return python_version


class PythonInputProvider(AbstractProvider):
    def __init__(self, environment=None, repos=tuple()):
        self.environment = environment
        self.repos = repos or []
        self.versions_by_package = {}
        self.dependencies_by_purl = {}

    def identify(self, requirement_or_candidate):
        """Given a requirement, return an identifier for it. Overridden."""
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
        """Produce a sort key for given requirement based on preference. Overridden."""

        transitive = all(p is not None for _, p in information[identifier])
        return transitive, identifier

    def get_versions_for_package(self, name, repo=None):
        """
        Return a list of versions for a package.
        """
        if repo and self.environment:
            return self.get_versions_for_package_from_repo(name, repo)
        else:
            return self.get_versions_for_package_from_pypi_json_api(name)

    def get_versions_for_package_from_repo(self, name, repo):
        """
        Return a list of versions for a package name from a repo
        """
        versions = []
        for version, package in repo._get_package_versions_map(name).items():
            wheels = package.get_supported_wheels(environment=self.environment)
            if list(wheels):
                versions.append(version)
        return versions

    def get_versions_for_package_from_pypi_json_api(self, name):
        """
        Return a list of versions for a package name from the PyPI.org JSON API
        """
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
            return self.get_requirements_for_package_from_pypi_simple(candidate)
        else:
            return self.get_requirements_for_package_from_pypi_json_api(purl)

    def get_requirements_for_package_from_pypi_simple(self, candidate):
        wheels = utils_pypi.download_wheel(
            name=candidate.name,
            version=str(candidate.version),
            environment=self.environment,
            repos=self.repos,
        )
        for wheel in wheels:
            deps = list(
                PypiWheelHandler.parse(os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, wheel))
            )
            assert len(deps) == 1
            deps = deps[0].dependencies
            for dep in deps:
                if dep.scope == "install":
                    yield packaging.requirements.Requirement(str(dep.extracted_requirement))

    def get_requirements_for_package_from_pypi_json_api(self, purl):

        # if no repos are provided use the incorrect but fast JSON API
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
        Generate candidates for the given identifier. Overridden.
        """
        for version in all_versions:
            parsed_version = packaging.version.parse(version)
            if not is_valid_version(parsed_version, requirements, identifier, bad_versions):
                continue
            yield Candidate(name=name, version=parsed_version, extras=extras)

    def _iter_matches(self, identifier, requirements, incompatibilities):
        """
        Yield candidates for the given identifier, requirements and incompatibilities
        """
        name, _, _extras = identifier.partition("[")
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
        """Find all possible candidates that satisfy given constraints. Overridden."""
        candidates = sorted(
            self._iter_matches(identifier, requirements, incompatibilities),
            key=operator.attrgetter("version"),
            reverse=True,
        )
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        """Whether the given requirement can be satisfied by a candidate. Overridden."""
        return candidate.version in requirement.specifier

    def _iter_dependencies(self, candidate):
        """
        Yield dependencies for the given candidate.
        """
        name = packaging.utils.canonicalize_name(candidate.name)
        # TODO: handle extras https://github.com/nexB/python-inspector/issues/10
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
                if r.marker.evaluate(
                    {
                        "extra": "",
                        "python_version": get_python_version_from_env_tag(
                            self.environment.python_version
                        ),
                        "platform_system": self.environment.operating_system.capitalize(),
                    }
                ):
                    yield r

    def get_dependencies(self, candidate):
        """Get dependencies of a candidate. Overridden."""
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
    Return a nested mapping of dependencies.
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


def format_resolution(results, as_tree=False):
    """
    Return a formatted resolution either as a tree or parent/children.
    """
    mapping = results.mapping
    graph = results.graph

    if not as_tree:
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
        as_parent_children.sort(key=lambda d: d["package"])
        return as_parent_children
    else:
        dependencies = []
        for src in get_all_srcs(mapping=mapping, graph=graph):
            dependencies.append(dfs(mapping=mapping, graph=graph, src=src))

        dependencies.sort(key=lambda d: d["package"])
        return dependencies


def get_resolved_dependencies(
    requirements: List[Requirement],
    environment: utils_pypi.Environment = None,
    repos: Sequence[utils_pypi.PypiSimpleRepository] = tuple(),
    as_tree: bool = False,
):
    """
    Return resolved dependencies of a ``requirements`` list of Requirement for
    an ``enviroment`` Environment. The resolved dependencies are formatted as
    parent/children or a nested tree if ``as_tree`` is True.

    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively instead
    """
    resolver = Resolver(
        provider=PythonInputProvider(environment=environment, repos=repos),
        reporter=BaseReporter(),
    )
    results = resolver.resolve(requirements=requirements)
    results = format_resolution(results, as_tree=as_tree)
    return results
