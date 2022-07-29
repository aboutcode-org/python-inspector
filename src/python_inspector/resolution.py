#
# Copyright (c) Tzu-ping Chung <uranusjr@gmail.com>, nexB Inc. and others.
# SPDX-License-Identifier: ISC AND Apache-2.0
# derived and heavily modified from https://github.com/sarugaku/resolvelib

# See https://github.com/nexB/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import operator
import os
import tarfile
from typing import Dict
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Sequence
from typing import Union
from zipfile import ZipFile

import packaging.utils
import requests
from packageurl import PackageURL
from packaging.requirements import Requirement
from packaging.version import LegacyVersion
from packaging.version import Version
from packaging.version import parse as parse_version
from resolvelib import AbstractProvider
from resolvelib import Resolver
from resolvelib.reporters import BaseReporter
from resolvelib.structs import DirectedGraph

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import BasePypiHandler
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import PypiWheelHandler
from _packagedcode.pypi import PythonSetupPyHandler
from _packagedcode.pypi import SetupCfgHandler
from _packagedcode.pypi import can_process_dependent_package
from python_inspector import utils_pypi
from python_inspector.utils_pypi import Environment
from python_inspector.utils_pypi import PypiSimpleRepository


class Candidate(NamedTuple):
    """
    A candidate is a package that can be installed.
    """

    name: str
    version: str
    extras: str


class Result(NamedTuple):
    """
    Represent a dependency resolution result from resolvelib.
    Below is the docstring copied from
    https://github.com/sarugaku/resolvelib/blob/0e6ed4efa9ca079512ec999b54f2e5175a3b2111/src/resolvelib/resolvers.py#L454

    The return value is a representation to the final resolution result. It
    is a tuple subclass with three public members:
    * ``mapping``: A dict of resolved candidates. Each key is an identifier
       of a requirement (as returned by the provider's `identify` method),
       and the value is the resolved candidate.
    * ``graph``: A `DirectedGraph` instance representing the dependency tree.
       The vertices are keys of `mapping`, and each edge represents *why*
       a particular package is included. A special vertex `None` is
       included to represent parents of user-supplied requirements.
    * ``criteria``: A dict of "criteria" that hold detailed information on
       how edges in the graph are derived. Each key is an identifier of a
       requirement, and the value is a `Criterion` instance.
    """

    mapping: Dict
    graph: DirectedGraph
    criteria: Dict


def get_response(url: str) -> Dict:
    """
    Return a mapping of the JSON response from fetching ``url``
    or None if the ``url`` cannot be fetched..
    """
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()


def get_requirements_from_distribution(
    handler: BasePypiHandler, location: str
) -> List[Requirement]:
    """
    Return a list of requirements from a source distribution or wheel at
    ``location`` using the provided ``handler`` DatafileHandler for parsing.
    """
    if not os.path.exists(location):
        return []
    deps = list(handler.parse(location))
    assert len(deps) == 1
    return list(get_requirements_from_dependencies(dependencies=deps[0].dependencies))


def is_requirements_file_in_setup_files(setup_files: List[str]) -> bool:
    """
    Return True if the string ``requirements.txt`` is found in any of the ``setup_files`` location
    strings to either a setup.py or setup.cfg file.
    This is an indication that a requirements.txt is likely loaded in the setup.py
    code and we use this as a hint to treat requirements.txt requirements
    as being for the setup.py file.
    """
    for setup_file in setup_files:
        if not os.path.exists(setup_file):
            continue
        with open(setup_file, encoding="utf-8") as f:
            # TODO also consider other file names
            if "requirements.txt" in f.read():
                return True
    return False


def is_valid_version(
    parsed_version: Union[LegacyVersion, Version],
    requirements: Dict,
    identifier: str,
    bad_versions: List[Version],
) -> bool:
    """
    Return True if the parsed_version is valid for the given identifier.
    """
    if (
        any(parsed_version not in r.specifier for r in requirements[identifier])
        or parsed_version in bad_versions
    ):
        return False
    return True


def get_python_version_from_env_tag(python_version: str) -> str:
    """
    >>> assert get_python_version_from_env_tag("310") == "3.10"
    >>> assert get_python_version_from_env_tag("39") == "3.9"
    """
    elements = list(python_version)
    elements.insert(1, ".")
    python_version = "".join(elements)
    return python_version


