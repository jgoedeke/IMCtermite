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
TSA_DIR = SAMPLES_DIR / "tsa"


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

        cpp_channel = json.loads(run_result.stdout[run_result.stdout.find("{"):])

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

        cpp_channel = json.loads(run_result.stdout[run_result.stdout.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"]
        np.testing.assert_allclose(cpp_channel["xdata"], python_channel["xdata"], rtol=1e-9, atol=1e-9)
        np.testing.assert_allclose(cpp_channel["ydata"], python_channel["ydata"], rtol=1e-9, atol=1e-9)

    @pytest.mark.parametrize("sample_name", ["imc2_TsaChannel.dat", "imc3_TsaChannel.dat"])
    def test_tsa_get_channel_adapter_matches_python_eager_load(self, sample_name, tmp_path):
        sample = TSA_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        source = tmp_path / "tsa_get_channel_adapter.cpp"
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

        binary = tmp_path / "tsa_get_channel_adapter"
        _compile_cpp_probe(source, binary)

        run_result = subprocess.run(
            [str(binary), str(sample), python_channel["uuid"]],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, run_result.stderr

        cpp_channel = json.loads(run_result.stdout[run_result.stdout.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"] == "10"
        assert cpp_channel["textdata"] == python_channel["textdata"]
        np.testing.assert_allclose(cpp_channel["xdata"], python_channel["xdata"], rtol=1e-9, atol=1e-9)

    @pytest.mark.parametrize("sample_name", ["imc2_TsaChannel.dat", "imc3_TsaChannel.dat"])
    def test_tsa_get_channel_events_matches_python(self, sample_name, tmp_path):
        sample = TSA_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_events = python_channel.get_channel_events(python_metadata["uuid"])

        source = tmp_path / "tsa_get_channel_events.cpp"
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
    imc::channel_events events = raw.get_channel_events(argv[2]);
    std::cout << "{\\\"texts\\\":[";
    for ( size_t i = 0; i < events.texts.size(); ++i )
    {
        if ( i > 0 ) std::cout << ",";
        std::cout << "\\\"" << events.texts[i] << "\\\"";
    }
    std::cout << "],\\\"timestamps\\\":[";
    for ( size_t i = 0; i < events.timestamps.size(); ++i )
    {
        if ( i > 0 ) std::cout << ",";
        std::cout << events.timestamps[i];
    }
    std::cout << "]}";
    return 0;
}
""".strip()
        )

        binary = tmp_path / "tsa_get_channel_events"
        _compile_cpp_probe(source, binary)

        run_result = subprocess.run(
            [str(binary), str(sample), python_metadata["uuid"]],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, run_result.stderr

        cpp_events = json.loads(run_result.stdout[run_result.stdout.find("{"):])

        assert cpp_events["texts"] == python_events["texts"]
        np.testing.assert_allclose(cpp_events["timestamps"], python_events["timestamps"], rtol=1e-9, atol=1e-9)

    @pytest.mark.parametrize("sample_name", ["imc2_TsaChannel.dat", "imc3_TsaChannel.dat"])
    def test_tsa_read_channel_event_chunk_matches_python(self, sample_name, tmp_path):
        sample = TSA_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_chunks = list(python_channel.iter_channel_events(python_metadata["uuid"], chunk_rows=1))

        source = tmp_path / "tsa_read_channel_event_chunk.cpp"
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
    imc::channel_event_chunk chunk = raw.read_channel_event_chunk(argv[2], 1, 1);
    std::cout << "{\\\"start\\\":" << chunk.start << ",\\\"count\\\":" << chunk.count << ",\\\"texts\\\":[";
    for ( size_t i = 0; i < chunk.texts.size(); ++i )
    {
        if ( i > 0 ) std::cout << ",";
        std::cout << "\\\"" << chunk.texts[i] << "\\\"";
    }
    std::cout << "],\\\"timestamps\\\":[";
    for ( size_t i = 0; i < chunk.timestamps.size(); ++i )
    {
        if ( i > 0 ) std::cout << ",";
        std::cout << chunk.timestamps[i];
    }
    std::cout << "]}";
    return 0;
}
""".strip()
        )

        binary = tmp_path / "tsa_read_channel_event_chunk"
        _compile_cpp_probe(source, binary)

        run_result = subprocess.run(
            [str(binary), str(sample), python_metadata["uuid"]],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, run_result.stderr

        cpp_chunk = json.loads(run_result.stdout[run_result.stdout.find("{"):])

        assert cpp_chunk["start"] == python_chunks[1]["start"] == 1
        assert cpp_chunk["count"] == 1
        assert cpp_chunk["texts"] == python_chunks[1]["texts"]
        np.testing.assert_allclose(cpp_chunk["timestamps"], python_chunks[1]["timestamps"], rtol=1e-9, atol=1e-9)
