#-----------------------------------------------------------------------------#

SHELL := /bin/bash

.PHONY: \
	install uninstall cpp-clean \
	check-python-build-deps check-python-coverage-deps \
	python-build python-build-native-coverage python-clean python-test \
	prepare-test test test-cli test-python native-coverage-clean \
	test-native-coverage test-clean coverage-clean clean

# name of executable and CLI tool
EXE = imctermite
PYTHON ?= python3
PYTEST_ARGS ?=
COVERAGE ?= 0
PYTHON_PACKAGE_PATH = ./python:./
PYTEST = PYTHONPATH=$(PYTHON_PACKAGE_PATH) $(PYTHON) -m pytest
GCOVR ?= $(PYTHON) -m gcovr
PYTHON_COVERAGE_XML = python-coverage.xml
PYTHON_COVERAGE_ARGS = --cov=imctermite --cov-report=term-missing --cov-report=xml:$(PYTHON_COVERAGE_XML)
NATIVE_COVERAGE_XML = native-coverage.xml
NATIVE_COVERAGE_TXT = native-coverage.txt

# directory names
SRC = src/
LIB = lib/
PYT = python/

# list headers and include directories
HPP = $(wildcard $(LIB)/*.hpp)
IPP = $(shell find $(LIB) -type f -name '*.hpp')
KIB = $(shell find $(LIB) -type d)
MIB = $(foreach dir,$(KIB),-I $(dir))

# choose compiler and its options
CC = g++ -std=c++17
BASE_OPT = -O3 -Wall -Wconversion -Wpedantic -Werror -Wunused-variable -Wsign-compare -static
CLI_VERSION_DEFINE = -DIMCTERMITE_VERSION=\"$(GVSN)\"
OPT ?= $(BASE_OPT)
COVERAGE_OPT = -O0 -g -Wall -Wconversion -Wpedantic -Werror -Wunused-variable -Wsign-compare --coverage
NATIVE_COVERAGE_COMPILE_ARGS = -O0 -g --coverage
NATIVE_COVERAGE_LINK_ARGS = --coverage
NATIVE_COVERAGE_ENV = IMCTERMITE_EXTRA_COMPILE_ARGS='$(NATIVE_COVERAGE_COMPILE_ARGS)' IMCTERMITE_EXTRA_LINK_ARGS='$(NATIVE_COVERAGE_LINK_ARGS)'
GCOVR_REPORT_ARGS = \
	--root . \
	--filter 'src/' \
	--filter 'lib/' \
	--filter 'python/imctermite/' \
	--exclude 'src/main.cpp.cpp$$' \
	--exclude 'python/imctermite/_imctermite.cpp$$' \
	--exclude 'build/'
TEST_PYTEST_COVERAGE_ARGS =
TEST_PYTEST_COVERAGE_PRECHECK = :

ifeq ($(COVERAGE),1)
TEST_PYTEST_COVERAGE_ARGS = $(PYTHON_COVERAGE_ARGS)
TEST_PYTEST_COVERAGE_PRECHECK = $(MAKE) check-python-coverage-deps PYTHON='$(PYTHON)'
endif

GVSN := $(shell cat VERSION | tr -d ' \n')

# define install location
INST := /usr/local/bin

#-----------------------------------------------------------------------------#
# C++ and CLI tool

# build executable

$(EXE): main.o
	$(CC) $(OPT) main.o -o $@

# build CLI object with the package version embedded at compile time
main.o: src/main.cpp $(IPP)
	$(CC) -c $(OPT) $(CLI_VERSION_DEFINE) $(MIB) $< -o $@

install: $(EXE)
	cp $< $(INST)/

uninstall: $(INST)/$(EXE)
	rm $<

cpp-clean:
	rm -vf $(EXE)
	rm -vf *.o

check-python-build-deps:
	@$(PYTHON) -c "import Cython, numpy, setuptools" >/dev/null 2>&1 || { \
		echo "Missing Python build dependencies for $(PYTHON). Install Cython, numpy, and setuptools outside Make."; \
		exit 1; \
	}

check-python-coverage-deps:
	@$(PYTHON) -c "import pytest_cov" >/dev/null 2>&1 || { \
		echo "Missing Python coverage dependency for $(PYTHON). Install pytest-cov outside Make."; \
		exit 1; \
	}

#-----------------------------------------------------------------------------#
# python

python-build: check-python-build-deps
	$(PYTHON) setup.py build_ext --inplace

python-build-native-coverage: check-python-build-deps
	@$(NATIVE_COVERAGE_ENV) $(PYTHON) setup.py build_ext --inplace

python-clean:
	rm -rvf build/ dist/ wheelhouse/ imctermite.egg-info/
	rm -rvf python/build/ python/dist/ python/wheelhouse/ python/imctermite.egg-info/
	rm -vf imctermite*.so imctermite*.pyd
	rm -vf python/imctermite*.so python/imctermite*.pyd
	rm -vf python/imctermite/*.so python/imctermite/*.pyd python/imctermite/*.cpp

python-test:
	PYTHONPATH=$(PYTHON_PACKAGE_PATH) $(PYTHON) python/examples/usage.py

prepare-test: $(EXE) python-build
	@echo "Prepared CLI and Python test environment."

#-----------------------------------------------------------------------------#
# tests

test:
	@echo "Running all tests..."
	@$(TEST_PYTEST_COVERAGE_PRECHECK)
	@$(PYTEST) $(TEST_PYTEST_COVERAGE_ARGS) $(PYTEST_ARGS)

test-cli:
	@echo "Running CLI tests..."
	@$(TEST_PYTEST_COVERAGE_PRECHECK)
	@$(PYTEST) $(TEST_PYTEST_COVERAGE_ARGS) tests/test_cli.py $(PYTEST_ARGS)

test-python:
	@echo "Running Python tests..."
	@$(TEST_PYTEST_COVERAGE_PRECHECK)
	@$(PYTEST) $(TEST_PYTEST_COVERAGE_ARGS) tests/test_python.py $(PYTEST_ARGS)

native-coverage-clean:
	find . -type f \( -name '*.gcda' -o -name '*.gcno' \) -delete
	rm -f $(NATIVE_COVERAGE_XML) $(NATIVE_COVERAGE_TXT)

test-native-coverage: native-coverage-clean
	@echo "Running tests with native coverage..."
	@$(MAKE) cpp-clean python-clean
	@$(MAKE) OPT='$(COVERAGE_OPT)' $(EXE)
	@$(MAKE) python-build-native-coverage
	@$(PYTEST) $(PYTEST_ARGS)
	@$(GCOVR) $(GCOVR_REPORT_ARGS) --xml-pretty -o $(NATIVE_COVERAGE_XML) --txt $(NATIVE_COVERAGE_TXT)
	@cat $(NATIVE_COVERAGE_TXT)

#-----------------------------------------------------------------------------#
# clean

test-clean:
	rm -rf .pytest_cache
	find tests/ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
 
coverage-clean: native-coverage-clean
	rm -f $(PYTHON_COVERAGE_XML)

clean: cpp-clean python-clean test-clean

#-----------------------------------------------------------------------------#
