# IMC3 Format Reference

This page summarizes the _IMC3 Data Format_ support currently implemented in
IMCtermite. It is intentionally shorter than the IMC2 reference: the library
supports IMC3 through the same public facade, but this page is an
implementation-oriented overview rather than a full vendor specification.

## Overview

IMC3 is the newer successor format alongside the legacy IMC2 marker stream.
IMCtermite auto-detects IMC3 files during load. In the current implementation,
IMC3 detection is based on the file header beginning with `|imc3,1;`.

Typical files use _.dat_ or _.raw_ extensions, just like IMC2. The extension by
itself is therefore not sufficient to determine the format; detection happens on
file content.

## Current support in IMCtermite

The shared CLI and Python interfaces support IMC3 for the same high-level tasks
as IMC2:

- listing channels and channel metadata
- retrieving per-channel sample counts and numeric metadata
- eager data extraction through `get_channels(include_data=True)`
- chunked channel streaming through the Python fast path
- CSV export through the CLI and Python facade

The current regression coverage includes these IMC3 shapes:

- single-channel files
- multi-channel files
- XY-style datasets
- bundled files containing multiple channels
- corresponding single-channel extracts of bundled datasets

## Current limitations

- compressed IMC3 files are currently rejected
- this page does not attempt to reproduce the full vendor-level binary layout

## Structure at a high level

Unlike IMC2, IMC3 is not exposed internally as a marker stream with `CN`, `CS`,
and related blocks. Instead, the parser reconstructs dataset metadata, groups,
channels, numeric types, scaling, timestamps, and typed sample buffers from the
IMC3 structure and then adapts them to the shared IMCtermite facade.

That means callers use the same `imc::raw` facade and Python `ImcTermite`
wrapper for both IMC2 and IMC3, even though the on-disk representations differ.
