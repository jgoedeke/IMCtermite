#!/usr/bin/env python3
"""
End-to-end tests for IMCtermite Python module
"""

import pytest
import os
import tempfile
import csv
import struct
import numpy as np

from tests.assertions import (
    assert_basic_sample_info,
    assert_exact_allclose,
    assert_exact_float_equal,
    REGRESSION_VALUE_ATOL,
    assert_scaled_chunks_match_raw_transform,
    assert_numeric_scaled_matches_raw,
    assert_regression_series_prefix,
    assert_regression_series_suffix,
    assert_tsa_channel_metadata,
    assert_tsa_texts_and_timestamps,
    assert_uniform_numeric_x_axis,
)
from tests.sample_manifest import (
    BASIC_SAMPLE_INFO_CASES,
    DATASET_A_DIR as DATASET_A,
    DATASET_B_DIR as DATASET_B,
    IMC3_DIR,
    IMC3_METADATA_SAMPLES,
    IMC3_PARITY_SAMPLES,
    KNOWN_CHANNEL_VALUE_CASES,
    KNOWN_VALUE_CASES,
    RAW_SCALED_INVARIANT_CHANNEL_CASES,
    SANITIZED_IMC3_DATA_SAMPLES,
    SANITIZED_IMC3_SAMPLES,
    SANITIZED_SINGLE_TO_BUNDLE,
    SAMPLES_DIR,
    SUPPORTED_TSA_EVENT_SAMPLE_NAMES,
    SUPPORTED_TSA_EVENT_SAMPLES,
    TSA_DIR,
    UNIFORM_X_INVARIANT_CHANNEL_CASES,
    UNSUPPORTED_TSA_EVENT_SAMPLES,
    require_sample,
    iter_supported_sample_files,
)

try:
    from imctermite import ImcTermite
except ImportError:
    pytest.skip("imctermite module not built - run 'make python-build' first", allow_module_level=True)


class TestModuleImport:
    """Test basic module functionality"""
    
    def test_module_imports(self):
        """Module should import without errors"""
        assert ImcTermite is not None
    
    def test_can_instantiate(self):
        """Should create instance with valid file"""
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")
        
        imc = ImcTermite(str(sample_file).encode())
        assert imc is not None


class TestChannelListing:
    """Test channel metadata retrieval"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance with sample file"""
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")
        return ImcTermite(str(sample_file).encode())
    
    def test_get_channel_list(self, imc_instance):
        """Should return list of channel metadata"""
        channels = imc_instance.get_channels(include_data=False)
        assert isinstance(channels, list)
        assert len(channels) > 0
    
    def test_channel_metadata_structure(self, imc_instance):
        """Channel metadata should have required fields"""
        channels = imc_instance.get_channels(include_data=False)
        first_channel = channels[0]
        
        # Check for expected keys
        required_keys = ['name', 'uuid', 'channel_type']
        for key in required_keys:
            assert key in first_channel, f"Missing key: {key}"

        assert first_channel['channel_type'] == 'numeric'
    
    def test_get_channel_data(self, imc_instance):
        """Should return channel data with xdata and ydata"""
        channels = imc_instance.get_channels(include_data=True)
        assert isinstance(channels, list)
        assert len(channels) > 0
        
        first_channel = channels[0]
        assert 'xdata' in first_channel
        assert 'ydata' in first_channel
        assert isinstance(first_channel['xdata'], list)
        assert isinstance(first_channel['ydata'], list)
        assert len(first_channel['xdata']) == len(first_channel['ydata'])

    def test_imc2_multichannel_order_matches_file_order(self):
        """IMC2 get_channels should preserve source-file channel order."""
        sample_file = require_sample(SAMPLES_DIR / "exampleB.raw")

        imc = ImcTermite(str(sample_file).encode())
        channels = imc.get_channels(include_data=False)

        assert [channel['group']['name'] for channel in channels] == ['kanal1', 'kanal2', 'E06_6_121']
        assert [int(channel['uuid']) for channel in channels] == sorted(int(channel['uuid']) for channel in channels)


