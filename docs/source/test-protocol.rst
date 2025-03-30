==============================================================
  Validation tests for Python package dependency resolution
==============================================================

In order to validate that the python-inspector dependency resolution is correct
here is a procedure.


Requirements
***************

You need to:

- have access to some Python codebase to use as a test bed.
- have a working installation of python-inspector
- have a working installation of scancode-toolkit v31.x (inlucing RCs) or higher


Test protocol
***************

Step 1: Collect development code details
--------------------------------------------

In this step, you will collect the list of requirements files that exist
in the codebase. You can use scancode::

    scancode --package --info <path/to/development/codebase/dir> \
      --json-pp <path/to/development-scan-output.json> --processes 4

You then need to review the scanc results to assemble a list of pip
requirement files used in development.

Or a simpler approach is to use the ``find`` command::

    find <path/to/development/codebase/dir> -name "requirement*.txt" \
      > <path/to/requirements-file-paths.txt>

The output is a list of pip requirement files used in the development codebase.



Step 2: Build your code
----------------------------

In this step, you need to run the build of your codebase and obtain the set
of deployed binaries. Building requires both dependency resolution and
installation of the resolved packages. The set of installed packages is used to
establish the ground truth and the expected results.

As an output, keep the Python version that is used and the directory(ies) where
the deployed code is built named further down as <path/to/deployed/codebase/dir>.


Step 3: Collect built code details
---------------------------------------

In this step, you will extract the deployed code and run a scan to
collect existing packages as resolved during the original build.

For this we will use extractcode and scancode with these commands::

    extractcode --shallow <path/to/deployed/codebase/dir>
    scancode --package --info <path/to/deployed/codebase/dir> \
      --json-pp <path/to/deployed-scan-output.json> --processes 4

You can adjust the number of processes up or down based on available CPU cores.

The output is the file <path/to/scan-output.json> that contains all the detected
packages that were installed during the build.


Step 4: Resolve dependencies using development requirement files
--------------------------------------------------------------------

