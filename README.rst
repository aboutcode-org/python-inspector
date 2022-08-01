python-inspector - inspect Python packages dependencies and metadata
=====================================================================


Copyright (c) nexB Inc. and others.
SPDX-License-Identifier: Apache-2.0
Homepage: https://github.com/nexB/python-inspector and https://www.aboutcode.org/


``python-inspector`` is a collection of utilities to:

- resolve PyPI packages dependencies

- parse various manifests and packages files such as pip requirement files,
  Pipfile, pyproject.toml, poetry.lock, setup.py and setup.cfg and legacy and
  current metadata file formats for eggs, wheels and sdist.

- query PyPI JSON and simple APIs for package information

It grew out of ScanCode toolkit to find and analyze PyPI archives and
installed Python packages and their files.

The goal of python-inspector is to be a comprehensive library
that can handle every style of Python package layouts, manifests and lockfiles.


Usage
--------

- Install with pip::

    pip install git+https://github.com/nexB/python-inspector

- Run the command line utility with::

    python-inspector --help



Its companion libraries are:

- ``pip-requirements-parser``, a mostly correct pip requirements parsing
  library extracted from pip.

- ``pkginfo2``, a safer fork of pkginfo to parse various installed and extracted
  package layouts and their metadata files.

- ``dparse2``, a safer fork of dparse to parse various package manifests

- ``resolvelib``, the library used by pip for dependency resolution

- ``packaging``, the official Python packaging utility library to process
  versions, specifiers, markers  and other packaging data formats.

- ``importlib_metadata``, the official Python utility library to process
  installed site-packages and their metadata formats.

- ``packageurl-python`` to use Package URL to reference Python packages
 
 