class TestDataIntegrity:
    """Test data extraction and validation"""
    
    @pytest.fixture
    def sample_data(self):
        """Load sample file and extract data"""
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")
        
        imc = ImcTermite(str(sample_file).encode())
        return imc.get_channels(include_data=True)
    
    def test_data_arrays_not_empty(self, sample_data):
        """Data arrays should not be empty"""
        for channel in sample_data:
            assert len(channel['xdata']) > 0
            assert len(channel['ydata']) > 0
    
    def test_data_values_are_numeric(self, sample_data):
        """All data values should be numeric"""
        for channel in sample_data:
            for x in channel['xdata'][:10]:  # Check first 10
                assert isinstance(x, (int, float))
            for y in channel['ydata'][:10]:
                assert isinstance(y, (int, float))
            for val in channel['ydata']:
                assert isinstance(val, (int, float))


class TestIMC3Support:
    """Test positive IMC3 loading via the public Python API."""

    @pytest.mark.parametrize(
        "imc2_name,imc3_name",
        IMC3_PARITY_SAMPLES,
    )
    def test_imc3_samples_match_imc2_integrity(self, imc2_name, imc3_name):
        """Paired IMC2 and IMC3 fixtures should expose the same numeric content."""
        imc2_sample = require_sample(SAMPLES_DIR / imc2_name)
        imc3_sample = require_sample(IMC3_DIR / imc3_name)

        imc2 = ImcTermite(str(imc2_sample).encode())
        imc3 = ImcTermite(str(imc3_sample).encode())

        imc2_channels = imc2.get_channels(include_data=False)
        imc3_channels = imc3.get_channels(include_data=False)

        assert len(imc2_channels) == len(imc3_channels)

        for imc2_channel, imc3_channel in zip(imc2_channels, imc3_channels):
            assert imc2.get_channel_length(imc2_channel["uuid"]) == imc3.get_channel_length(imc3_channel["uuid"])
            assert imc2_channel.get("datatype") == imc3_channel.get("datatype")
            assert imc2_channel.get("xunit") == imc3_channel.get("xunit")
            assert_exact_float_equal(imc2_channel.get("xstepwidth", 0.0), imc3_channel.get("xstepwidth", 0.0))
            assert_exact_float_equal(imc2_channel.get("xoffset", 0.0), imc3_channel.get("xoffset", 0.0))
            assert_exact_float_equal(imc2_channel.get("factor", 1.0), imc3_channel.get("factor", 1.0))
            assert_exact_float_equal(imc2_channel.get("offset", 0.0), imc3_channel.get("offset", 0.0))

            imc2_data = imc2.get_channel_data(imc2_channel["uuid"], include_x=True)
            imc3_data = imc3.get_channel_data(imc3_channel["uuid"], include_x=True)

            assert_exact_allclose(imc2_data["x"], imc3_data["x"], equal_nan=True)
            assert_exact_allclose(imc2_data["y"], imc3_data["y"], equal_nan=True)

    @pytest.mark.parametrize(
        "sample_name,expected_names",
        IMC3_METADATA_SAMPLES,
    )
    def test_imc3_metadata_listing(self, sample_name, expected_names):
        sample = require_sample(IMC3_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=False)

        assert [channel["name"] for channel in channels] == expected_names

    def test_imc3_include_data_extracts_xy_values(self):
        sample = require_sample(IMC3_DIR / "imc3_xy_dataset.dat")

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=True)

        assert len(channels) == 1
        channel = channels[0]
        assert len(channel["xdata"]) == len(channel["ydata"]) > 0
        assert channel["xdata"][0] != channel["xdata"][1]
        assert channel["ydata"][0] != channel["ydata"][1]

    def test_imc3_rejects_compressed_files(self, tmp_path):
        sample = tmp_path / "compressed_imc3.dat"
        sample.write_bytes(
            b"|imc3,1;"
            + b"|CB1"
            + struct.pack("<IIBBBBhHHH", 1, 2, 0, 0, 0, 1, 0, 0, 1, 0)
        )

        with pytest.raises(RuntimeError, match="unsupported IMC3 compression"):
            ImcTermite(str(sample).encode())

    @pytest.mark.parametrize("sample_name,expected_channel_count", SANITIZED_IMC3_SAMPLES)
    def test_sanitized_imc3_metadata_listing(self, sample_name, expected_channel_count):
        sample = require_sample(IMC3_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=False)

        assert len(channels) == expected_channel_count
        assert all(imc.get_channel_length(channel["uuid"]) == 148836 for channel in channels)

    @pytest.mark.parametrize("sample_name", SANITIZED_IMC3_DATA_SAMPLES)
    def test_sanitized_imc3_channel_data_extracts_samples(self, sample_name):
        sample = require_sample(IMC3_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channel = imc.get_channels(include_data=False)[0]
        data = imc.get_channel_data(channel["uuid"], include_x=True)

        assert len(data["x"]) == len(data["y"]) == 148836
        assert_exact_float_equal(data["x"][0], 0.0)
        assert float(data["x"][1]) > float(data["x"][0])

    @pytest.mark.parametrize("single_name,bundle_index", SANITIZED_SINGLE_TO_BUNDLE)
    def test_sanitized_single_channels_match_bundle(self, single_name, bundle_index):
        single_sample = require_sample(IMC3_DIR / single_name)
        bundle_sample = require_sample(IMC3_DIR / "imc3_sanitized_bundle.dat")

        single = ImcTermite(str(single_sample).encode())
        bundle = ImcTermite(str(bundle_sample).encode())

        single_channel = single.get_channels(include_data=False)[0]
        bundle_channel = bundle.get_channels(include_data=False)[bundle_index]

        assert single.get_channel_length(single_channel["uuid"]) == bundle.get_channel_length(bundle_channel["uuid"])
        assert single_channel.get("datatype") == bundle_channel.get("datatype")
        assert single_channel.get("xunit") == bundle_channel.get("xunit")
        assert single_channel.get("yunit") == bundle_channel.get("yunit")
        assert_exact_float_equal(single_channel.get("xstepwidth", 0.0), bundle_channel.get("xstepwidth", 0.0))
        assert_exact_float_equal(single_channel.get("xoffset", 0.0), bundle_channel.get("xoffset", 0.0))
        assert_exact_float_equal(single_channel.get("factor", 1.0), bundle_channel.get("factor", 1.0))
        assert_exact_float_equal(single_channel.get("offset", 0.0), bundle_channel.get("offset", 0.0))

        single_scaled = single.get_channel_data(single_channel["uuid"], include_x=True)
        bundle_scaled = bundle.get_channel_data(bundle_channel["uuid"], include_x=True)
        assert_exact_allclose(single_scaled["x"], bundle_scaled["x"], equal_nan=True)
        assert_exact_allclose(single_scaled["y"], bundle_scaled["y"], equal_nan=True)

        single_raw = single.get_channel_data(single_channel["uuid"], include_x=False, mode="raw")
        bundle_raw = bundle.get_channel_data(bundle_channel["uuid"], include_x=False, mode="raw")
        np.testing.assert_array_equal(single_raw["y"], bundle_raw["y"])


class TestTSASupport:
    """Regression coverage for TSA event channels in IMC2 and IMC3 containers."""

    @pytest.mark.parametrize("sample_name,expected_length", SUPPORTED_TSA_EVENT_SAMPLES)
    def test_tsa_metadata_listing(self, sample_name, expected_length):
        sample = require_sample(TSA_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=False)

        assert len(channels) == 1
        assert_tsa_channel_metadata(imc, channels[0], expected_length)

    def test_tsa_imc2_and_imc3_match(self):
        imc2_sample = require_sample(TSA_DIR / "imc2_TsaChannel.dat")
        imc3_sample = require_sample(TSA_DIR / "imc3_TsaChannel.dat")

        imc2_channel = ImcTermite(str(imc2_sample).encode()).get_channels(include_data=True)[0]
        imc3_channel = ImcTermite(str(imc3_sample).encode()).get_channels(include_data=True)[0]

        assert imc2_channel["datatype"] == imc3_channel["datatype"] == "10"
        assert imc2_channel["channel_type"] == imc3_channel["channel_type"] == "event"
        assert imc2_channel["textdata"] == imc3_channel["textdata"] == ["hello", "0123456789"]
        assert_exact_allclose(imc2_channel["xdata"], imc3_channel["xdata"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_get_channel_data_returns_timestamp_and_text(self, sample_name):
        sample = require_sample(TSA_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channel = imc.get_channels(include_data=False)[0]
        data = imc.get_channel_data(channel["uuid"], include_x=True)

        assert list(data.keys()) == ["text", "x"]
        assert_tsa_texts_and_timestamps(sample_name, data["text"], data["x"])

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLE_NAMES)
    def test_tsa_get_channel_events_returns_event_native_shape(self, sample_name):
        sample = require_sample(TSA_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channel = imc.get_channels(include_data=False)[0]
        events = imc.get_channel_events(channel["uuid"])

        assert list(events.keys()) == ["texts", "timestamps"]
        assert len(events["texts"]) == len(events["timestamps"])
        assert_tsa_texts_and_timestamps(sample_name, events["texts"], events["timestamps"])

    @pytest.mark.parametrize("sample_name,error_pattern", UNSUPPORTED_TSA_EVENT_SAMPLES)
    def test_new_event_samples_report_currently_unsupported_modes(self, sample_name, error_pattern):
        sample = require_sample(TSA_DIR / sample_name)

        with pytest.raises(RuntimeError, match=error_pattern):
            ImcTermite(str(sample).encode())

    def test_get_channel_events_rejects_numeric_channels(self):
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")

        imc = ImcTermite(str(sample_file).encode())
        channel = imc.get_channels(include_data=False)[0]

        with pytest.raises(RuntimeError, match="channel is numeric"):
            imc.get_channel_events(channel["uuid"])

    @pytest.mark.parametrize("sample_name", ["imc2_TsaChannel.dat", "imc3_TsaChannel.dat"])
    def test_tsa_print_channel_writes_timestamp_and_text(self, sample_name, tmp_path):
        sample = require_sample(TSA_DIR / sample_name)

        imc = ImcTermite(str(sample).encode())
        channel = imc.get_channels(include_data=False)[0]
        output_file = tmp_path / f"{sample.stem}.csv"
        imc.print_channel(channel["uuid"], output_file, b','[0])

        rows = list(csv.reader(output_file.read_text().splitlines()))
        assert rows[0] == ["time", "TsaChannel"]
        assert float(rows[2][0]) == 20.0
        assert rows[2][1] == "hello"
        assert float(rows[3][0]) == 40.0
        assert rows[3][1] == "0123456789"


class TestJsonEscaping:
    """Regression tests for JSON metadata escaping."""

    def test_metadata_with_control_characters_stays_valid_json(self, tmp_path):
        reg_file = tmp_path / "json_escape_regression.raw"

        name = b'LINE\nTAB\tQ"'
        comment = b'COMMENT\tWITH\nQUOTE"'
        raw = bytearray()
        raw += TestChannelStateRegression._block("CF", "2,1", version=2)
        raw += TestChannelStateRegression._block("CK", "1,1")
        raw += TestChannelStateRegression._block("CG", "1,1,1")
        raw += TestChannelStateRegression._block("CD", "1E-1,1,1,s,0,0,0")
        raw += TestChannelStateRegression._block("NT", "1,1,2020,0,0,0.0")
        raw += TestChannelStateRegression._block("CC", "1,1")
        raw += TestChannelStateRegression._block("CP", "1,2,4,16,0,0,1,0")
        raw += TestChannelStateRegression._block("Cb", "1,0,1,1,0,4,0,4,1,0.0,0.0")
        raw += TestChannelStateRegression._block(
            "CN",
            b"0,0,0,"
            + str(len(name)).encode("ascii")
            + b"," + name
            + b"," + str(len(comment)).encode("ascii")
            + b"," + comment,
        )
        raw += TestChannelStateRegression._block("CS", b"1," + bytes([1, 0, 2, 0]))
        reg_file.write_bytes(raw)

        channel = ImcTermite(str(reg_file).encode()).get_channels(include_data=False)[0]

        assert channel["group"]["name"] == name.decode("ascii")
        assert channel["group"]["comment"] == comment.decode("ascii")


class TestChannelStateRegression:
    """Regression tests for channel component state handling."""

    @staticmethod
    def _block(key: str, payload, version: int = 1) -> bytes:
        if isinstance(payload, str):
            payload_bytes = payload.encode("ascii")
        else:
            payload_bytes = payload
        return (
            b"|"
            + key.encode("ascii")
            + b","
            + str(version).encode("ascii")
            + b","
            + str(len(payload_bytes)).encode("ascii")
            + b","
            + payload_bytes
            + b";"
        )

    def test_component_state_is_reset_between_channels(self, tmp_path):
        reg_file = tmp_path / "channel_state_regression.dat"

        raw = bytearray()
        raw += self._block("CF", "2,1", version=2)
        raw += self._block("CK", "1,1")

        raw += self._block("CG", "1,3,2")
        raw += self._block("CD", "5E-2,1,1,s,0,0,0")
        raw += self._block("NT", "1,1,2020,0,0,0.0")
        raw += self._block("CC", "1,1")
        raw += self._block("CP", "1,2,4,16,0,0,1,0")
        raw += self._block("Cb", "1,0,1,1,0,4,0,4,1,0.0,0.0")
        raw += self._block("CC", "2,1")
        raw += self._block("CP", "2,2,4,16,0,0,1,0")
        raw += self._block("Cb", "1,0,2,1,4,4,0,4,1,0.0,0.0")
        raw += self._block("CN", "0,0,0,6,CHAN_A,1,A")
        raw += self._block("CS", b"1," + bytes([1, 0, 2, 0, 11, 0, 12, 0]))

        raw += self._block("CG", "1,1,1")
        raw += self._block("CD", "1E-1,1,1,s,0,0,0")
        raw += self._block("NT", "1,1,2020,0,0,0.0")
        raw += self._block("CC", "1,1")
        raw += self._block("CP", "1,2,4,16,0,0,1,0")
        raw += self._block("Cb", "1,0,1,1,0,6,0,6,1,0.0,0.0")
        raw += self._block("CN", "0,0,0,6,CHAN_B,1,B")
        raw += self._block("CS", b"1," + bytes([21, 0, 22, 0, 23, 0]))

        reg_file.write_bytes(raw)

        imc = ImcTermite(str(reg_file).encode())
        channels = {
            channel["group"]["name"]: channel
            for channel in imc.get_channels(include_data=False)
        }

        def count_rows(uuid: str) -> int:
            total = 0
            for chunk in imc.iter_channel_numpy(
                uuid.encode("utf-8"),
                include_x=True,
                chunk_rows=1024,
                mode="scaled",
            ):
                assert len(chunk["x"]) == len(chunk["y"])
                total += len(chunk["y"])
            return total

        assert len(channels) == 2
        assert count_rows(channels["CHAN_A"]["uuid"]) == 2
        assert count_rows(channels["CHAN_B"]["uuid"]) == 3

class TestChunkedNumpy:
    """Test chunked NumPy API"""

    def test_chunked_iteration_all_samples(self):
        """Verify chunked iteration against get_channels for all samples"""
        
        # Get all .raw and .dat files recursively
        raw_files = iter_supported_sample_files()
        
        for raw_file in raw_files:
            # print(f"Testing {raw_file.name}")
            try:
                imc = ImcTermite(str(raw_file).encode())
                
                # Get reference data
                channels_ref = imc.get_channels(include_data=True)
                
                for ch_ref in channels_ref:
                    uuid = ch_ref['uuid'].encode('utf-8')
                    if 'textdata' in ch_ref:
                        with pytest.raises(RuntimeError, match="TSA event streaming"):
                            list(imc.iter_channel_numpy(uuid, include_x=True, chunk_rows=100, mode="scaled"))
                        continue
                    
                    # Test with include_x=True
                    y_chunks = []
                    x_chunks = []
                    
                    # Use a small chunk size to ensure we test chunking logic even on small files
                    # Some files might be very small, so 100 is a good stress test
                    for chunk in imc.iter_channel_numpy(uuid, include_x=True, chunk_rows=100, mode="scaled"):
                        y_chunks.append(chunk['y'])
                        x_chunks.append(chunk['x'])
                    
                    if not y_chunks:
                        assert len(ch_ref['ydata']) == 0
                        continue
                        
                    y_full = np.concatenate(y_chunks)
                    x_full = np.concatenate(x_chunks)
                    
                    # Compare with reference
                    # Note: get_channels returns lists of floats. 
                    # We compare them with numpy arrays.
                    
                    # Check lengths first
                    assert len(y_full) == len(ch_ref['ydata']), f"Length mismatch in {raw_file.name} channel {uuid}"
                    
                    # Check values
                    assert np.allclose(y_full, ch_ref['ydata'], equal_nan=True), f"Y data mismatch in {raw_file.name} channel {uuid}"
                    assert np.allclose(x_full, ch_ref['xdata'], equal_nan=True), f"X data mismatch in {raw_file.name} channel {uuid}"
                    
                    # Test with include_x=False
                    y_chunks_nox = []
                    for chunk in imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=100, mode="scaled"):
                        y_chunks_nox.append(chunk['y'])
                        assert 'x' not in chunk
                    
                    if y_chunks_nox:
                        y_full_nox = np.concatenate(y_chunks_nox)
                        assert np.allclose(y_full_nox, ch_ref['ydata'], equal_nan=True), f"Y data mismatch (no x) in {raw_file.name} channel {uuid}"

                    # Test raw mode (basic check that it runs and returns correct length)
                    # We can't easily verify values without reimplementing the scaling logic,
                    # but we can check that it returns something valid.
                    y_chunks_raw = []
                    for chunk in imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=100, mode="raw"):
                        y_chunks_raw.append(chunk['y'])
                        # Check that dtype is not float64 unless it really is float data
                        # Most samples are likely int16 or similar
                        # print(f"Raw dtype: {chunk['y'].dtype}")
                    
                    if y_chunks_raw:
                        y_full_raw = np.concatenate(y_chunks_raw)
                        assert len(y_full_raw) == len(ch_ref['ydata']), f"Raw length mismatch in {raw_file.name} channel {uuid}"

            
            except Exception as e:
                pytest.fail(f"Failed processing {raw_file.name}: {str(e)}")

    def test_datatype11_scaled_matches_raw(self):
        """Datatype 11 (digital) must not apply CR scaling in scaled mode."""
        raw_files = iter_supported_sample_files()

        checked = 0
        for raw_file in raw_files:
            imc = ImcTermite(str(raw_file).encode())
            channels = imc.get_channels(include_data=False)

            for channel in channels:
                if str(channel.get('datatype')) != '11':
                    continue

                uuid = channel['uuid'].encode('utf-8')

                raw_chunks = list(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="raw"))
                scaled_chunks = list(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="scaled"))

                if not raw_chunks:
                    continue

                assert_scaled_chunks_match_raw_transform(channel, raw_chunks, scaled_chunks)
                checked += 1

        if checked == 0:
            pytest.skip("No datatype 11 channels found in bundled sample files")

    @pytest.mark.parametrize("file_path,channel_index", RAW_SCALED_INVARIANT_CHANNEL_CASES)
    def test_nondigital_scaled_matches_raw_with_metadata_transform(self, file_path, channel_index):
        """Curated numeric channels should keep scaled = raw * factor + offset behavior across streamed chunks."""
        sample_file = require_sample(SAMPLES_DIR / file_path)

        imc = ImcTermite(str(sample_file).encode())
        channel = imc.get_channels(include_data=False)[channel_index]

        datatype = str(channel.get('datatype'))
        assert datatype not in {'10', '11'}

        uuid = channel['uuid'].encode('utf-8')
        raw_chunks = list(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=257, mode="raw"))
        scaled_chunks = list(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=257, mode="scaled"))

        assert raw_chunks
        assert_scaled_chunks_match_raw_transform(channel, raw_chunks, scaled_chunks)
    