def fetch_and_extract_sdist(
    repos: List[PypiSimpleRepository], candidate: Candidate, python_version: str
) -> Union[str, None]:
    """
    Fetch and extract the source distribution (sdist) for the ``candidate`` Candidate
    from the `repos` list of PyPiRepository
    and a required ``python_version`` Python version.
    Return the directory location string where the sdist has been extracted.
    Return None if the sdist was not fetched either
    because does not exist in any of the ``repos`` or it does not work with
    the required ``python_version``.
    Raise an Exception if extraction fails.
    """
    sdist = utils_pypi.download_sdist(
        name=candidate.name,
        version=str(candidate.version),
        repos=repos,
        python_version=python_version,
    )

    if not sdist:
        return

    if sdist.endswith(".tar.gz"):
        sdist_file = sdist.rstrip(".tar.gz")
        with tarfile.open(os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, sdist)) as file:
            file.extractall(
                os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file)
            )
    elif sdist.endswith(".zip"):
        sdist_file = sdist.rstrip(".zip")
        with ZipFile(os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, sdist)) as zip:
            zip.extractall(
                os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file)
            )

    else:
        raise Exception(f"Unable to extract sdist {sdist}")

    return os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file, sdist_file)


def get_requirements_from_dependencies(dependencies: List[DependentPackage]) -> List[Requirement]:
    """
    Generate parsed requirements for the given ``dependencies``.
    """
    for dep in dependencies:
        if not dep.purl:
            continue

        # TODO: consider other scopes and using the is_runtime flag
        if dep.scope != "install":
            continue

        # FIXME We are skipping editable requirements
        # and other pip options for now
        # https://github.com/nexB/python-inspector/issues/41
        if can_process_dependent_package(dep):
            yield Requirement(str(dep.extracted_requirement))


def remove_extras(identifier: str) -> str:
    """
    Return the identifier without extras.
    >>> assert remove_extras("foo[bar]") == "foo"
    """
    name, _, _ = identifier.partition("[")
    return name


