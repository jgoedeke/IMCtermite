from typing import Any, Iterator

def get_codepage(chn: bytes | str) -> str: ...

class imctermite:
    def __init__(self, rawfile: str | bytes) -> None: ...
    def submit_file(self, rawfile: str | bytes) -> None: ...
    def get_channels(self, include_data: bool) -> list[dict[str, Any]]: ...
    def get_channel_length(self, channeluuid: str | bytes) -> int: ...
    def iter_channel_numpy(
        self,
        channeluuid: str | bytes,
        include_x: bool = True,
        chunk_rows: int = 1000000,
        mode: str = "scaled",
        start_index: int = 0
    ) -> Iterator[dict[str, Any]]: ...
    def get_channel_data(
        self,
        channeluuid: str | bytes,
        include_x: bool = True,
        mode: str = "scaled"
    ) -> dict[str, Any]: ...
    def print_channel(
        self,
        channeluuid: str | bytes,
        outputfile: str | bytes,
        delimiter: str | bytes,
        chunk_size: int = 100000
    ) -> None: ...
    def print_channels(
        self,
        outputdir: str | bytes,
        delimiter: str | bytes,
        chunk_size: int = 100000
    ) -> None: ...
    def print_table(self, outputfile: str | bytes) -> None: ...
