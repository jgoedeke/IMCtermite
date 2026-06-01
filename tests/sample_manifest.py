from pathlib import Path
import sys

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DATASET_A_DIR = SAMPLES_DIR / "datasetA"
DATASET_B_DIR = SAMPLES_DIR / "datasetB"
IMC3_DIR = SAMPLES_DIR / "imc3"
TSA_DIR = SAMPLES_DIR / "tsa"

CLI_PATH = PROJECT_ROOT / "imctermite"
if sys.platform == "win32":
    CLI_PATH = CLI_PATH.with_suffix(".exe")


IMC3_PARITY_SAMPLES = [
    ("sampleA.raw", "imc3_sampleA.dat"),
    ("sampleB.raw", "imc3_sampleB.dat"),
    ("XY_dataset_example.dat", "imc3_XY_dataset_example.dat"),
]

IMC3_METADATA_SAMPLES = [
    ("imc3_single-channel.dat", ["AmplitudeSpectrum"]),
    ("imc3_multi-channel.dat", ["x", "y", "z"]),
    ("imc3_xy_dataset.dat", ["circle"]),
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

SANITIZED_IMC3_DATA_SAMPLES = ["imc3_sanitized_bundle.dat", "imc3_sanitized_02.raw"]

SANITIZED_SINGLE_TO_BUNDLE = [
    ("imc3_sanitized_01.raw", 0),
    ("imc3_sanitized_02.raw", 1),
    ("imc3_sanitized_03.raw", 2),
    ("imc3_sanitized_04.raw", 3),
    ("imc3_sanitized_05.raw", 4),
    ("imc3_sanitized_06.raw", 5),
]

SUPPORTED_TSA_EVENT_SAMPLES = [
    ("imc2_TsaChannel.dat", 2),
    ("imc3_TsaChannel.dat", 2),
    ("imc2_tsa_multicluster.dat", 33),
    ("imc3_tsa_multicluster.dat", 33),
    ("imc2_tsa_padding_and_escaping.dat", 9),
    ("imc3_tsa_padding_and_escaping.dat", 9),
]

SUPPORTED_TSA_EVENT_SAMPLE_NAMES = [sample_name for sample_name, _ in SUPPORTED_TSA_EVENT_SAMPLES]

TSA_PADDING_ESCAPED_TEXTS = [
    "",
    "A",
    "AB",
    "ABC",
    "ABCD",
    'comma,quote"slash\\\\',
    "line1\\r\\nline2",
    "tab\\tseparated",
    "A\\x00B",
]

TSA_MULTICLUSTER_TIMESTAMPS = np.concatenate(
    [np.array([0.0, 0.01]), np.array([0.02 + i * 0.01 for i in range(1, 31)]), np.array([0.4])]
)

UNSUPPORTED_TSA_EVENT_SAMPLES = [
    ("imc2_event_numeric_many_small_events.dat", r"unknown critical key: Cv1"),
    ("imc2_event_numeric_varied_metadata.dat", r"unknown critical key: Cv1"),
    ("imc2_mixed_numeric_and_event_channel.dat", r"unknown critical key: Cv1"),
    (
        "imc3_event_numeric_many_small_events.dat",
        r"unsupported IMC3 channel flags: multi-event and color-value channels are not implemented",
    ),
    (
        "imc3_event_numeric_varied_metadata.dat",
        r"unsupported IMC3 channel flags: multi-event and color-value channels are not implemented",
    ),
    (
        "imc3_mixed_numeric_and_event_channel.dat",
        r"unsupported IMC3 channel flags: multi-event and color-value channels are not implemented",
    ),
]

UNSUPPORTED_SAMPLE_PATHS = {TSA_DIR / sample_name for sample_name, _ in UNSUPPORTED_TSA_EVENT_SAMPLES}

KNOWN_VALUE_CASES = [
    (
        "datasetA/datasetA_1.raw",
        {
            "num_channels": 1,
            "data_length": 6000,
            "yunit": "G",
            "xstepwidth": 0.005,
            "ydata_first": [0.010029276, 0.015780726],
            "ydata_last": [-0.02981583, -0.030068753],
            "xdata_first": [416.01],
        },
    ),
    (
        "sampleA.raw",
        {
            "num_channels": 1,
            "data_length": 2402,
            "yunit": '"mbar"',
            "xoffset": 2044.03,
            "ydata_first": [956.013793945, 955.484924316, 955.487670898],
            "ydata_last": [866.840881348, 866.91619873, 866.985290527],
        },
    ),
    (
        "sample_x_precision.raw",
        {
            "num_channels": 1,
            "data_length": 33596,
            "xstepwidth": 0.01,
            "xoffset": 0.005,
            "xdata_first": [0.005, 0.015, 0.025],
            "ydata_first": [0.0, 0.0, 0.0],
            "ydata_last": [0.0, 0.0, 0.0],
        },
    ),
    (
        "XY_dataset_example.dat",
        {
            "num_channels": 1,
            "data_length": 13094,
            "ydata_first": [0, 0, 0],
            "ydata_last": [2796202, 2796202, 2982616],
            "xdata_first": [67.855759, 67.880796],
            "xdata_last": [395.158317],
        },
    ),
]

NUMERIC_INVARIANT_SAMPLE_PATHS = [
    "datasetA/datasetA_1.raw",
    "sampleA.raw",
    "sample_x_precision.raw",
]


def require_sample(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"Sample file not found: {path}")
    return path


def iter_sample_files(root: Path = SAMPLES_DIR) -> list[Path]:
    if not root.exists():
        pytest.skip(f"Samples directory not found: {root}")

    samples = sorted(
        set(
            list(root.glob("*.raw"))
            + list(root.glob("*.dat"))
            + list(root.glob("**/*.raw"))
            + list(root.glob("**/*.dat"))
        )
    )

    if not samples:
        pytest.skip(f"No .raw or .dat files in samples directory: {root}")

    return samples


def iter_supported_sample_files(root: Path = SAMPLES_DIR) -> list[Path]:
    return [sample for sample in iter_sample_files(root) if sample not in UNSUPPORTED_SAMPLE_PATHS]