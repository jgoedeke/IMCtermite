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


class TestUnsupportedFormats:
    """Test clear errors for unsupported file formats"""

    def test_imc3_signature_reports_unsupported_format(self, tmp_path):
        """IMC3-like headers should fail with an explicit unsupported-format error."""
        imc3_file = tmp_path / "unsupported_imc3.dat"
        imc3_file.write_bytes(b"|imc3,1;|CB1\x00\x00\x00\x00")

        with pytest.raises(RuntimeError, match="unsupported IMC3 format"):
            ImcTermite(str(imc3_file).encode())


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


class TestEventMarkers:
    """Synthetic tests for Cv/CV event semantics."""

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

    @staticmethod
    def _ev72(offset_lo: int, length_lo: int, t: float, y_off: float, x_off: float, x0: float, y_fac: float, x_fac: float, dx: float) -> bytes:
        return struct.pack("<II7dII", offset_lo, length_lo, t, y_off, x_off, x0, y_fac, x_fac, dx, 0, 0)

    def test_event_validcd_and_validnt_are_applied(self, tmp_path):
        test_file = tmp_path / "event_channel.dat"

        raw = bytearray()
        raw += self._block("CF", "2,1", version=2)
        raw += self._block("CK", "1,1")
        raw += self._block("CG", "1,1,1")
        raw += self._block("CD", "1.0,1,1,s,0,0,0")
        raw += self._block("NT", "1,1,2020,0,0,0.0")
        raw += self._block("CC", "1,1")
        raw += self._block("CP", "1,2,4,16,0,0,1,0")
        raw += self._block("Cb", "1,0,1,1,0,20,0,20,1,0.0,0.0")

        # Cv: index=1, offset=0, direct-follow=1, stride=0, count=2,
        # valid_nt=1, valid_cd=3 (dx + x0 from event), valid_cr1/2=0
        raw += self._block("Cv", "1,0,1,0,2,1,3,0,0")

        ev_payload = (
            b"1,2,"
            + self._ev72(0, 5, 0.0, 0.0, 0.0, 10.0, 1.0, 1.0, 0.5)
            + self._ev72(5, 5, 10.0, 0.0, 0.0, 20.0, 1.0, 1.0, 1.0)
        )
        raw += self._block("CV", ev_payload)

        raw += self._block("CN", "0,0,0,6,EVT_CH,1,E")
        raw += self._block("CS", b"1," + bytes([0, 0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0, 8, 0, 9, 0]))

        test_file.write_bytes(raw)

        imc = ImcTermite(str(test_file).encode())
        channels = imc.get_channels(include_data=False)
        assert len(channels) == 1
        ch = channels[0]

        events = ch.get("events", {})
        assert events.get("has-description") is True
        assert events.get("has-list") is True
        assert events.get("count-parsed") == 2
        assert events.get("trigger-time-source") == "CV"
        assert ch.get("trigger-time") == "1980-01-01T00:00:00"

        uid = ch["uuid"].encode("utf-8")
        chunk = next(imc.iter_channel_numpy(uid, include_x=True, chunk_rows=20, mode="scaled"))
        x = chunk["x"]
        y = chunk["y"]

        expected_x = np.array([10.0, 10.5, 11.0, 11.5, 12.0, 20.0, 21.0, 22.0, 23.0, 24.0])
        expected_y = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
        np.testing.assert_allclose(x, expected_x, rtol=0, atol=1e-12)
        np.testing.assert_allclose(y, expected_y, rtol=0, atol=1e-12)

    def test_event_count_parsed_uses_72byte_records(self, tmp_path):
        test_file = tmp_path / "event_count_72.dat"

        raw = bytearray()
        raw += self._block("CF", "2,1", version=2)
        raw += self._block("CK", "1,1")
        raw += self._block("CG", "1,1,1")
        raw += self._block("CD", "1.0,1,1,s,0,0,0")
        raw += self._block("NT", "1,1,2020,0,0,0.0")
        raw += self._block("CC", "1,1")
        raw += self._block("CP", "1,2,4,16,0,0,1,0")
        raw += self._block("Cb", "1,0,1,1,0,12,0,12,1,0.0,0.0")
        raw += self._block("Cv", "1,0,1,0,3,0,0,0,0")

        ev_payload = (
            b"1,3,"
            + self._ev72(0, 2, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
            + self._ev72(2, 2, 2.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
            + self._ev72(4, 2, 3.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        )
        raw += self._block("CV", ev_payload)
        raw += self._block("CN", "0,0,0,5,EV72,1,E")
        raw += self._block("CS", b"1," + bytes([1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0]))

        test_file.write_bytes(raw)

        imc = ImcTermite(str(test_file).encode())
        ch = imc.get_channels(include_data=False)[0]
        assert ch["events"]["count-parsed"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
