# IMC2 Format Reference

This page documents the legacy _IMC2 Data Format_ that IMCtermite parses from
marker-based _.raw_ and _.dat_ files.

## Overview

A file of the _IMC2 Data Format_ type with extension _.raw_ (or _.dat_) is a
_mixed text/binary file_ featuring a set of markers (keys) that indicate the
start of various blocks of data that provide meta information and the actual
measurement data. Every single marker is introduced by the character `"|" =
0x7c` followed by two uppercase letters that characterize the type of marker.
Each block is further divided into several parameters separated by commas
(`"," = 0x2c`) and terminated by a semicolon (`";" = 0x3b`).

For instance, the header of a raw file may look like this:

```
|CF,2,1,1;|CK,1,3,1,1;
|NO,1,86,0,78,imc STUDIO 5.0 R10 (04.08.2017)@imc DEVICES 2.9R7 (25.7.2017)@imcDev__15190567,0,;
|CG,1,5,1,1,1; |CD,2,  63,  5.0000000000000001E-03,1,1,s,0,0,0,  0.0000000000000000E+00,1;
|NT,1,16,1,1,1980,0,0,0.0;       |CC,1,3,1,1;|CP,1,16,1,4,7,32,0,0,1,0;
|CR,1,60,0,  1.0000000000000000E+00,  0.0000000000000000E+00,1,4,mbar;|CN,1,27,0,0,0,15,pressure_Vacuum,0,;
|Cb,1, 117,1,0,    1,         1,         0,      9608,         0,      9608,1,  2.0440300000000000E+03,  1.2416717060000000E+09,;
|CS,1,      9619,         1,�oD	�nD6�nD)�nD�
```

Line breaks are introduced above only for readability. Most of the markers
introduce blocks of text, while the block identified by `|CS` contains binary
sample data. The format supports storage of _multiple data sets (channels)_ in a
single file. The channels may be ordered in _multiplex_ mode (ordering with
respect to time) or _block_ mode (ordering with respect to channels).

## Marker model

The markers (keys) are introduced by `"|" = 0x7c` followed by two uppercase
letters. There are _two types_ of markers distinguished by the first letter:

1. _critical_ markers: introduced by `|C`
2. _noncritical_ markers: introduced by `|N`

The second letter represents further details of the specific key. While the
_noncritical_ keys are optional, a _.raw_ file cannot be decoded correctly if a
_critical_ marker is misinterpreted, invalid, or damaged.

The second uppercase letter is followed by the first comma and the _version_ of
the key starting from `1`. After the next comma, a text-encoded integer
specifies the length of the entire block, i.e. the number of bytes between the
following comma and the terminating semicolon. The remaining block structure is
key-specific and may contain different numbers of parameters.

The format allows for carriage returns (`CR = 0x0d`) and line feeds
(`LF = 0x0a`) between keys, i.e. between the block-terminating semicolon and the
pipe character of the next key.

## Critical markers

| marker | description |
|--------|-------------|
| CF     | format version and processor |
| CK     | start of group of keys, indicates correct or incorrect closure of the measurement series |
| CB     | defines a group of channels |
| CT     | text definition including group association index |
| CG     | introduces group of components corresponding to CC keys |
| CD1,2  | old/new version of abscissa description |
| CZ     | scaling of z-axis for segments |
| CC     | start of a component |
| CP     | information about buffer, datatype and samples of a component |
| Cb     | buffer description |
| CR     | permissible range of values in a component |
| CN     | name and comment of a channel |
| CS     | raw binary data |
| CI     | single numerical value including unit |
| Ca     | add reference key |

## Noncritical markers

| marker | description |
|--------|-------------|
| NO     | origin of data |
| NT     | timestamp of trigger |
| ND     | display properties |
| NU     | user defined key |
| Np     | property of a channel |
| NE     | extraction rule for channels from BUS data |

## Ordering rules

The format loosely defines some rules for the ordering of markers in the file
stream. The rules for critical keys include:

- _CK_ has to follow _CF_
- _CK_ may be followed by any number of _CG_ blocks
- each _CG_ has to be followed by any number of component sequences made of
  _CC_, _CP_, optional _CR_, optional _ND_, and terminated by either _CS_ or
  the start of a new group, component, text field, or buffer