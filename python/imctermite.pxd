
# use some C++ STL libraries
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool

cdef extern from "lib/imc_raw.hpp" namespace "imc":

  cdef struct channel_chunk:
    vector[unsigned char] x_bytes
    vector[unsigned char] y_bytes
    unsigned long int start
    unsigned long int count
    bool has_x
    int x_type
    int y_type

  cdef cppclass cppimctermite "imc::raw":

    # constructor(s)
    cppimctermite() except +
    cppimctermite(string rawfile) except +

    # provide raw file
    void set_file(string rawfile) except +

    # get JSON list of channels
    vector[string] get_channels(bool json, bool data) except +

    # get length of a channel
    unsigned long int get_channel_length(string uuid) except +

    # get numeric type of a channel
    int get_channel_numeric_type(string uuid) except +

    # read a chunk of channel data
    channel_chunk read_channel_chunk(string uuid, unsigned long int start, unsigned long int count, bool include_x, bool raw_mode) except +

    # print single channel/all channels
    void print_channel(string channeluuid, string outputdir, char delimiter) except +
    void print_channels(string outputdir, char delimiter) except +
    void print_table(string outputfile) except +
