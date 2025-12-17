# IMCtermite Tests

End-to-end tests for both the CLI tool and Python module.


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

