
[![License](https://img.shields.io/github/license/jgoedeke/IMCtermite)](https://github.com/jgoedeke/IMCtermite/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/jgoedeke/IMCtermite)](https://github.com/jgoedeke/IMCtermite/stargazers)
[![Tests](https://img.shields.io/github/actions/workflow/status/jgoedeke/IMCtermite/test.yml?branch=main&label=tests)](https://github.com/jgoedeke/IMCtermite/actions/workflows/test.yml?query=branch%3Amain)
[![Release](https://img.shields.io/github/actions/workflow/status/jgoedeke/IMCtermite/release-please.yml?branch=main&label=release)](https://github.com/jgoedeke/IMCtermite/actions/workflows/release-please.yml?query=branch%3Amain)
[![PyPI](https://img.shields.io/pypi/v/imctermite3)](https://pypi.org/project/imctermite3/)
[![Python versions](https://img.shields.io/pypi/pyversions/imctermite3)](https://pypi.org/project/imctermite3/)

# IMCtermite

_IMCtermite_ provides access to proprietary IMC measurement file formats
introduced and developed by
[imc Test & Measurement GmbH](https://www.imc-tm.de/). The library currently
supports both the legacy _IMC2 Data Format_ and the newer _IMC3 Data Format_,
which are commonly encountered with the file extensions _.raw_ and _.dat_.
These formats are employed i.a. by the measurement hardware
[imc CRONOSflex](https://www.imc-tm.de/produkte/messtechnik-hardware/imc-cronosflex/ueberblick/)
to dump and store data and the software packages
[imc Studio](https://www.imc-tm.de/produkte/messtechnik-software/imc-studio/ueberblick/)
& [imc FAMOS](https://www.imc-tm.de/produkte/messtechnik-software/imc-famos/)
for measurement data control and analysis. Thanks to the integrated Python module,
the extracted measurement data can be stored in any open-source file format
accessible by Python like i.a. _csv_, _json_ or _parquet_.

On the [Record Evolution Platform](https://www.record-evolution.de/en/home-en/),
the library can be used both as a command line tool for interactive usage and as a
Python module to integrate IMC measurement files into any ETL workflow.

## Supported formats

- _IMC2_ marker-based files. Reference: [docs/imc2-format.md](docs/imc2-format.md)
- _IMC3_ files, including bundled and single-channel variants. Reference: [docs/imc3-format.md](docs/imc3-format.md)

## Overview

* [Supported formats](#supported-formats)
* [Format reference](#format-reference)
* [Build and Installation](#installation)
* [Usage and Examples](#usage)
* [Testing](#testing)
* [Releases](https://github.com/jgoedeke/IMCtermite/releases)
* [References](#references)

## Format reference

IMCtermite auto-detects the file format while loading a file. The same CLI and
Python interfaces are used for both supported formats; no explicit format flag
is required.

| format | typical extensions | support status | notes |
|--------|--------------------|----------------|-------|
| IMC2   | _.raw_, _.dat_     | supported      | Legacy marker-based stream format |
| IMC3   | _.raw_, _.dat_     | supported      | Structured successor format; compressed IMC3 is currently rejected |

Detailed format notes live in dedicated pages:

- [IMC2 format reference](docs/imc2-format.md)
- [IMC3 format reference](docs/imc3-format.md)

## Installation

The _IMCtermite_ library may be employed both as a _CLI_ tool and a _python_
module.

### CLI tool

Building the CLI requires a compiler supporting C++17.

To build the CLI tool locally, use the default target `make` resulting
in the binary `imctermite`. To ensure system-wide availability, the installation
of the tool (in the default location `/usr/local/bin`) is done via

```
make install
```

which may require root permissions.

### Python

To integrate the library into a customized ETL toolchain, several python targets
are available. From the repository root, use a Python 3.10+ environment and a
C++17 compiler. Install the build dependencies before building the extension
in place:

```Shell
python3 -m pip install "setuptools>=77.0.0" wheel Cython "numpy>=1.26.0"
make python-build
```

#### Installation with pip

This fork is distributed as [imctermite3](https://pypi.org/project/imctermite3/)
on the [Python Package Index](https://pypi.org). Once published, install it with

```Shell
python3 -m pip install imctermite3
```

The Python import remains `from imctermite import ImcTermite`. The distribution
targets binary wheels for _Windows_ and _Linux_ on x86-64 with CPython 3.10-3.14 and
requires NumPy, which pip installs automatically.

Do not install `imctermite` and `imctermite3` in the same environment: both
provide the `imctermite` import package. To replace the original distribution:

```Shell
python3 -m pip uninstall imctermite
python3 -m pip install imctermite3
```

If your platform/architecture has no compatible wheel, pip builds the source
distribution instead. This requires Python 3.10+ and a compiler supporting
C++17 (e.g. _gcc version >= 10.2.0_). Pip installs the declared build dependencies
automatically in an isolated environment.

## Usage

### CLI

The usage of the `imctermite` binary looks like this:

```
imctermite <imc-file> [options]
```

You have to provide a single supported IMC file and any option to specify what
to do with the data. All available options can be listed with `imctermite --help`:

```
Options:

 -c, --listchannels      list channels
 -b, --listblocks        list IMC key-blocks
 -d, --output            output directory to print channels
 -s, --delimiter         csv delimiter/separator char for output
 -h, --help              show this help message
 -v, --version           display version
```

For instance, to show a list of all channels included in `sample-data.raw`, you
do `imctermite sample-data.raw --listchannels`. No output files are
written by default. Output files are written only when an existing (!) directory
is provided as argument to the `--output` option. By default, every output file
is written using a `,` delimiter. You may provide any custom separator with the
option `--delimiter`. For example, to export CSV files using `|`:

```Shell
mkdir -p output
imctermite samples/sampleA.raw -b -c -d output -s '|'
```

### Python

Given the `IMCtermite` module is available, we can import it and declare an instance
of it by passing an IMC file to the constructor:

```Python
from imctermite import ImcTermite

imcraw = ImcTermite("samples/sampleA.raw")
```

An example of how to create an instance and obtain the list of channels is:

```Python
from imctermite import ImcTermite

try:
    imcraw = ImcTermite("samples/sampleA.raw")
except RuntimeError as error:
    print("failed to load/parse IMC file: " + str(error))
else:
    channels = imcraw.get_channels(False)
    print(channels)
```

### Typed channel metadata

For integrations that need a stable metadata contract without loading sample
data, use the typed API:

```Python
from imctermite import ImcTermite

imcraw = ImcTermite("samples/sampleA.raw")
for channel in imcraw.get_channels_metadata():
    print(channel.name, channel.y_unit, channel.sample_count)
```

`ChannelMetadata.name` is the canonical channel name and falls back to the IMC
component-group name when the source channel name is empty. The literal source
value remains available as `ChannelMetadata.source_name`. The existing
`get_channels()` dictionary schema is unchanged.

File, group, standalone text-object, and typed channel-property metadata are
available through separate typed getters:

```Python
metadata = imcraw.get_file_metadata()
groups = imcraw.get_groups_metadata()
text_objects = imcraw.get_text_objects_metadata()
channel = imcraw.get_channels_metadata()[0]

print(metadata.producer, metadata.comment)
print(channel.properties)
```

### TSA custom-decoder support

For native custom decoders, `lib/imc_raw.hpp` provides copied TSA container
bytes and logical timestamped-record access. This supports application-specific
frame decoding while IMCtermite remains responsible only for container parsing,
metadata, and sample access; it does not decode proprietary protocol
descriptions or write IMC files.

A more complete [example](python/examples/usage.py), including the methods for
obtaining the channels, i.a. their data and/or directly printing them to files,
can be found in the `python/examples` folder.

### Chunked NumPy export (fast path)

For large files, you can iterate over channel data in chunks as NumPy arrays. This avoids creating large Python lists and allows for streaming processing (e.g. writing to Parquet). See [`python/examples/usage_numpy_chunks.py`](python/examples/usage_numpy_chunks.py) for a complete example.

## Testing

See [tests/README.md](tests/README.md) for prerequisites, test commands, and coverage.

## References

### IMC

- https://www.imc-tm.de/produkte/messtechnik-software/imc-famos/import-export
- https://www.imc-tm.de/produkte/messtechnik-hardware/imc-cronosflex/ueberblick/
- https://www.imc-tm.de/download-center/produkt-downloads/imc-famos/handbuecher
- https://www.imc-tm.de/fileadmin/Public/Downloads/Manuals/imc_FAMOS/imcGemeinsameKomponenten.pdf
- https://github.com/Apollo3zehn/ImcFamosFile
- https://apollo3zehn.github.io/ImcFamosFile/api/ImcFamosFile.FamosFileKeyType.html

### Cython

- https://cython.readthedocs.io/en/latest/src/userguide/wrapping_CPlusPlus.html

### PyPI

- https://pypi.org/help/#apitoken
- https://sgoel.dev/posts/uploading-binary-wheels-to-pypi-from-github-actions/
- https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idstepsrun
- https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml
- https://cibuildwheel.readthedocs.io/en/stable/deliver-to-pypi/
- https://github.com/actions/download-artifact#download-all-artifacts
- https://github.com/actions/download-artifact?tab=readme-ov-file#download-multiple-filtered-artifacts-to-the-same-directory

### iconv

- https://www.gnu.org/software/libiconv/
- https://vcpkg.io/en/packages.html
- https://vcpkg.io/en/getting-started
