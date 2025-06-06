#
# Copyright (c) Tzu-ping Chung <uranusjr@gmail.com>, nexB Inc. and others.
# SPDX-License-Identifier: ISC AND Apache-2.0
# derived and heavily modified from https://github.com/sarugaku/resolvelib

# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import ast
import asyncio
import operator
import os
import tarfile
from traceback import format_exc
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Tuple
from typing import Type
from typing import Union
from zipfile import ZipFile

import packvers.utils
from packageurl import PackageURL
from packvers.requirements import Requirement
from packvers.version import LegacyVersion
from packvers.version import Version
from packvers.version import parse as parse_version
from resolvelib import AbstractProvider
from resolvelib.structs import DirectedGraph

from _packagedcode.models import DependentPackage
from _packagedcode.pypi import BasePypiHandler
from _packagedcode.pypi import PipRequirementsFileHandler
from _packagedcode.pypi import PypiWheelHandler
from _packagedcode.pypi import PythonSetupPyHandler
from _packagedcode.pypi import SetupCfgHandler
from _packagedcode.pypi import can_process_dependent_package
from python_inspector import pyinspector_settings as settings
from python_inspector import utils_pypi
from python_inspector.error import NoVersionsFound
from python_inspector.setup_py_live_eval import iter_requirements
from python_inspector.utils import Candidate
from python_inspector.utils import contain_string
from python_inspector.utils import get_response_async
from python_inspector.utils_pypi import PypiSimpleRepository


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


def get_requirements_from_distribution(
    handler: Type[BasePypiHandler],
    location: str,
) -> List[Requirement]:
    """
    Return a list of requirements from a source distribution or wheel at
    ``location`` using the provided ``handler`` DatafileHandler for parsing.
    """
    if not location:
        return []
    if not os.path.exists(location):
        return []
    reqs = []
    try:
        for package_data in handler.parse(location):
            dependencies = package_data.dependencies
            reqs.extend(get_requirements_from_dependencies(dependencies=dependencies))
    except Exception as e:
        trace = format_exc()
        raise Exception(
            f"Failed to get_requirements_from_distribution for: {location!r}\n{trace}"
        ) from e
    return reqs


def get_deps_from_distribution(
    handler: BasePypiHandler,
    location: str,
) -> List[DependentPackage]:
    """
    Return a list of requirements from a source distribution or wheel at
    ``location`` using the provided ``handler`` DatafileHandler for parsing.
    """
    if not location:
        return []
    if not os.path.exists(location):
        return []
    deps = []
    for package_data in handler.parse(location):
        dependencies = package_data.dependencies
        deps.extend(dependencies=dependencies)
    return deps


def get_environment_marker_from_environment(environment):
    return {
        "extra": "",
        "python_version": get_python_version_from_env_tag(
            python_version=environment.python_version
        ),
        "platform_system": environment.operating_system.capitalize(),
        "sys_platform": environment.operating_system,
    }


def parse_reqs_from_setup_py_insecurely(setup_py):
    """
    Yield  Requirement(s) from a ``setup_py`` setup.py file location .
    """
    if not os.path.exists(setup_py):
        return []
    for req in iter_requirements(level="", extras=[], setup_file=setup_py):
        yield Requirement(req)


def parse_deps_from_setup_py_insecurely(setup_py):
    """
    Yield DependentPackage(s) from the ``setup_py`` setup.py file location .
    """
    if not os.path.exists(setup_py):
        return []
    for req in iter_requirements(level="", extras=[], setup_file=setup_py):
        parsed_req = Requirement(req)
        yield DependentPackage(
            purl=str(
                PackageURL(
                    type="pypi",
                    name=parsed_req.name,
                )
            ),
            extracted_requirement=req,
            scope="install",
            is_runtime=False,
        )


