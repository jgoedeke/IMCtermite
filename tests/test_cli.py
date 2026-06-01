#!/usr/bin/env python3
"""
End-to-end tests for IMCtermite CLI tool
"""

import pytest
import subprocess
import sys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CLI = PROJECT_ROOT / "imctermite"
if sys.platform == "win32":
    CLI = CLI.with_suffix(".exe")
SAMPLES_DIR = PROJECT_ROOT / "samples" / "datasetA"
IMC3_DIR = PROJECT_ROOT / "samples" / "imc3"
TSA_DIR = PROJECT_ROOT / "samples" / "tsa"
SUPPORTED_TSA_EVENT_SAMPLES = [
    "imc2_TsaChannel.dat",
    "imc3_TsaChannel.dat",
    "imc2_tsa_multicluster.dat",
    "imc3_tsa_multicluster.dat",
    "imc2_tsa_padding_and_escaping.dat",
    "imc3_tsa_padding_and_escaping.dat",
]
SANITIZED_IMC3_SAMPLES = [
    ("imc3_sanitized_01.raw", 1),
    ("imc3_sanitized_02.raw", 1),
    ("imc3_sanitized_03.raw", 1),
    ("imc3_sanitized_04.raw", 1),
    ("imc3_sanitized_05.raw", 1),
    ("imc3_sanitized_06.raw", 1),
    ("imc3_sanitized_bundle.dat", 6),
]


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

    @pytest.mark.parametrize(
        "sample_name,expected_text",
        [
            ("imc3_single-channel.dat", "AmplitudeSpectrum"),
            ("imc3_multi-channel.dat", "name:               x"),
            ("imc3_xy_dataset.dat", "circle"),
        ],
    )
    def test_imc3_samples_list_channels(self, sample_name, expected_text):
        """Bundled IMC3 fixtures should list channels successfully."""
        sample = IMC3_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        result = subprocess.run(
            [str(CLI), str(sample), "--listchannels"],
            capture_output=True,
            text=True,
            errors='replace'
        )

        assert result.returncode == 0
        assert expected_text in result.stdout

    @pytest.mark.parametrize("sample_name,expected_channels", SANITIZED_IMC3_SAMPLES)
    def test_sanitized_imc3_files_list_channels(self, sample_name, expected_channels):
        sample = IMC3_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        result = subprocess.run(
            [str(CLI), str(sample), "--listchannels"],
            capture_output=True,
            text=True,
            errors='replace'
        )

        assert result.returncode == 0
        assert result.stdout.count("uuid:") == expected_channels

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLES)
    def test_tsa_samples_list_channels(self, sample_name):
        sample = TSA_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        result = subprocess.run(
            [str(CLI), str(sample), "--listchannels"],
            capture_output=True,
            text=True,
            errors='replace'
        )

        assert result.returncode == 0
        assert "channel-type:       event" in result.stdout
        assert "datatype:           10" in result.stdout
        assert "xname:              time" in result.stdout
        assert "TsaChannel" in result.stdout


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

    @pytest.mark.parametrize("sample_name", SUPPORTED_TSA_EVENT_SAMPLES)
    def test_tsa_csv_output_contains_timestamp_and_text(self, sample_name, tmp_path):
        sample = TSA_DIR / sample_name
        if not sample.exists():
            pytest.skip(f"Sample file not found: {sample}")

        output_dir = tmp_path / "tsa_csv_output"
        output_dir.mkdir()

        result = subprocess.run(
            [str(CLI), str(sample), "--output", str(output_dir)],
            capture_output=True,
            text=True,
            errors='replace'
        )

        assert result.returncode == 0
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) == 1
        rows = list(csv.reader(csv_files[0].read_text().splitlines()))
        assert rows[0] == ["time", "TsaChannel"]
        if sample_name.endswith("TsaChannel.dat"):
            assert float(rows[2][0]) == 20.0
            assert rows[2][1] == "hello"
            assert float(rows[3][0]) == 40.0
            assert rows[3][1] == "0123456789"
        elif "multicluster" in sample_name:
            assert float(rows[2][0]) == 0.0
            assert rows[2][1] == ""
            assert float(rows[3][0]) == 0.01
            assert rows[3][1] == "short"
            assert float(rows[-1][0]) == 0.4
            assert rows[-1][1].startswith("0123456789")
        else:
            assert float(rows[2][0]) == 0.0
            assert rows[2][1] == ""
            assert float(rows[3][0]) == 0.0
            assert rows[3][1] == "A"
            assert float(rows[-1][0]) == 0.013
            assert rows[-1][1] == "A\\x00B"


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

    def test_empty_file_reports_format_neutral_message(self, tmp_path):
        """Empty files should use the format-neutral no-data error message."""
        empty_file = tmp_path / "empty.raw"
        empty_file.write_bytes(b"")

        result = subprocess.run(
            [str(CLI), str(empty_file), "--listchannels"],
            capture_output=True,
            text=True,
            errors="replace",
        )

        assert result.returncode != 0
        assert "empty or unreadable IMC file" in result.stderr
        assert "no channels or blocks were found" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
