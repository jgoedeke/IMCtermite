"""
Type stub file for IMCtermite Cython extension.
This provides IDE support, type checking, and autocomplete for the imctermite module.
"""

from typing import Any, Dict, Iterator, List, Literal, Optional, Union
import numpy as np
import numpy.typing as npt

def get_codepage(chn: bytes) -> str:
    """Get the codepage for decoding channel data."""
    ...

class imctermite:
    """
    IMCtermite parser for .raw (IMC2 Data Format) files.
    
    This class provides methods to read and parse IMC measurement data files,
    extracting channel metadata and data.
    """
    
    def __init__(self, rawfile: Union[str, bytes]) -> None:
        """
        Initialize parser with a .raw file.
        
        Args:
            rawfile: Path to the .raw file to parse
        """
        ...
    
    def submit_file(self, rawfile: Union[str, bytes]) -> None:
        """
        Set or change the raw file to parse.
        
        Args:
            rawfile: Path to the .raw file to parse
        """
        ...
    
    def get_channels(self, include_data: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of all channels in the file with their metadata.
        
        Args:
            include_data: If True, includes the actual measurement data in the result.
                         If False, only returns metadata (faster for inspection).
        
        Returns:
            List of dictionaries containing channel information:
            - uuid: Unique identifier for the channel
            - xname: X-axis name (typically "time")
            - yname: Y-axis name (measurement name)
            - xunit: X-axis unit
            - yunit: Y-axis unit
            - length: Number of data points
            - xdata: X-axis data (if include_data=True)
            - ydata: Y-axis data (if include_data=True)
            - buffer_type: Data type identifier
            - codepage: Text encoding information
        """
        ...
    
    def get_channel_length(self, channeluuid: Union[str, bytes]) -> int:
        """
        Get the number of data points in a channel.
        
        Args:
            channeluuid: UUID of the channel to query
        
        Returns:
            Number of data points in the channel
        """
        ...
    
    def iter_channel_numpy(
        self,
        channeluuid: Union[str, bytes],
        include_x: bool = True,
        chunk_rows: int = 1000000,
        mode: Literal["scaled", "raw"] = "scaled",
        start_index: int = 0
    ) -> Iterator[Dict[str, Union[int, npt.NDArray[Any]]]]:
        """
        Iterate over channel data in chunks as numpy arrays.
        
        This is memory-efficient for large datasets as it yields data in chunks
        rather than loading everything into memory at once.
        
        Args:
            channeluuid: UUID of the channel to read
            include_x: If True, includes x-axis data in results
            chunk_rows: Number of rows per chunk (default: 1,000,000)
            mode: "scaled" for calibrated values or "raw" for uncalibrated ADC values
            start_index: Starting row index (for partial reads)
        
        Yields:
            Dictionary containing:
            - start: Starting index of this chunk
            - y: numpy array of Y-axis values
            - x: numpy array of X-axis values (if include_x=True)
        
        Example:
            >>> imc = imctermite("measurement.raw")
            >>> channels = imc.get_channels(include_data=False)
            >>> uuid = channels[0]['uuid']
            >>> for chunk in imc.iter_channel_numpy(uuid, chunk_rows=100000):
            ...     print(f"Processing {len(chunk['y'])} samples starting at {chunk['start']}")
            ...     # Process chunk['x'] and chunk['y'] arrays
        """
        ...
    
    def get_channel_data(
        self,
        channeluuid: Union[str, bytes],
        include_x: bool = True,
        mode: Literal["scaled", "raw"] = "scaled"
    ) -> Dict[str, npt.NDArray[Any]]:
        """
        Get all data for a channel as numpy arrays.
        
        Args:
            channeluuid: UUID of the channel to read
            include_x: If True, includes x-axis data in result
            mode: "scaled" for calibrated values or "raw" for uncalibrated ADC values
        
        Returns:
            Dictionary containing:
            - y: numpy array of Y-axis values
            - x: numpy array of X-axis values (if include_x=True)
        
        Note:
            This loads the entire channel into memory. For large datasets,
            consider using iter_channel_numpy() instead.
        
        Example:
            >>> imc = imctermite("measurement.raw")
            >>> channels = imc.get_channels(include_data=False)
            >>> uuid = channels[0]['uuid']
            >>> data = imc.get_channel_data(uuid)
            >>> print(f"X shape: {data['x'].shape}, Y shape: {data['y'].shape}")
        """
        ...
    
    def print_channel(
        self,
        channeluuid: Union[str, bytes],
        outputfile: Union[str, bytes],
        delimiter: Union[str, bytes] = b',',
        chunk_size: int = 100000
    ) -> None:
        """
        Export a single channel to a CSV file.
        
        Args:
            channeluuid: UUID of the channel to export
            outputfile: Path to output file
            delimiter: Column delimiter character (default: comma)
            chunk_size: Number of rows to process at once
        """
        ...
    
    def print_channels(
        self,
        outputdir: Union[str, bytes],
        delimiter: Union[str, bytes] = b',',
        chunk_size: int = 100000
    ) -> None:
        """
        Export all channels to separate CSV files in a directory.
        
        Args:
            outputdir: Directory path for output files
            delimiter: Column delimiter character (default: comma)
            chunk_size: Number of rows to process at once
        """
        ...
    
    def print_table(self, outputfile: Union[str, bytes]) -> None:
        """
        Export all channels with headers to a single formatted text file.
        
        Args:
            outputfile: Path to output file
        """
        ...
