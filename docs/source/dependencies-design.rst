====================================================
  Python package dependencies resolver design
====================================================


This is a design to create a new command line tool to resolve Python
dependencies for a given Python version, operating system and
architecture. The name for this new tool is “python-inspector”.


***************
Context
***************

For the collection of the set of dependent packages for a given Python
application, the package management tool (commonly pip) will first
collect the direct dependencies and then query the PyPI APIs to collect
the dependencies of each dependency.

For each dependency, there can be a version "requirement" that can be an
exact version, a version expression (aka. version specifier) as defined
in `pep-0440 <https://www.python.org/dev/peps/pep-0440/>`__
with additional OS and environment tags and constraints as specified in
`pep-0508 <https://www.python.org/dev/peps/pep-0508/>`__ .

In particular the required Python version of a package (or version specifier)
can be set for the whole package (with the``python_requires`` attribute) or as
a marker for a given direct or indirect dependency. pip processes requirement
specifiers and constraints from a "requirements" file and internally resolves
dependency versions recursively by querying the PyPI Python package
index repository at https://PyPI.org

***************
Problem
***************

pip does not support querying or reporting of resolved dependencies
without actually installing them in a build; even for a mere download it
does build temporarily every package as a wheel to work exclusively from
wheel dependencies. The problem for compliance automation is that you
may need to collect information about resolved dependencies without
actually building the project and physically installing all the
packages.

The installation and underlying dependency resolution is only for the
current Python version used to run pip which may not be the target
version used at runtime and may not be a supported version for some
dependencies. In addition, the installation may demand a complex
environment including compiler and toolchains (when native code is
compiled during the build) that may be impossible to provision
automatically, leading to a failed installation and a failure to resolve
dependencies.

Because of these factors, it can be incredibly difficult to resolve the
set of dependencies of a given Python package or project. When the use
case is to resolve a list of dependencies, there is a significant
performance impact to actually download and physically install all the
dependent package archives instead of just working on the much smaller
set of metadata of each package. Even when using pip just to download
dependency archives, it will attempt to build each archive first (with
the same problems as listed above) to collect its dependency metadata
even when the metadata are already present and can be collected as-is.

***************
Solution
***************

One approach to resolve this issue is to attempt to resolve the
dependencies using all the current Python versions (e.g., from 3.6 to
3.10) and stop when one resolution is completed. This can work in
practice, but it results in a complex setup typically using multiple
Docker images for each of the supported Python versions. It would also
fail to build native dependencies unless the required toolchain is also
identified and installed.

The solution approach designed for this project is to use a single Python
version to call the underlying version resolution libraries and
functions to perform the resolution in a well-controlled way without
invoking pip as a subprocess. This will eventually request resolution of
dependencies for a base Python version that is not the current Python
version. For example, it will be possible to resolve dependencies for
Python 3.8, even though the current Python version running the tool may
be 3.9. The actual Python version running the tool may be different from
the version used to support the dependency resolution.

The designed solution will be a new Python package and command line tool
that can be installed on one Python version and can resolve dependencies
from requirements files for any provided Python version as an argument
(which may not be the same as the installed Python version). The output
will be a JSON file listing the resolved dependencies in two ways:

1. as a flat list of unique name/versions (using Package URLs)
2. as a nested dependency tree, with possible duplicates because a given
   name/version may be the dependency of more than one packages

For instance, if we have these immediate direct dependencies (using
pinned versions for illustration):

-  foo 1.0 and bar 2.0
-  foo 1.0 depends in turn on baz 2.0 and thing 3.0
-  bar 2.0 depends in turn on shebang 1.0 and thing 3.0

Then complete dependency list (including duplicates) is:

-  foo 1.0
-  bar 2.0
-  baz 2.0
-  thing 3.0
-  shebang 1.0
-  thing 3.0

And the dependency tree is:

-  foo 1.0

   -  baz 2.0
   -  thing 3.0

-  bar 2.0

   -  shebang 1.0
   -  thing 3.0

And a flat list of unique dependencies would be:

-  foo 1.0
-  bar 2.0
-  baz 2.0
-  thing 3.0
-  shebang 1.0

The implementation may likely be similar to
`pipgrip <https://github.com/ddelange/pipgrip>`__,
but using the `resolvelib <https://github.com/sarugaku/resolvelib>`__
library as used and vendored in pip instead of an implementation of
Dart's PubGrub algorithm as provided in pipgrip or poetry.

The expected benefit of this tool is a simpler way to resolve Python
dependencies that will not require complex installation of a Python toolchain
specific to a given project environment when the goal is only to resolve
dependencies. In particular the key new  capability is to run this tool on a
single Python version and resolve versions for alternative Python versions,
operating systems and architectures without having to install all the packages
in the dependency tree.


***************
Design
***************

Processing outline
------------------

The outline of the processing is to:

-  Parse and validate the requirements as inputs

-  For each top-level requirement (e.g. name/version):

   -  Fetch all the corresponding versions metadata using the PyPI API(s)
   -  Fetch the packages as needed to further obtain the next-level
      dependencies, and this recursively

-  Resolve a correct dependency version for each name.
-  Dump JSON


User experience:
----------------

The goal of the command line interface and user experience is to be
obvious and familiar to a pip user.

We will create a new CLI named "python-inspector" with these key options:

Inputs:
~~~~~~~~~

Two options determine what are the input packages to resolve:

-  ``--requirement <requirements.txt file>``: a path to a pip requirements
   file. Can be repeated to combine multiple inputs.

-  ``--specifier <name==version>``: a single package name==version
   specification as in django==1.2.3. Can be repeated to combine
   multiple inputs.

