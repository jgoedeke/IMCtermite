"""Public Python API for the `imctermite` package.

This package ships a native (Cython/C++) extension for fast parsing of IMC
`.raw` files. The public surface here is a small typed wrapper around that
native implementation so IDEs/type checkers can use inline type annotations.

Public API:
- `ImcTermite`: preferred entry point.

Backwards compatibility:
- `imctermite`: deprecated alias class (warns on construction).
"""

from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Any, Iterator, Literal, TypedDict, cast

import numpy as np
import numpy.typing as npt

from . import _imctermite as _native

if TYPE_CHECKING:
    from . import _imctermite


_Mode = Literal["scaled", "raw"]


class ChannelNumpyChunk(TypedDict):
    """One chunk returned by `ImcTermite.iter_channel_numpy()`.

    Keys:
    - `start`: start index of this chunk in the channel.
    - `y`: numpy array of y-values.
    - `x`: numpy array of x-values (only present when `include_x=True`).
    """

    start: int
    y: npt.NDArray[Any]
    x: npt.NDArray[Any]


class ChannelEventChunk(TypedDict, total=False):
        """One chunk returned by `ImcTermite.iter_channel_events()`.

        Keys:
        - `start`: start index of this chunk in the event channel.
        - `texts`: decoded TSA event payload strings.
        - `timestamps`: numpy array of decoded timestamps when
            `include_timestamps=True`.
        """

        start: int
        texts: list[str]
        timestamps: npt.NDArray[np.float64]


class ChannelNumpyData(TypedDict):
    """Return value of `ImcTermite.get_channel_data()`.

    Keys:
    - `y`: numpy array of y-values.
    - `x`: numpy array of x-values (only present when `include_x=True`).
    """

    y: npt.NDArray[Any]
    x: npt.NDArray[Any]


class ChannelTsaData(TypedDict, total=False):
    """Return value of `ImcTermite.get_channel_data()` for TSA event channels.

    Keys:
    - `text`: decoded TSA event payload strings.
    - `x`: numpy array of decoded timestamps (when `include_x=True`).
    """

    text: list[str]
    x: npt.NDArray[np.float64]


class ChannelEventData(TypedDict, total=False):
        """Return value of `ImcTermite.get_channel_events()`.

        Keys:
        - `texts`: decoded TSA event payload strings.
        - `timestamps`: numpy array of decoded timestamps when
            `include_timestamps=True`.
        """

        texts: list[str]
        timestamps: npt.NDArray[np.float64]


ChannelData = ChannelNumpyData | ChannelTsaData


