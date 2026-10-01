# IMCtermite Tests

End-to-end tests for both the CLI tool and Python module.

Current split:
- `test_cli.py` covers the CLI executable behavior.
- `test_python.py` covers the Python wrapper API and data regressions.
- `test_streaming.py` covers chunked/streaming API behavior.
- `test_cpp.py` covers native C++ facade regressions via compiled probes.


## Running Tests

### All Tests
```bash
make prepare-test
make test
make test COVERAGE=1   # Same tests plus Python wrapper coverage report
pytest                 # Direct pytest
```

### CLI Tests Only
```bash
make prepare-test
make test-cli
make test-cli COVERAGE=1
pytest tests/test_cli.py
```

### Python Module Tests Only
```bash
make prepare-test
make test-python
make test-python COVERAGE=1
pytest tests/test_python.py
```

## Prerequisites

Run the commands below from the repository root with Python 3.10+ and a C++17 compiler.

### Recommended: Explicit preparation

Prepare the local extension build before using the make targets:

```bash
make prepare-test
```

This expects the Python environment to already contain the external build and
test dependencies you need, notably `setuptools>=77.0.0`, `wheel`, `Cython`,
`numpy>=1.26.0`, and `pytest`.

If you want Python wrapper coverage through the same targets, install `pytest-cov`
outside Make and run the same test target with `COVERAGE=1`.

### Alternative: Development install

Install the package in editable mode with test dependencies yourself if you prefer working from a virtualenv-managed install:

```bash
python -m pip install -e ".[test]"
make
```

Then run tests with pytest:
```bash
pytest
```

### Alternative: Manual prerequisites

If you prefer to prepare the environment manually, install the dependencies and
build both the CLI and extension before running tests:

```bash
python -m pip install "setuptools>=77.0.0" wheel Cython "numpy>=1.26.0" pytest
make prepare-test
make test
```

If you want Python wrapper coverage through the same targets, install `pytest-cov`
as well and add `COVERAGE=1`:

```bash
pip install pytest pytest-cov
make test COVERAGE=1
```

