from pathlib import Path
import sys

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DATASET_A_DIR = SAMPLES_DIR / "datasetA"
DATASET_B_DIR = SAMPLES_DIR / "datasetB"
EVENTS_DIR = SAMPLES_DIR / "events"
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
IMC3_TSA_LEADING_PARTIAL_SAMPLE = ("imc3_tsa_leading_partial_fragment.dat", "PPT_TEST_2", 2956)
IMC3_TSA_LARGE_INITIAL_SAMPLE_OFFSET = ("imc3_tsa_large_initial_sample_offset.dat", "PPT_TEST_2", 24439)

SUPPORTED_IMC2_NUMERIC_EVENT_SAMPLES = [
    ("imc2_event_numeric_many_small_events.dat", 24),
    ("imc2_event_numeric_varied_metadata.dat", 3),
]

SUPPORTED_IMC3_NUMERIC_EVENT_SAMPLES = [
    ("imc3_event_numeric_many_small_events.dat", 24),
    ("imc3_event_numeric_varied_metadata.dat", 3),
]

SINGLE_NUMERIC_EVENT_EDGE_SAMPLES = [
    ("imc2_event_numeric_single_minimal.dat", "SingleEvent", 1),
    ("imc3_event_numeric_single_minimal.dat", "SingleEvent", 1),
]

MULTI_CHANNEL_NUMERIC_EVENT_SAMPLES = [
    ("imc2_event_numeric_two_channels.dat", ["Temperature", "Pressure"], [2, 3]),
    ("imc3_event_numeric_two_channels.dat", ["Temperature", "Pressure"], [2, 3]),
]

MIXED_MULTI_EVENT_SAMPLE_CASES = [
    ("imc2_event_numeric_two_channels_plus_numeric.dat", ["Speed", "Alarm", "Burst"], ["numeric", "event", "event"], [500, 2, 2]),
    ("imc3_event_numeric_two_channels_plus_numeric.dat", ["Speed", "Alarm", "Burst"], ["numeric", "event", "event"], [500, 2, 2]),
]

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


def _build_basic_sample_info(paths, *, datatypes, channel_types=None, channel_names=None):
    resolved_channel_types = channel_types or ["numeric"] * len(datatypes)
    assert len(resolved_channel_types) == len(datatypes)
    if channel_names is not None:
        assert len(channel_names) == len(datatypes)

    cases = {}
    for path in paths:
        entry = {
            "num_channels": len(datatypes),
            "datatypes": list(datatypes),
            "channel_types": list(resolved_channel_types),
        }
        if channel_names is not None:
            entry["channel_names"] = list(channel_names)
        cases[path] = entry
    return cases


def _with_basic_group_names(cases, group_names):
    for path, names in group_names.items():
        assert path in cases
        cases[path]["group_names"] = list(names)
    return cases


