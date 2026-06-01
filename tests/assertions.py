from itertools import zip_longest

import numpy as np

from tests.sample_manifest import TSA_MULTICLUSTER_TIMESTAMPS, TSA_PADDING_ESCAPED_TEXTS


EXACT_FLOAT_RTOL = 1e-9
EXACT_FLOAT_ATOL = 1e-9
REGRESSION_VALUE_ATOL = 1e-6
NONDIGITAL_SCALE_RTOL = 2e-6
NONDIGITAL_SCALE_ATOL = 5e-6


def assert_basic_sample_info(channels, expected: dict) -> None:
    assert len(channels) == expected["num_channels"]
    assert [channel.get("channel_type") for channel in channels] == expected["channel_types"]
    assert [str(channel.get("datatype")) for channel in channels] == expected["datatypes"]
    if "channel_names" in expected:
        assert [channel.get("name") for channel in channels] == expected["channel_names"]
    if "group_names" in expected:
        assert [((channel.get("group") or {}).get("name", "")) for channel in channels] == expected["group_names"]


def assert_exact_float_equal(actual, expected, message: str | None = None) -> None:
    assert abs(float(actual) - float(expected)) < EXACT_FLOAT_ATOL, message


def assert_exact_allclose(actual, expected, *, equal_nan: bool = False) -> None:
    np.testing.assert_allclose(
        actual,
        expected,
        rtol=EXACT_FLOAT_RTOL,
        atol=EXACT_FLOAT_ATOL,
        equal_nan=equal_nan,
    )


def assert_tsa_channel_metadata(imc, channel: dict, expected_length: int) -> None:
    assert channel["channel_type"] == "event"
    assert channel["datatype"] == "10"
    assert channel["name"] == "TsaChannel"
    assert channel["xname"] == "time"
    assert channel["xunit"] == "s"
    assert imc.get_channel_length(channel["uuid"]) == expected_length


def assert_tsa_texts_and_timestamps(sample_name: str, texts, timestamps) -> None:
    if sample_name.endswith("TsaChannel.dat"):
        assert list(texts) == ["hello", "0123456789"]
        assert_exact_allclose(timestamps, np.array([20.0, 40.0]))
    elif "multicluster" in sample_name:
        assert len(texts) == 33
        assert texts[0] == ""
        assert texts[1] == "short"
        assert all(text == texts[2] for text in texts[2:-1])
        assert texts[-1] == texts[2] * 3
        assert_exact_allclose(timestamps, TSA_MULTICLUSTER_TIMESTAMPS)
    else:
        assert list(texts) == TSA_PADDING_ESCAPED_TEXTS
        assert_exact_allclose(
            timestamps,
            np.array([0.0, 0.0, 0.001, 0.001, 0.002, 0.003, 0.005, 0.008, 0.013]),
        )


def assert_tsa_csv_rows(sample_name: str, rows) -> None:
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


def assert_streamed_numeric_matches_eager(streamed_chunks, eager_x, eager_y) -> None:
    streamed_x = np.concatenate([chunk["x"] for chunk in streamed_chunks])
    streamed_y = np.concatenate([chunk["y"] for chunk in streamed_chunks])

    assert_chunk_start_progression(streamed_chunks, "y")
    assert_exact_allclose(streamed_x, np.array(eager_x))
    assert_exact_allclose(streamed_y, np.array(eager_y))


def assert_chunk_start_progression(chunks, item_key: str) -> None:
    expected_start = 0
    for chunk in chunks:
        assert chunk["start"] == expected_start
        expected_start += len(chunk[item_key])


def assert_event_chunks_match_eager(streamed_chunks, eager_events) -> None:
    assert_chunk_start_progression(streamed_chunks, "texts")
    assert [text for chunk in streamed_chunks for text in chunk["texts"]] == eager_events["texts"]
    assert_exact_allclose(
        np.concatenate([chunk["timestamps"] for chunk in streamed_chunks]),
        eager_events["timestamps"],
    )


def assert_scaled_chunks_match_raw_transform(channel: dict, raw_chunks, scaled_chunks) -> None:
    assert len(raw_chunks) == len(scaled_chunks)
    assert_chunk_start_progression(raw_chunks, "y")
    assert_chunk_start_progression(scaled_chunks, "y")

    datatype = str(channel.get("datatype"))
    factor = float(channel.get("factor", 1.0))
    offset = float(channel.get("offset", 0.0))
    effective_factor = 1.0 if factor == 0.0 else factor

    for raw_chunk, scaled_chunk in zip_longest(raw_chunks, scaled_chunks):
        assert raw_chunk is not None and scaled_chunk is not None
        assert raw_chunk["start"] == scaled_chunk["start"]
        assert len(raw_chunk["y"]) == len(scaled_chunk["y"])
        assert scaled_chunk["y"].dtype == np.float64

        expected = raw_chunk["y"].astype(np.float64)
        if datatype != "11":
            expected = expected * effective_factor + offset

        if datatype == "11":
            np.testing.assert_allclose(scaled_chunk["y"], expected, rtol=0.0, atol=0.0, equal_nan=True)
        else:
            np.testing.assert_allclose(
                scaled_chunk["y"],
                expected,
                rtol=NONDIGITAL_SCALE_RTOL,
                atol=NONDIGITAL_SCALE_ATOL,
                equal_nan=True,
            )


def assert_uniform_numeric_x_axis(channel: dict, x_values, indices) -> None:
    xoffset = float(channel.get("xoffset", 0.0))
    xstepwidth = float(channel.get("xstepwidth", 0.0))

    for index in indices:
        expected = xoffset + index * xstepwidth
        assert_exact_float_equal(
            x_values[index],
            expected,
            f"xdata[{index}] should equal xoffset + index * xstepwidth ({expected})"
        )


def assert_numeric_scaled_matches_raw(channel: dict, scaled_y, raw_y, indices) -> None:
    factor = float(channel.get("factor", 1.0))
    offset = float(channel.get("offset", 0.0))
    effective_factor = 1.0 if factor == 0.0 else factor

    raw_array = np.asarray(raw_y, dtype=np.float64)
    scaled_array = np.asarray(scaled_y, dtype=np.float64)

    for index in indices:
        expected = raw_array[index] * effective_factor + offset
        assert_exact_float_equal(
            scaled_array[index],
            expected,
            f"scaled y[{index}] should equal raw * factor + offset ({expected})"
        )


def assert_regression_series_prefix(values, expected_values) -> None:
    for index, expected_value in enumerate(expected_values):
        assert abs(values[index] - expected_value) < REGRESSION_VALUE_ATOL


def assert_regression_series_suffix(values, expected_values) -> None:
    for index, expected_value in enumerate(expected_values):
        suffix_index = -(len(expected_values) - index)
        assert abs(values[suffix_index] - expected_value) < REGRESSION_VALUE_ATOL