class PythonInputProvider(AbstractProvider):
    def __init__(self, environment=None, repos=tuple()):
        self.environment = environment
        self.repos = repos or []
        self.versions_by_package = {}
        self.dependencies_by_purl = {}
        self.wheel_or_sdist_by_package = {}

    def identify(self, requirement_or_candidate: Union[Candidate, Requirement]) -> str:
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

    def get_versions_for_package(
        self, name: str, repo: Union[List[PypiSimpleRepository], None] = None
    ) -> List[Version]:
        """
        Return a list of versions for a package.
        """
        if repo and self.environment:
            return self.get_versions_for_package_from_repo(name, repo)
        else:
            return self.get_versions_for_package_from_pypi_json_api(name)

    def get_versions_for_package_from_repo(
        self, name: str, repo: PypiSimpleRepository
    ) -> List[Version]:
        """
        Return a list of versions for a package name from a repo
        """
        versions = []
        for version, package in repo.get_package_versions(name).items():
            python_version = parse_version(
                get_python_version_from_env_tag(python_version=self.environment.python_version)
            )
            wheels = list(package.get_supported_wheels(environment=self.environment))
            if wheels:
                valid_wheel_present = False
                for wheel in wheels:
                    if utils_pypi.valid_distribution(wheel, python_version):
                        valid_wheel_present = True
                if valid_wheel_present:
                    versions.append(version)
            if package.sdist:
                if utils_pypi.valid_distribution(package.sdist, python_version):
                    versions.append(version)
        return versions

    def get_versions_for_package_from_pypi_json_api(self, name: str) -> List[Version]:
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

    def get_requirements_for_package(
        self, purl: PackageURL, candidate: Candidate
    ) -> Generator[Requirement, None, None]:
        """
        Yield requirements for a package.
        """
        if self.repos and self.environment:
            return self.get_requirements_for_package_from_pypi_simple(candidate)
        else:
            return self.get_requirements_for_package_from_pypi_json_api(purl)

    def get_requirements_for_package_from_pypi_simple(
        self, candidate: Candidate
    ) -> List[Requirement]:
        """
        Return requirements for a package from the simple repositories.
        """
        python_version = parse_version(
            get_python_version_from_env_tag(python_version=self.environment.python_version)
        )

        wheels = utils_pypi.download_wheel(
            name=candidate.name,
            version=str(candidate.version),
            environment=self.environment,
            repos=self.repos,
            python_version=python_version,
        )

        has_wheels = False

        for wheel in wheels:
            wheel_location = os.path.join(utils_pypi.CACHE_THIRDPARTY_DIR, wheel)
            deps = get_requirements_from_distribution(
                handler=PypiWheelHandler,
                location=wheel_location,
            )
            if deps:
                has_wheels = True
                yield from deps

        if not has_wheels:
            sdist_location = fetch_and_extract_sdist(
                repos=self.repos, candidate=candidate, python_version=python_version
            )

            if sdist_location:
                setup_py_location = os.path.join(
                    sdist_location,
                    "setup.py",
                )
                setup_cfg_location = os.path.join(
                    sdist_location,
                    "setup.cfg",
                )

                location_by_sdist_parser = {
                    PythonSetupPyHandler: setup_py_location,
                    SetupCfgHandler: setup_cfg_location,
                }

                deps_in_setup = False

                for handler, location in location_by_sdist_parser.items():
                    deps = get_requirements_from_distribution(
                        handler=handler,
                        location=location,
                    )
                    if deps:
                        deps_in_setup = True
                        yield from deps

                requirement_location = os.path.join(
                    sdist_location,
                    "requirements.txt",
                )
                if not deps_in_setup and is_requirements_file_in_setup_files(
                    setup_files=[setup_py_location, setup_cfg_location]
                ):
                    deps = get_requirements_from_distribution(
                        handler=PipRequirementsFileHandler,
                        location=requirement_location,
                    )
                    if deps:
                        yield from deps

    def get_requirements_for_package_from_pypi_json_api(
        self, purl: PackageURL
    ) -> List[Requirement]:
        """
        Return requirements for a package from the PyPI.org JSON API
        """
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
            yield Requirement(dependency)

    def get_candidates(
        self,
        all_versions: List[str],
        requirements: List[Requirement],
        identifier: str,
        bad_versions: List[str],
        name: str,
        extras: Dict,
    ) -> Generator[Candidate, None, None]:
        """
        Generate candidates for the given identifier. Overridden.
        """
        for version in all_versions:
            parsed_version = parse_version(version)
            if not is_valid_version(
                parsed_version=parsed_version,
                requirements=requirements,
                identifier=identifier,
                bad_versions=bad_versions,
            ):
                continue
            yield Candidate(name=name, version=parsed_version, extras=extras)

    def _iter_matches(
        self,
        identifier: str,
        requirements: List[Requirement],
        incompatibilities: Dict,
    ) -> Generator[Candidate, None, None]:
        """
        Yield candidates for the given identifier, requirements and incompatibilities
        """
        name = remove_extras(identifier=identifier)
        bad_versions = {c.version for c in incompatibilities[identifier]}
        extras = {e for r in requirements[identifier] for e in r.extras}
        if not self.repos:
            all_versions = self.get_versions_for_package(name=name)
            yield from self.get_candidates(
                all_versions, requirements, identifier, bad_versions, name, extras
            )
        else:
            for repo in self.repos:
                all_versions = self.get_versions_for_package(name=name, repo=repo)
                yield from self.get_candidates(
                    all_versions, requirements, identifier, bad_versions, name, extras
                )

    def find_matches(
        self,
        identifier: str,
        requirements: List[Requirement],
        incompatibilities: Dict,
    ) -> List[Candidate]:
        """Find all possible candidates that satisfy given constraints. Overridden."""
        candidates = sorted(
            self._iter_matches(identifier, requirements, incompatibilities),
            key=operator.attrgetter("version"),
            reverse=True,
        )
        return candidates

    def is_satisfied_by(self, requirement: Requirement, candidate: Candidate) -> bool:
        """Whether the given requirement can be satisfied by a candidate. Overridden."""
        return candidate.version in requirement.specifier

    def _iter_dependencies(self, candidate: Candidate) -> Generator[Requirement, None, None]:
        """
        Yield dependencies for the given candidate.
        """
        name = packaging.utils.canonicalize_name(candidate.name)
        # TODO: handle extras https://github.com/nexB/python-inspector/issues/10
        if candidate.extras:
            r = f"{name}=={candidate.version}"
            yield Requirement(r)

        purl = PackageURL(
            type="pypi",
            name=name,
            version=str(candidate.version),
        )

        for r in self.get_requirements_for_package(purl=purl, candidate=candidate):
            if r.marker is None:
                yield r
            else:
                if r.marker.evaluate(
                    {
                        "extra": "",
                        "python_version": get_python_version_from_env_tag(
                            python_version=self.environment.python_version
                        ),
                        "platform_system": self.environment.operating_system.capitalize(),
                        "sys_platform": self.environment.operating_system,
                    }
                ):
                    yield r

    def get_dependencies(self, candidate: Candidate) -> List[Requirement]:
        """Get dependencies of a candidate. Overridden."""
        return list(self._iter_dependencies(candidate))