def is_valid_version(
    parsed_version: Union[LegacyVersion, Version],
    requirements: Dict,
    identifier: str,
    bad_versions: List[Version],
) -> bool:
    """
    Return True if the parsed_version is valid for the given identifier.
    """
    if parsed_version in bad_versions:
        return False
    if any(parsed_version not in r.specifier for r in requirements[identifier]):
        if all(not r.specifier for r in requirements[identifier]):
            return True
        return False
    return True


def get_python_version_from_env_tag(python_version: str) -> str:
    """
    Return the python version extracted from an environment tag.

    >>> assert get_python_version_from_env_tag("310") == "3.10"
    >>> assert get_python_version_from_env_tag("39") == "3.9"
    """
    elements = list(python_version)
    elements.insert(1, ".")
    python_version = "".join(elements)
    return python_version


async def fetch_and_extract_sdist(
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
    sdist = await utils_pypi.download_sdist(
        name=candidate.name,
        version=str(candidate.version),
        repos=repos,
        python_version=python_version,
    )

    if not sdist:
        return

    return get_sdist_file_path_from_filename(sdist)


def get_sdist_file_path_from_filename(sdist):
    if sdist.endswith(".tar.gz"):
        sdist_file = sdist.rstrip(".tar.gz")
        with tarfile.open(os.path.join(settings.CACHE_THIRDPARTY_DIR, sdist)) as file:
            file.extractall(
                os.path.join(settings.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file)
            )
    elif sdist.endswith(".zip"):
        sdist_file = sdist.rstrip(".zip")
        with ZipFile(os.path.join(settings.CACHE_THIRDPARTY_DIR, sdist)) as zip:
            zip.extractall(
                os.path.join(settings.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file)
            )

    else:
        raise Exception(f"Unable to extract sdist {sdist}")

    return os.path.join(settings.CACHE_THIRDPARTY_DIR, "extracted_sdists", sdist_file, sdist_file)


def get_requirements_from_dependencies(
    dependencies: List[DependentPackage], scopes: Tuple[str] = ("install",)
) -> List[Requirement]:
    """
    Generate parsed requirements for the given ``dependencies``.
    """
    for dep in dependencies:
        if not dep.purl:
            continue

        # TODO: consider other scopes and using the is_runtime flag
        if dep.scope not in scopes:
            continue

        # FIXME We are skipping editable requirements
        # and other pip options for now
        # https://github.com/aboutcode-org/python-inspector/issues/41
        if can_process_dependent_package(dep):
            yield Requirement(str(dep.extracted_requirement))


def remove_extras(identifier: str) -> str:
    """
    Return the identifier without extras.
    >>> assert remove_extras("foo[bar]") == "foo"
    """
    name, _, _ = identifier.partition("[")
    return name


def get_reqs_from_requirements_file_in_sdist(sdist_location: str, files: List) -> List[Requirement]:
    """
    Return a list of parsed requirements from the ``sdist_location`` sdist location
    """
    if contain_string(string="requirements.txt", files=files):
        requirement_location = os.path.join(
            sdist_location,
            "requirements.txt",
        )
        yield from get_requirements_from_distribution(
            handler=PipRequirementsFileHandler,
            location=requirement_location,
        )


def get_reqs_insecurely(setup_py_location):
    """
    Return a list of Requirement(s) from  ``setup_py_location`` setup.py file location
    """
    yield from parse_reqs_from_setup_py_insecurely(setup_py=setup_py_location)


def get_requirements_from_python_manifest(
    sdist_location: str, setup_py_location: str, files: List, analyze_setup_py_insecurely: bool
) -> List[Requirement]:
    """
    Return a list of parsed requirements from the ``sdist_location`` sdist location
    """
    # Look in requirements file if and only if they are referred in setup.py or setup.cfg
    # And no deps have been yielded by requirements file.
    requirements = list(
        get_reqs_from_requirements_file_in_sdist(
            files=files,
            sdist_location=sdist_location,
        )
    )
    if requirements:
        yield from requirements

    elif contain_string(string="_require", files=[setup_py_location]):
        if analyze_setup_py_insecurely:
            yield from get_reqs_insecurely(
                setup_py_location=setup_py_location,
            )

        else:
            # Do not raise exception here as we may have a setup.py that does not
            # have any dependencies.
            with open(setup_py_location) as sf:
                file_contents = sf.read()
                node = ast.parse(file_contents)
                setup_fct = [
                    elem
                    for elem in ast.walk(node)
                    if (
                        isinstance(elem, ast.Expr)
                        and isinstance(elem.value, ast.Call)
                        and isinstance(elem.value.func, ast.Name)
                        and elem.value.func.id == "setup"
                    )
                ]
                if len(setup_fct) > 1:
                    print(
                        f"Warning: identified multiple definitions of 'setup()' in {setup_py_location}, "
                        "defaulting to the first occurrence"
                    )
                setup_fct = setup_fct[0]
                install_requires = [
                    k.value for k in setup_fct.value.keywords if k.arg == "install_requires"
                ]
                if install_requires:
                    if len(install_requires) > 1:
                        print(
                            f"Warning: identified multiple definitions of 'install_requires' in "
                            "{setup_py_location}, defaulting to the first occurrence"
                        )
                    install_requires = install_requires[0].elts
                    if len(install_requires) != 0:
                        raise Exception(
                            f"Unable to collect setup.py dependencies securely: {setup_py_location}"
                        )


DEFAULT_ENVIRONMENT = utils_pypi.Environment.from_pyver_and_os(
    python_version="38", operating_system="linux"
)


class PythonInputProvider(AbstractProvider):
    def __init__(
        self,
        environment=DEFAULT_ENVIRONMENT,
        repos=tuple(),
        analyze_setup_py_insecurely=True,
        ignore_errors=False,
    ):
        self.environment = environment
        self.environment_marker = get_environment_marker_from_environment(self.environment)
        self.repos = repos or []
        self.versions_by_package: Dict[str, List[Version]] = {}
        self.dependencies_by_purl = {}
        self.wheel_or_sdist_by_package = {}
        self.analyze_setup_py_insecurely = analyze_setup_py_insecurely
        self.ignore_errors = ignore_errors

    def identify(self, requirement_or_candidate: Union[Candidate, Requirement]) -> str:
        """Given a requirement, return an identifier for it. Overridden."""
        name = packvers.utils.canonicalize_name(requirement_or_candidate.name)
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

    def get_versions_for_package(self, name: str) -> List[Version]:
        """
        Return a list of versions for a package.
        """
        versions = self.versions_by_package.get(name)
        if not versions:
            return asyncio.run(self.fill_versions_for_package(name))
        else:
            return versions

    async def fill_versions_for_package(self, name: str) -> List[Version]:
        versions = self.versions_by_package.get(name) or []
        if versions:
            return versions

        if self.repos and self.environment:
            for repo in self.repos:
                versions.extend(await self._get_versions_for_package_from_repo(name, repo))
        else:
            versions.extend(await self._get_versions_for_package_from_pypi_json_api(name))

        self.versions_by_package[name] = versions
        return versions

    async def _get_versions_for_package_from_repo(
        self, name: str, repo: PypiSimpleRepository
    ) -> List[Version]:
        """
        Return a list of versions for a package name from a repo
        """
        versions = []
        for version, package in (await repo.get_package_versions(name)).items():
            python_version = parse_version(
                get_python_version_from_env_tag(python_version=self.environment.python_version)
            )
            wheels = list(package.get_supported_wheels(environment=self.environment))
            valid_wheel_present = False
            pypi_valid_python_version = False
            if wheels:
                for wheel in wheels:
                    if utils_pypi.valid_python_version(
                        python_requires=wheel.python_requires, python_version=python_version
                    ):
                        valid_wheel_present = True
            if package.sdist:
                pypi_valid_python_version = utils_pypi.valid_python_version(
                    python_requires=package.sdist.python_requires, python_version=python_version
                )
            if valid_wheel_present or pypi_valid_python_version:
                versions.append(version)

        return versions

    async def _get_versions_for_package_from_pypi_json_api(self, name: str) -> List[Version]:
        """
        Return a list of versions for a package name from the PyPI.org JSON API
        """
        api_url = f"https://pypi.org/pypi/{name}/json"
        resp = await get_response_async(api_url)
        if not resp:
            return []
        releases = resp.get("releases") or {}
        return releases.keys() or []

    def get_requirements_for_package(
        self, purl: PackageURL, candidate: Candidate
    ) -> List[Requirement]:
        dependencies = self.dependencies_by_purl.get(str(purl))
        if not dependencies:
            return asyncio.run(self.fill_requirements_for_package(purl, candidate))
        else:
            return dependencies

    async def fill_requirements_for_package(
        self, purl: PackageURL, candidate: Candidate
    ) -> List[Requirement]:
        """
        Yield requirements for a package.
        """
        dependencies = self.dependencies_by_purl.get(str(purl)) or []
        if dependencies:
            return dependencies

        if self.repos and self.environment:
            dependencies.extend(
                await self._get_requirements_for_package_from_pypi_simple(candidate)
            )
        else:
            dependencies.extend(await self._get_requirements_for_package_from_pypi_json_api(purl))

        self.dependencies_by_purl[str(purl)] = dependencies
        return dependencies

    async def _get_requirements_for_package_from_pypi_simple(
        self, candidate: Candidate
    ) -> List[Requirement]:
        """
        Return requirements for a package from the simple repositories.
        """
        python_version = parse_version(
            get_python_version_from_env_tag(python_version=self.environment.python_version)
        )

        wheels = await utils_pypi.download_wheel(
            name=candidate.name,
            version=str(candidate.version),
            environment=self.environment,
            repos=self.repos,
            python_version=python_version,
        )

        if wheels:
            for wheel in wheels:
                wheel_location = os.path.join(settings.CACHE_THIRDPARTY_DIR, wheel)
                requirements = get_requirements_from_distribution(
                    handler=PypiWheelHandler,
                    location=wheel_location,
                )
                # We are only looking at the first wheel and not other wheels
                return requirements
        else:
            sdist_location = await fetch_and_extract_sdist(
                repos=self.repos, candidate=candidate, python_version=python_version
            )
            if not sdist_location:
                return []

            setup_py_location = os.path.join(
                sdist_location,
                "setup.py",
            )
            setup_cfg_location = os.path.join(
                sdist_location,
                "setup.cfg",
            )

            if self.analyze_setup_py_insecurely:
                return get_reqs_insecurely(setup_py_location=setup_py_location)
            else:
                requirements = list(
                    get_setup_requirements(
                        sdist_location=sdist_location,
                        setup_py_location=setup_py_location,
                        setup_cfg_location=setup_cfg_location,
                    )
                )
                if requirements:
                    return requirements
                else:
                    # Look in requirements file if and only if thy are referred in setup.py or setup.cfg
                    # And no deps have been yielded by requirements file
                    return get_requirements_from_python_manifest(
                        sdist_location=sdist_location,
                        setup_py_location=setup_py_location,
                        files=[setup_cfg_location, setup_py_location],
                        analyze_setup_py_insecurely=self.analyze_setup_py_insecurely,
                    )

    async def _get_requirements_for_package_from_pypi_json_api(
        self, purl: PackageURL
    ) -> List[Requirement]:
        """
        Return requirements for a package from the PyPI.org JSON API
        """
        # if no repos are provided use the incorrect but fast JSON API
        api_url = f"https://pypi.org/pypi/{purl.name}/{purl.version}/json"
        resp = await get_response_async(api_url)
        if not resp:
            return []
        info = resp.get("info") or {}
        requires_dist = info.get("requires_dist") or []
        return list(map(lambda r: Requirement(r), requires_dist))

    def get_candidates(
        self,
        all_versions: List[str],
        requirements: List[Requirement],
        identifier: str,
        bad_versions: List[str],
        name: str,
        extras: Dict,
    ) -> Iterable[Candidate]:
        """
        Generate candidates for the given identifier. Overridden.
        """
        valid_versions = []
        for version in all_versions:
            parsed_version = parse_version(version)
            if is_valid_version(
                parsed_version=parsed_version,
                requirements=requirements,
                identifier=identifier,
                bad_versions=bad_versions,
            ):
                valid_versions.append(parsed_version)
        if not all(version.is_prerelease for version in valid_versions):
            valid_versions = [version for version in valid_versions if not version.is_prerelease]
        for version in valid_versions:
            yield Candidate(name=name, version=version, extras=extras)

    def _iter_matches(
        self,
        identifier: str,
        requirements: Mapping[str, List[Requirement]],
        incompatibilities: Dict,
    ) -> Generator[Candidate, None, None]:
        """
        Yield candidates for the given identifier, requirements and incompatibilities.
        """
        name = remove_extras(identifier=identifier)
        bad_versions = {c.version for c in incompatibilities[identifier]}
        extras = {e for r in requirements[identifier] for e in r.extras}
        versions = []
        versions.extend(self.get_versions_for_package(name=name))

        if not versions:
            if self.ignore_errors:
                yield from [Candidate("NonExistant", "0.0.0", "")]
                return
            else:
                raise NoVersionsFound(f"This package does not exist: {name}")
        yield from self.get_candidates(
            all_versions=versions,
            requirements=requirements,
            identifier=identifier,
            bad_versions=bad_versions,
            name=name,
            extras=extras,
        )

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, List[Requirement]],
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
        if candidate.version in requirement.specifier:
            return True
        elif not requirement.specifier:
            return True
        return False

    def _iter_dependencies(self, candidate: Candidate) -> Iterable[Requirement]:
        """
        Yield dependencies for the given candidate.
        """
        name = packvers.utils.canonicalize_name(candidate.name)
        # TODO: handle extras https://github.com/aboutcode-org/python-inspector/issues/10
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
                if r.marker.evaluate(self.environment_marker):
                    yield r

    def get_dependencies(self, candidate: Candidate) -> List[Requirement]:
        """Get dependencies of a candidate. Overridden."""
        return list(self._iter_dependencies(candidate))


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


