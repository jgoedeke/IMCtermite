
import imctermite
import sys
import os

def print_timerange(filename):
    """
    Demonstrates how to efficiently get the time range (first and last X values)
    of channels without reading the entire file.
    """
    
    try:
        imc = imctermite.imctermite(filename)
    except RuntimeError as e:
        print(f"Error loading file: {e}")
        return

    # Get list of channels (metadata only, no data loaded yet)
    channels = imc.get_channels(False)
    
    if not channels:
        print("No channels found in file.")
        return

    print(f"File: {filename}")
    print("-" * 80)
    print(f"{'Channel Name':<25} | {'Start (X)':<15} | {'End (X)':<15} | {'Samples':<10}")
    print("-" * 80)

    for chn in channels:
        uuid = chn['uuid']
        name = chn.get('yname', 'Unknown')
        
        length = imc.get_channel_length(uuid)
        
        if length == 0:
            print(f"{name:<25} | {'Empty':<15} | {'Empty':<15} | {0:<10}")
            continue

        # Get first sample (efficiently, reading only 1 row)
        # We request X data to get the time/index
        # chunk_rows=1 ensures we only read/convert the absolute minimum data
        gen_first = imc.iter_channel_numpy(uuid, start_index=0, chunk_rows=1, include_x=True)
        try:
            first_chunk = next(gen_first)
            first_x = first_chunk['x'][0]
        except (StopIteration, IndexError):
            first_x = float('nan')

        # Get last sample
        gen_last = imc.iter_channel_numpy(uuid, start_index=length-1, chunk_rows=1, include_x=True)
        try:
            last_chunk = next(gen_last)
            last_x = last_chunk['x'][0]
        except (StopIteration, IndexError):
            last_x = float('nan')

        print(f"{name:<25} | {first_x:<15.5f} | {last_x:<15.5f} | {length:<10}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python usage_timerange.py <path_to_raw_file>")
        print("Example: python usage_timerange.py ../../samples/datasetA/datasetA_1.raw")
    else:
        print_timerange(sys.argv[1])
