#!/usr/bin/env python3
"""
End-to-end tests for IMCtermite CLI tool
"""

import pytest
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CLI = PROJECT_ROOT / "imctermite"
if sys.platform == "win32":
    CLI = CLI.with_suffix(".exe")
SAMPLES_DIR = PROJECT_ROOT / "samples" / "datasetA"


class TestCLIBasics:
    """Test basic CLI functionality"""
    
    def test_cli_exists(self):
        """CLI binary should exist"""
        assert CLI.exists(), f"CLI not found at {CLI}"
    
    def test_help_output(self):
        """Should display help message"""
        result = subprocess.run([str(CLI), "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()
    
    def test_version_output(self):
        """Should display version"""
        result = subprocess.run([str(CLI), "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert len(result.stdout) > 0
    
    def test_invalid_file_handling(self):
        """Should fail gracefully on nonexistent file"""
        result = subprocess.run(
            [str(CLI), "/nonexistent/file.raw"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0


class TestChannelOperations:
    """Test channel listing and data extraction"""
    
    @pytest.fixture
    def sample_file(self):
        """Get path to sample file"""
        sample = SAMPLES_DIR / "datasetA_1.raw"
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")
        return sample
    
    def test_list_channels(self, sample_file):
        """Should list channels with metadata"""
        result = subprocess.run(
            [str(CLI), str(sample_file), "--listchannels"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "uuid" in result.stdout
    
    def test_list_blocks(self, sample_file):
        """Should list IMC blocks"""
        result = subprocess.run(
            [str(CLI), str(sample_file), "--listblocks"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Block markers like CF, CK, CC, etc.
        assert "C" in result.stdout and ("F" in result.stdout or "K" in result.stdout)


class TestCSVOutput:
    """Test CSV file generation"""
    
    @pytest.fixture
    def sample_file(self):
        """Get path to sample file"""
        sample = SAMPLES_DIR / "datasetA_1.raw"
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")
        return sample
    
    def test_generate_csv_output(self, sample_file, tmp_path):
        """Should generate CSV files"""
        output_dir = tmp_path / "csv_output"
        output_dir.mkdir()
        
        result = subprocess.run(
            [str(CLI), str(sample_file), "--output", str(output_dir)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) > 0, "Should generate at least one CSV file"
    
    def test_csv_format_valid(self, sample_file, tmp_path):
        """Generated CSV should have valid format"""
        output_dir = tmp_path / "csv_output"
        output_dir.mkdir()
        
        subprocess.run(
            [str(CLI), str(sample_file), "--output", str(output_dir)],
            capture_output=True
        )
        
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) > 0
        
        # Check first CSV file
        first_csv = csv_files[0]
        content = first_csv.read_text()
        lines = content.strip().split('\n')
        
        assert len(lines) > 1, "CSV should have header and data"
        assert ',' in lines[0], "CSV should use comma delimiter"
    
    def test_custom_delimiter(self, sample_file, tmp_path):
        """Should support custom delimiter"""
        output_dir = tmp_path / "csv_delim"
        output_dir.mkdir()
        
        result = subprocess.run(
            [str(CLI), str(sample_file), "--output", str(output_dir), "--delimiter", ";"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) > 0
        
        # Check delimiter is applied
        first_csv = csv_files[0]
        content = first_csv.read_text()
        first_line = content.split('\n')[0]
        assert ';' in first_line, "Should use semicolon delimiter"


class TestMultipleFiles:
    """Test processing multiple sample files"""
    
    def test_process_all_sample_files(self):
        """Should successfully process all .raw and .dat files in samples directory (list channels)"""
        samples_root = SAMPLES_DIR.parent
        if not samples_root.exists():
            pytest.skip(f"Samples directory not found: {samples_root}")
        
        # Get all .raw and .dat files recursively
        samples = sorted(list(samples_root.glob("*.raw")) + 
                        list(samples_root.glob("*.dat")) +
                        list(samples_root.glob("**/*.raw")) + 
                        list(samples_root.glob("**/*.dat")))
        # Remove duplicates
        samples = sorted(set(samples))
        
        if len(samples) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
        failed = []
        for sample in samples:
            result = subprocess.run(
                [str(CLI), str(sample), "--listchannels"],
                capture_output=True,
                text=True,
                errors='replace'  # Handle non-UTF8 characters in output
            )
            if result.returncode != 0:
                failed.append(f"{sample.relative_to(samples_root)}: exit code {result.returncode}")
        
        assert len(failed) == 0, f"Failed to process {len(failed)}/{len(samples)} files: {failed}"
    
    def test_extract_all_sample_files_with_data(self):
        """Should successfully extract data from all .raw and .dat files"""
        import tempfile
        import shutil
        
        samples_root = SAMPLES_DIR.parent
        if not samples_root.exists():
            pytest.skip(f"Samples directory not found: {samples_root}")
        
        # Get all .raw and .dat files recursively
        samples = sorted(list(samples_root.glob("*.raw")) + 
                        list(samples_root.glob("*.dat")) +
                        list(samples_root.glob("**/*.raw")) + 
                        list(samples_root.glob("**/*.dat")))
        samples = sorted(set(samples))
        
        if len(samples) == 0:
            pytest.skip("No .raw or .dat files in samples directory")
        
        # Create temp directory for output
        temp_dir = tempfile.mkdtemp()
        try:
            failed = []
            for sample in samples:
                result = subprocess.run(
                    [str(CLI), str(sample), "--output", temp_dir],
                    capture_output=True,
                    text=True,
                    errors='replace'
                )
                if result.returncode != 0:
                    failed.append(f"{sample.relative_to(samples_root)}: exit code {result.returncode}")
            
            assert len(failed) == 0, f"Failed to extract data from {len(failed)}/{len(samples)} files: {failed}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestExitCodes:
    """Test exit code behavior"""
    
    def test_success_exit_code(self):
        """Should return 0 on success"""
        sample = SAMPLES_DIR / "datasetA_1.raw"
        if not sample.exists():
            pytest.skip("Sample file not found")
        
        result = subprocess.run(
            [str(CLI), str(sample), "--listchannels"],
            capture_output=True
        )
        assert result.returncode == 0
    
    def test_error_exit_code(self):
        """Should return non-zero on error"""
        result = subprocess.run(
            [str(CLI), "/nonexistent/file.raw"],
            capture_output=True
        )
        assert result.returncode != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
