#-----------------------------------------------------------------------------#

SHELL := /bin/bash

# name of executable and CLI tool
EXE = imctermite

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
OPT = -O3 -Wall -Wconversion -Wpedantic -Werror -Wunused-variable -Wsign-compare

# determine git version/commit and release tag
GTAG := $(shell git tag -l --sort=version:refname | tail -n1 | sed "s/$^v//g")
GHSH := $(shell git rev-parse HEAD | head -c8)
GVSN := $(shell cat python/VERSION | tr -d ' \n')

# current timestamp
TMS = $(shell date +%Y%m%dT%H%M%S)

# define install location
INST := /usr/local/bin

#-----------------------------------------------------------------------------#
# C++ and CLI tool

# build executable
$(EXE): check-tags main.o
	$(CC) $(OPT) main.o -o $@

# build main.cpp and include git version/commit tag
main.o: src/main.cpp $(IPP)
	@cp $< $<.cpp
	@sed -i 's/TAGSTRING/$(GTAG)/g' $<.cpp
	@sed -i 's/HASHSTRING/$(GHSH)/g' $<.cpp
	@sed -i 's/TIMESTAMPSTRING/$(TMS)/g' $<.cpp
	$(CC) -c $(OPT) $(MIB) $<.cpp -o $@
	@rm $<.cpp

install: $(EXE)
	cp $< $(INST)/

uninstall: $(INST)/$(EXE)
	rm $<

cpp-clean:
	rm -vf $(EXE)
	rm -vf *.o

#-----------------------------------------------------------------------------#
# C++ linter

check-code:
	cppcheck --enable=all -I lib/ src/main.cpp

#-----------------------------------------------------------------------------#
# versions

$(GTAG):
	@echo "consistent versions check successful: building $(GTAG)"

check-tags:
	@echo "latest git tag:  $(GTAG)"
	@echo "latest git hash: $(GHSH)"
	@echo "python version:  $(GVSN)"

#-----------------------------------------------------------------------------#
# Docker

docker-build:
	docker build ./ --tag imctermite:0.1

docker-run:
	docker run -it --rm imctermite:0.1 /bin/bash

#-----------------------------------------------------------------------------#
# python

python-build: check-tags
	make -C python/ build-inplace
	cp python/imctermite*.so ./ -v 2>/dev/null || cp python/imctermite*.pyd ./ -v 2>/dev/null || true

python-clean:
	make -C python/ clean
	rm -vf imctermite*.so imctermite*.pyd

python-test:
	PYTHONPATH=./ python python/examples/usage.py

#-----------------------------------------------------------------------------#
# tests

test: $(EXE) python-build
	@echo "Running all tests..."
	@PYTHONPATH=./ pytest

test-cli: $(EXE)
	@echo "Running CLI tests..."
	@PYTHONPATH=./ pytest tests/test_cli.py

test-python: python-build
	@echo "Running Python tests..."
	@PYTHONPATH=./ pytest tests/test_python.py

#-----------------------------------------------------------------------------#
# clean

test-clean:
	rm -rf .pytest_cache
	find tests/ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean: cpp-clean python-clean test-clean

#-----------------------------------------------------------------------------#
# github actions

github-action-lint: .github/workflows/pypi-deploy.yml
	actionlint $<

# for reference, see:
# https://github.com/rhysd/actionlint

#-----------------------------------------------------------------------------#
