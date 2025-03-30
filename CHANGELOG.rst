Changelog
=========

v0.13.1
-----------

- Fix ResolutionImpossible for lief==0.15.1 #202
- Add license expression data from pypi API #208
- Add python 3.13 in python-inspector #196
- Update homepage_url and fix CI and tests


v0.12.1
-----------

- Update link references of ownership from nexB to aboutcode-org


v0.12.0
-----------

- Add support for Python3.12


v0.11.0
-----------

- Add ignore error mode.
- Fix missing index_urls parsing.


v0.10.0
-----------

- Fix resolving requirements with percent encoded characters.


v0.9.8
-------------

- Add the ability to handle relative links.


v0.9.7
-------------

- Fix resolution of setup files which partially have dynamic dependencies.


v0.9.6
-------------

- Mock the actual setup provider defined in setup.py.
- Update dependency resolvelib to latest.

v0.9.5
-------------

- Update readme with test instructions.
- Fail gracefully at parsing setup.py with no deps.
- Support comments in netrc file #107.


v0.9.4
------

- Create PyPI cache location in the home directory if a cache directory cannot be made at the project root.
- Replace packaging with packvers.
- Prevent duplicated package versions.


v0.9.3
------

- Add support for recursive requirements.
- Add python 3.11 as a valid python version in choices.
- Operating system and python version are now required fields in CLI.
- Add dot versions (3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 2.7) with
  current python version choices for CLI (36, 37, 38, 39, 310, 311, 27).


v0.9.2
------

- Make os and python version as mandatory input parameters.
- Do not return duplicates binaries.
- Return empty list for resolved dependencies graph in case of no dependencies
  are found #94 https://github.com/nexB/python-inspector/issues/94.


v0.9.1
------

- Add --prefer-source option, to prefer source packages over binary ones
  if no source distribution is available then binary distributions are used.


v0.9.0
------

- Add API function for using cleanly as a library.
- Add support for setuptools.setup in live evaluation.
- Do not fail if no direct dependencies are provided.


v0.8.5
------

- Adapt python-inspector output according to SCTK output.


v0.8.4
------

- Raise error for non existing package.


v0.8.3
------

- Bump dependencies version in tests.


v0.8.2
------

- For a package that doesn't have a single stable release use the latest pre-release version.


v0.8.1
------

- Version v0.7.2 was tagged with the same commit as v0.7.1, so this is
  a new release with the correct commit.


v0.8.0
------

- Change Output Format to look like ScanCode-Toolkit #68
  https://github.com/nexB/python-inspector/issues/68 , we have removed
  "requirements" from the ouptut and added a new field "files".


v0.7.1
------

- Correct version reporting #70
  https://github.com/nexB/python-inspector/issues/70 .


v0.7.0
------

- Enable live evaluation of the "setup.py" that use computed arguments.
  When this occurs, a live evaluation of the Python code is the only working
  solution short of a full installation. Because this can be a security issue,
  there is a new "--analyze-setup-py-insecurely" command line option to enable this feature.
  Note that this not more insecure than actually installing a PyPI package.
- Add metadata for packages.


v0.6.5
------

- Add --version option.


v0.6.4
------

- Add support for setup.py


v0.6.3
------

- Ensure to filter out top level dependencies on the basis of their environment markers
- Do not ignore files on basis of name


v0.6.2
------

- Ignore invalid requirement files on basis of name
- Use netrc file from home directory if not present


v0.6.1
------

- Use latest ScanCode toolkit packagedcode including the ability to collect
  extra index URLs from requirements.txt
- Use new pipdeptree-like format for improved compatibility
- Rename command line tool name from "dad" to "python-inspector"


v0.5.0
------

Initial release.