class TestCSVOutput:
    """Test CSV file generation"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance"""
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")
        return ImcTermite(str(sample_file).encode())
    
    def test_print_channel_to_csv(self, imc_instance, tmp_path):
        """Should create CSV file for single channel"""
        output_file = tmp_path / "test_channel.csv"
        
        channels = imc_instance.get_channels(include_data=False)
        if len(channels) == 0:
            pytest.skip("No channels in sample file")
        
        channel_uuid = channels[0]['uuid']
        imc_instance.print_channel(channel_uuid.encode(), str(output_file).encode(), b','[0])
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
    
    def test_csv_format_valid(self, imc_instance, tmp_path):
        """Generated CSV should be valid"""
        output_file = tmp_path / "test_channel.csv"
        
        channels = imc_instance.get_channels(include_data=False)
        if len(channels) == 0:
            pytest.skip("No channels in sample file")
        
        channel_uuid = channels[0]['uuid']
        imc_instance.print_channel(channel_uuid.encode(), str(output_file).encode(), b','[0])
        
        # Read and validate CSV
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            assert len(rows) > 1, "CSV should have header and data"
            assert len(rows[0]) == 2, "CSV should have 2 columns"
            
            # Check second row is numeric (first row is header with units)
            if len(rows) > 1:
                data_row = rows[1]
                try:
                    float(data_row[0])  # Should not raise
                    float(data_row[1])  # Should not raise
                except ValueError:
                    # Maybe first row is header, try second data row
                    if len(rows) > 2:
                        data_row = rows[2]
                        float(data_row[0])
                        float(data_row[1])
    
    def test_print_all_channels(self, imc_instance, tmp_path):
        """Should create CSV files for all channels"""
        output_dir = tmp_path / "all_channels"
        output_dir.mkdir()
        
        imc_instance.print_channels(str(output_dir).encode(), b','[0])
        
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) > 0, "Should generate at least one CSV file"