BASIC_SAMPLE_GROUP_NAMES = (
    {"XY_dataset_example.dat": ["here is the channel name"]}
    | {
        f"datasetA/datasetA_{index}.raw": [name]
        for index, name in [
            (1, "ACC_long"),
            (2, "Flex_AccelPdlPosn"),
            (3, "Flex_AirTemp_Outsd_IC"),
            (4, "Flex_AirTemp_Outsd"),
            (5, "Flex_BrkPdl_Stat"),
            (6, "Flex_BrkTrq_D_V2"),
            (7, "Flex_BrkTrq_R"),
            (8, "Flex_BrkTrq_V2"),
            (9, "Flex_EngLoad_OBD"),
            (10, "Flex_EngRPM"),
            (11, "Flex_Odo"),
            (12, "Flex_PkBrk_Stat"),
            (13, "Flex_StWhl_Angl"),
            (14, "Flex_StWhl_AnglSpd"),
            (15, "Flex_TC_liquidFuelCons1"),
            (16, "Flex_VehSpd_Disp"),
            (17, "Flex_WhlRPM_FL"),
            (18, "Flex_WhlRPM_FR"),
            (19, "Flex_WhlRPM_RL"),
            (20, "Flex_WhlRPM_RR"),
            (21, "GPS.height"),
            (22, "GPS.speed"),
            (23, "GPS.time.sec"),
            (24, "Pressure_FL"),
            (25, "Pressure_PC"),
            (26, "Pressure_RR"),
            (27, "Pressure_SC"),
            (28, "setup_id"),
            (29, "Temp_Disc_FL"),
            (30, "Temp_Disc_FR"),
            (31, "Temp_Disc_RL"),
            (32, "Temp_Disc_RR"),
            (33, "Temp_Fluid_FL"),
            (34, "Temp_Fluid_RL"),
            (35, "Travel_Piston"),
            (36, "Vacuum_Booster"),
            (37, "vehicle_id"),
            (38, "ACC_lat"),
        ]
    }
    | {
        f"datasetB/datasetB_{index}.raw": [name]
        for index, name in [
            (1, "ABSMode_HS"),
            (2, "MSRMode_HS"),
            (3, "AbsThrottlePosition_HS"),
            (4, "ABSWarningLamp_HS"),
            (5, "AccPedalAnalogPos_HS"),
            (6, "ACC_vehicle_lat"),
            (7, "ACC_vehicle_long"),
            (8, "AmbientAirPressure_HS"),
            (9, "AmbientTemp_HS"),
            (10, "AWD_TerrainMode_HS"),
            (11, "BrakePedalActiveQF_HS"),
            (12, "BrakePressure_HS"),
            (13, "EngineSpeed_HS"),
            (14, "EPBStatus_RB"),
            (15, "GearBoxTrqLoss_HS"),
            (16, "Gear_HS"),
            (17, "GPS.time.sec"),
            (18, "HillDescentMode_HS"),
            (19, "LateralAcceleration_HS"),
            (20, "LongAcceleration_HS"),
            (21, "LongAccOverGround_HS"),
            (22, "BrakeLightSwitch_HS"),
            (23, "pedal_force"),
            (24, "piston_travel"),
            (25, "pressure_FL"),
            (26, "pressure_RL"),
            (27, "pressure_Vacuum"),
            (28, "RollRateActual_HS"),
            (29, "SteeringAngleSign_HS"),
            (30, "SteeringAngle_HS"),
            (31, "Temp_Disc_FR"),
            (32, "Temp_Disc_RR"),
            (33, "Temp_Fluid_FR"),
            (34, "Temp_Fluid_RR"),
            (35, "Temp_Pad_FL"),
            (36, "TorsionBarTorque_HS"),
            (37, "VehicleSpeed_HS"),
            (38, "WheelDirectionRL_HS"),
            (39, "WheelDirectionRR_HS"),
            (40, "WheelSpeedFrL_HS"),
            (41, "WheelSpeedFrR_HS"),
            (42, "WheelSpeedReL_HS"),
            (43, "WheelSpeedReR_HS"),
            (44, "YawRateActual_HS"),
            (45, "YawRate_HS"),
        ]
    }
    | {
        "exampleA-20230124.raw": ["Average"],
        "exampleA.raw": ["Mittelwert"],
        "exampleB-20230124.raw": ["Chan1", "Chan2"],
        "exampleB.raw": ["kanal1", "kanal2", "E06_6_121"],
        "exampleC-20230124.raw": ["MyXY_plot"],
        "sampleA.raw": ["pressure_Vacuum"],
        "sampleB.raw": ["VehicleSpeed_HS"],
        "sample_x_precision.raw": ["Distance_RAD"],
        "imc3/imc3_multi-channel.dat": ["cone", "cone", "cone"],
        "events/imc2_event_numeric_many_small_events.dat": ["Signal"],
        "events/imc2_event_numeric_varied_metadata.dat": ["Signal"],
        "events/imc2_event_numeric_single_minimal.dat": ["SingleEvent"],
        "events/imc2_event_numeric_two_channels.dat": ["Temperature", "Pressure"],
        "events/imc2_event_numeric_two_channels_plus_numeric.dat": ["Speed", "Alarm", "Burst"],
        "events/imc2_mixed_numeric_and_event_channel.dat": ["Temperature", "Alarm"],
        "events/imc3_event_numeric_many_small_events.dat": ["Signal"],
        "events/imc3_event_numeric_varied_metadata.dat": ["Signal"],
        "events/imc3_event_numeric_single_minimal.dat": ["SingleEvent"],
        "events/imc3_event_numeric_two_channels.dat": ["Temperature", "Pressure"],
        "events/imc3_event_numeric_two_channels_plus_numeric.dat": ["Speed", "Alarm", "Burst"],
        "events/imc3_mixed_numeric_and_event_channel.dat": ["Temperature", "Alarm"],
        "tsa/imc3_tsa_large_initial_sample_offset.dat": ["PPT_TEST_2"],
        "tsa/imc3_tsa_leading_partial_fragment.dat": ["PPT_TEST_2"],
        "tsa/imc2_TsaChannel.dat": ["TsaChannel"],
        "tsa/imc2_tsa_multicluster.dat": ["TsaChannel"],
        "tsa/imc2_tsa_padding_and_escaping.dat": ["TsaChannel"],
    }
)


