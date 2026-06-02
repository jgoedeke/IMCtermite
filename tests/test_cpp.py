#!/usr/bin/env python3
"""
Native C++ facade regression tests for IMCtermite.
"""

import csv
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import numpy as np
import pytest

from tests.assertions import assert_exact_allclose, assert_tsa_csv_rows
from tests.sample_manifest import (
    DATASET_A_DIR,
    DATASET_B_DIR,
    EVENTS_DIR,
    IMC3_DIR,
    MIXED_MULTI_EVENT_SAMPLE_CASES,
    MULTI_CHANNEL_NUMERIC_EVENT_SAMPLES,
    PROJECT_ROOT,
    SAMPLES_DIR,
    require_sample,
    SUPPORTED_IMC2_NUMERIC_EVENT_SAMPLES,
    SUPPORTED_IMC3_NUMERIC_EVENT_SAMPLES,
    SUPPORTED_TSA_EVENT_SAMPLE_NAMES,
    TSA_DIR,
)

try:
    from imctermite import ImcTermite
except ImportError:
    pytest.skip("imctermite module not built - run 'make python-build' first", allow_module_level=True)


CPP_PROBE_SOURCE = textwrap.dedent(
    """
    #include <cstdint>
    #include <iomanip>
    #include <iostream>
    #include <string>
    #include <type_traits>
    #include <vector>

    #include "imc_raw.hpp"

    template <typename T>
    void print_array(const std::vector<unsigned char>& bytes)
    {
        const T* ptr = reinterpret_cast<const T*>(bytes.data());
        size_t count = bytes.size() / sizeof(T);
        std::cout << "[";
        for ( size_t i = 0; i < count; ++i )
        {
            if ( i > 0 ) std::cout << ",";
            if constexpr (std::is_same_v<T, char16_t>)
            {
                std::cout << static_cast<unsigned int>(ptr[i]);
            }
            else
            {
                std::cout << +ptr[i];
            }
        }
        std::cout << "]";
    }

    void print_by_type(const std::vector<unsigned char>& bytes, int type)
    {
        switch ( type )
        {
            case imc::numtype::unsigned_byte: print_array<unsigned char>(bytes); break;
            case imc::numtype::signed_byte: print_array<signed char>(bytes); break;
            case imc::numtype::unsigned_short: print_array<unsigned short>(bytes); break;
            case imc::numtype::signed_short: print_array<signed short>(bytes); break;
            case imc::numtype::unsigned_long: print_array<unsigned int>(bytes); break;
            case imc::numtype::signed_long: print_array<int>(bytes); break;
            case imc::numtype::ffloat: print_array<float>(bytes); break;
            case imc::numtype::ddouble: print_array<double>(bytes); break;
            case imc::numtype::two_byte_word_digital: print_array<char16_t>(bytes); break;
            case imc::numtype::eight_byte_unsigned_long: print_array<uint64_t>(bytes); break;
            case imc::numtype::six_byte_unsigned_long:
                std::cout << "[";
                for ( size_t i = 0; i < bytes.size() / 8; ++i )
                {
                    if ( i > 0 ) std::cout << ",";
                    const uint64_t* ptr = reinterpret_cast<const uint64_t*>(bytes.data());
                    std::cout << ptr[i];
                }
                std::cout << "]";
                break;
            case imc::numtype::eight_byte_signed_long: print_array<int64_t>(bytes); break;
            default: std::cout << "[]"; break;
        }
    }

    void print_double_array(const std::vector<double>& values)
    {
        std::cout << "[";
        for ( size_t i = 0; i < values.size(); ++i )
        {
            if ( i > 0 ) std::cout << ",";
            std::cout << values[i];
        }
        std::cout << "]";
    }

    void print_string_array(const std::vector<std::string>& values)
    {
        std::cout << "[";
        for ( size_t i = 0; i < values.size(); ++i )
        {
            if ( i > 0 ) std::cout << ",";
            std::cout << '"' << imc::escape_json_string(values[i]) << '"';
        }
        std::cout << "]";
    }

    template <typename EventPayload>
    void print_numeric_event_array(const EventPayload& payload)
    {
        std::cout << "[";
        size_t offset = 0;
        for ( size_t i = 0; i < payload.counts.size(); ++i )
        {
            if ( i > 0 ) std::cout << ",";

            unsigned long int count = payload.counts[i];
            std::vector<double> x_values;
            std::vector<double> y_values;
            x_values.reserve(count);
            y_values.reserve(count);
            for ( unsigned long int sample_index = 0; sample_index < count; ++sample_index )
            {
                x_values.push_back(payload.xstarts[i] + static_cast<double>(sample_index) * payload.xstepwidths[i]);
                y_values.push_back(payload.yvalues[offset + sample_index]);
            }

            std::cout << R"({"x":)";
            print_double_array(x_values);
            std::cout << R"(,"y":)";
            print_double_array(y_values);
            std::cout << R"(,"xstart":)" << payload.xstarts[i]
                      << R"(,"xstepwidth":)" << payload.xstepwidths[i]
                      << R"(,"timestamp":)" << payload.timestamps[i]
                      << "}";
            offset += count;
        }
        std::cout << "]";
    }

    int main(int argc, char** argv)
    {
        if ( argc < 2 )
        {
            return 2;
        }

        std::string command(argv[1]);
        std::cout << std::setprecision(17);

        if ( command == "get_channel_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            imc::channel channel = raw.get_channel(argv[3]);
            std::cout << channel.get_json(true);
            return 0;
        }

        if ( command == "get_channel_events_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            imc::channel_events events = raw.get_channel_events(argv[3]);
            if ( events.numeric )
            {
                std::cout << R"({"events":)";
                print_numeric_event_array(events);
                std::cout << "}";
                return 0;
            }

            std::cout << R"({"texts":)";
            print_string_array(events.texts);
            std::cout << R"(,"timestamps":)";
            print_double_array(events.timestamps);
            std::cout << "}";
            return 0;
        }

        if ( command == "read_channel_event_chunk_json" )
        {
            if ( argc != 6 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            imc::channel_event_chunk chunk = raw.read_channel_event_chunk(
                argv[3],
                static_cast<unsigned long int>(std::stoul(argv[4])),
                static_cast<unsigned long int>(std::stoul(argv[5]))
            );
            if ( chunk.numeric )
            {
                std::cout << R"({"start":)" << chunk.start << R"(,"count":)" << chunk.count << R"(,"events":)";
                print_numeric_event_array(chunk);
                std::cout << "}";
                return 0;
            }

            std::cout << R"({"start":)" << chunk.start << R"(,"count":)" << chunk.count << R"(,"texts":)";
            print_string_array(chunk.texts);
            std::cout << R"(,"timestamps":)";
            print_double_array(chunk.timestamps);
            std::cout << "}";
            return 0;
        }

        if ( command == "print_channel_csv" )
        {
            if ( argc != 5 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            raw.print_channel(argv[3], argv[4], ',');
            return 0;
        }

        if ( command == "read_channel_chunk_json" )
        {
            if ( argc != 8 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            imc::channel_chunk chunk = raw.read_channel_chunk(
                argv[3],
                static_cast<unsigned long int>(std::stoul(argv[4])),
                static_cast<unsigned long int>(std::stoul(argv[5])),
                std::string(argv[6]) == "1",
                std::string(argv[7]) == "1"
            );

            std::cout << R"({"start":)" << chunk.start
                      << R"(,"count":)" << chunk.count
                      << R"(,"has_x":)" << (chunk.has_x ? "true" : "false")
                      << R"(,"x_type":)" << chunk.x_type
                      << R"(,"y_type":)" << chunk.y_type
                      << R"(,"x":)";
            if ( chunk.has_x )
            {
                print_by_type(chunk.x_bytes, chunk.x_type);
            }
            else
            {
                std::cout << "[]";
            }
            std::cout << R"(,"y":)";
            print_by_type(chunk.y_bytes, chunk.y_type);
            std::cout << "}";
            return 0;
        }

        return 2;
    }
    """
).strip()

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


