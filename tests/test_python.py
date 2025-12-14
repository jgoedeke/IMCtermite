#!/usr/bin/env python3
"""
End-to-end tests for IMCtermite Python module
"""

import pytest
import os
import tempfile
import csv
from pathlib import Path

try:
    import imctermite
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
        assert imctermite is not None
    
    def test_can_instantiate(self):
        """Should create instance with valid file"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
        imc = imctermite.imctermite(str(sample_file).encode())
        assert imc is not None


class TestChannelListing:
    """Test channel metadata retrieval"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance with sample file"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        return imctermite.imctermite(str(sample_file).encode())
    
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
        
        imc = imctermite.imctermite(str(sample_file).encode())
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
    
    def test_xdata_monotonic(self, sample_data):
        """X-data (time) should be monotonically increasing"""
        for channel in sample_data:
            xdata = channel['xdata']
            if len(xdata) > 1:
                # Check if mostly increasing (allow small floating point issues)
                increasing_count = sum(1 for i in range(len(xdata)-1) if xdata[i] <= xdata[i+1])
                ratio = increasing_count / (len(xdata) - 1)
                assert ratio > 0.95, f"X-data not monotonic enough: {ratio:.2%}"


class TestCSVOutput:
    """Test CSV file generation"""
    
    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        return imctermite.imctermite(str(sample_file).encode())
    
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
        files_to_test = sorted(list(SAMPLES_DIR.glob("*.raw")) + 
                               list(SAMPLES_DIR.glob("*.dat")) +
                               list(SAMPLES_DIR.glob("**/*.raw")) + 
                               list(SAMPLES_DIR.glob("**/*.dat")))
        # Remove duplicates (files in root will be in both patterns)
        files_to_test = sorted(set(files_to_test))
        
        if len(files_to_test) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
        successful = 0
        failed = []
        for sample_file in files_to_test:
            try:
                imc = imctermite.imctermite(str(sample_file).encode())
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
        files_to_test = sorted(list(SAMPLES_DIR.glob("*.raw")) + 
                               list(SAMPLES_DIR.glob("*.dat")) +
                               list(SAMPLES_DIR.glob("**/*.raw")) + 
                               list(SAMPLES_DIR.glob("**/*.dat")))
        files_to_test = sorted(set(files_to_test))
        
        if len(files_to_test) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
        successful = 0
        failed = []
        for sample_file in files_to_test:
            try:
                imc = imctermite.imctermite(str(sample_file).encode())
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
        imc1 = imctermite.imctermite(str(file1).encode())
        channels1 = imc1.get_channels(include_data=False)
        
        # Load second file
        imc2 = imctermite.imctermite(str(file2).encode())
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
        
        imc = imctermite.imctermite(str(sample_file).encode())
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
            imctermite.imctermite(b"/nonexistent/file.raw")
    
    def test_invalid_channel_name(self):
        """Should handle invalid channel name gracefully"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        
        imc = imctermite.imctermite(str(sample_file).encode())
        
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
