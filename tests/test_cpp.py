#!/usr/bin/env python3
"""
Native C++ facade regression tests for IMCtermite.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

try:
    from imctermite import ImcTermite
except ImportError:
    pytest.skip("imctermite module not built - run 'make python-build' first", allow_module_level=True)

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DATASET_A_DIR = SAMPLES_DIR / "datasetA"
IMC3_DIR = SAMPLES_DIR / "imc3"


def _compile_cpp_probe(source_path: Path, binary_path: Path) -> None:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is required for the native C++ regression test")

    compile_result = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-I",
            str(PROJECT_ROOT / "lib"),
            "-I",
            str(PROJECT_ROOT / "lib" / "3rdparty"),
            str(source_path),
            "-o",
            str(binary_path),
        ],
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr


class TestCppFacade:
    """Regression tests for the legacy C++ facade surfaces."""

    def test_imc2_get_channel_matches_python_eager_load(self, tmp_path):
        """The legacy C++ get_channel facade should preserve IMC2 eager-load behavior."""
        sample = DATASET_A_DIR / "datasetA_1.raw"
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        source = tmp_path / "imc2_get_channel_adapter.cpp"
        source.write_text(
            """
#include <iostream>

#include "imc_raw.hpp"

int main(int argc, char** argv)
{
  if ( argc != 3 )
  {
    return 2;
  }

  imc::raw raw(argv[1]);
  imc::channel channel = raw.get_channel(argv[2]);
  std::cout << channel.get_json(true);
  return 0;
}
""".strip()
        )

        binary = tmp_path / "imc2_get_channel_adapter"
        _compile_cpp_probe(source, binary)

        run_result = subprocess.run(
            [str(binary), str(sample), python_channel["uuid"]],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, run_result.stderr

        cpp_channel = json.loads(run_result.stdout)

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"]
        np.testing.assert_allclose(cpp_channel["xdata"], python_channel["xdata"], rtol=1e-9, atol=1e-9)
        np.testing.assert_allclose(cpp_channel["ydata"], python_channel["ydata"], rtol=1e-9, atol=1e-9)

    def test_imc3_get_channel_adapter_matches_python_eager_load(self, tmp_path):
        """The legacy C++ get_channel adapter should load IMC3 data through the dataset path."""
        sample = IMC3_DIR / "imc3_sampleA.dat"
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        source = tmp_path / "imc3_get_channel_adapter.cpp"
        source.write_text(
            """
#include <iostream>

#include "imc_raw.hpp"

int main(int argc, char** argv)
{
  if ( argc != 3 )
  {
    return 2;
  }

  imc::raw raw(argv[1]);
  imc::channel channel = raw.get_channel(argv[2]);
  std::cout << channel.get_json(true);
  return 0;
}
""".strip()
        )

        binary = tmp_path / "imc3_get_channel_adapter"
        _compile_cpp_probe(source, binary)

        run_result = subprocess.run(
            [str(binary), str(sample), python_channel["uuid"]],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, run_result.stderr

        cpp_channel = json.loads(run_result.stdout)

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"]
        np.testing.assert_allclose(cpp_channel["xdata"], python_channel["xdata"], rtol=1e-9, atol=1e-9)
        np.testing.assert_allclose(cpp_channel["ydata"], python_channel["ydata"], rtol=1e-9, atol=1e-9)