def _run_cpp_probe(binary_path: Path, args: list[str]) -> str:
    run_result = subprocess.run(
        [str(binary_path), *args],
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    return run_result.stdout


@pytest.fixture(scope="session")
def cpp_probe_binary(tmp_path_factory):
    build_dir = tmp_path_factory.mktemp("cpp_probe")
    source = build_dir / "imctermite_cpp_probe.cpp"
    binary = build_dir / "imctermite_cpp_probe"
    source.write_text(CPP_PROBE_SOURCE)
    _compile_cpp_probe(source, binary)
    return binary


CHUNK_PARITY_CASES = [
    (SAMPLES_DIR / "exampleB.raw", 0, True),
    (SAMPLES_DIR / "XY_dataset_example.dat", 0, True),
    (IMC3_DIR / "imc3_xy_dataset.dat", 0, True),
    (DATASET_B_DIR / "datasetB_1.raw", 0, False),
]

NUMERIC_EVENT_SAMPLE_NAMES = [
    sample_name for sample_name, _ in (SUPPORTED_IMC2_NUMERIC_EVENT_SAMPLES + SUPPORTED_IMC3_NUMERIC_EVENT_SAMPLES)
]


class TestCppFacade:
    """Regression tests for the legacy C++ facade surfaces."""

    def test_imc2_get_channel_matches_python_eager_load(self, cpp_probe_binary):
        """The legacy C++ get_channel facade should preserve IMC2 eager-load behavior."""
        sample = require_sample(DATASET_A_DIR / "datasetA_1.raw")

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_json", str(sample), python_channel["uuid"]],
        )

        cpp_channel = json.loads(run_output[run_output.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"]
        assert_exact_allclose(cpp_channel["xdata"], python_channel["xdata"])
        assert_exact_allclose(cpp_channel["ydata"], python_channel["ydata"])

    def test_imc3_get_channel_adapter_matches_python_eager_load(self, cpp_probe_binary):
        """The legacy C++ get_channel adapter should load IMC3 data through the dataset path."""
        sample = require_sample(IMC3_DIR / "imc3_sampleA.dat")

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_json", str(sample), python_channel["uuid"]],
        )

        cpp_channel = json.loads(run_output[run_output.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"]
        assert_exact_allclose(cpp_channel["xdata"], python_channel["xdata"])
        assert_exact_allclose(cpp_channel["ydata"], python_channel["ydata"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_get_channel_adapter_matches_python_eager_load(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_json", str(sample), python_channel["uuid"]],
        )

        cpp_channel = json.loads(run_output[run_output.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"] == "10"
        assert cpp_channel["textdata"] == python_channel["textdata"]
        assert_exact_allclose(cpp_channel["xdata"], python_channel["xdata"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_get_channel_events_matches_python(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_events = python_channel.get_channel_events(python_metadata["uuid"])

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_events_json", str(sample), python_metadata["uuid"]],
        )

        cpp_events = json.loads(run_output[run_output.find("{"):])

        assert cpp_events["texts"] == python_events["texts"]
        assert_exact_allclose(cpp_events["timestamps"], python_events["timestamps"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_read_channel_event_chunk_matches_python(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_chunks = list(python_channel.iter_channel_events(python_metadata["uuid"], chunk_rows=1))

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_channel_event_chunk_json", str(sample), python_metadata["uuid"], "1", "1"],
        )

        cpp_chunk = json.loads(run_output[run_output.find("{"):])

        assert cpp_chunk["start"] == python_chunks[1]["start"] == 1
        assert cpp_chunk["count"] == 1
        assert cpp_chunk["texts"] == python_chunks[1]["texts"]
        assert_exact_allclose(cpp_chunk["timestamps"], python_chunks[1]["timestamps"])

    @pytest.mark.parametrize("sample_name", ["imc2_event_numeric_varied_metadata.dat", "imc3_event_numeric_varied_metadata.dat"])
    def test_numeric_event_get_channel_adapter_matches_python_eager_load(self, sample_name, cpp_probe_binary):
        sample = require_sample(EVENTS_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode()).get_channels(include_data=True)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_json", str(sample), python_channel["uuid"]],
        )

        cpp_channel = json.loads(run_output[run_output.find("{"):])

        assert cpp_channel["uuid"] == python_channel["uuid"]
        assert cpp_channel["datatype"] == python_channel["datatype"] == "7"
        assert len(cpp_channel["events"]) == len(python_channel["events"])
        for cpp_event, python_event in zip(cpp_channel["events"], python_channel["events"]):
            assert cpp_event["timestamp"] == python_event["timestamp"]
            assert cpp_event["xstart"] == python_event["xstart"]
            assert cpp_event["xstepwidth"] == python_event["xstepwidth"]
            assert_exact_allclose(cpp_event["xdata"], python_event["xdata"])
            assert_exact_allclose(cpp_event["ydata"], python_event["ydata"])

    @pytest.mark.parametrize("sample_name", NUMERIC_EVENT_SAMPLE_NAMES)
    def test_numeric_event_get_channel_events_matches_python(self, sample_name, cpp_probe_binary):
        sample = require_sample(EVENTS_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_events = python_channel.get_channel_events(python_metadata["uuid"])

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_events_json", str(sample), python_metadata["uuid"]],
        )

        cpp_events = json.loads(run_output[run_output.find("{"):])

        assert len(cpp_events["events"]) == len(python_events["events"])
        for cpp_event, python_event in zip(cpp_events["events"], python_events["events"]):
            assert cpp_event["timestamp"] == python_event["timestamp"]
            assert cpp_event["xstart"] == python_event["xstart"]
            assert cpp_event["xstepwidth"] == python_event["xstepwidth"]
            assert_exact_allclose(cpp_event["x"], python_event["x"])
            assert_exact_allclose(cpp_event["y"], python_event["y"])

    @pytest.mark.parametrize("sample_name", NUMERIC_EVENT_SAMPLE_NAMES)
    def test_numeric_event_read_channel_event_chunk_matches_python(self, sample_name, cpp_probe_binary):
        sample = require_sample(EVENTS_DIR / sample_name)

        python_channel = ImcTermite(str(sample).encode())
        python_metadata = python_channel.get_channels(include_data=False)[0]
        python_chunks = list(python_channel.iter_channel_events(python_metadata["uuid"], chunk_rows=1))

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_channel_event_chunk_json", str(sample), python_metadata["uuid"], "1", "1"],
        )

        cpp_chunk = json.loads(run_output[run_output.find("{"):])

        assert cpp_chunk["start"] == python_chunks[1]["start"] == 1
        assert cpp_chunk["count"] == 1
        assert len(cpp_chunk["events"]) == 1
        assert cpp_chunk["events"][0]["timestamp"] == python_chunks[1]["events"][0]["timestamp"]
        assert cpp_chunk["events"][0]["xstart"] == python_chunks[1]["events"][0]["xstart"]
        assert cpp_chunk["events"][0]["xstepwidth"] == python_chunks[1]["events"][0]["xstepwidth"]
        assert_exact_allclose(cpp_chunk["events"][0]["x"], python_chunks[1]["events"][0]["x"])
        assert_exact_allclose(cpp_chunk["events"][0]["y"], python_chunks[1]["events"][0]["y"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_print_channel_matches_python_csv_output(self, sample_name, cpp_probe_binary, tmp_path):
        sample = require_sample(TSA_DIR / sample_name)

        python_imc = ImcTermite(str(sample).encode())
        channel = python_imc.get_channels(include_data=False)[0]
        output_file = tmp_path / f"{sample.stem}.csv"

        _run_cpp_probe(
            cpp_probe_binary,
            ["print_channel_csv", str(sample), channel["uuid"], str(output_file)],
        )

        rows = list(csv.reader(output_file.read_text().splitlines()))
        assert_tsa_csv_rows(sample_name, rows)

    @pytest.mark.parametrize(
        "sample_name,expected_groups,_expected_lengths",
        MULTI_CHANNEL_NUMERIC_EVENT_SAMPLES,
    )
    def test_multi_channel_numeric_event_get_channel_events_match_python(
        self,
        sample_name,
        expected_groups,
        _expected_lengths,
        cpp_probe_binary,
    ):
        sample = require_sample(EVENTS_DIR / sample_name)

        python_imc = ImcTermite(str(sample).encode())
        channels = python_imc.get_channels(include_data=False)

        assert [channel["group"]["name"] for channel in channels] == expected_groups
        for channel in channels:
            python_events = python_imc.get_channel_events(channel["uuid"])
            run_output = _run_cpp_probe(
                cpp_probe_binary,
                ["get_channel_events_json", str(sample), channel["uuid"]],
            )
            cpp_events = json.loads(run_output[run_output.find("{"):])

            assert len(cpp_events["events"]) == len(python_events["events"])
            for cpp_event, python_event in zip(cpp_events["events"], python_events["events"]):
                assert cpp_event["timestamp"] == python_event["timestamp"]
                assert cpp_event["xstart"] == python_event["xstart"]
                assert cpp_event["xstepwidth"] == python_event["xstepwidth"]
                assert_exact_allclose(cpp_event["x"], python_event["x"])
                assert_exact_allclose(cpp_event["y"], python_event["y"])

    @pytest.mark.parametrize(
        "sample_name,expected_groups,expected_types,_expected_lengths",
        MIXED_MULTI_EVENT_SAMPLE_CASES,
    )
    def test_mixed_multi_event_channels_match_python(
        self,
        sample_name,
        expected_groups,
        expected_types,
        _expected_lengths,
        cpp_probe_binary,
    ):
        sample = require_sample(EVENTS_DIR / sample_name)

        python_imc = ImcTermite(str(sample).encode())
        channels = python_imc.get_channels(include_data=False)

        assert [channel["group"]["name"] for channel in channels] == expected_groups
        assert [channel["channel_type"] for channel in channels] == expected_types
        for channel in channels[1:]:
            python_events = python_imc.get_channel_events(channel["uuid"])
            run_output = _run_cpp_probe(
                cpp_probe_binary,
                ["get_channel_events_json", str(sample), channel["uuid"]],
            )
            cpp_events = json.loads(run_output[run_output.find("{"):])

            assert len(cpp_events["events"]) == len(python_events["events"])
            for cpp_event, python_event in zip(cpp_events["events"], python_events["events"]):
                assert cpp_event["timestamp"] == python_event["timestamp"]
                assert cpp_event["xstart"] == python_event["xstart"]
                assert cpp_event["xstepwidth"] == python_event["xstepwidth"]
                assert_exact_allclose(cpp_event["x"], python_event["x"])
                assert_exact_allclose(cpp_event["y"], python_event["y"])

    @pytest.mark.parametrize("sample_path,channel_index,include_x", CHUNK_PARITY_CASES)
    @pytest.mark.parametrize("mode", ["scaled", "raw"])
    def test_read_channel_chunk_matches_python(self, sample_path, channel_index, include_x, mode, cpp_probe_binary):
        sample = require_sample(sample_path)

        python_imc = ImcTermite(str(sample).encode())
        metadata = python_imc.get_channels(include_data=False)[channel_index]
        full_data = python_imc.get_channel_data(metadata["uuid"], include_x=include_x, mode=mode)
        start = 1
        count = min(5, len(full_data["y"]) - start)
        assert count > 0

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            [
                "read_channel_chunk_json",
                str(sample),
                metadata["uuid"],
                str(start),
                str(count),
                "1" if include_x else "0",
                "1" if mode == "raw" else "0",
            ],
        )

        cpp_chunk = json.loads(run_output[run_output.find("{"):])

        assert cpp_chunk["start"] == start
        assert cpp_chunk["count"] == count
        assert cpp_chunk["has_x"] == include_x

        assert_exact_allclose(
            np.asarray(cpp_chunk["y"], dtype=np.float64),
            np.asarray(full_data["y"][start:start + count], dtype=np.float64),
        )

        if include_x:
            assert_exact_allclose(
                np.asarray(cpp_chunk["x"], dtype=np.float64),
                np.asarray(full_data["x"][start:start + count], dtype=np.float64),
            )
