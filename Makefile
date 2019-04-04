# Specify defaults for testing
PREFIX := $(shell pwd)/prefix
PYTHON = dls-python
PYTHON_VERSION_SHORT := $(shell dls-python --version 2>&1 | grep -oP "(?<=^Python )[0-9]+.[0-9]+")
MODULEVER=0.0

# Override with any release info
-include Makefile.private

# This is run when we type make
dist: setup.py $(wildcard malcolm/*/*.py)
	MODULEVER=$(MODULEVER) $(PYTHON) setup.py bdist_egg
	touch dist

# Clean the module
clean:
	$(PYTHON) setup.py clean
	rm -rf build dist *egg-info installed.files prefix docs/html docs/build
	find -name '*.pyc' -delete -or -name '*~' -delete

# Install the built egg and keep track of what was installed
install: dist docs
	mkdir -p $(PREFIX)/lib/python$(PYTHON_VERSION_SHORT)/site-packages
	$(PYTHON) setup.py easy_install -m \
		--record=installed.files \
		--prefix=$(PREFIX) dist/*.egg

testpublish:
	$(PYTHON) setup.py sdist upload -r pypitest

test:
	PYTHONPATH=../scanpointgenerator $(PYTHON) setup.py test

docs:
	sphinx-build -b html docs docs/html

.PHONY: docs
