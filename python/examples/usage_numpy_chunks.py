
import imctermite
import json
import os
import numpy as np

# Path to a sample file
raw_file = b"samples/datasetA/datasetA_1.raw"
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
first_channel_uuid = channels[0]['uuid'].encode('utf-8')
print(f"Iterating over channel {first_channel_uuid}")

# Iterate in chunks
total_rows = 0
chunk_size = 100

for chunk in imcraw.iter_channel_numpy(first_channel_uuid, include_x=True, chunk_rows=chunk_size):
    start = chunk['start']
    y = chunk['y']
    x = chunk.get('x')
    
    count = len(y)
    total_rows += count
    
    print(f"Chunk start={start}, count={count}, y_shape={y.shape}, y_dtype={y.dtype}")
    if x is not None:
        print(f"  x_shape={x.shape}, x_dtype={x.dtype}")
        
    # Verify data (optional, just checking first few values)
    if start == 0 and count > 0:
        print(f"  First y value: {y[0]}")

    # Here you could write the chunk to a Parquet file using pyarrow or fastparquet
    # e.g.
    # table = pa.Table.from_pydict({"x": x, "y": y})
    # pq.write_table(table, output_file)

print(f"Total rows read: {total_rows}")
