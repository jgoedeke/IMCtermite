---
name: "IMCtermite Parser Regression"
description: "Reproduce a parsing failure from a broken IMC file, add a regression fixture/test, fix the parser, and validate the result"
argument-hint: "Broken file path plus optional expected values or observations"
agent: "agent"
---

Resolve an IMC parser regression in this repository.

Treat the prompt argument as containing:
- the path to the problematic file
- optional expected values, reference observations, or notes about what should parse

Use these repository sources as ground truth before doing anything else:
- [README.md](../../README.md)
- [makefile](../../makefile)
- [tests/sample_manifest.py](../../tests/sample_manifest.py)
- [tests/test_python.py](../../tests/test_python.py)
- [tests/test_cli.py](../../tests/test_cli.py)
- [tests/test_cpp.py](../../tests/test_cpp.py)
- [tests/test_streaming.py](../../tests/test_streaming.py)

Follow this workflow:

1. Parse the request and identify:
   - the broken file path
   - whether the file is already in the repository
   - whether expected values were supplied
   - whether the file is intended to become a checked-in sample fixture
2. Reproduce the problem through the public surfaces first:
   - the CLI (`./imctermite <file> -c` or the smallest equivalent command)
   - the Python API (`ImcTermite(...)`)
   - use the narrowest command sequence that captures the failure or mismatch clearly
3. If the file is not yet in the repository and should become a sample:
   - confirm that the user wants it checked in if that is not already explicit
   - place it under the appropriate `samples/` subdirectory
   - choose a descriptive fixture name based on the parsing behavior, not the original external filename
4. Add regression coverage:
   - prefer small embedded expectations in tests over external CSV or text reference files
   - use representative assertions such as event counts, first/last values, or small windows of expected data
   - if a new tracked sample is added, update [tests/sample_manifest.py](../../tests/sample_manifest.py)
   - add assertions to the existing test modules instead of creating new ad hoc test files
   - extend CLI/C++/streaming tests only when the bug is visible through those surfaces
5. Fix the parser:
   - keep the change as local and format-driven as possible
   - encode the actual format rule revealed by the failing file instead of hard-coding a fixture-specific workaround
6. Validate in the repository’s existing workflow:
   - run focused tests for the affected area first
   - then run the existing build/test flow, typically `make prepare-test` if needed and `make test`
   - use existing repository commands only
7. Finish by reporting:
   - how the failure was reproduced
   - whether a sample fixture was added or renamed
   - which tests were added or updated
   - which parser files changed
   - what validation was run and whether it passed

Repository-specific rules:
- Prefer embedded representative expected values in tests over checked-in reference CSVs.
- Update [tests/sample_manifest.py](../../tests/sample_manifest.py) whenever a new sample fixture is added under `samples/`.
- Sample names should describe the interesting parsing behavior, such as leading partial fragments, large initial sample offsets, or mixed event layouts.
- Reuse the existing test organization in `tests/test_python.py`, `tests/test_cli.py`, `tests/test_cpp.py`, and `tests/test_streaming.py`.
- If the user supplies only a broken file and no expectations, derive the smallest robust regression surface from the corrected parser output and explain what was asserted.
- If the user supplies external reference data, use it to derive embedded assertions and avoid leaving the repository dependent on that external file unless the user explicitly asks for that dependency.
- Stop and ask focused questions if fixture check-in, expected behavior, or intended scope is ambiguous.
