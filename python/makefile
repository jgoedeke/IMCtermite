
setup:
	cat ../README.md | grep '^# IMCtermite' -A 50000 > ./README.md
	#pandoc -f markdown -t rst -o README.rst README.md
	#python -m rstvalidator README.rst
	cp -r ../lib ./
	cp -v ../LICENSE ./

setup-clean:
	rm -vf README.md README.rst LICENSE
	rm -rf lib/

build: setup
	python3 -m pip install -e .

build-sdist: setup
	python3 -m build --sdist
	python3 -m twine check dist/*

build-bdist: setup
	python3 -m build --wheel
	python3 -m twine check dist/*

build-clean:
	rm -vf imctermite*.so imctermite*.pyd imctermite*.cpp
	rm -rvf dist/ imctermite.egg-info/
	rm -rvf build/

cibuildwheel-build: setup
	cibuildwheel --platform linux

cibuildwheel-clean:
	rm -rvf wheelhouse/

pypi-upload:
	python3 -m twine upload dist/$(shell ls -t dist/ | head -n1)

clean: setup build-clean cibuildwheel-clean setup-clean

run-example:
	PYTHONPATH=$(pwd) python3 examples/usage_files.py