class TestMultipleFiles:
    """Test processing multiple sample files"""

    def test_basic_sample_manifest_covers_all_supported_files(self):
        supported_files = {
            sample_file.relative_to(SAMPLES_DIR).as_posix() for sample_file in iter_supported_sample_files()
        }
        assert set(BASIC_SAMPLE_INFO_CASES) == supported_files
    
    def test_process_all_sample_files(self):
        """Should process all .raw and .dat files in samples directory (metadata only)"""
        files_to_test = iter_supported_sample_files()
        
        successful = 0
        failed = []
        for sample_file in files_to_test:
            try:
                imc = ImcTermite(str(sample_file).encode())
                channels = imc.get_channels(include_data=False)
                relative_path = sample_file.relative_to(SAMPLES_DIR).as_posix()
                expected = BASIC_SAMPLE_INFO_CASES[relative_path]
                assert_basic_sample_info(channels, expected)
                if len(channels) > 0:
                    successful += 1
            except Exception as e:
                failed.append(f"{sample_file.relative_to(SAMPLES_DIR)}: {e}")
        
        assert len(failed) == 0, f"Failed to process {len(failed)}/{len(files_to_test)} files: {failed}"
        assert successful == len(files_to_test), f"Only {successful}/{len(files_to_test)} files had channels"
    
    def test_extract_all_sample_files_with_data(self):
        """Should fully extract all .raw and .dat files with data"""
        files_to_test = iter_supported_sample_files()
        
        successful = 0
        failed = []
        for sample_file in files_to_test:
            try:
                imc = ImcTermite(str(sample_file).encode())
                channels = imc.get_channels(include_data=True)
                
                # Verify we got data
                if len(channels) > 0:
                    # Check that at least one channel has actual data (xdata or ydata)
                    has_data = False
                    for channel in channels:
                        if ('xdata' in channel and len(channel['xdata']) > 0) or \
                                    ('ydata' in channel and len(channel['ydata']) > 0) or \
                                    ('textdata' in channel and len(channel['textdata']) > 0):
                            has_data = True
                            break
                    
                    if has_data:
                        successful += 1
                    else:
                        failed.append(f"{sample_file.relative_to(SAMPLES_DIR)}: no data in channels")
                else:
                    failed.append(f"{sample_file.relative_to(SAMPLES_DIR)}: no channels found")
            except Exception as e:
                failed.append(f"{sample_file.relative_to(SAMPLES_DIR)}: {e}")
        
        assert len(failed) == 0, f"Failed to extract data from {len(failed)}/{len(files_to_test)} files: {failed}"
        assert successful == len(files_to_test), f"Only {successful}/{len(files_to_test)} files extracted with data"
    
    def test_reload_different_file(self):
        """Should be able to load different files sequentially"""
        file1 = require_sample(DATASET_A / "datasetA_1.raw")
        file2 = require_sample(DATASET_A / "datasetA_2.raw")
        
        # Load first file
        imc1 = ImcTermite(str(file1).encode())
        channels1 = imc1.get_channels(include_data=False)
        
        # Load second file
        imc2 = ImcTermite(str(file2).encode())
        channels2 = imc2.get_channels(include_data=False)
        
        # Both should work
        assert len(channels1) > 0
        assert len(channels2) > 0