BASIC_SAMPLE_INFO_CASES = _with_basic_group_names((
    _build_basic_sample_info(["XY_dataset_example.dat"], datatypes=["6"])
    | _build_basic_sample_info(
        [f"datasetA/datasetA_{index}.raw" for index in [1, 21, 22, *range(24, 39)]],
        datatypes=["7"],
    )
    | _build_basic_sample_info(
        [f"datasetA/datasetA_{index}.raw" for index in [11, 23]],
        datatypes=["6"],
    )
    | _build_basic_sample_info(
        [
            f"datasetA/datasetA_{index}.raw"
            for index in [2, 3, 4, 5, 6, 7, 8, 9, 10, *range(12, 21)]
        ],
        datatypes=["4"],
    )
    | _build_basic_sample_info(
        [f"datasetB/datasetB_{index}.raw" for index in [1, 2, 22, 29]],
        datatypes=["11"],
    )
    | _build_basic_sample_info(
        [f"datasetB/datasetB_{index}.raw" for index in [6, 7, *range(23, 28), *range(31, 36)]],
        datatypes=["7"],
    )
    | _build_basic_sample_info(
        [f"datasetB/datasetB_{index}.raw" for index in [17]],
        datatypes=["6"],
    )
    | _build_basic_sample_info(
        [
            f"datasetB/datasetB_{index}.raw"
            for index in [3, 4, 5, *range(8, 17), *range(18, 22), 28, 30, *range(36, 46)]
        ],
        datatypes=["4"],
    )
    | _build_basic_sample_info(["exampleA-20230124.raw", "exampleA.raw"], datatypes=["8"])
    | _build_basic_sample_info(["exampleB-20230124.raw"], datatypes=["2", "2"])
    | _build_basic_sample_info(["exampleB.raw"], datatypes=["1", "1", "7"])
    | _build_basic_sample_info(["exampleC-20230124.raw", "sampleA.raw"], datatypes=["7"])
    | _build_basic_sample_info(["sampleB.raw", "sample_x_precision.raw"], datatypes=["4"])
    | _build_basic_sample_info(
        ["imc3/imc3_XY_dataset_example.dat"],
        datatypes=["6"],
        channel_names=["here is the channel name"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_multi-channel.dat"],
        datatypes=["7", "7", "7"],
        channel_names=["x", "y", "z"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sampleA.dat"],
        datatypes=["7"],
        channel_names=["pressure_Vacuum"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sampleB.dat"],
        datatypes=["4"],
        channel_names=["VehicleSpeed_HS"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sanitized_01.raw"],
        datatypes=["4"],
        channel_names=["channel01channe"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sanitized_02.raw", "imc3/imc3_sanitized_03.raw", "imc3/imc3_sanitized_05.raw", "imc3/imc3_sanitized_06.raw"],
        datatypes=["4"],
        channel_names=["channel01c"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sanitized_04.raw"],
        datatypes=["4"],
        channel_names=["channel01channel01cha"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_sanitized_bundle.dat"],
        datatypes=["4", "4", "4", "4", "4", "4"],
        channel_names=[
            "channel01channe",
            "channel02c",
            "channel03c",
            "channel04channel04cha",
            "channel05c",
            "channel06c",
        ],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_single-channel.dat"],
        datatypes=["7"],
        channel_names=["AmplitudeSpectrum"],
    )
    | _build_basic_sample_info(
        ["imc3/imc3_xy_dataset.dat"],
        datatypes=["8"],
        channel_names=["circle"],
    )
    | _build_basic_sample_info(
        [
            "events/imc2_event_numeric_many_small_events.dat",
            "events/imc2_event_numeric_varied_metadata.dat",
            "events/imc2_event_numeric_single_minimal.dat",
        ],
        datatypes=["7"],
        channel_types=["event"],
    )
    | _build_basic_sample_info(
        [
            "events/imc3_event_numeric_many_small_events.dat",
            "events/imc3_event_numeric_varied_metadata.dat",
            "events/imc3_event_numeric_single_minimal.dat",
        ],
        datatypes=["7"],
        channel_types=["event"],
    )
    | _build_basic_sample_info(
        ["events/imc2_mixed_numeric_and_event_channel.dat"],
        datatypes=["7", "7"],
        channel_types=["numeric", "event"],
    )
    | _build_basic_sample_info(
        ["events/imc3_mixed_numeric_and_event_channel.dat"],
        datatypes=["7", "7"],
        channel_types=["numeric", "event"],
    )
    | _build_basic_sample_info(
        ["events/imc2_event_numeric_two_channels.dat", "events/imc3_event_numeric_two_channels.dat"],
        datatypes=["7", "7"],
        channel_types=["event", "event"],
    )
    | _build_basic_sample_info(
        ["events/imc2_event_numeric_two_channels_plus_numeric.dat", "events/imc3_event_numeric_two_channels_plus_numeric.dat"],
        datatypes=["7", "7", "7"],
        channel_types=["numeric", "event", "event"],
    )
    | _build_basic_sample_info(
        ["tsa/imc3_tsa_large_initial_sample_offset.dat"],
        datatypes=["10"],
        channel_types=["event"],
        channel_names=["PPT_TEST_2"],
    )
    | _build_basic_sample_info(
        ["tsa/imc3_tsa_leading_partial_fragment.dat"],
        datatypes=["10"],
        channel_types=["event"],
        channel_names=["PPT_TEST_2"],
    )
    | _build_basic_sample_info(
        [
            "tsa/imc2_TsaChannel.dat",
            "tsa/imc2_tsa_multicluster.dat",
            "tsa/imc2_tsa_padding_and_escaping.dat",
            "tsa/imc3_TsaChannel.dat",
            "tsa/imc3_tsa_multicluster.dat",
            "tsa/imc3_tsa_padding_and_escaping.dat",
        ],
        datatypes=["10"],
        channel_types=["event"],
        channel_names=["TsaChannel"],
    )
), BASIC_SAMPLE_GROUP_NAMES)

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

KNOWN_CHANNEL_VALUE_CASES = [
    (
        "imc3/imc3_multi-channel.dat",
        1,
        {
            "name": "y",
            "datatype": "7",
            "data_length": 62,
            "xdata_first": [0.0, 1.0, 2.0],
            "xdata_last": [59.0, 60.0, 61.0],
            "ydata_first": [0.0, 125.0, 125.0],
            "ydata_last": [125.0, 125.0, 125.0],
        },
    ),
    (
        "imc3/imc3_xy_dataset.dat",
        0,
        {
            "name": "circle",
            "datatype": "8",
            "data_length": 360,
            "xdata_first": [3.0, 3.017452406, 3.034899497],
            "xdata_last": [2.947664044, 2.965100503, 2.982547594],
            "ydata_first": [1.0, 0.999847695, 0.999390827],
            "ydata_last": [0.998629535, 0.999390827, 0.999847695],
        },
    ),
]

UNIFORM_X_INVARIANT_CHANNEL_CASES = [
    ("datasetA/datasetA_1.raw", 0),
    ("sampleA.raw", 0),
    ("sample_x_precision.raw", 0),
    ("imc3/imc3_multi-channel.dat", 1),
]

RAW_SCALED_INVARIANT_CHANNEL_CASES = [
    # Curated channels only: the broad `scaled == raw * factor + offset` rule is
    # not universal across the full corpus.
    ("datasetA/datasetA_1.raw", 0),
    ("sampleA.raw", 0),
    ("sample_x_precision.raw", 0),
    ("imc3/imc3_multi-channel.dat", 1),
    ("XY_dataset_example.dat", 0),
    ("imc3/imc3_xy_dataset.dat", 0),
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