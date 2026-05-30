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
from pathlib import Path

try:
    from imctermite import ImcTermite
except ImportError:
    pytest.skip("imctermite module not built - run 'make python-build' first", allow_module_level=True)

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DATASET_A = SAMPLES_DIR / "datasetA"
DATASET_B = SAMPLES_DIR / "datasetB"
IMC3_DIR = SAMPLES_DIR / "imc3"
SANITIZED_IMC3_SAMPLES = [
    ("imc3_sanitized_01.raw", 1),
    ("imc3_sanitized_02.raw", 1),
    ("imc3_sanitized_03.raw", 1),
    ("imc3_sanitized_04.raw", 1),
    ("imc3_sanitized_05.raw", 1),
    ("imc3_sanitized_06.raw", 1),
    ("imc3_sanitized_bundle.dat", 6),
]
SANITIZED_SINGLE_TO_BUNDLE = [
    ("imc3_sanitized_01.raw", 0),
    ("imc3_sanitized_02.raw", 1),
    ("imc3_sanitized_03.raw", 2),
    ("imc3_sanitized_04.raw", 3),
    ("imc3_sanitized_05.raw", 4),
    ("imc3_sanitized_06.raw", 5),
]


class TestModuleImport:
    """Test basic module functionality"""
    
    def test_module_imports(self):
        """Module should import without errors"""
        assert ImcTermite is not None
    
    def test_can_instantiate(self):
        """Should create instance with valid file"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
        imc = ImcTermite(str(sample_file).encode())
        assert imc is not None


class TestChannelListing:
    """Test channel metadata retrieval"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance with sample file"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
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
        required_keys = ['name', 'uuid']
        for key in required_keys:
            assert key in first_channel, f"Missing key: {key}"
    
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
        sample_file = SAMPLES_DIR / "exampleB.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        imc = ImcTermite(str(sample_file).encode())
        channels = imc.get_channels(include_data=False)

        assert [channel['uuid'] for channel in channels] == ['377', '707', '1038']


