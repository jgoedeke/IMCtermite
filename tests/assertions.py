import numpy as np

from tests.sample_manifest import TSA_MULTICLUSTER_TIMESTAMPS, TSA_PADDING_ESCAPED_TEXTS


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
        np.testing.assert_allclose(timestamps, np.array([20.0, 40.0]), rtol=1e-9, atol=1e-9)
    elif "multicluster" in sample_name:
        assert len(texts) == 33
        assert texts[0] == ""
        assert texts[1] == "short"
        assert all(text == texts[2] for text in texts[2:-1])
        assert texts[-1] == texts[2] * 3
        np.testing.assert_allclose(timestamps, TSA_MULTICLUSTER_TIMESTAMPS, rtol=1e-9, atol=1e-9)
    else:
        assert list(texts) == TSA_PADDING_ESCAPED_TEXTS
        np.testing.assert_allclose(
            timestamps,
            np.array([0.0, 0.0, 0.001, 0.001, 0.002, 0.003, 0.005, 0.008, 0.013]),
            rtol=1e-9,
            atol=1e-9,
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

    np.testing.assert_allclose(streamed_x, np.array(eager_x), rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(streamed_y, np.array(eager_y), rtol=1e-9, atol=1e-9)


def assert_event_chunks_match_eager(streamed_chunks, eager_events) -> None:
    assert [text for chunk in streamed_chunks for text in chunk["texts"]] == eager_events["texts"]
    np.testing.assert_allclose(
        np.concatenate([chunk["timestamps"] for chunk in streamed_chunks]),
        eager_events["timestamps"],
        rtol=1e-9,
        atol=1e-9,
    )
    assert [chunk["start"] for chunk in streamed_chunks] == list(range(0, len(eager_events["texts"]), 1))


def assert_uniform_numeric_x_axis(channel: dict, x_values, indices) -> None:
    xoffset = float(channel.get("xoffset", 0.0))
    xstepwidth = float(channel.get("xstepwidth", 0.0))

    for index in indices:
        expected = xoffset + index * xstepwidth
        assert abs(float(x_values[index]) - expected) < 1e-9, (
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
        assert abs(scaled_array[index] - expected) < 1e-9, (
            f"scaled y[{index}] should equal raw * factor + offset ({expected})"
        )