In this step, you will resolve the dependencies using python-inspector python-inspector
command for each of the requirements files identified in Step 1 using the
Python version identified in Step 2. Run this command for each requirements
file, using each time a different output file name. We assume here Python
version 3.8 (note the absence of dot when passed as a command line option::

    python-inspector --python-version 38 --requirement <path/to/requirements.txt> \
      --json <path/to/resolved-requirements.txt.json> \
      --netrc <path/to/.netrc>

The output is a list of JSON files with resolved packages for each of the
input requirements files.


Step 5: Collect expected resolved packages
----------------------------------------------

In this step, you need to collect the list of built packages "purl" found in
the top level "packages" attribute of the JSON scan output from Step 3.

The output is a list of expected purls with a version.


Step 6: Collect actual resolved packages
----------------------------------------------

In this step, you need to collect the list of purls "package" attribute resolved
found in the top level "resolved_dependencies" attribute of the python-inspector
resolution output from Step 4.

The output is a list of actual purls with a version.


Step 7: Compare expected with actual resolved packages
---------------------------------------------------------

In this step, you compare the output from Step 5 and Step 6 and validate the
correctness of python-inpector resolution.

The output is a list of differences:

- list 1: expected purls not present in the resolved purls.
- list 2: resolved purls not present in the expected purls.


(and if needed you can also collate the list of similar purls for reference).


If the build, build scan and resolution worked as expected, the list 1 and list 2
should be empty. The differences need to be investigated.

The possible causes could be:

- extra actual resolved packages when some of the requirement files from Step 3
  also contains files for requirements that are not deployed (e.g. test, tools.)

- missing actual resolved packages when the reference codebase from Step 1 uses
  other build manifests beyond requirements.txt files. If this is the case, you
  should carefully identify which other build manifests are used  by reviewing
  the development scan from Step 3. and report each manifest format as enhancement
  request in the python-inspector issue tracker.

- finally it can be a bug in python-inspector proper. Please report an issue
  in the python-inspector issue tracker. Attach the list or JSON output(s)
  from Step 1, Step 3 and Step 4. And the results of the review of Step 5, 6
  and 7. Alternatively you can share these files with python-inspector
  maintainers if these are private.


End-to-end example
**********************

Setup
------


We use this repo https://github.com/tjcsl/ion as a sample codebase.
And the reference Python version is 3.8::

    mkdir -p ~/tmp/pyinsp-example/
    cd ~/tmp/pyinsp-example/
    git clone https://github.com/tjcsl/ion


Another example could be https://github.com/digitalocean/sample-django

We use the latest main branch from python-inspector and scancode-toolkit 31.0.0rc2
installed on Linux with Python 3.8 using the release tarball from:
https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v31.0.0rc2

ScanCode setup::

    mkdir -p ~/tmp/pyinsp-example/tools
    cd ~/tmp/pyinsp-example/tools
    wget https://github.com/aboutcode-org/scancode-toolkit/releases/download/v31.0.0rc2/scancode-toolkit-31.0.0rc2_py38-linux.tar.xz
    tar -xf scancode-toolkit-31.0.0rc2_py38-linux.tar.xz
    cd scancode-toolkit-31.0.0rc2/
    ./scancode --help

python-inspector setup::

    cd ~/tmp/pyinsp-example/tools
    git clone https://github.com/aboutcode-org/python-inspector
    python3.8 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    cd python-inspector
    ./configure

We will store all outputs in this directory::

    mkdir -p ~/tmp/pyinsp-example/output


Step 1: Collect development code details
--------------------------------------------

We run a simple find::

    find ~/tmp/pyinsp-example/ion \
      -name "requirement*.txt" > ~/tmp/pyinsp-example/output/requirements-file-paths.txt

We find these two requirement files in ~/tmp/pyinsp-example/output/requirements-file-paths.txt::

    ~/tmp/pyinsp-example/ion/docs/rtd-requirements.txt
    ~/tmp/pyinsp-example/ion/requirements.txt


Step 2: Build your code
----------------------------

We perform a simple "editable" build in place::

    cd ~/tmp/pyinsp-example/codebase/ion
    python3.8 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install --editable .
    deactivate


Step 3: Collect built code details
---------------------------------------

We extract in place::

    cd ~/tmp/pyinsp-example/tools/scancode-toolkit-31.0.0rc2/
    ./extractcode --shallow ~/tmp/pyinsp-example/codebase/ion

And collect built details::

    ./scancode --package --info ~/tmp/pyinsp-example/codebase/ion \
      --json-pp ~/tmp/pyinsp-example/codebase/output/deployed-scan-output.json --processes 4

The output files is::

    ~/tmp/pyinsp-example/codebase/output/deployed-scan-output.json


Step 4: Resolve dependencies using development requirement files
--------------------------------------------------------------------

    cd ~/tmp/pyinsp-example/tools/python-inspector
    source venv/bin/activate

    python-inspector --requirement ~/tmp/pyinsp-example/ion/docs/rtd-requirements.txt \
      --json ~/tmp/pyinsp-example/output/resolved-rtd-requirements.txt.json

    python-inspector --requirement ~/tmp/pyinsp-example/ion/requirements.txt \
      --json ~/tmp/pyinsp-example/output/resolved-requirements.txt.json

    deactivate

The output files are::

    ~/tmp/pyinsp-example/output/resolved-rtd-requirements.txt.json
    ~/tmp/pyinsp-example/output/resolved-requirements.txt.json


Step 5: Collect expected resolved packages
----------------------------------------------

Run this python script to generate text file with expected purls

::

  import json
  with open("~/tmp/pyinsp-example/codebase/output/deployed-scan-output.json") as f:
      scancode_data = json.load(f)
  scancode_purls = []
  for package in scancode_data["packages"]:
      if package["purl"] not in scancode_purls:
          scancode_purls.append(package["purl"])
  scancode_purls = sorted(scancode_purls)
  with open("~/tmp/pyinsp-example/codebase/output/scan.txt", "w") as f:
      f.write("\n".join(scancode_purls))


The output is a list of expected purls with a version.


Step 6: Collect actual resolved packages
----------------------------------------------

Run this python script to generate text file with actual purls

::

  import json
  py_insp_purls = []
  for json_file in [
      "~/tmp/pyinsp-example/output/resolved-rtd-requirements.txt.json",
      "~/tmp/pyinsp-example/output/resolved-requirements.txt.json",
  ]:
      with open(json_file) as f:
          py_insp_data = json.load(f)
      for package in py_insp_data["resolved_dependencies"]:
          if package["package"] not in py_insp_purls:
              py_insp_purls.append(package["package"])
  py_insp_purls = sorted(py_insp_purls)
  with open("~/tmp/pyinsp-example/codebase/output/py-insp.txt", "w") as f:
      f.write("\n".join(py_insp_purls))


The output is a list of actual purls with a version.


Step 7: Compare expected with actual resolved packages
---------------------------------------------------------

We run a sdiff command::

    sdiff ~/tmp/pyinsp-example/codebase/output/py-insp.txt ~/tmp/pyinsp-example/codebase/output/scan.txt