class TestDataRegression:
    """Test specific known values to catch parsing regressions"""
    
    @pytest.mark.parametrize("file_path,expected", KNOWN_VALUE_CASES)
    def test_known_values(self, file_path, expected):
        """Verify known values from sample files to catch parsing regressions"""
        sample_file = require_sample(SAMPLES_DIR / file_path)
        
        imc = ImcTermite(str(sample_file).encode())
        channels = imc.get_channels(include_data=True)
        
        # Check number of channels
        assert len(channels) == expected['num_channels'], \
            f"Should have {expected['num_channels']} channel(s)"
        
        ch = channels[0]
        
        # Verify data length
        ydata = ch.get('ydata', [])
        assert len(ydata) == expected['data_length'], \
            f"Should have {expected['data_length']} data points"
        
        # Verify metadata if specified
        if 'yunit' in expected:
            assert ch.get('yunit') == expected['yunit'], \
                f"Unit should be {expected['yunit']}"
        
        if 'xstepwidth' in expected:
            assert_exact_float_equal(ch.get('xstepwidth'), expected['xstepwidth']), \
                f"X step width should be {expected['xstepwidth']}"
        
        if 'xoffset' in expected:
            assert_exact_float_equal(ch.get('xoffset'), expected['xoffset']), \
                f"X offset should be {expected['xoffset']}"
        
        # Verify ydata first values
        tolerance = REGRESSION_VALUE_ATOL
        for i, expected_val in enumerate(expected['ydata_first']):
            if isinstance(expected_val, float):
                assert abs(ydata[i] - expected_val) < tolerance, \
                    f"ydata[{i}] should be {expected_val}"
            else:
                assert ydata[i] == expected_val, \
                    f"ydata[{i}] should be {expected_val}"
        
        # Verify ydata last values
        for i, expected_val in enumerate(expected['ydata_last']):
            idx = -(len(expected['ydata_last']) - i)
            if isinstance(expected_val, float):
                assert abs(ydata[idx] - expected_val) < tolerance, \
                    f"ydata[{idx}] should be {expected_val}"
            else:
                assert ydata[idx] == expected_val, \
                    f"ydata[{idx}] should be {expected_val}"
        
        # Verify xdata if specified
        if 'xdata_first' in expected:
            xdata = ch.get('xdata', [])
            for i, expected_val in enumerate(expected['xdata_first']):
                assert abs(xdata[i] - expected_val) < tolerance, \
                    f"xdata[{i}] should be {expected_val}"
        
        if 'xdata_last' in expected:
            xdata = ch.get('xdata', [])
            for i, expected_val in enumerate(expected['xdata_last']):
                idx = -(len(expected['xdata_last']) - i)
                assert abs(xdata[idx] - expected_val) < tolerance, \
                    f"xdata[{idx}] should be {expected_val}"

    @pytest.mark.parametrize("file_path,channel_index,expected", KNOWN_CHANNEL_VALUE_CASES)
    def test_known_channel_values(self, file_path, channel_index, expected):
        sample_file = require_sample(SAMPLES_DIR / file_path)

        imc = ImcTermite(str(sample_file).encode())
        channel = imc.get_channels(include_data=True)[channel_index]

        assert channel.get("name") == expected["name"]
        assert channel.get("datatype") == expected["datatype"]
        assert len(channel.get("ydata", [])) == expected["data_length"]

        assert_regression_series_prefix(channel["xdata"], expected["xdata_first"])
        assert_regression_series_suffix(channel["xdata"], expected["xdata_last"])
        assert_regression_series_prefix(channel["ydata"], expected["ydata_first"])
        assert_regression_series_suffix(channel["ydata"], expected["ydata_last"])

    @pytest.mark.parametrize("file_path,channel_index", UNIFORM_X_INVARIANT_CHANNEL_CASES)
    def test_uniform_numeric_xdata_matches_metadata_reconstruction(self, file_path, channel_index):
        sample_file = require_sample(SAMPLES_DIR / file_path)

        imc = ImcTermite(str(sample_file).encode())
        channel = imc.get_channels(include_data=True)[channel_index]
        indices = sorted({0, 1, 2, len(channel["xdata"]) // 2, len(channel["xdata"]) - 1})

        assert_uniform_numeric_x_axis(channel, channel["xdata"], indices)

    @pytest.mark.parametrize("file_path,channel_index", RAW_SCALED_INVARIANT_CHANNEL_CASES)
    def test_numeric_scaled_values_match_raw_values_and_metadata_transform(self, file_path, channel_index):
        sample_file = require_sample(SAMPLES_DIR / file_path)

        imc = ImcTermite(str(sample_file).encode())
        channel = imc.get_channels(include_data=False)[channel_index]
        scaled = imc.get_channel_data(channel["uuid"], include_x=False, mode="scaled")
        raw = imc.get_channel_data(channel["uuid"], include_x=False, mode="raw")
        indices = sorted({0, 1, 2, len(scaled["y"]) // 2, len(scaled["y"]) - 1})

        assert_numeric_scaled_matches_raw(channel, scaled["y"], raw["y"], indices)


class TestErrorHandling:
    """Test error conditions"""
    
    def test_nonexistent_file(self):
        """Should raise error for nonexistent file"""
        with pytest.raises(Exception):
            ImcTermite(b"/nonexistent/file.raw")
    
    def test_invalid_channel_name(self):
        """Should handle invalid channel name gracefully"""
        sample_file = require_sample(DATASET_A / "datasetA_1.raw")
        
        imc = ImcTermite(str(sample_file).encode())

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = f.name

        try:
            with pytest.raises(RuntimeError, match="channel does not exist:NONEXISTENT_CHANNEL_UUID"):
                imc.print_channel(b"NONEXISTENT_CHANNEL_UUID", output_file.encode(), b','[0])
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
