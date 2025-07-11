python-inspector - inspect Python package dependencies and metadata
=====================================================================



``python-inspector`` is a collection of utilities to:

- resolve PyPI packages dependencies

- parse various requirements.txt files and setup.py files as input
  for resolving dependencies.

- parse various manifests and packages files such as
  Pipfile, pyproject.toml, poetry.lock and setup.cfg and legacy and
  current metadata file formats for eggs, wheels and sdist. These
  have not been wired with the command line yet.

- query PyPI JSON and simple APIs for package information

It grew out of ScanCode toolkit to find and analyze PyPI archives and
installed Python packages and their files.

The goal of python-inspector is to be a comprehensive library
that can handle every style of Python package layouts, manifests and lockfiles.


SPDX-License-Identifier: Apache-2.0

Copyright (c) AboutCode, nexB Inc. and others.

Homepage: https://github.com/aboutcode-org/python-inspector and https://www.aboutcode.org/


Usage
--------

- Install the stable release with pip from PyPI::

    pip install python-inspector

- Or install the latest with pip::

    pip install git+https://github.com/aboutcode-org/python-inspector

- Run the command line utility with::

    python-inspector --help


Development
--------------

Run::

    git clone https://github.com/aboutcode-org/python-inspector

Create a virtual environment and install deps locally::

    make dev
    source venv/bin/activate


When in the virtual environment, run python-inspector from that clone::

    python-inspector --help


Run tests::

    make test

Run code checks::

    make check

Run code formatting::

    make valie

Check available make targets for further details



More testing
------------------

- Run the tests with pytest::

    pytest -vvs

- Or run them faster using 12 cores ::

    pytest -vvs --numprocesses=12


Regenerate test files
-----------------------------

Some tests use live data from Pypi.org to run resolutions. When the package versions have
changed, the resolution can change and some of the tests fail. We have an environment variable
that regenerates the expected JSON result files when set.

To regenerate expected test result files for the failed tests, use this command::

    PYINSP_REGEN_TEST_FIXTURES=yes pytest -vvs --lf

Then, carefully review the diff before committing the expected JSON test result files to validate
that the changes are OK and mostly affect small changes in resolved package versions.


Credits and dependencies
---------------------------

For info, python-inspector embeds or depends on these libraries:

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

- ``scancode-toolkit`` for Python package manifest parsing.



Acknowledgements, Funding, Support and Sponsoring
--------------------------------------------------------

This project is funded, supported and sponsored by:

- Generous support and contributions from users like you!
- the European Commission NGI programme
- the NLnet Foundation
- the Swiss State Secretariat for Education, Research and Innovation (SERI)
- Google, including the Google Summer of Code and the Google Seasons of Doc programmes
- Mercedes-Benz Group
- Microsoft and Microsoft Azure
- AboutCode ASBL
- nexB Inc.



|europa|   |dgconnect|

|ngi|   |nlnet|

|aboutcode|  |nexb|


This project was funded through the NGI0 Discovery Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 825322.

|ngidiscovery| https://nlnet.nl/project/vulnerabilitydatabase/


This project was funded through the NGI0 Core Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101092990.

|ngizerocore| https://nlnet.nl/project/Back2source-next/



.. |nlnet| image:: https://nlnet.nl/logo/banner.png
    :target: https://nlnet.nl
    :height: 50
    :alt: NLnet foundation logo

.. |ngi| image:: https://ngi.eu/wp-content/uploads/thegem-logos/logo_8269bc6efcf731d34b6385775d76511d_1x.png
    :target: https://ngi.eu35
    :height: 50
    :alt: NGI logo

.. |nexb| image:: https://nexb.com/wp-content/uploads/2022/04/nexB.svg
    :target: https://nexb.com
    :height: 30
    :alt: nexB logo

.. |europa| image:: https://ngi.eu/wp-content/uploads/sites/77/2017/10/bandiera_stelle.png
    :target: http://ec.europa.eu/index_en.htm
    :height: 40
    :alt: Europa logo

.. |aboutcode| image:: https://aboutcode.org/wp-content/uploads/2023/10/AboutCode.svg
    :target: https://aboutcode.org/
    :height: 30
    :alt: AboutCode logo

.. |swiss| image:: https://www.sbfi.admin.ch/sbfi/en/_jcr_content/logo/image.imagespooler.png/1493119032540/logo.png
    :target: https://www.sbfi.admin.ch/sbfi/en/home/seri/seri.html
    :height: 40
    :alt: Swiss logo

.. |dgconnect| image:: https://commission.europa.eu/themes/contrib/oe_theme/dist/ec/images/logo/positive/logo-ec--en.svg
    :target: https://commission.europa.eu/about-european-commission/departments-and-executive-agencies/communications-networks-content-and-technology_en
    :height: 40
    :alt: EC DG Connect logo

.. |ngizerocore| image:: https://nlnet.nl/image/logos/NGI0_tag.svg
    :target: https://nlnet.nl/core
    :height: 40
    :alt: NGI Zero Core Logo

.. |ngizerocommons| image:: https://nlnet.nl/image/logos/NGI0_tag.svg
    :target: https://nlnet.nl/commonsfund/
    :height: 40
    :alt: NGI Zero Commons Logo

.. |ngizeropet| image:: https://nlnet.nl/image/logos/NGI0PET_tag.svg
    :target: https://nlnet.nl/PET
    :height: 40
    :alt: NGI Zero PET logo

.. |ngizeroentrust| image:: https://nlnet.nl/image/logos/NGI0Entrust_tag.svg
    :target: https://nlnet.nl/entrust
    :height: 38
    :alt: NGI Zero Entrust logo

.. |ngiassure| image:: https://nlnet.nl/image/logos/NGIAssure_tag.svg
    :target: https://nlnet.nl/image/logos/NGIAssure_tag.svg
    :height: 32
    :alt: NGI Assure logo

.. |ngidiscovery| image:: https://nlnet.nl/image/logos/NGI0Discovery_tag.svg
    :target: https://nlnet.nl/discovery/
    :height: 40
    :alt: NGI Discovery logo
