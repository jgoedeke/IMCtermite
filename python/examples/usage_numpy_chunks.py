
import imctermite
import json
import os
import numpy as np

# Path to a sample file
# Using sampleB.raw because it has integer data with scaling (factor=0.01, offset=327.68)
raw_file = "samples/sampleB.raw"
if not os.path.exists(raw_file):
    print(f"Sample file {raw_file} not found.")
    exit(1)

print(f"Loading {raw_file}")

try:
    imcraw = imctermite.imctermite(raw_file)
except RuntimeError as e:
    print(f"Failed to load/parse raw-file: {e}")
    exit(1)

# Get channels metadata
channels = imcraw.get_channels(False)
if not channels:
    print("No channels found.")
    exit(0)

# Pick the first channel
# For sampleB.raw, channel 347 is the interesting one
target_uuid = "347"
channel_info = next((ch for ch in channels if ch['uuid'] == target_uuid), channels[0])

first_channel_uuid = channel_info['uuid']
print(f"Iterating over channel {first_channel_uuid} ({channel_info.get('name', 'unnamed')})")

# Check native datatype
if 'datatype' in channel_info:
    print(f"Native IMC datatype ID: {channel_info['datatype']}")

# Example 1: Scaled mode (default) - returns floats (physical units)
print("\n--- Scaled Mode (Physical Units) ---")
total_rows = 0
chunk_size = 1000

for chunk in imcraw.iter_channel_numpy(first_channel_uuid, include_x=True, chunk_rows=chunk_size, mode="scaled"):
    start = chunk['start']
    y = chunk['y']
    x = chunk.get('x')
    
    count = len(y)
    total_rows += count
    
    if total_rows <= chunk_size * 2: # Print only first few chunks
        print(f"Chunk start={start}, count={count}, y_shape={y.shape}, y_dtype={y.dtype}")
        if x is not None:
            print(f"  x_shape={x.shape}, x_dtype={x.dtype}")
        if count > 0:
            print(f"  First y value: {y[0]}")

print(f"Total rows read (scaled): {total_rows}")

# Example 2: Raw mode - returns native types (e.g. integers)
print("\n--- Raw Mode (Native Types) ---")

# Get scaling factors
factor = float(channel_info.get('factor', 1.0))
offset = float(channel_info.get('offset', 0.0))
print(f"Scaling: factor={factor}, offset={offset}")

total_rows = 0

for chunk in imcraw.iter_channel_numpy(first_channel_uuid, include_x=True, chunk_rows=chunk_size, mode="raw"):
    start = chunk['start']
    y = chunk['y']
    
    count = len(y)
    total_rows += count
    
    if total_rows <= chunk_size * 2:
        print(f"Chunk start={start}, count={count}, y_shape={y.shape}, y_dtype={y.dtype}")
        if count > 0:
            raw_val = y[0]
            scaled_val = raw_val * factor + offset
            print(f"  First y value (raw): {raw_val}")
            print(f"  First y value (manually scaled): {scaled_val}")

print(f"Total rows read (raw): {total_rows}")