class TestDataIntegrity:
    """Test data extraction and validation"""
    
    @pytest.fixture
    def sample_data(self):
        """Load sample file and extract data"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
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
        [
            ("sampleA.raw", "imc3_sampleA.dat"),
            ("sampleB.raw", "imc3_sampleB.dat"),
            ("XY_dataset_example.dat", "imc3_XY_dataset_example.dat"),
        ],
    )
    def test_imc3_samples_match_imc2_integrity(self, imc2_name, imc3_name):
        """Paired IMC2 and IMC3 fixtures should expose the same numeric content."""
        imc2_sample = SAMPLES_DIR / imc2_name
        imc3_sample = IMC3_DIR / imc3_name
        if not imc2_sample.exists():
            pytest.skip(f"Sample file not found: {imc2_sample}")
        if not imc3_sample.exists():
            pytest.skip(f"Sample file not found: {imc3_sample}")

        imc2 = ImcTermite(str(imc2_sample).encode())
        imc3 = ImcTermite(str(imc3_sample).encode())

        imc2_channels = imc2.get_channels(include_data=False)
        imc3_channels = imc3.get_channels(include_data=False)

        assert len(imc2_channels) == len(imc3_channels)

        for imc2_channel, imc3_channel in zip(imc2_channels, imc3_channels):
            assert imc2.get_channel_length(imc2_channel["uuid"]) == imc3.get_channel_length(imc3_channel["uuid"])
            assert imc2_channel.get("datatype") == imc3_channel.get("datatype")
            assert imc2_channel.get("xunit") == imc3_channel.get("xunit")
            assert float(imc2_channel.get("xstepwidth", 0.0)) == float(imc3_channel.get("xstepwidth", 0.0))
            assert float(imc2_channel.get("xoffset", 0.0)) == float(imc3_channel.get("xoffset", 0.0))
            assert float(imc2_channel.get("factor", 1.0)) == float(imc3_channel.get("factor", 1.0))
            assert float(imc2_channel.get("offset", 0.0)) == float(imc3_channel.get("offset", 0.0))

            imc2_data = imc2.get_channel_data(imc2_channel["uuid"], include_x=True)
            imc3_data = imc3.get_channel_data(imc3_channel["uuid"], include_x=True)

            np.testing.assert_allclose(imc2_data["x"], imc3_data["x"], rtol=1e-9, atol=1e-9, equal_nan=True)
            np.testing.assert_allclose(imc2_data["y"], imc3_data["y"], rtol=1e-9, atol=1e-9, equal_nan=True)

    @pytest.mark.parametrize(
        "sample_name,expected_names",
        [
            ("imc3_single-channel.dat", ["AmplitudeSpectrum"]),
            ("imc3_multi-channel.dat", ["x", "y", "z"]),
            ("imc3_xy_dataset.dat", ["circle"]),
        ],
    )
    def test_imc3_metadata_listing(self, sample_name, expected_names):
        sample = IMC3_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=False)

        assert [channel["name"] for channel in channels] == expected_names

    def test_imc3_include_data_extracts_xy_values(self):
        sample = IMC3_DIR / "imc3_xy_dataset.dat"
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

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
        sample = IMC3_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        imc = ImcTermite(str(sample).encode())
        channels = imc.get_channels(include_data=False)

        assert len(channels) == expected_channel_count
        assert all(imc.get_channel_length(channel["uuid"]) == 148836 for channel in channels)

    @pytest.mark.parametrize("sample_name", ["imc3_sanitized_bundle.dat", "imc3_sanitized_02.raw"])
    def test_sanitized_imc3_channel_data_extracts_samples(self, sample_name):
        sample = IMC3_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        imc = ImcTermite(str(sample).encode())
        channel = imc.get_channels(include_data=False)[0]
        data = imc.get_channel_data(channel["uuid"], include_x=True)

        assert len(data["x"]) == len(data["y"]) == 148836
        assert float(data["x"][0]) == 0.0
        assert float(data["x"][1]) > float(data["x"][0])

    @pytest.mark.parametrize("single_name,bundle_index", SANITIZED_SINGLE_TO_BUNDLE)
    def test_sanitized_single_channels_match_bundle(self, single_name, bundle_index):
        single_sample = IMC3_DIR / single_name
        bundle_sample = IMC3_DIR / "imc3_sanitized_bundle.dat"
        if not single_sample.exists():
            pytest.skip(f"Sample file not found: {single_sample}")
        if not bundle_sample.exists():
            pytest.skip(f"Sample file not found: {bundle_sample}")

        single = ImcTermite(str(single_sample).encode())
        bundle = ImcTermite(str(bundle_sample).encode())

        single_channel = single.get_channels(include_data=False)[0]
        bundle_channel = bundle.get_channels(include_data=False)[bundle_index]

        assert single.get_channel_length(single_channel["uuid"]) == bundle.get_channel_length(bundle_channel["uuid"])
        assert single_channel.get("datatype") == bundle_channel.get("datatype")
        assert single_channel.get("xunit") == bundle_channel.get("xunit")
        assert single_channel.get("yunit") == bundle_channel.get("yunit")
        assert float(single_channel.get("xstepwidth", 0.0)) == float(bundle_channel.get("xstepwidth", 0.0))
        assert float(single_channel.get("xoffset", 0.0)) == float(bundle_channel.get("xoffset", 0.0))
        assert float(single_channel.get("factor", 1.0)) == float(bundle_channel.get("factor", 1.0))
        assert float(single_channel.get("offset", 0.0)) == float(bundle_channel.get("offset", 0.0))

        single_scaled = single.get_channel_data(single_channel["uuid"], include_x=True)
        bundle_scaled = bundle.get_channel_data(bundle_channel["uuid"], include_x=True)
        np.testing.assert_allclose(single_scaled["x"], bundle_scaled["x"], rtol=1e-9, atol=1e-9, equal_nan=True)
        np.testing.assert_allclose(single_scaled["y"], bundle_scaled["y"], rtol=1e-9, atol=1e-9, equal_nan=True)

        single_raw = single.get_channel_data(single_channel["uuid"], include_x=False, mode="raw")
        bundle_raw = bundle.get_channel_data(bundle_channel["uuid"], include_x=False, mode="raw")
        np.testing.assert_array_equal(single_raw["y"], bundle_raw["y"])


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
        raw_files = sorted(list(SAMPLES_DIR.glob("**/*.raw")) + 
                           list(SAMPLES_DIR.glob("**/*.dat")))
        
        for raw_file in raw_files:
            # print(f"Testing {raw_file.name}")
            try:
                imc = ImcTermite(str(raw_file).encode())
                
                # Get reference data
                channels_ref = imc.get_channels(include_data=True)
                
                for ch_ref in channels_ref:
                    uuid = ch_ref['uuid'].encode('utf-8')
                    
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
        raw_files = sorted(list(SAMPLES_DIR.glob("**/*.raw")) +
                           list(SAMPLES_DIR.glob("**/*.dat")))

        checked = 0
        for raw_file in raw_files:
            imc = ImcTermite(str(raw_file).encode())
            channels = imc.get_channels(include_data=False)

            for channel in channels:
                if str(channel.get('datatype')) != '11':
                    continue

                checked += 1
                uuid = channel['uuid'].encode('utf-8')

                raw_chunk = next(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="raw"))
                scaled_chunk = next(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="scaled"))

                expected = raw_chunk['y'].astype(np.float64)
                assert scaled_chunk['y'].dtype == np.float64
                assert np.array_equal(scaled_chunk['y'], expected), (
                    f"Datatype 11 scaling mismatch in {raw_file.name} channel {channel['uuid']}"
                )

        if checked == 0:
            pytest.skip("No datatype 11 channels found in bundled sample files")

    def test_nondigital_scaled_matches_raw_with_metadata_transform(self):
        """Non-digital channels should keep scaled = raw * factor + offset behavior."""
        raw_files = sorted(list(SAMPLES_DIR.glob("**/*.raw")) +
                           list(SAMPLES_DIR.glob("**/*.dat")))

        checked = 0
        for raw_file in raw_files:
            imc = ImcTermite(str(raw_file).encode())
            channels = imc.get_channels(include_data=False)

            for channel in channels:
                datatype = str(channel.get('datatype'))
                if datatype == '11':
                    continue

                try:
                    factor = float(channel.get('factor', '1'))
                    offset = float(channel.get('offset', '0'))
                except (TypeError, ValueError):
                    continue

                uuid = channel['uuid'].encode('utf-8')
                raw_chunk = next(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="raw"))
                scaled_chunk = next(imc.iter_channel_numpy(uuid, include_x=False, chunk_rows=256, mode="scaled"))

                if raw_chunk['y'].size == 0:
                    continue

                fact = 1.0 if factor == 0.0 else factor
                expected = raw_chunk['y'].astype(np.float64) * fact + offset
                assert np.allclose(scaled_chunk['y'], expected, rtol=0.0, atol=0.0, equal_nan=True), (
                    f"Non-digital scaling mismatch in {raw_file.name} channel {channel['uuid']} "
                    f"(datatype={datatype}, factor={factor}, offset={offset})"
                )
                checked += 1

                if checked >= 20:
                    break
            if checked >= 20:
                break

        if checked == 0:
            pytest.skip("No non-digital channels with parseable factor/offset found in bundled sample files")
    

class TestCSVOutput:
    """Test CSV file generation"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
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
    
    def test_process_all_sample_files(self):
        """Should process all .raw and .dat files in samples directory (metadata only)"""
        if not SAMPLES_DIR.exists():
            pytest.skip(f"Samples directory not found: {SAMPLES_DIR}")
        
        # Get all .raw and .dat files recursively
        files_to_test = sorted(list(SAMPLES_DIR.glob("**/*.raw")) + 
                               list(SAMPLES_DIR.glob("**/*.dat")))
        
        if len(files_to_test) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
        successful = 0
        failed = []
        for sample_file in files_to_test:
            try:
                imc = ImcTermite(str(sample_file).encode())
                channels = imc.get_channels(include_data=False)
                if len(channels) > 0:
                    successful += 1
            except Exception as e:
                failed.append(f"{sample_file.relative_to(SAMPLES_DIR)}: {e}")
        
        assert len(failed) == 0, f"Failed to process {len(failed)}/{len(files_to_test)} files: {failed}"
        assert successful == len(files_to_test), f"Only {successful}/{len(files_to_test)} files had channels"
    
    def test_extract_all_sample_files_with_data(self):
        """Should fully extract all .raw and .dat files with data"""
        if not SAMPLES_DIR.exists():
            pytest.skip(f"Samples directory not found: {SAMPLES_DIR}")
        
        # Get all .raw and .dat files recursively
        files_to_test = sorted(list(SAMPLES_DIR.glob("**/*.raw")) + 
                               list(SAMPLES_DIR.glob("**/*.dat")))
        
        if len(files_to_test) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
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
                           ('ydata' in channel and len(channel['ydata']) > 0):
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
        file1 = DATASET_A / "datasetA_1.raw"
        file2 = DATASET_A / "datasetA_2.raw"
        
        if not (file1.exists() and file2.exists()):
            pytest.skip("Need at least 2 sample files")
        
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
    
    @pytest.mark.parametrize("file_path,expected", [
        # datasetA_1.raw - Standard .raw format with gravity unit
        ("datasetA/datasetA_1.raw", {
            'num_channels': 1,
            'data_length': 6000,
            'yunit': 'G',
            'xstepwidth': 0.005,
            'ydata_first': [0.010029276, 0.015780726],
            'ydata_last': [-0.02981583, -0.030068753],  # [-2], [-1]
            'xdata_first': [416.01],
        }),
        # sampleA.raw - Pressure data with mbar units
        ("sampleA.raw", {
            'num_channels': 1,
            'data_length': 2402,
            'yunit': '"mbar"',
            'xoffset': 2044.03,
            'ydata_first': [956.013793945, 955.484924316, 955.487670898],
            'ydata_last': [866.840881348, 866.91619873, 866.985290527],  # [-3], [-2], [-1]
        }),
        # sample_x_precision.raw - Regression test for x-axis precision with offset
        ("sample_x_precision.raw", {
            'num_channels': 1,
            'data_length': 33596,
            'xstepwidth': 0.01,
            'xoffset': 0.005,
            'xdata_first': [0.005, 0.015, 0.025],
            'ydata_first': [0.0, 0.0, 0.0],
            'ydata_last': [0.0, 0.0, 0.0],
        }),
        # XY_dataset_example.dat - Different .dat format with explicit X-Y data
        ("XY_dataset_example.dat", {
            'num_channels': 1,
            'data_length': 13094,
            'ydata_first': [0, 0, 0],
            'ydata_last': [2796202, 2796202, 2982616],  # [-3], [-2], [-1]
            'xdata_first': [67.855759, 67.880796],
            'xdata_last': [395.158317],
        }),
    ])
    def test_known_values(self, file_path, expected):
        """Verify known values from sample files to catch parsing regressions"""
        sample_file = SAMPLES_DIR / file_path
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
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
            assert abs(float(ch.get('xstepwidth')) - expected['xstepwidth']) < 1e-9, \
                f"X step width should be {expected['xstepwidth']}"
        
        if 'xoffset' in expected:
            assert abs(float(ch.get('xoffset')) - expected['xoffset']) < 1e-9, \
                f"X offset should be {expected['xoffset']}"
        
        # Verify ydata first values
        tolerance = 1e-6  # Default tolerance for floating-point comparisons
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


class TestErrorHandling:
    """Test error conditions"""
    
    def test_nonexistent_file(self):
        """Should raise error for nonexistent file"""
        with pytest.raises(Exception):
            ImcTermite(b"/nonexistent/file.raw")
    
    def test_invalid_channel_name(self):
        """Should handle invalid channel name gracefully"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
        imc = ImcTermite(str(sample_file).encode())
        
        # This should either raise or return empty - both are acceptable
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                output_file = f.name
            
            imc.print_channel(b"NONEXISTENT_CHANNEL_UUID", output_file.encode(), b','[0])
            
            # If it didn't raise, check if file is empty or has minimal content
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                # Either file doesn't exist or is very small (just header)
                assert size < 100
        except Exception:
            # Raising an exception is also acceptable behavior
            pass
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
