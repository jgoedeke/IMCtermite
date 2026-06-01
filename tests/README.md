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
make test              # Via makefile (builds if needed)
pytest                 # Direct pytest
```

### CLI Tests Only
```bash
make test-cli
pytest tests/test_cli.py
```

### Python Module Tests Only
```bash
make test-python
pytest tests/test_python.py
```

## Prerequisites

### Recommended: Development install

Install the package in editable mode with test dependencies (handles all requirements automatically):

```bash
pip install -e "python[test]"
```

Then run tests with pytest:
```bash
pytest
```

### Alternative: Using makefile

If you prefer `make test`, just install pytest first:

```bash
pip install pytest
make test
```

