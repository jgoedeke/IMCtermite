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

```bash
pip install cython pytest setuptools
```
