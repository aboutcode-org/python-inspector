# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV=venv
ACTIVATE?=. ${VENV}/bin/activate;

dev:
	@echo "-> Configure the development envt."
	./configure --dev

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	${VENV}/bin/isort --sl -l 100 src tests setup.py --skip-glob "*/_packagedcode/*"

black:
	@echo "-> Apply black code formatter"
	${VENV}/bin/black -l 100 src tests setup.py --exclude "_packagedcode/.*"

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

valid: isort black

check:
	@echo "-> Run pycodestyle (PEP8) validation"
	@${ACTIVATE} pycodestyle --max-line-length=110 \
	   --exclude=.eggs,etc/scripts,src/_packagedcode,venv/,lib/,thirdparty/,docs/,.cache/ .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --sl --check-only -l 100 setup.py src tests --skip-glob "*/_packagedcode/*"
	@echo "-> Run black validation"
	@${ACTIVATE} black --check -l 100 src tests setup.py --exclude "_packagedcode/.*"

clean:
	@echo "-> Clean the Python env"
	./configure --clean

test:
	@echo "-> Run the test suite"
	${VENV}/bin/pytest -vvs

docs:
	rm -rf docs/_build/
	@${ACTIVATE} sphinx-build docs/ docs/_build/

.PHONY:  conf dev check valid black isort clean test docs
