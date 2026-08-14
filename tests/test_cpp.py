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

    void print_channel_metadata(const imc::channel_metadata& metadata)
    {
        std::cout << R"({"schema_version":)" << metadata.schema_version
                  << R"(,"uuid":")" << imc::escape_json_string(metadata.uuid)
                  << R"(","name":")" << imc::escape_json_string(metadata.name)
                  << R"(","source_name":")" << imc::escape_json_string(metadata.source_name)
                  << R"(","kind":)" << static_cast<int>(metadata.kind)
                  << R"(,"dimension":)" << metadata.dimension
                  << R"(,"y_numeric_type":)" << metadata.y_numeric_type
                  << R"(,"y_significant_bits":)" << metadata.y_significant_bits
                  << R"(,"sample_count":)" << metadata.sample_count
                  << R"(,"trigger_time":)" << metadata.trigger_time
                  << R"(,"x_step_width":)" << metadata.x_step_width
                  << R"(,"x_offset":)" << metadata.x_offset
                  << R"(,"y_factor":)" << metadata.y_factor
                  << R"(,"y_offset":)" << metadata.y_offset
                  << R"(,"group_name":")" << imc::escape_json_string(metadata.group_name)
                  << R"(","properties":)";
        std::cout << "[";
        for ( size_t index = 0; index < metadata.properties.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::property_metadata& property = metadata.properties[index];
            std::cout << R"({"name":")" << imc::escape_json_string(property.name)
                      << R"(","value":")" << imc::escape_json_string(property.value)
                      << R"(","type_code":)" << property.type_code
                      << R"(,"flags":)" << property.flags
                      << "}";
        }
        std::cout << "]}";
    }

    void print_file_metadata(const imc::file_metadata& metadata)
    {
        std::cout << R"({"producer":")" << imc::escape_json_string(metadata.producer)
                  << R"(","comment":")" << imc::escape_json_string(metadata.comment)
                  << R"(","language_code":")" << imc::escape_json_string(metadata.language_code)
                  << R"(","codepage":")" << imc::escape_json_string(metadata.codepage)
                  << R"("})";
    }

    void print_groups_metadata(const std::vector<imc::group_metadata>& groups)
    {
        std::cout << "[";
        for ( size_t index = 0; index < groups.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::group_metadata& group = groups[index];
            std::cout << R"({"index":)" << group.index
                      << R"(,"name":")" << imc::escape_json_string(group.name)
                      << R"(","comment":")" << imc::escape_json_string(group.comment)
                      << R"("})";
        }
        std::cout << "]";
    }

    void print_text_objects_metadata(const std::vector<imc::text_object_metadata>& text_objects)
    {
        std::cout << "[";
        for ( size_t index = 0; index < text_objects.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::text_object_metadata& text = text_objects[index];
            std::cout << R"({"group_index":)" << text.group_index
                      << R"(,"name":")" << imc::escape_json_string(text.name)
                      << R"(","comment":")" << imc::escape_json_string(text.comment)
                      << R"(","content":")" << imc::escape_json_string(text.content)
                      << R"("})";
        }
        std::cout << "]";
    }

    void print_channel_representation(const imc::channel_representation& representation)
    {
        std::cout << R"({"schema_version":)" << representation.schema_version
                  << R"(,"format":)" << static_cast<int>(representation.format)
                  << R"(,"storage_kind":)" << static_cast<int>(representation.storage_kind)
                  << R"(,"uuid":")" << imc::escape_json_string(representation.uuid)
                  << R"(","has_generated_x_axis":)" << (representation.has_generated_x_axis ? "true" : "false")
                  << R"(,"x_numeric_type":)" << representation.x_numeric_type
                  << R"(,"y_numeric_type":)" << representation.y_numeric_type
                  << R"(,"x_sample_width_bytes":)" << representation.x_sample_width_bytes
                  << R"(,"y_sample_width_bytes":)" << representation.y_sample_width_bytes
                  << R"(,"x_payload_size_bytes":)" << representation.x_payload_size_bytes
                  << R"(,"y_payload_size_bytes":)" << representation.y_payload_size_bytes
                  << R"(,"numeric_sample_count":)" << representation.numeric_sample_count
                  << R"(,"segment_count":)" << representation.segment_count
                  << R"(,"tsa_payload_size_bytes":)" << representation.tsa_payload_size_bytes
                  << "}";
    }

    void print_tsa_record_descriptors(const std::vector<imc::tsa_record_descriptor>& descriptors)
    {
        std::cout << "[";
        for ( size_t index = 0; index < descriptors.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::tsa_record_descriptor& descriptor = descriptors[index];
            std::cout << R"({"record_ordinal":)" << descriptor.record_ordinal
                      << R"(,"raw_timestamp":)" << descriptor.raw_timestamp
                      << R"(,"timestamp":)" << descriptor.timestamp
                      << R"(,"logical_payload_offset_bytes":)" << descriptor.logical_payload_offset_bytes
                      << R"(,"payload_length_bytes":)" << descriptor.payload_length_bytes
                      << "}";
        }
        std::cout << "]";
    }

    void print_tsa_channel_segments(const std::vector<imc::tsa_channel_segment>& segments)
    {
        std::cout << "[";
        for ( size_t index = 0; index < segments.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::tsa_channel_segment& segment = segments[index];
            std::cout << R"({"segment_ordinal":)" << segment.segment_ordinal
                      << R"(,"raw_payload_offset_bytes":)" << segment.raw_payload_offset_bytes
                      << R"(,"raw_payload_length_bytes":)" << segment.raw_payload_length_bytes
                      << R"(,"is_source_defined":)" << (segment.is_source_defined ? "true" : "false")
                      << "}";
        }
        std::cout << "]";
    }

    void print_numeric_channel_segments(const std::vector<imc::numeric_channel_segment>& segments)
    {
        std::cout << "[";
        for ( size_t index = 0; index < segments.size(); ++index )
        {
            if ( index > 0 ) std::cout << ",";
            const imc::numeric_channel_segment& segment = segments[index];
            std::cout << R"({"segment_ordinal":)" << segment.segment_ordinal
                      << R"(,"sample_offset":)" << segment.sample_offset
                      << R"(,"sample_count":)" << segment.sample_count
                      << R"(,"trigger_time_seconds_since_1980":)" << segment.trigger_time_seconds_since_1980
                      << R"(,"x_start":)" << segment.x_start
                      << R"(,"x_step_width":)" << segment.x_step_width
                      << "}";
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

        if ( command == "get_channel_metadata_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_channel_metadata(raw.get_channel_metadata(argv[3]));
            return 0;
        }

        if ( command == "get_channels_metadata_json" )
        {
            if ( argc != 3 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            const std::vector<imc::channel_metadata> metadata = raw.get_channels_metadata();
            std::cout << "[";
            for ( size_t index = 0; index < metadata.size(); ++index )
            {
                if ( index > 0 ) std::cout << ",";
                print_channel_metadata(metadata[index]);
            }
            std::cout << "]";
            return 0;
        }

        if ( command == "get_file_metadata_json" )
        {
            if ( argc != 3 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_file_metadata(raw.get_file_metadata());
            return 0;
        }

        if ( command == "get_groups_metadata_json" )
        {
            if ( argc != 3 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_groups_metadata(raw.get_groups_metadata());
            return 0;
        }

        if ( command == "get_text_objects_metadata_json" )
        {
            if ( argc != 3 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_text_objects_metadata(raw.get_text_objects_metadata());
            return 0;
        }

        if ( command == "get_channel_representation_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_channel_representation(raw.get_channel_representation(argv[3]));
            return 0;
        }

        if ( command == "read_tsa_payload_json" )
        {
            if ( argc != 6 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            std::vector<unsigned char> payload = raw.read_tsa_payload(
                argv[3],
                static_cast<uint64_t>(std::stoull(argv[4])),
                static_cast<uint64_t>(std::stoull(argv[5]))
            );
            print_array<unsigned char>(payload);
            return 0;
        }

        if ( command == "read_tsa_record_descriptors_json" )
        {
            if ( argc != 6 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_tsa_record_descriptors(raw.read_tsa_record_descriptors(
                argv[3],
                static_cast<uint64_t>(std::stoull(argv[4])),
                static_cast<uint64_t>(std::stoull(argv[5]))
            ));
            return 0;
        }

        if ( command == "read_tsa_record_payload_json" )
        {
            if ( argc != 5 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_array<unsigned char>(raw.read_tsa_record_payload(
                argv[3],
                static_cast<uint64_t>(std::stoull(argv[4]))
            ));
            return 0;
        }

        if ( command == "read_component_payload_json" )
        {
            if ( argc != 7 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            imc::channel_component component = std::string(argv[4]) == "x"
                ? imc::channel_component::x
                : imc::channel_component::y;
            print_array<unsigned char>(raw.read_component_payload(
                argv[3],
                component,
                static_cast<uint64_t>(std::stoull(argv[5])),
                static_cast<uint64_t>(std::stoull(argv[6]))
            ));
            return 0;
        }

        if ( command == "get_tsa_channel_segments_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_tsa_channel_segments(raw.get_tsa_channel_segments(argv[3]));
            return 0;
        }

        if ( command == "get_numeric_channel_segments_json" )
        {
            if ( argc != 4 )
            {
                return 2;
            }

            imc::raw raw(argv[2]);
            print_numeric_channel_segments(raw.get_numeric_channel_segments(argv[3]));
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

COMPONENTS_DIR = SAMPLES_DIR / "components"
METADATA_DIR = SAMPLES_DIR / "metadata"
COMPONENT_PAYLOAD_SAMPLES = [
    COMPONENTS_DIR / "imc2_component_payload_6byte.dat",
    COMPONENTS_DIR / "imc3_component_payload_6byte.dat",
]
SIX_BYTE_Y_VALUES = [0, 1, 255, 256, 65535, 65536, 4294967295, 1099511627776, 281474976710655]
SIX_BYTE_XY_X_VALUES = [0, 1, 255, 256, 65535, 65536]
SIX_BYTE_XY_Y_VALUES = [281474976710655, 1099511627776, 4294967295, 65536, 256, 1]
METADATA_SAMPLES = [
    METADATA_DIR / "imc2_object_and_file_metadata.dat",
    METADATA_DIR / "imc3_object_and_file_metadata.dat",
]
FIXTURE_PROPERTIES = [
    {"name": "Fixture.Text", "value": "alpha,beta", "type_code": 0, "flags": 0},
    {"name": "Fixture.Integer", "value": "212", "type_code": 1, "flags": 0},
    {"name": "Fixture.Real", "value": "21.5", "type_code": 2, "flags": 0},
    {"name": "Fixture.Boolean", "value": "1", "type_code": 5, "flags": 0},
]

NUMERIC_EVENT_SAMPLE_NAMES = [
    sample_name for sample_name, _ in (SUPPORTED_IMC2_NUMERIC_EVENT_SAMPLES + SUPPORTED_IMC3_NUMERIC_EVENT_SAMPLES)
]


class TestCppFacade:
    """Regression tests for the legacy C++ facade surfaces."""

    @pytest.mark.parametrize("sample", METADATA_SAMPLES)
    def test_native_container_metadata_matches_fixture(self, sample, cpp_probe_binary):
        sample = require_sample(sample)

        def probe(command):
            output = _run_cpp_probe(cpp_probe_binary, [command, str(sample)])
            return json.loads(output[output.find("{") if output.lstrip().startswith("{") else output.find("["):])

        file_metadata = probe("get_file_metadata_json")
        groups = probe("get_groups_metadata_json")
        text_objects = probe("get_text_objects_metadata_json")
        channels = probe("get_channels_metadata_json")

        assert file_metadata["producer"] == "Famos"
        assert file_metadata["comment"] == "file comment: metadata fixture"
        assert groups == [{"index": 1, "name": "MetadataGroup", "comment": "group comment"}]
        assert text_objects == [{
            "group_index": 1,
            "name": "Readme",
            "comment": "text object comment",
            "content": "metadata fixture text object",
        }]
        assert len(channels) == 1
        assert channels[0]["name"] == "Signal"
        assert channels[0]["group_name"] == (
            "Signal" if sample.name.startswith("imc2_") else "MetadataGroup"
        )
        assert channels[0]["properties"] == FIXTURE_PROPERTIES

    @pytest.mark.parametrize("sample", COMPONENT_PAYLOAD_SAMPLES)
    def test_component_payload_preserves_exact_six_byte_values(self, sample, cpp_probe_binary):
        sample = require_sample(sample)
        parser = ImcTermite(sample)
        channels = parser.get_channels(include_data=False)
        six_byte_y = next(
            channel for channel in channels if (channel["name"] or channel["group"]["name"]) == "SixByteY"
        )
        six_byte_xy = next(
            channel for channel in channels if (channel["name"] or channel["group"]["name"]) == "SixByteXY"
        )

        y_representation = json.loads(_run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_representation_json", str(sample), six_byte_y["uuid"]],
        ))
        xy_representation = json.loads(_run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_representation_json", str(sample), six_byte_xy["uuid"]],
        ))
        assert y_representation["y_numeric_type"] == 13
        assert y_representation["y_sample_width_bytes"] == 6
        assert y_representation["y_payload_size_bytes"] == len(SIX_BYTE_Y_VALUES) * 6
        assert xy_representation["x_numeric_type"] == 13
        assert xy_representation["y_numeric_type"] == 13
        assert xy_representation["x_sample_width_bytes"] == 6
        assert xy_representation["y_sample_width_bytes"] == 6

        def read_payload(uuid, component, offset, length):
            return json.loads(_run_cpp_probe(
                cpp_probe_binary,
                ["read_component_payload_json", str(sample), uuid, component, str(offset), str(length)],
            ))

        expected_y = list(b"".join(value.to_bytes(6, "little") for value in SIX_BYTE_Y_VALUES))
        expected_x = list(b"".join(value.to_bytes(6, "little") for value in SIX_BYTE_XY_X_VALUES))
        expected_xy_y = list(b"".join(value.to_bytes(6, "little") for value in SIX_BYTE_XY_Y_VALUES))
        assert read_payload(six_byte_y["uuid"], "y", 0, len(expected_y)) == expected_y
        assert read_payload(six_byte_xy["uuid"], "x", 0, len(expected_x)) == expected_x
        assert read_payload(six_byte_xy["uuid"], "y", 0, len(expected_xy_y)) == expected_xy_y
        assert read_payload(six_byte_xy["uuid"], "y", 5, 8) == expected_xy_y[5:13]
        assert read_payload(six_byte_xy["uuid"], "y", len(expected_xy_y), 0) == []

        promoted = parser.get_channel_data(six_byte_y["uuid"], include_x=False, mode="raw")["y"]
        assert promoted.tolist() == SIX_BYTE_Y_VALUES

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

    @pytest.mark.parametrize(
        "sample",
        [
            DATASET_A_DIR / "datasetA_1.raw",
            IMC3_DIR / "imc3_sampleA.dat",
        ],
    )
    def test_typed_channel_metadata_matches_existing_json(self, sample, cpp_probe_binary):
        sample = require_sample(sample)
        json_metadata = ImcTermite(str(sample).encode()).get_channels(include_data=False)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_metadata_json", str(sample), json_metadata["uuid"]],
        )
        typed_metadata = json.loads(run_output[run_output.find("{"):])

        assert typed_metadata["schema_version"] == 1
        assert typed_metadata["uuid"] == json_metadata["uuid"]
        assert typed_metadata["name"] == (json_metadata["name"] or json_metadata["group"]["name"])
        assert typed_metadata["source_name"] == json_metadata["name"]
        assert typed_metadata["y_numeric_type"] == int(json_metadata["datatype"])
        assert typed_metadata["y_significant_bits"] == int(json_metadata["significantbits"])
        assert typed_metadata["x_step_width"] == float(json_metadata["xstepwidth"])
        assert typed_metadata["x_offset"] == float(json_metadata["xoffset"])
        assert typed_metadata["y_factor"] == float(json_metadata["factor"])
        assert typed_metadata["y_offset"] == float(json_metadata["offset"])
        assert typed_metadata["group_name"] == json_metadata["group"]["name"]

    @pytest.mark.parametrize(
        ("sample", "expected_format", "expected_generated_x_axis"),
        [
            (DATASET_A_DIR / "datasetA_1.raw", 0, True),
            (IMC3_DIR / "imc3_sampleA.dat", 1, True),
            (SAMPLES_DIR / "XY_dataset_example.dat", 0, False),
        ],
    )
    def test_channel_representation_matches_existing_metadata(
        self,
        sample,
        expected_format,
        expected_generated_x_axis,
        cpp_probe_binary,
    ):
        sample = require_sample(sample)
        metadata = ImcTermite(str(sample).encode()).get_channels(include_data=False)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_channel_representation_json", str(sample), metadata["uuid"]],
        )
        representation = json.loads(run_output[run_output.find("{"):])

        assert representation["schema_version"] == 1
        assert representation["format"] == expected_format
        assert representation["uuid"] == metadata["uuid"]
        assert representation["has_generated_x_axis"] is expected_generated_x_axis
        assert representation["y_numeric_type"] == int(metadata["datatype"])
        assert representation["y_payload_size_bytes"] == int(metadata["buffer-size"])
        assert representation["numeric_sample_count"] > 0

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
    def test_tsa_physical_payload_is_exactly_reconstructable_from_ranges(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)
        channel = ImcTermite(str(sample).encode()).get_channels(include_data=False)[0]

        full_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_payload_json", str(sample), channel["uuid"], "0", str(int(channel["buffer-size"]))],
        )
        full_payload = json.loads(full_output[full_output.find("["):])
        midpoint = len(full_payload) // 2
        first_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_payload_json", str(sample), channel["uuid"], "0", str(midpoint)],
        )
        second_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_payload_json", str(sample), channel["uuid"], str(midpoint), str(len(full_payload) - midpoint)],
        )

        assert json.loads(first_output[first_output.find("["):]) + json.loads(second_output[second_output.find("["):]) == full_payload

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_record_descriptors_match_decoded_record_order(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)
        parser = ImcTermite(str(sample).encode())
        channel = parser.get_channels(include_data=False)[0]
        events = parser.get_channel_events(channel["uuid"])

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_record_descriptors_json", str(sample), channel["uuid"], "0", str(len(events["texts"]))],
        )
        descriptors = json.loads(run_output[run_output.find("["):])

        assert [descriptor["record_ordinal"] for descriptor in descriptors] == list(range(len(events["texts"])))
        assert_exact_allclose([descriptor["timestamp"] for descriptor in descriptors], events["timestamps"])
        assert all(descriptor["payload_length_bytes"] >= 0 for descriptor in descriptors)

    @pytest.mark.parametrize("sample_name", ["imc2_TsaChannel.dat", "imc3_TsaChannel.dat"])
    def test_tsa_record_payloads_preserve_the_logical_record_bytes(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)
        channel = ImcTermite(str(sample).encode()).get_channels(include_data=False)[0]

        first_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_record_payload_json", str(sample), channel["uuid"], "0"],
        )
        second_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_record_payload_json", str(sample), channel["uuid"], "1"],
        )

        assert bytes(json.loads(first_output[first_output.find("["):])) == b"hello"
        assert bytes(json.loads(second_output[second_output.find("["):])) == b"0123456789"

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_record_payload_lengths_match_descriptors(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)
        parser = ImcTermite(str(sample).encode())
        channel = parser.get_channels(include_data=False)[0]
        event_count = len(parser.get_channel_events(channel["uuid"])["texts"])

        descriptor_output = _run_cpp_probe(
            cpp_probe_binary,
            ["read_tsa_record_descriptors_json", str(sample), channel["uuid"], "0", str(event_count)],
        )
        descriptors = json.loads(descriptor_output[descriptor_output.find("["):])
        for descriptor in descriptors:
            payload_output = _run_cpp_probe(
                cpp_probe_binary,
                ["read_tsa_record_payload_json", str(sample), channel["uuid"], str(descriptor["record_ordinal"])],
            )
            assert len(json.loads(payload_output[payload_output.find("["):])) == descriptor["payload_length_bytes"]

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_channel_segment_covers_the_complete_physical_payload(self, sample_name, cpp_probe_binary):
        sample = require_sample(TSA_DIR / sample_name)
        channel = ImcTermite(str(sample).encode()).get_channels(include_data=False)[0]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_tsa_channel_segments_json", str(sample), channel["uuid"]],
        )
        segments = json.loads(run_output[run_output.find("["):])

        assert segments == [{
            "segment_ordinal": 0,
            "raw_payload_offset_bytes": 0,
            "raw_payload_length_bytes": int(channel["buffer-size"]),
            "is_source_defined": False,
        }]

    @pytest.mark.parametrize("sample_name", NUMERIC_EVENT_SAMPLE_NAMES)
    def test_numeric_channel_segments_match_existing_event_metadata(self, sample_name, cpp_probe_binary):
        sample = require_sample(EVENTS_DIR / sample_name)
        parser = ImcTermite(str(sample).encode())
        channel = parser.get_channels(include_data=False)[0]
        events = parser.get_channel_events(channel["uuid"])["events"]

        run_output = _run_cpp_probe(
            cpp_probe_binary,
            ["get_numeric_channel_segments_json", str(sample), channel["uuid"]],
        )
        segments = json.loads(run_output[run_output.find("["):])

        assert [segment["segment_ordinal"] for segment in segments] == list(range(len(events)))
        assert [segment["sample_count"] for segment in segments] == [len(event["y"]) for event in events]
        assert_exact_allclose([segment["trigger_time_seconds_since_1980"] for segment in segments], [event["timestamp"] for event in events])

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
