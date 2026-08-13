
# use some C++ STL libraries
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool

cdef extern from "imc_raw.hpp" namespace "imc":

  cdef struct channel_metadata:
    int schema_version
    string uuid
    string name
    string source_name
    string comment
    string origin
    string origin_comment
    string description
    string language_code
    string codepage
    string y_name
    string y_unit
    string x_name
    string x_unit
    string group_name
    string group_comment
    int dimension
    int x_numeric_type
    int y_numeric_type
    int x_significant_bits
    int y_significant_bits
    unsigned long long sample_count
    unsigned long long group_index
    bool has_group
    double trigger_time
    double absolute_trigger_time
    double x_step_width
    double x_offset
    double x_factor
    double x_scaling_offset
    double y_factor
    double y_offset
    int kind_code()

  cdef struct channel_events:
    bool numeric
    vector[double] timestamps
    vector[string] texts
    vector[unsigned long int] counts
    vector[double] xstarts
    vector[double] xstepwidths
    vector[double] yvalues

  cdef struct channel_event_chunk:
    bool numeric
    vector[double] timestamps
    vector[string] texts
    vector[unsigned long int] counts
    vector[double] xstarts
    vector[double] xstepwidths
    vector[double] yvalues
    unsigned long int start
    unsigned long int count

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

    # get typed channel metadata without sample data
    channel_metadata get_channel_metadata(string uuid) except +
    vector[channel_metadata] get_channels_metadata() except +

    # get length of a channel
    unsigned long int get_channel_length(string uuid) except +

    # get numeric type of a channel
    int get_channel_numeric_type(string uuid) except +

    # identify whether a channel uses any event-native representation
    bool is_event_channel(string uuid) except +

    # read a chunk of channel data
    channel_chunk read_channel_chunk(string uuid, unsigned long int start, unsigned long int count, bool include_x, bool raw_mode) except +

    # read full TSA event payloads
    channel_events get_channel_events(string uuid) except +

    # read a chunk of TSA event payloads
    channel_event_chunk read_channel_event_chunk(string uuid, unsigned long int start, unsigned long int count) except +

    # print single channel/all channels
    void print_channel(string channeluuid, string outputdir, char delimiter, unsigned long int chunk_size) except +
    void print_channels(string outputdir, char delimiter, unsigned long int chunk_size) except +
    void print_table(string outputfile) except +