Notes: pip uses an unnamed argument instead of an option for the
"specifier". We could use the same design. This can be changed easily
later. Or even accept both ways.

Environment:
~~~~~~~~~~~~

Two options to select the OS/Python to use for dependency resolution and
selecting pre-built binary packages (options can be repeated):

-  ``--python-version <python_version>``: the Python version(s) to use for
   wheels and dependency resolution. Can be repeated.
-  ``--operating-system <os>`` : The OS(ses) to use for wheels: one of
   linux, macos or windows. Can be repeated.

Notes: the assumption is that we only support X86/64 by default as an
architecture for now. We could refine this later with support for
passing other architectures.

pip uses multiple lower options that require a detailed knowledge of the
various envt. tags defined by PyPI and use by pip: ``--platform``, ``--python-version``,
``--implementation``, ``--abi``. We consider these lower level options to be
less straightforward to use, though we could use these too at the cost
of making the CLI more complex to use

Configuration:
~~~~~~~~~~~~~~

One option to point to alternative, local or private PyPI indexes and
repositories.

-  ``--index-url URL``: PyPI index URL(s) to use for wheels and sources, in
   order of preference. The default is to use only the public PyPI
   repository. When multiple repositories are provided, each repository
   is tried in sequence. A repository must support at the minimum the
   PyPI "simple" API. Both the "simple" API and the PyPI JSON
   "warehouse-style" API are supported.

- ``--prefer-source``: when set, prefer source distribution instead
  of binary distribution. In case there is no source distribution
  available, the tool should provide binary distribution.

Strategy and error processing:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The initial approach is to use the default dependency resolution
strategy of pip which is to eagerly select the latest possible versions
for an initial installation.

This strategy is strict and may fail to resolve certain dependencies
that would be otherwise correct and installable.

In the future, we could implement additional strategies such as:

-  Always take the latest version of everything
-  Always use the minimum possible version that satisfies all constraints
-  Always use the highest possible version that satisfies all constraints

In addition, these strategies could be used as a fallback when the
standard resolution fails to produce a viable option: for instance if
the resolver cannot find a satisfying version of a package, a fallback
strategy could be to use the latest version of this package.

If such fallback is enabled, it should be guarded by a command line
option.

Output:
~~~~~~~

One option to point to JSON output file to create

-  ``--json FILE``: Write output as pretty-printed JSON to FILE.

The JSON output will be a JSON "object" of name/value pairs with:

1. a "headers" list of objects with technical information on the command
   line run options, inputs and arguments (similar to ScanCode Toolkit
   headers)
   This will include an "errors" list of error messages if any.

2. a "dependencies" list of objects as a flat list of unique
   name/versions (using Package URLs) listing all dependencies at full
   depth.

-   We can later consider adding extra data such as: package medatada
    and the list of actual downloadable archive URLs for each package

1. a "dependency_tree" combination of nested lists and objects to
   represent the resolved dependencies in a tree the "root" notes in
   this tree are the requirements and specifiers provided as input (e.g.
   assumed to be direct dependencies) (with possible duplicates because
   a given name/version may be the dependency of more than one packages)


Key third party package dependencies:
-------------------------------------

The python-inspector will have these key dependencies (this is
indicative and does not include non-functional and scaffolding libraries
and tools):

-  pip-requirements-parser: this is a nexB-maintained "correct" parser
   for pip requirements files
-  packaging: the core official Python library to manage various
   packaging-related objects
-  importlib_metadata: the core official Python library to manage
   various packaging-related objects
-  resolvelib: the dependency resolution library used by pip internally
   https://github.com/sarugaku/resolvelib
-  pkginfo2: this is a nexB-maintained parser for multiple Python
   metadata formats
-  dparse2: this is a nexB-maintained parser for multiple Python
   metadata formats
-  packageurl: this is a nexB-maintained library for Package URLs

Data structures and models
--------------------------

The key data structures and models are:

To model PyPI interactions:

-  Distribution: represents a package distribution for a specific name,
   version and download URL. Comes in two flavors: Wheel for binaries
   and Sdist for sources.
-  PypiPackage: represents a PyPI package for a specific name and
   version and has a list of Wheel and one Sdist.
-  Environment: represents the combination of OS/architectures/Python
   versions used.
-  PypiRepository: a PyPI repository contains PypiPackage packages

To model package and dependency results:

-  Package: a package and its metadata identified by a Package URL. This
   is essentially the same model as the ScanCode Toolkit Package model.
   Contains a list and a tree of dependencies as DependentPackage
-  DependentPackage: a dependency and its metadata identified by a
   Package URL. . This is essentially the same model as the ScanCode
   Toolkit DependentPackage model.


Questions:
-------------------

-  What would be the preferred approach to deal with resolution
   conflicts? Since late 2020 and the adoption of a stricter dependency
   resolver by pip, several packages may present a conflict where the
   version cannot be determined exactly when using strict resolution.
   One approach in these cases is to look for the latest version or
   lowest version.

-  Resolving dependencies require fetching package archives to extract,
   parse and collect a dependency's dependencies in most cases. These
   will be cached and this could be an explicit by-product of the
   resolution.


Future improvements
-------------------

The initial plan is to  support only for pip requirements file format, but ScanCode
Toolkit can process most of the Python ecosystem manifest formats
(setup.py, setup.cfg, pyproject.toml, Pipfile, and various lockfiles
formats). One approach would be to use SCTK output as an input to this
dependency resolution.

ScanCode Toolkit can detect the and normalize the declared licenses in package
metadata and also collect and normalize all the metadata. This could be
a refinement for later.