def get_wheel_download_urls(
    purl: PackageURL,
    repos: List[PypiSimpleRepository],
    environment: Environment,
    python_version: str,
) -> List[str]:
    """
    Return a list of download urls for the given purl.
    """
    for repo in repos:
        for wheel in utils_pypi.get_supported_and_valid_wheels(
            repo=repo,
            name=purl.name,
            version=purl.version,
            environment=environment,
            python_version=python_version,
        ):
            yield wheel.download_url


def get_sdist_download_url(
    purl: PackageURL, repos: List[PypiSimpleRepository], python_version: str
) -> str:
    """
    Return a list of download urls for the given purl.
    """
    for repo in repos:
        sdist = utils_pypi.get_valid_sdist(
            repo=repo,
            name=purl.name,
            version=purl.version,
            python_version=python_version,
        )
        if sdist:
            return sdist.download_url


def get_all_srcs(mapping: Dict, graph: DirectedGraph):
    """
    Return a list of all sources in the graph.
    """
    for name in mapping.keys():
        if list(graph.iter_parents(name)) == [None]:
            yield name


def dfs(mapping: Dict, graph: DirectedGraph, src: str):
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


def format_resolution(
    results: Result, environment: Environment, repos: List[PypiSimpleRepository], as_tree=False
):
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
            python_version = get_python_version_from_env_tag(
                python_version=environment.python_version
            )
            wheel_urls = list(
                get_wheel_download_urls(
                    purl=parent_purl,
                    repos=repos,
                    environment=environment,
                    python_version=python_version,
                )
            )
            sdist_url = get_sdist_download_url(
                purl=parent_purl,
                repos=repos,
                python_version=python_version,
            )
            parent_children = dict(
                package=str(parent_purl),
                dependencies=dependencies,
                wheel_urls=list(dict.fromkeys(wheel_urls)),
                sdist_url=sdist_url,
            )
            as_parent_children.append(parent_children)
        as_parent_children.sort(key=lambda d: d["package"])
        return as_parent_children
    else:
        dependencies = []
        for src in get_all_srcs(mapping=mapping, graph=graph):
            dependencies.append(dfs(mapping=mapping, graph=graph, src=src))

        dependencies.sort(key=lambda d: d["package"])
        return dependencies


def pdt_dfs(mapping, graph, src):
    """
    Return a nested mapping of dependencies.

    This takes ``mapping`` and ``graph`` as input. And do a dfs
    (aka. depth-first search see https://en.wikipedia.org/wiki/Depth-first_search)
    on the ``graph`` to get the dependencies of the given ``src``.
    And use the ``mapping`` to get the version of the given dependency.
    """
    children = list(graph.iter_children(src))
    if not children:
        return dict(
            key=src, package_name=src, installed_version=str(mapping[src].version), dependencies=[]
        )
    # recurse
    dependencies = [pdt_dfs(mapping, graph, c) for c in children]
    dependencies.sort(key=lambda d: d["key"])
    return dict(
        key=src,
        package_name=src,
        installed_version=str(mapping[src].version),
        dependencies=dependencies,
    )


def format_pdt_tree(results):
    """
    Return a formatted tree of dependencies in the style of pipdeptree.
    """
    mapping = results.mapping
    graph = results.graph
    dependencies = []
    for src in get_all_srcs(mapping=mapping, graph=graph):
        dependencies.append(pdt_dfs(mapping=mapping, graph=graph, src=src))
    dependencies.sort(key=lambda d: d["key"])
    return dependencies


def get_resolved_dependencies(
    requirements: List[Requirement],
    environment: Environment = None,
    repos: Sequence[PypiSimpleRepository] = tuple(),
    as_tree: bool = False,
    max_rounds: int = 200000,
    verbose: bool = False,
    pdt_output: bool = False,
):
    """
    Return resolved dependencies of a ``requirements`` list of Requirement for
    an ``enviroment`` Environment. The resolved dependencies are formatted as
    parent/children or a nested tree if ``as_tree`` is True.

    Used the provided ``repos`` list of PypiSimpleRepository.
    If empty, use instead the PyPI.org JSON API exclusively instead
    """
    try:
        resolver = Resolver(
            provider=PythonInputProvider(environment=environment, repos=repos),
            reporter=BaseReporter(),
        )
        resolver_results = resolver.resolve(requirements=requirements, max_rounds=max_rounds)
        if pdt_output:
            return format_pdt_tree(resolver_results)
        return format_resolution(
            resolver_results, as_tree=as_tree, environment=environment, repos=repos
        )
    except Exception as e:
        if verbose:
            import click

            click.secho(f"{e!r}", err=True)