class ImcTermite:
    """Parser for IMC `.raw` files.

    This is a typed Python wrapper around the native `imctermite._imctermite`
    extension class.
    """

    _native: _imctermite.imctermite

    def __init__(self, rawfile: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> None:
        """Create a parser for a `.raw` file.

        Args:
            rawfile: Path to the `.raw` file.
        """

        self._native = _native.imctermite(os.fspath(rawfile))

    def submit_file(self, rawfile: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> None:
        """Switch to a different `.raw` file.

        Args:
            rawfile: Path to the `.raw` file.
        """

        self._native.submit_file(os.fspath(rawfile))

    def get_channels(self, include_data: bool = True) -> list[dict[str, Any]]:
        """Return channel metadata (and optionally embedded data).

        Args:
            include_data: If `True`, includes `xdata`/`ydata` in the returned
                dictionaries. If `False`, returns metadata only.

        Returns:
            A list of dictionaries with channel information.
        """

        return self._native.get_channels(include_data)

    def get_channel_length(self, channeluuid: str | bytes) -> int:
        """Return number of samples in a channel."""

        return int(self._native.get_channel_length(channeluuid))

    def iter_channel_numpy(
        self,
        channeluuid: str | bytes,
        include_x: bool = True,
        chunk_rows: int = 1_000_000,
        mode: _Mode = "scaled",
        start_index: int = 0,
    ) -> Iterator[ChannelNumpyChunk]:
        """Iterate channel data as numpy arrays in chunks.

        This is the preferred API for large channels because it avoids loading
        the entire channel into memory.

        Args:
            channeluuid: Channel UUID.
            include_x: Include x-values in the yielded chunks.
            chunk_rows: Maximum number of rows per yielded chunk.
            mode: `"scaled"` for calibrated values or `"raw"` for uncalibrated
                ADC values.
            start_index: Start reading at this sample index.

        Yields:
            Dicts containing at least `start` and `y` keys and optionally an `x`
            key when `include_x=True`.

        Note:
            TSA event channels are intentionally excluded from this numeric
            streaming API in the first implementation pass and raise
            `RuntimeError` instead.
        """

        return cast(
            Iterator[ChannelNumpyChunk],
            self._native.iter_channel_numpy(
                channeluuid,
                include_x=include_x,
                chunk_rows=chunk_rows,
                mode=mode,
                start_index=start_index,
            ),
        )

    def get_channel_data(
        self,
        channeluuid: str | bytes,
        include_x: bool = True,
        mode: _Mode = "scaled",
    ) -> ChannelData:
        """Return the full channel data.

        Note:
            This loads the entire channel into memory. For large channels,
            prefer `iter_channel_numpy()`.

        Returns:
            Numeric channels return numpy `x`/`y` arrays. TSA event channels
            return decoded `text` payloads and, when `include_x=True`, a numpy
            `x` array with decoded timestamps.
        """

        return cast(
            ChannelData,
            self._native.get_channel_data(channeluuid, include_x=include_x, mode=mode),
        )

    def get_channel_events(
        self,
        channeluuid: str | bytes,
        include_timestamps: bool = True,
    ) -> ChannelEventData:
        """Return TSA event payloads using an event-native shape.

        Args:
            channeluuid: Channel UUID.
            include_timestamps: Include decoded timestamps in the result.

        Returns:
            A dict containing `texts` and, when requested, `timestamps`.

        Note:
            This method is only valid for TSA event channels and raises
            `RuntimeError` for numeric channels.
        """

        return cast(
            ChannelEventData,
            self._native.get_channel_events(channeluuid, include_timestamps=include_timestamps),
        )

    def iter_channel_events(
        self,
        channeluuid: str | bytes,
        include_timestamps: bool = True,
        chunk_rows: int = 1_000_000,
        start_index: int = 0,
    ) -> Iterator[ChannelEventChunk]:
        """Iterate TSA event data in chunks.

        Args:
            channeluuid: Channel UUID.
            include_timestamps: Include decoded timestamps in the yielded chunks.
            chunk_rows: Maximum number of events per yielded chunk.
            start_index: Start reading at this event index.

        Yields:
            Dicts containing `start`, `texts`, and optionally `timestamps`.

        Note:
            This method is only valid for TSA event channels and raises
            `RuntimeError` for numeric channels.
        """

        return cast(
            Iterator[ChannelEventChunk],
            self._native.iter_channel_events(
                channeluuid,
                include_timestamps=include_timestamps,
                chunk_rows=chunk_rows,
                start_index=start_index,
            ),
        )

    def print_channel(
        self,
        channeluuid: str | bytes,
        outputfile: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        delimiter: str | bytes = b",",
        chunk_size: int = 100_000,
    ) -> None:
        """Export one channel to a delimited text file (typically CSV)."""

        self._native.print_channel(
            channeluuid,
            os.fspath(outputfile),
            delimiter=delimiter,
            chunk_size=chunk_size,
        )

    def print_channels(
        self,
        outputdir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        delimiter: str | bytes = b",",
        chunk_size: int = 100_000,
    ) -> None:
        """Export all channels to separate files in a directory."""

        self._native.print_channels(os.fspath(outputdir), delimiter=delimiter, chunk_size=chunk_size)

    def print_table(self, outputfile: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> None:
        """Export a human-readable table of all channels."""

        self._native.print_table(os.fspath(outputfile))


class imctermite(ImcTermite):
    """Deprecated alias for `ImcTermite`.

    This keeps old code working:

        `from imctermite import imctermite`
    """

    def __init__(self, rawfile: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> None:
        warnings.warn(
            "`from imctermite import imctermite` is deprecated; use `from imctermite import ImcTermite`.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(rawfile)


def get_codepage(chn: bytes) -> str:
    """Return the codepage name used to decode channel metadata."""

    return _native.get_codepage(chn)

__all__ = ["ImcTermite", "imctermite", "get_codepage"]
