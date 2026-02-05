#!/usr/bin/env python3
"""
Tests for the new streaming/chunking functionality in IMCtermite
"""

import pytest
import numpy as np
from pathlib import Path

try:
    from imctermite import ImcTermite
except ImportError:
    pytest.skip("imctermite module not built - run 'make python-build' first", allow_module_level=True)

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DATASET_A = SAMPLES_DIR / "datasetA"

class TestStreaming:
    """Test iter_channel_numpy functionality"""

    @pytest.fixture
    def imc_instance(self):
        """Create IMC instance with sample file"""
        sample_file = DATASET_A / "datasetA_1.raw"
        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")
        return ImcTermite(str(sample_file).encode())

    @pytest.fixture
    def first_channel_uuid(self, imc_instance):
        """Get UUID of the first channel"""
        channels = imc_instance.get_channels(include_data=False)
        assert len(channels) > 0
        return channels[0]['uuid']

    def test_iter_channel_numpy_scaled(self, imc_instance, first_channel_uuid):
        """Test default scaled streaming"""
        # Get ground truth via old method
        full_channels = imc_instance.get_channels(include_data=True)
        target_channel = next(ch for ch in full_channels if ch['uuid'] == first_channel_uuid)
        expected_y = np.array(target_channel['ydata'])
        
        # Stream data
        streamed_y = []
        # Encode UUID to bytes for C++ std::string
        uuid_bytes = first_channel_uuid.encode('utf-8')
        for chunk in imc_instance.iter_channel_numpy(uuid_bytes, chunk_rows=100):
            assert 'y' in chunk
            assert isinstance(chunk['y'], np.ndarray)
            assert chunk['y'].dtype == np.float64 # Scaled should be float64
            streamed_y.append(chunk['y'])
            
        full_streamed_y = np.concatenate(streamed_y)
        
        # Compare
        np.testing.assert_allclose(full_streamed_y, expected_y, rtol=1e-4)

    def test_iter_channel_numpy_raw(self, imc_instance, first_channel_uuid):
        """Test raw streaming"""
        # We can't easily compare raw values to scaled values without knowing the factor/offset
        # But we can check types and consistency
        
        streamed_y_raw = []
        uuid_bytes = first_channel_uuid.encode('utf-8')
        for chunk in imc_instance.iter_channel_numpy(uuid_bytes, chunk_rows=100, mode="raw"):
            assert 'y' in chunk
            assert isinstance(chunk['y'], np.ndarray)
            # Raw type depends on file, but shouldn't necessarily be float64 unless the raw data is float
            streamed_y_raw.append(chunk['y'])
            
        full_streamed_y_raw = np.concatenate(streamed_y_raw)
        
        # Ensure we got data
        assert len(full_streamed_y_raw) > 0

    def test_chunking_behavior(self, imc_instance, first_channel_uuid):
        """Test that small chunks work correctly"""
        # Get total length
        channels = imc_instance.get_channels(include_data=False)
        # We don't have direct access to length in metadata without loading, 
        # but we can infer it from a full load or just count
        
        chunk_size = 10
        uuid_bytes = first_channel_uuid.encode('utf-8')
        chunks = list(imc_instance.iter_channel_numpy(uuid_bytes, chunk_rows=chunk_size))
        
        # Check that most chunks are of size 10
        for i, chunk in enumerate(chunks[:-1]): # All but last should be full
            assert len(chunk['y']) == chunk_size
            
        # Check continuity of 'start' index
        expected_start = 0
        for chunk in chunks:
            assert chunk['start'] == expected_start
            expected_start += len(chunk['y'])

    def test_include_x_parameter(self, imc_instance, first_channel_uuid):
        """Test include_x=False"""
        uuid_bytes = first_channel_uuid.encode('utf-8')
        for chunk in imc_instance.iter_channel_numpy(uuid_bytes, include_x=False, chunk_rows=100):
            assert 'y' in chunk
            assert 'x' not in chunk

    def test_invalid_channel_uuid(self, imc_instance):
        """Test behavior with invalid UUID"""
        # Depending on implementation, this might raise an error or return empty generator
        # Based on C++ code: throw std::runtime_error("channel does not exist:" + uuid);
        # Cython should propagate this as RuntimeError
        
        with pytest.raises(RuntimeError):
            list(imc_instance.iter_channel_numpy(b"non-existent-uuid"))