def format_resolution(results: Result, as_tree=False):
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
            parent_children = dict(
                package=str(parent_purl),
                dependencies=dependencies,
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


def get_package_list(results):
    """
    Return a list of packages in the resolution.
    """
    mapping = results.mapping
    graph = results.graph
    parents = mapping.keys()
    packages = set()
    for parent in parents:
        parent_purl = PackageURL(
            type="pypi",
            name=parent,
            version=str(mapping[parent].version),
        )
        packages.add(str(parent_purl))
        for dependency in graph.iter_children(parent):
            dep_purl = PackageURL(
                type="pypi",
                name=dependency,
                version=str(mapping[dependency].version),
            )
            packages.add(str(dep_purl))
    return list(sorted(packages))


def get_setup_requirements(sdist_location: str, setup_py_location: str, setup_cfg_location: str):
    """
    Yield Requirement(s) from Pypi in the ``location`` directory that contains
    a setup.py and/or a setup.cfg and optionally a requirements.txt file if
    ``use_requirements`` is True and this file is used in the setup.py or setup.cfg.
    Perform an insecure live evaluation of the Python code if needed and if
    ``analyze_setup_py_insecurely`` is True.
    """

    if not os.path.exists(setup_py_location) and not os.path.exists(setup_cfg_location):
        raise Exception(f"No setup.py or setup.cfg found in pypi sdist {sdist_location}")

    # Some commonon packages like flask may have some dependencies in setup.cfg
    # and some dependencies in setup.py. We are going to check both.
    location_by_sdist_parser = {
        PythonSetupPyHandler: setup_py_location,
        SetupCfgHandler: setup_cfg_location,
    }

    for handler, location in location_by_sdist_parser.items():
        reqs = get_requirements_from_distribution(
            handler=handler,
            location=location,
        )
        yield from reqs
