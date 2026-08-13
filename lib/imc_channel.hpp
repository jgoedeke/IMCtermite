//---------------------------------------------------------------------------//

#ifndef IMCCHANNEL
#define IMCCHANNEL

#include "imc_datatype.hpp"
#include "imc_conversion.hpp"
#include "imc_block.hpp"
#include "imc_metadata.hpp"
#include <functional>
#include <sstream>
#include <math.h>
#include <algorithm>
#include <chrono>
#include <ctime>
#include <time.h>
#include <cstring>
#if defined(__linux__) || defined(__APPLE__)
#include <iconv.h>
#endif

//---------------------------------------------------------------------------//

namespace imc
{
  inline std::time_t utc_timegm(std::tm* value)
  {
#if defined(__WIN32__) || defined(_WIN32)
    return _mkgmtime(value);
#else
    return timegm(value);
#endif
  }

  inline std::string escape_json_string(const std::string& value)
  {
    static const char* hex = "0123456789abcdef";
    std::string escaped;
    escaped.reserve(value.size());

    for ( unsigned char ch : value )
    {
      switch ( ch )
      {
        case '"': escaped += "\\\""; break;
        case '\\': escaped += "\\\\"; break;
        case '\b': escaped += "\\b"; break;
        case '\f': escaped += "\\f"; break;
        case '\n': escaped += "\\n"; break;
        case '\r': escaped += "\\r"; break;
        case '\t': escaped += "\\t"; break;
        default:
          if ( ch < 0x20 )
          {
            escaped += "\\u00";
            escaped.push_back(hex[(ch >> 4) & 0x0f]);
            escaped.push_back(hex[ch & 0x0f]);
          }
          else
          {
            escaped.push_back(static_cast<char>(ch));
          }
      }
    }

    return escaped;
  }

  struct tsa_event
  {
    double timestamp;
    std::string text;
  };

  struct tsa_event_descriptor
  {
    uint64_t raw_timestamp;
    size_t text_offset;
    size_t text_length;
  };

  struct tsa_index_data
  {
    std::vector<unsigned char> logical_stream;
    std::vector<tsa_event_descriptor> events;
  };

  struct numeric_event_descriptor
  {
    unsigned long int start = 0;
    unsigned long int count = 0;
    double timestamp = 0.0;
    double xstart = 0.0;
    double xstepwidth = 1.0;
  };

  inline uint16_t read_tsa_u16(const unsigned char* data)
  {
    return static_cast<uint16_t>(data[0])
      | (static_cast<uint16_t>(data[1]) << 8);
  }

  inline uint64_t read_tsa_u48(const unsigned char* data)
  {
    uint64_t value = 0;
    for ( int index = 0; index < 6; ++index )
    {
      value |= static_cast<uint64_t>(data[index]) << (index * 8);
    }
    return value;
  }

      inline uint32_t read_le_u32(const unsigned char* data)
      {
        return static_cast<uint32_t>(data[0])
          | (static_cast<uint32_t>(data[1]) << 8)
          | (static_cast<uint32_t>(data[2]) << 16)
          | (static_cast<uint32_t>(data[3]) << 24);
      }

      inline double read_le_double(const unsigned char* data)
      {
        double value = 0.0;
        std::memcpy(&value, data, sizeof(double));
        return value;
      }

      inline std::vector<numeric_event_descriptor> parse_imc2_numeric_event_index(
        const unsigned char* data,
        size_t size
      )
      {
        static const size_t entry_size = 72;

        if ( size == 0 )
        {
          return {};
        }

        if ( size % entry_size != 0 )
        {
          throw std::runtime_error("invalid IMC2 numeric event index: unexpected CV1 payload size");
        }

        std::vector<numeric_event_descriptor> events;
        events.reserve(size / entry_size);

        unsigned long int start = 0;
        for ( size_t offset = 0; offset < size; offset += entry_size )
        {
          numeric_event_descriptor event;
          event.start = start;
          event.count = read_le_u32(data + offset + 4);
          event.timestamp = read_le_double(data + offset + 8);
          event.xstart = read_le_double(data + offset + 32);
          event.xstepwidth = read_le_double(data + offset + 56);
          events.push_back(event);
          start += event.count;
        }

        return events;
      }

  inline std::string decode_tsa_text(const unsigned char* data, size_t length)
  {
    static const char* hex = "0123456789ABCDEF";
    std::string text;
    text.reserve(length);

    for ( size_t index = 0; index < length; ++index )
    {
      unsigned char value = data[index];
      switch ( value )
      {
        case '\\': text += "\\\\"; break;
        case '\n': text += "\\n"; break;
        case '\r': text += "\\r"; break;
        case '\t': text += "\\t"; break;
        default:
          if ( value >= 0x20 && value <= 0x7e )
          {
            text.push_back(static_cast<char>(value));
          }
          else
          {
            text += "\\x";
            text.push_back(hex[(value >> 4) & 0x0f]);
            text.push_back(hex[value & 0x0f]);
          }
          break;
      }
    }

    return text;
  }

  inline bool try_parse_tsa_logical_stream(const unsigned char* data,
                                           size_t size,
                                           std::vector<tsa_event_descriptor>& events,
                                           std::string* failure = nullptr)
  {
    events.clear();
    size_t cursor = 0;
    while ( cursor + 2 <= size )
    {
      uint16_t length = read_tsa_u16(data + cursor);
      if ( length == 0 )
      {
        if ( cursor + 4 <= size
          && read_tsa_u16(data + cursor + 2) == 0 )
        {
          cursor += 4;
          continue;
        }
        return true;
      }

      if ( length < 8 )
      {
        if ( failure != nullptr ) *failure = "invalid TSA payload: sample length shorter than header";
        return false;
      }

      size_t padded_length = (length + 3U) & ~static_cast<size_t>(3U);
      if ( cursor + padded_length > size )
      {
        if ( failure != nullptr ) *failure = "invalid TSA payload: truncated sample";
        return false;
      }

      tsa_event_descriptor descriptor;
      descriptor.raw_timestamp = read_tsa_u48(data + cursor + 2);
      descriptor.text_offset = cursor + 8;
      descriptor.text_length = length - 8;
      events.push_back(descriptor);

      cursor += padded_length;
    }

    return true;
  }

  inline tsa_index_data build_tsa_index(const unsigned char* data, size_t size)
  {
    tsa_index_data index;
    index.logical_stream.reserve(size);
    size_t initial_logical_skip = 0;

    for ( size_t cluster_start = 0; cluster_start < size; cluster_start += 512 )
    {
      size_t remaining = size - cluster_start;
      if ( remaining < 4 )
      {
        throw std::runtime_error("invalid TSA payload: truncated sync header");
      }

      uint16_t synch_last = read_tsa_u16(data + cluster_start);
      uint16_t first_sample_offset = read_tsa_u16(data + cluster_start + 2);
      if ( cluster_start == 0 && first_sample_offset >= 4 )
      {
        initial_logical_skip = static_cast<size_t>(first_sample_offset - 4U);
      }
      if ( synch_last > index.logical_stream.size() )
      {
        index.logical_stream.clear();
      }
      else if ( synch_last > 0 )
      {
        index.logical_stream.resize(index.logical_stream.size() - synch_last);
      }

      size_t cluster_end = (std::min)(cluster_start + static_cast<size_t>(512), size);
      index.logical_stream.insert(index.logical_stream.end(), data + cluster_start + 4, data + cluster_end);
    }

    if ( initial_logical_skip > 0 )
    {
      if ( initial_logical_skip >= index.logical_stream.size() )
      {
        throw std::runtime_error("invalid TSA payload: initial sample offset exceeds logical stream");
      }
      index.logical_stream.erase(
        index.logical_stream.begin(),
        index.logical_stream.begin() + static_cast<std::ptrdiff_t>(initial_logical_skip)
      );
    }

    std::string parse_failure;
    if ( try_parse_tsa_logical_stream(
      index.logical_stream.data(),
      index.logical_stream.size(),
      index.events,
      &parse_failure
    ) )
    {
      return index;
    }

    // Some IMC3 TSA payloads begin with a truncated fragment before the first
    // full event record. When the initial parse fails, search the first cluster
    // for the earliest full-event boundary and rebuild the logical stream from
    // there instead of rejecting the whole channel.
    size_t best_offset = 0;
    size_t best_event_count = 0;
    std::vector<tsa_event_descriptor> candidate_events;
    size_t search_limit = (std::min)(static_cast<size_t>(508), index.logical_stream.size());
    for ( size_t offset = 1; offset < search_limit; ++offset )
    {
      if ( try_parse_tsa_logical_stream(
        index.logical_stream.data() + offset,
        index.logical_stream.size() - offset,
        candidate_events
      ) )
      {
        if ( !candidate_events.empty()
          && (candidate_events.size() > best_event_count
            || (candidate_events.size() == best_event_count && (best_offset == 0 || offset < best_offset))) )
        {
          best_offset = offset;
          best_event_count = candidate_events.size();
          index.events = candidate_events;
        }
      }
    }

    if ( best_offset > 0 )
    {
      index.logical_stream.erase(index.logical_stream.begin(), index.logical_stream.begin() + static_cast<std::ptrdiff_t>(best_offset));
      return index;
    }

    throw std::runtime_error(parse_failure);
  }

  inline std::vector<tsa_event> decode_tsa_event_slice(const std::vector<unsigned char>& logical_stream,
                                                       const std::vector<tsa_event_descriptor>& descriptors,
                                                       double factor, double offset,
                                                       unsigned long int start,
                                                       unsigned long int count)
  {
    if ( count == 0 )
    {
      return {};
    }

    size_t start_index = static_cast<size_t>(start);
    if ( start_index >= descriptors.size() )
    {
      return {};
    }

    size_t available = descriptors.size() - start_index;
    size_t actual_count = (std::min)(available, static_cast<size_t>(count));

    std::vector<tsa_event> events;
    events.reserve(actual_count);
    for ( size_t index = 0; index < actual_count; ++index )
    {
      const tsa_event_descriptor& descriptor = descriptors[start_index + index];
      tsa_event event;
      event.timestamp = static_cast<double>(descriptor.raw_timestamp) * factor + offset;
      event.text = decode_tsa_text(logical_stream.data() + descriptor.text_offset, descriptor.text_length);
      events.push_back(std::move(event));
    }

    return events;
  }

  inline std::vector<tsa_event> decode_tsa_events(const unsigned char* data, size_t size,
                                                  double factor, double offset)
  {
    tsa_index_data index = build_tsa_index(data, size);
    return decode_tsa_event_slice(index.logical_stream, index.events, factor, offset, 0,
                                  static_cast<unsigned long int>(index.events.size()));
  }

  inline std::vector<tsa_event> decode_tsa_events_range(const unsigned char* data, size_t size,
                                                        double factor, double offset,
                                                        unsigned long int start,
                                                        unsigned long int count)
  {
    tsa_index_data index = build_tsa_index(data, size);
    return decode_tsa_event_slice(index.logical_stream, index.events, factor, offset, start, count);
  }

  inline std::string join_stringvec_json(const std::vector<std::string>& values)
  {
    std::stringstream ss;
    ss << "[";
    for ( size_t index = 0; index < values.size(); ++index )
    {
      if ( index > 0 )
      {
        ss << ",";
      }
      ss << "\"" << escape_json_string(values[index]) << "\"";
    }
    ss << "]";
    return ss.str();
  }

  inline std::string join_doublevec_json(const std::vector<double>& values, int prec = 17)
  {
    std::stringstream ss;
    ss << "[";
    ss << std::setprecision(prec);
    for ( size_t index = 0; index < values.size(); ++index )
    {
      if ( index > 0 )
      {
        ss << ",";
      }
      ss << values[index];
    }
    ss << "]";
    return ss.str();
  }

  inline std::string escape_csv_field(const std::string& value, char sep)
  {
    bool needs_quotes = false;
    std::string escaped;
    escaped.reserve(value.size());

    for ( char ch : value )
    {
      if ( ch == '"' )
      {
        escaped += "\"\"";
        needs_quotes = true;
      }
      else
      {
        if ( ch == sep || ch == '\n' || ch == '\r' )
        {
          needs_quotes = true;
        }
        escaped.push_back(ch);
      }
    }

    if ( sep == ' ' )
    {
      return escaped;
    }

    return needs_quotes ? std::string("\"") + escaped + std::string("\"") : escaped;
  }

  struct channel_chunk {
    std::vector<unsigned char> x_bytes;
    std::vector<unsigned char> y_bytes;
    unsigned long int start;
    unsigned long int count;
    bool has_x;
    int x_type;
    int y_type;
  };

  using channel_chunk_reader = std::function<channel_chunk(unsigned long int, unsigned long int, bool, bool)>;
  using numeric_event_value_reader = std::function<std::vector<double>(unsigned long int, unsigned long int)>;

  struct component_env
  {
    std::string uuid_;
    // required channel components for CG channels only
    std::string CCuuid_, CPuuid_;
    // optional channel components for CG channels only
    std::string CDuuid_, NTuuid_;
    std::string Cbuuid_, CRuuid_;

    // reset all members
    void reset()
    {
      uuid_.clear();
      CCuuid_.clear();
      CPuuid_.clear();
      CDuuid_.clear();
      Cbuuid_.clear();
      CRuuid_.clear();
      NTuuid_.clear();
    }
  };

  // collect uuid's of blocks required for full channel reconstruction
  struct channel_env
  {
    // define unique identifer for channel_env
    std::string uuid_;

    // collect common affiliate blocks for every channel
    std::string NOuuid_, NLuuid_;
    // collect affiliate blocks for a single channel
    // channel types
    std::string CBuuid_, CGuuid_, CIuuid_, CTuuid_;
    std::string CNuuid_, CDuuid_, NTuuid_;
    std::string CSuuid_;
    std::string CVuuid_, Cvuuid_;

    component_env compenv1_;
    component_env compenv2_;


    // reset all members
    void reset()
    {
      uuid_.clear();
      NOuuid_.clear();
      NLuuid_.clear();
      CBuuid_.clear();
      CGuuid_.clear();
      CIuuid_.clear();
      CTuuid_.clear();
      CNuuid_.clear();
      CDuuid_.clear();
      NTuuid_.clear();
      CSuuid_.clear();
      CVuuid_.clear();
      Cvuuid_.clear();
      compenv1_.reset();
      compenv2_.reset();
    }

    // get info
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"uuid:"<<uuid_<<"\n"
        <<std::setw(width)<<std::left<<"NOuuid:"<<NOuuid_<<"\n"
        <<std::setw(width)<<std::left<<"NLuuid:"<<NLuuid_<<"\n"
        //
        <<std::setw(width)<<std::left<<"CBuuid:"<<CBuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CGuuid:"<<CGuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CIuuid:"<<CIuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CTuuid:"<<CTuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CNuuid:"<<CNuuid_<<"\n"
        //
        <<std::setw(width)<<std::left<<"CCuuid:"<<compenv1_.CCuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CPuuid:"<<compenv1_.CPuuid_<<"\n"
        //
        <<std::setw(width)<<std::left<<"CDuuid:"<<compenv1_.CDuuid_<<"\n"
        <<std::setw(width)<<std::left<<"Cbuuid:"<<compenv1_.Cbuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CRuuid:"<<compenv1_.CRuuid_<<"\n"
        <<std::setw(width)<<std::left<<"NTuuid:"<<compenv1_.NTuuid_<<"\n"
        <<std::setw(width)<<std::left<<"Cvuuid:"<<Cvuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CVuuid:"<<CVuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CSuuid:"<<CSuuid_<<"\n";
      return ss.str();
    }

    // get JSON info string
    std::string get_json()
    {
      std::stringstream ss;
      ss<<"{"<<"\"uuid\":\""<<uuid_
             <<"\",\"NOuuid\":\""<<NOuuid_
             <<"\",\"NLuuid\":\""<<NLuuid_
             <<"\",\"CBuuid\":\""<<CBuuid_
             <<"\",\"CGuuid\":\""<<CGuuid_
             <<"\",\"CIuuid\":\""<<CIuuid_
             <<"\",\"CTuuid\":\""<<CTuuid_
             <<"\",\"CNuuid\":\""<<CNuuid_
             <<"\",\"CCuuid\":\""<<compenv1_.CCuuid_
             <<"\",\"CPuuid\":\""<<compenv1_.CPuuid_
             <<"\",\"CDuuid\":\""<<compenv1_.CDuuid_
             <<"\",\"Cbuuid\":\""<<compenv1_.Cbuuid_
             <<"\",\"CRuuid\":\""<<compenv1_.CRuuid_
             <<"\",\"NTuuid\":\""<<compenv1_.NTuuid_
             <<"\",\"Cvuuid\":\""<<Cvuuid_
             <<"\",\"CVuuid\":\""<<CVuuid_
             <<"\",\"CSuuid\":\""<<CSuuid_
             <<"\"}";
      return ss.str();
    }
  };

  // adjust stream object
  void customize_stream(std::ostream& stout, int prec, bool fixed)
  {
    if ( fixed )
    {
      stout<<std::setprecision(prec)<<std::fixed;
    }
    else
    {
      stout<<std::setprecision(prec);
    }
  }

  // given a list of numeric objects, join it into a string
  template<typename dt>
  std::string joinvec(std::vector<dt> myvec, unsigned long int limit = 10, int prec = 10, bool fixed = true)
  {
    // include entire list for limit = 0
    unsigned long int myvecsize = (unsigned long int)myvec.size();
    limit = (limit == 0) ? myvecsize : limit;

    std::stringstream ss;
    ss<<"[";
    if ( myvec.size() <= limit )
    {
      for ( dt el: myvec )
      {
        customize_stream(ss,prec,fixed);
        ss<<el<<",";
      }
    }
    else
    {
      unsigned long int heals = limit/2;
      for ( unsigned long int i = 0; i < heals; i++ )
      {
        customize_stream(ss,prec,fixed);
        ss<<myvec[i]<<",";
      }
      ss<<"...";
      for ( unsigned long int i = myvecsize-heals; i < myvecsize; i++ )
      {
        customize_stream(ss,prec,fixed);
        ss<<myvec[i]<<",";
      }
    }
    std::string sumstr = ss.str();
    if ( sumstr.size() > 1 ) sumstr.pop_back();
    sumstr += std::string("]");
    return sumstr;
  }

  #if defined(__linux__) || defined(__APPLE__)
  // convert encoding of any descriptions, channel-names, units etc.
  class iconverter
  {
    std::string in_enc_, out_enc_;
    iconv_t cd_;
    size_t out_buffer_size_;

    public:

      iconverter(std::string in_enc, std::string out_enc, size_t out_buffer_size = 1024) :
        in_enc_(in_enc), out_enc_(out_enc), out_buffer_size_(out_buffer_size)
      {
        // allocate descriptor for character set conversion
        // (https://man7.org/linux/man-pages/man3/iconv_open.3.html)
        cd_ = iconv_open(out_enc.c_str(), in_enc.c_str());

        if ( (iconv_t)-1 == cd_ )
        {
          if ( errno == EINVAL )
          {
            std::string errmsg = std::string("The encoding conversion from ") + in_enc
              + std::string(" to ") + out_enc + std::string(" is not supported by the implementation.");
            throw std::runtime_error(errmsg);
          }
        }
      }

      void convert(std::string &astring)
      {
        if ( astring.empty() ) return;

        std::vector<char> in_buffer(astring.begin(),astring.end());
        char *inbuf = &in_buffer[0];
        size_t inbytes = in_buffer.size();

        std::vector<char> out_buffer(out_buffer_size_);
        char *outbuf = &out_buffer[0];
        size_t outbytes = out_buffer.size();

        // perform character set conversion
        // ( - https://man7.org/linux/man-pages/man3/iconv.3.html
        //   - https://www.ibm.com/docs/en/zos/2.2.0?topic=functions-iconv-code-conversion )
        while ( inbytes > 0 )
        {
          size_t res = iconv(cd_,&inbuf,&inbytes,&outbuf,&outbytes);

          if ( (size_t)-1 == res )
          {
            std::string errmsg;
            if ( errno == EILSEQ )
            {
              errmsg = std::string("An invalid multibyte sequence is encountered in the input.");
              throw std::runtime_error(errmsg);
            }
            else if ( errno == EINVAL )
            {
              errmsg = std::string("An incomplete multibyte sequence is encountered in the input")
                     + std::string(" and the input byte sequence terminates after it.");
            }
            else if ( errno == E2BIG )
            {
              errmsg = std::string("The output buffer has no more room for the next converted character.");
            }
            throw std::runtime_error(errmsg);
          }
        }

        std::string outstring(out_buffer.begin(),out_buffer.end()-outbytes);
        astring = outstring;
      }
  };
  #elif defined(__WIN32__) || defined(_WIN32)
  class iconverter
  {
    public:
      iconverter(std::string in_enc, std::string out_enc, size_t out_buffer_size = 1024) {}
      void convert(std::string &astring) {}
  };
  #endif

  struct component_group
  {
    imc::component CC_;
    imc::packaging CP_;
    imc::abscissa CD_;
    imc::buffer Cb_;
    imc::range CR_;
    imc::channelobj CN_;
    imc::triggertime NT_;
    bool has_cd_;
    bool has_cr_;

    component_env compenv_;

    // Constructor to parse the associated blocks
    component_group(component_env &compenv, std::map<std::string, imc::block>* blocks, const unsigned char* buffer)
        : has_cd_(false), has_cr_(false), compenv_(compenv)
    {
        if (blocks->count(compenv.CCuuid_) == 1)
        {
            CC_.parse(buffer, blocks->at(compenv.CCuuid_).get_parameters());
        }
        if (blocks->count(compenv.CPuuid_) == 1)
        {
            CP_.parse(buffer, blocks->at(compenv.CPuuid_).get_parameters());
        }
        if (blocks->count(compenv.CDuuid_) == 1)
        {
            CD_.parse(buffer, blocks->at(compenv.CDuuid_).get_parameters());
            has_cd_ = true;
        }
        if (blocks->count(compenv.Cbuuid_) == 1)
        {
            Cb_.parse(buffer, blocks->at(compenv.Cbuuid_).get_parameters());
        }
        if (blocks->count(compenv.CRuuid_) == 1)
        {
            CR_.parse(buffer, blocks->at(compenv.CRuuid_).get_parameters());
            has_cr_ = true;
        }
        if (blocks->count(compenv.NTuuid_) == 1)
        {
            NT_.parse(buffer, blocks->at(compenv.NTuuid_).get_parameters());
        }
    }
  };


  // channel
  struct channel
  {
    // associated environment of blocks and map of blocks
    channel_env chnenv_;
    std::map<std::string,imc::block>* blocks_;
    const unsigned char* buffer_;
    channel_chunk_reader chunk_reader_;
    numeric_event_value_reader numeric_event_value_reader_;

    imc::origin_data NO_;
    imc::language NL_;
    imc::text CT_;
    imc::groupobj CB_;
    imc::datafield CG_;
    imc::channelobj CN_;

    // collect meta-data of channels according to env,
    // just everything valueable in here
    // TODO: is this necessary?
    std::string uuid_;
    std::string name_, comment_;
    std::string origin_, origin_comment_, text_;
    std::chrono::system_clock::time_point trigger_time_, absolute_trigger_time_;
    double trigger_time_frac_secs_;
    std::string language_code_, codepage_;
    std::string yname_, yunit_;
    std::string xname_, xunit_;
    double xstepwidth_, xstart_;
    int xprec_;
    int dimension_;

    // buffer and data
    int xsignbits_, xnum_bytes_;
    int ysignbits_, ynum_bytes_;
    // unsigned long int byte_offset_;
    unsigned long int xbuffer_offset_, ybuffer_offset_;
    unsigned long int xbuffer_size_, ybuffer_size_;
    long int addtime_;
    imc::numtype xdatatp_, ydatatp_;
    std::vector<imc::datatype> xdata_, ydata_;
    std::vector<std::string> textdata_;
    const unsigned char* tsa_raw_data_;
    unsigned long int tsa_raw_size_;
    std::vector<unsigned char> tsa_logical_stream_;
    std::vector<tsa_event_descriptor> tsa_event_index_;
    std::vector<numeric_event_descriptor> numeric_event_index_;
    bool tsa_index_built_;
    bool tsa_loaded_;
    unsigned long int numeric_event_total_samples_;

    // range, factor and offset
    double xfactor_, yfactor_;
    double xoffset_, yoffset_;
    
    unsigned long int number_of_samples_ = 0;

    // group reference the channel belongs to
    unsigned long int group_index_;
    std::string group_uuid_, group_name_, group_comment_;

    channel():
      blocks_(nullptr), buffer_(nullptr),
      trigger_time_frac_secs_(0.0),
      xstepwidth_(1.0), xstart_(0.0), xprec_(0), dimension_(0),
      xsignbits_(0), xnum_bytes_(0), ysignbits_(0), ynum_bytes_(0),
      xbuffer_offset_(0), ybuffer_offset_(0), xbuffer_size_(0), ybuffer_size_(0),
      addtime_(0), xdatatp_(numtype::unsigned_byte), ydatatp_(numtype::unsigned_byte),
      tsa_raw_data_(nullptr), tsa_raw_size_(0), tsa_index_built_(false), tsa_loaded_(false),
      numeric_event_total_samples_(0),
      xfactor_(1.), yfactor_(1.), xoffset_(0.), yoffset_(0.),
      number_of_samples_(0), group_index_(static_cast<unsigned long int>(-1))
    {}

    // constructor takes channel's block environment
    channel(channel_env &chnenv, std::map<std::string,imc::block>* blocks,
                                 const unsigned char* buffer):
      chnenv_(chnenv), blocks_(blocks), buffer_(buffer),
      trigger_time_frac_secs_(0.0),
      xstepwidth_(1.0), xstart_(0.0), xprec_(0), dimension_(0),
      xsignbits_(0), xnum_bytes_(0), ysignbits_(0), ynum_bytes_(0),
      xbuffer_offset_(0), ybuffer_offset_(0), xbuffer_size_(0), ybuffer_size_(0),
      addtime_(0), xdatatp_(numtype::unsigned_byte), ydatatp_(numtype::unsigned_byte),
      tsa_raw_data_(nullptr), tsa_raw_size_(0), tsa_index_built_(false), tsa_loaded_(false),
      numeric_event_total_samples_(0),
      xfactor_(1.), yfactor_(1.), xoffset_(0.), yoffset_(0.),
      group_index_(-1)
    {
      // use uuid from CN block
      uuid_ = chnenv_.CNuuid_;

      // extract associated NO data
      if ( blocks_->count(chnenv_.NOuuid_) == 1 )
      {
	NO_.parse(buffer_, blocks_->at(chnenv_.NOuuid_).get_parameters());
	origin_ = NO_.generator_;
	comment_ = NO_.comment_;
      }

      // extract associated NL data
      if ( blocks_->count(chnenv_.NLuuid_) == 1 )
      {
	NL_.parse(buffer_, blocks_->at(chnenv_.NLuuid_).get_parameters());
	codepage_ = NL_.codepage_;
	language_code_ = NL_.language_code_;
      }

      // extract associated CB data
      if ( blocks_->count(chnenv_.CBuuid_) == 1 )
      {
        CB_.parse(buffer_, blocks_->at(chnenv_.CBuuid_).get_parameters());
      }

      // extract associated CT data
      if ( blocks_->count(chnenv_.CTuuid_) == 1 )
      {
        CT_.parse(buffer_, blocks_->at(chnenv_.CTuuid_).get_parameters());
        text_ = CT_.name_ + std::string(" - ")
              + CT_.text_ + std::string(" - ")
              + CT_.comment_;
      }

      // extract associated CN data
      if ( blocks_->count(chnenv_.CNuuid_) == 1 )
      {
        CN_.parse(buffer_, blocks_->at(chnenv_.CNuuid_).get_parameters());
	group_index_ = CN_.group_index_;
	group_name_ = CN_.name_;
	group_comment_ = CN_.comment_;
      }

      if ( !chnenv_.compenv1_.uuid_.empty() && chnenv_.compenv2_.uuid_.empty() )
      {
        // normal dataset (single component)
        // set common NT and CD keys if no others are specified
        if (chnenv_.compenv1_.NTuuid_.empty()) chnenv_.compenv1_.NTuuid_ = chnenv_.NTuuid_;
        if (chnenv_.compenv1_.CDuuid_.empty()) chnenv_.compenv1_.CDuuid_ = chnenv_.CDuuid_;

        // comp_group1 contains y-data, x-data is based on xstepwidth_, xstart_ and the length of y-data
        component_group comp_group1(chnenv_.compenv1_, blocks_, buffer_);
        dimension_ = 1;

        if (!comp_group1.has_cd_)
        {
          throw std::runtime_error("missing CD key for single-component channel " + uuid_);
        }

        xstepwidth_ = comp_group1.CD_.dx_;
        xunit_ = comp_group1.CD_.unit_;
        ybuffer_offset_ = comp_group1.Cb_.offset_buffer_;
        ybuffer_size_ = comp_group1.Cb_.number_bytes_;
        xstart_ = comp_group1.Cb_.x0_;
        name_ = comp_group1.CN_.name_;
        yname_ = comp_group1.CN_.name_;
        comment_ = comp_group1.CN_.comment_;
        ynum_bytes_ = comp_group1.CP_.bytes_;
        ydatatp_ = comp_group1.CP_.numeric_type_;
        ysignbits_ = comp_group1.CP_.signbits_;
        if ( ydatatp_ == numtype::timestamp_ascii )
        {
          if ( name_.empty() )
          {
            name_ = group_name_;
            yname_ = group_name_;
          }
          xname_ = "time";
          xfactor_ = comp_group1.has_cr_ ? comp_group1.CR_.factor_ : 1.0;
          xoffset_ = comp_group1.has_cr_ ? comp_group1.CR_.offset_ : comp_group1.Cb_.x0_;
          xstepwidth_ = xfactor_;
          xstart_ = xoffset_;
          xunit_ = comp_group1.has_cr_ ? comp_group1.CR_.unit_ : std::string("");
          yfactor_ = xfactor_;
          yoffset_ = xoffset_;
          yunit_.clear();
        }
        else if (comp_group1.has_cr_ && ydatatp_ != numtype::two_byte_word_digital)
        {
          yfactor_ = comp_group1.CR_.factor_;
          yoffset_ = comp_group1.CR_.offset_;
          yunit_ = comp_group1.CR_.unit_;
        }
        else
        {
          yfactor_ = 1.0;
          yoffset_ = 0.0;
          yunit_.clear();
        }
        // generate std::chrono::system_clock::time_point type
        std::time_t ts = imc::utc_timegm(&comp_group1.NT_.tms_);
        trigger_time_ = std::chrono::system_clock::from_time_t(ts);
        trigger_time_frac_secs_ = comp_group1.NT_.trigger_time_frac_secs_;
        // calculate absolute trigger-time
        addtime_ = static_cast<long int>(comp_group1.Cb_.add_time_);
        absolute_trigger_time_ = trigger_time_ + std::chrono::seconds(addtime_);
        //                                       + std::chrono::nanoseconds((long int)(trigger_time_frac_secs_*1.e9));
      }
      else if ( !chnenv_.compenv1_.uuid_.empty() && !chnenv_.compenv2_.uuid_.empty() )
      {
        // XY dataset (two components)
        // set common NT and CD keys if no others are specified
        if (chnenv_.compenv1_.NTuuid_.empty()) chnenv_.compenv1_.NTuuid_ = chnenv_.NTuuid_;
        if (chnenv_.compenv1_.CDuuid_.empty()) chnenv_.compenv1_.CDuuid_ = chnenv_.CDuuid_;
        if (chnenv_.compenv2_.NTuuid_.empty()) chnenv_.compenv2_.NTuuid_ = chnenv_.NTuuid_;
        if (chnenv_.compenv2_.CDuuid_.empty()) chnenv_.compenv2_.CDuuid_ = chnenv_.CDuuid_;

        // comp_group1 contains x-data, comp_group2 contains y-data
        component_group comp_group1(chnenv_.compenv1_, blocks_, buffer_);
        component_group comp_group2(chnenv_.compenv2_, blocks_, buffer_);
        dimension_ = 2;

        xbuffer_offset_ = comp_group2.Cb_.offset_buffer_;
        xbuffer_size_ = comp_group2.Cb_.number_bytes_;
        ybuffer_offset_ = comp_group1.Cb_.offset_buffer_;
        ybuffer_size_ = comp_group1.Cb_.number_bytes_;
        xdatatp_ = comp_group2.CP_.numeric_type_;
        xsignbits_ = comp_group2.CP_.signbits_;
        ydatatp_ = comp_group1.CP_.numeric_type_;
        ysignbits_ = comp_group1.CP_.signbits_;
        if (comp_group2.has_cr_ && xdatatp_ != numtype::two_byte_word_digital)
        {
          xfactor_ = comp_group2.CR_.factor_;
          xoffset_ = comp_group2.CR_.offset_;
        }
        else
        {
          xfactor_ = 1.0;
          xoffset_ = 0.0;
        }
        if (comp_group1.has_cr_ && ydatatp_ != numtype::two_byte_word_digital)
        {
          yfactor_ = comp_group1.CR_.factor_;
          yoffset_ = comp_group1.CR_.offset_;
        }
        else
        {
          yfactor_ = 1.0;
          yoffset_ = 0.0;
        }
        // generate std::chrono::system_clock::time_point type
        std::time_t ts = imc::utc_timegm(&comp_group2.NT_.tms_);
        trigger_time_ = std::chrono::system_clock::from_time_t(ts);
        trigger_time_frac_secs_ = comp_group2.NT_.trigger_time_frac_secs_;
        absolute_trigger_time_ = trigger_time_;
      }
      else
      {
        // no datafield
      }

      // start converting binary buffer to imc::datatype
      if ( !chnenv_.CSuuid_.empty() ) init_metadata();

      // convert any non-UTF-8 codepage to UTF-8 and cleanse any text
      convert_encoding();
      cleanse_text();
    }

    void set_chunk_reader(channel_chunk_reader chunk_reader)
    {
      chunk_reader_ = std::move(chunk_reader);
    }

    void set_numeric_event_payload(const std::vector<numeric_event_descriptor>& numeric_event_index,
                                   unsigned long int total_samples,
                                   numeric_event_value_reader value_reader = {})
    {
      numeric_event_index_ = numeric_event_index;
      numeric_event_total_samples_ = total_samples;
      number_of_samples_ = static_cast<unsigned long int>(numeric_event_index_.size());
      numeric_event_value_reader_ = std::move(value_reader);
      xdata_.clear();
      ydata_.clear();
      textdata_.clear();
    }

    bool is_tsa_channel() const
    {
      return ydatatp_ == numtype::timestamp_ascii;
    }

    bool is_numeric_event_channel() const
    {
      return !numeric_event_index_.empty();
    }

    bool is_event_channel() const
    {
      return is_tsa_channel() || is_numeric_event_channel();
    }

    std::string channel_type() const
    {
      return is_event_channel() ? std::string("event") : std::string("numeric");
    }

    channel_metadata metadata() const
    {
      channel_metadata result;
      result.uuid = uuid_;
      result.name = name_.empty() ? group_name_ : name_;
      result.source_name = name_;
      result.comment = comment_;
      result.origin = origin_;
      result.origin_comment = origin_comment_;
      result.description = text_;
      result.language_code = language_code_;
      result.codepage = codepage_;
      result.y_name = yname_;
      result.y_unit = yunit_;
      result.x_name = xname_;
      result.x_unit = xunit_;
      result.group_name = group_name_;
      result.group_comment = group_comment_;
      result.kind = is_tsa_channel()
        ? channel_kind::tsa_event
        : (is_numeric_event_channel() ? channel_kind::numeric_event : channel_kind::numeric);
      result.dimension = dimension_;
      result.x_numeric_type = static_cast<int>(xdatatp_);
      result.y_numeric_type = static_cast<int>(ydatatp_);
      result.x_significant_bits = xsignbits_;
      result.y_significant_bits = ysignbits_;
      result.sample_count = number_of_samples_;
      result.group_index = group_index_;
      result.has_group = group_index_ != static_cast<unsigned long int>(-1);
      result.trigger_time = seconds_since_1980(trigger_time_) + trigger_time_frac_secs_;
      result.absolute_trigger_time = seconds_since_1980(absolute_trigger_time_) + trigger_time_frac_secs_;
      result.x_step_width = xstepwidth_;
      result.x_offset = xstart_;
      result.x_factor = xfactor_;
      result.x_scaling_offset = xoffset_;
      result.y_factor = yfactor_;
      result.y_offset = yoffset_;
      return result;
    }

    void set_tsa_raw_payload(const unsigned char* data, unsigned long int size)
    {
      tsa_raw_data_ = data;
      tsa_raw_size_ = size;
      tsa_logical_stream_.clear();
      tsa_event_index_.clear();
      tsa_index_built_ = false;
      tsa_loaded_ = false;
      xdata_.clear();
      ydata_.clear();
      textdata_.clear();
    }

    void ensure_tsa_index()
    {
      if ( !is_tsa_channel() || tsa_index_built_ )
      {
        return;
      }

      if ( tsa_raw_data_ == nullptr )
      {
        std::vector<imc::parameter> prms = blocks_->at(chnenv_.CSuuid_).get_parameters();
        unsigned long int buffstrt = prms[3].begin();
        tsa_raw_data_ = buffer_ + buffstrt + ybuffer_offset_ + 1;
        tsa_raw_size_ = ybuffer_size_;
      }

      tsa_index_data index = build_tsa_index(tsa_raw_data_, tsa_raw_size_);
      tsa_logical_stream_ = std::move(index.logical_stream);
      tsa_event_index_ = std::move(index.events);
      number_of_samples_ = static_cast<unsigned long int>(tsa_event_index_.size());
      tsa_index_built_ = true;
    }

    void ensure_tsa_loaded()
    {
      if ( !is_tsa_channel() || tsa_loaded_ )
      {
        return;
      }

      ensure_tsa_index();

      std::vector<tsa_event> events = decode_tsa_event_slice(
        tsa_logical_stream_,
        tsa_event_index_,
        xfactor_,
        xoffset_,
        0,
        number_of_samples_
      );
      xdata_.clear();
      ydata_.clear();
      textdata_.clear();
      xdata_.reserve(events.size());
      textdata_.reserve(events.size());
      for ( const tsa_event& event : events )
      {
        xdata_.push_back(imc::datatype(event.timestamp));
        textdata_.push_back(event.text);
      }
      int prec_step = (xfactor_ > 0 ) ? (int)ceil(fabs(log10(xfactor_))) : 10;
      int prec_start = (fabs(xoffset_) > 0 && fabs(xoffset_) < 1.0) ? (int)ceil(fabs(log10(fabs(xoffset_)))) : 0;
      xprec_ = (std::max)(prec_step, prec_start);
      tsa_loaded_ = true;
    }

    std::vector<tsa_event> read_tsa_events(unsigned long int start, unsigned long int count)
    {
      if ( !is_tsa_channel() )
      {
        throw std::runtime_error("channel is numeric; use read_chunk() instead");
      }

      ensure_tsa_index();
      return decode_tsa_event_slice(tsa_logical_stream_, tsa_event_index_, xfactor_, xoffset_, start, count);
    }

    std::vector<numeric_event_descriptor> read_numeric_events(unsigned long int start, unsigned long int count)
    {
      if ( !is_numeric_event_channel() )
      {
        throw std::runtime_error("channel is not a numeric event channel");
      }

      if ( count == 0 )
      {
        return {};
      }

      size_t start_index = static_cast<size_t>(start);
      if ( start_index >= numeric_event_index_.size() )
      {
        return {};
      }

      size_t available = numeric_event_index_.size() - start_index;
      size_t actual_count = (std::min)(available, static_cast<size_t>(count));
      return std::vector<numeric_event_descriptor>(
        numeric_event_index_.begin() + static_cast<long int>(start_index),
        numeric_event_index_.begin() + static_cast<long int>(start_index + actual_count)
      );
    }

    std::vector<double> read_numeric_event_y_values(unsigned long int start, unsigned long int count)
    {
      if ( !is_numeric_event_channel() )
      {
        throw std::runtime_error("channel is not a numeric event channel");
      }

      if ( count == 0 )
      {
        return {};
      }

      if ( numeric_event_value_reader_ )
      {
        return numeric_event_value_reader_(start, count);
      }

      std::vector<double> values;
      std::vector<imc::parameter> prms = blocks_->at(chnenv_.CSuuid_).get_parameters();
      unsigned long int buffstrt = prms[3].begin();
      unsigned long int abs_start = buffstrt + ybuffer_offset_ + 1;

      switch ( ydatatp_ )
      {
        case numtype::unsigned_byte: imc::convert_chunk_to_double<imc_Ubyte>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::signed_byte: imc::convert_chunk_to_double<imc_Sbyte>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::unsigned_short: imc::convert_chunk_to_double<imc_Ushort>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::signed_short: imc::convert_chunk_to_double<imc_Sshort>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::unsigned_long: imc::convert_chunk_to_double<imc_Ulongint>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::signed_long: imc::convert_chunk_to_double<imc_Slongint>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::ffloat: imc::convert_chunk_to_double<imc_float>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::ddouble: imc::convert_chunk_to_double<imc_double>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::two_byte_word_digital: imc::convert_chunk_to_double<imc_digital>(buffer_ + abs_start, start, count, 1.0, 0.0, values); break;
        case numtype::eight_byte_unsigned_long: imc::convert_chunk_to_double<uint64_t>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::six_byte_unsigned_long: imc::convert_chunk_to_double<imc_sixbyte>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        case numtype::eight_byte_signed_long: imc::convert_chunk_to_double<int64_t>(buffer_ + abs_start, start, count, yfactor_, yoffset_, values); break;
        default:
          throw std::runtime_error("Unsupported type for numeric-event reading (Y): " + std::to_string(ydatatp_));
      }

      return values;
    }

    // initialize metadata without loading data
    void init_metadata()
    {
      std::vector<imc::parameter> prms = blocks_->at(chnenv_.CSuuid_).get_parameters();
      if ( prms.size() < 4)
      {
        throw std::runtime_error("CS block is invalid and features to few parameters");
      }

      // extract (channel dependent) part of buffer
      size_t yCSbuffer_size = ybuffer_size_;

      if ( is_tsa_channel() )
      {
        unsigned long int buffstrt = prms[3].begin();
        set_tsa_raw_payload(buffer_ + buffstrt + ybuffer_offset_ + 1, static_cast<unsigned long int>(yCSbuffer_size));
        ensure_tsa_loaded();
        return;
      }

      if ( is_numeric_event_channel() )
      {
        number_of_samples_ = static_cast<unsigned long int>(numeric_event_index_.size());
        if ( ysignbits_ == 0 )
        {
          throw std::runtime_error("invalid IMC2 numeric event channel layout");
        }

        unsigned long int total_values = static_cast<unsigned long int>(yCSbuffer_size / (ysignbits_ / 8));
        if ( total_values != numeric_event_total_samples_ )
        {
          throw std::runtime_error("IMC2 numeric event metadata does not match raw sample count");
        }
        return;
      }

      // determine number of values in buffer
      unsigned long int ynum_values = (unsigned long int)(yCSbuffer_size/(ysignbits_/8));
      if ( ynum_values*(ysignbits_/8) != yCSbuffer_size )
      {
        throw std::runtime_error("CSbuffer and significant bits of y datatype don't match");
      }
      
      number_of_samples_ = ynum_values;

      if (dimension_ ==  1)
      {
        // find appropriate precision for "xdata_" by means of "xstepwidth_"
        int prec_step = (xstepwidth_ > 0 ) ? (int)ceil(fabs(log10(xstepwidth_))) : 10;
        int prec_start = (fabs(xstart_) > 0 && fabs(xstart_) < 1.0) ? (int)ceil(fabs(log10(fabs(xstart_)))) : 0;
        // Use (std::max)(...) to avoid Windows macros (min/max) breaking std::max.
        xprec_ = (std::max)(prec_step, prec_start);
      }
      else if (dimension_ == 2)
      {
        // const unsigned char* xCSbuffer = buffer_ + buffstrt + xbuffer_offset_ + 1;
        size_t xCSbuffer_size = xbuffer_size_;
        unsigned long int xnum_values = (unsigned long int)(xCSbuffer_size/(xsignbits_/8));
        
        if ( xnum_values != ynum_values )
        {
          throw std::runtime_error(
            std::string("x and y data have different number of values")
            + std::string(" (channel uuid='") + uuid_
            + std::string("', name='") + name_
            + std::string("', x_values=") + std::to_string(xnum_values)
            + std::string(", y_values=") + std::to_string(ynum_values)
            + std::string(", x_buffer_size=") + std::to_string(xCSbuffer_size)
            + std::string(", y_buffer_size=") + std::to_string(yCSbuffer_size)
            + std::string(", x_signbits=") + std::to_string(xsignbits_)
            + std::string(", y_signbits=") + std::to_string(ysignbits_)
            + std::string(")")
          );
        }
        xprec_ = 9;
      }
      else
      {
        throw std::runtime_error("unsupported dimension");
      }
    }

    // convert buffer to actual datatype (loads all data)
    void load_all_data()
    {
      if ( is_tsa_channel() )
      {
        ensure_tsa_loaded();
        return;
      }

      if ( chunk_reader_ )
      {
        channel_chunk chunk = read_chunk(0, number_of_samples_, true, false);
        const double* y_ptr = reinterpret_cast<const double*>(chunk.y_bytes.data());
        ydata_.assign(y_ptr, y_ptr + chunk.count);

        const double* x_ptr = reinterpret_cast<const double*>(chunk.x_bytes.data());
        xdata_.assign(x_ptr, x_ptr + chunk.count);
        return;
      }

      std::vector<imc::parameter> prms = blocks_->at(chnenv_.CSuuid_).get_parameters();
      unsigned long int buffstrt = prms[3].begin();
      const unsigned char* yCSbuffer = buffer_ + buffstrt + ybuffer_offset_ + 1;
      size_t yCSbuffer_size = ybuffer_size_;
      unsigned long int ynum_values = number_of_samples_;

      if (dimension_ ==  1)
      {
        process_data(ydata_, ynum_values, ydatatp_, yCSbuffer, yCSbuffer_size);
        for ( unsigned long int i = 0; i < ynum_values; i++ )
        {
          xdata_.push_back(xstart_+(double)i*xstepwidth_);
        }
      }
      else if (dimension_ == 2)
      {
        const unsigned char* xCSbuffer = buffer_ + buffstrt + xbuffer_offset_ + 1;
        size_t xCSbuffer_size = xbuffer_size_;
        process_data(xdata_, ynum_values, xdatatp_, xCSbuffer, xCSbuffer_size);
        process_data(ydata_, ynum_values, ydatatp_, yCSbuffer, yCSbuffer_size);
      }

      transformData(xdata_, xfactor_, xoffset_);
      transformData(ydata_, yfactor_, yoffset_);
    }

    channel_chunk read_chunk(unsigned long int start, unsigned long int count, bool include_x, bool raw_mode)
    {
      if ( is_event_channel() )
      {
        throw std::runtime_error("event channel streaming via iter_channel_numpy is not implemented");
      }

      if ( chunk_reader_ )
      {
        return chunk_reader_(start, count, include_x, raw_mode);
      }

        unsigned long int total_len = number_of_samples_;

        if ( start >= total_len )
        {
            return { {}, {}, start, 0, include_x, 0, 0 };
        }

        unsigned long int end = start + count;
        if ( end > total_len ) end = total_len;
        unsigned long int actual_count = end - start;

        channel_chunk chunk;
        chunk.start = start;
        chunk.count = actual_count;
        chunk.has_x = include_x;
        chunk.x_type = 0;
        chunk.y_type = 0;
        
        std::vector<imc::parameter> prms = blocks_->at(chnenv_.CSuuid_).get_parameters();
        unsigned long int buffstrt = prms[3].begin();

        // Handle Y data
        if (raw_mode) {
            int type = (int)ydatatp_;
            unsigned long int bytes_per_sample = ysignbits_ / 8;
            unsigned long int abs_start = buffstrt + ybuffer_offset_ + 1 + start * bytes_per_sample;
            unsigned long int byte_count = actual_count * bytes_per_sample;
            
            if (type == 13) { // six_byte_unsigned_long -> promote to 8 byte (uint64)
                chunk.y_type = 13;
                chunk.y_bytes.resize(actual_count * 8);
                uint64_t* dest = reinterpret_cast<uint64_t*>(chunk.y_bytes.data());
                for (unsigned long int i = 0; i < actual_count; ++i) {
                    unsigned long int src_idx = abs_start + i * 6;
                    uint64_t val = 0;
                    for (int b = 0; b < 6; ++b) val |= (uint64_t)buffer_[src_idx + b] << (b * 8);
                    dest[i] = val;
                }
            } else {
                chunk.y_type = type;
                chunk.y_bytes.resize(byte_count);
                std::copy(buffer_ + abs_start, buffer_ + abs_start + byte_count, chunk.y_bytes.begin());
            }
        } else {
            // Scaled mode: convert to double
            chunk.y_type = 8; // imc::numtype::ddouble
            chunk.y_bytes.resize(actual_count * sizeof(double));
            std::vector<double> temp_data;
            
            unsigned long int abs_start = buffstrt + ybuffer_offset_ + 1; // Base start
            
            switch (ydatatp_) {
                case numtype::unsigned_byte: imc::convert_chunk_to_double<imc_Ubyte>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::signed_byte: imc::convert_chunk_to_double<imc_Sbyte>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::unsigned_short: imc::convert_chunk_to_double<imc_Ushort>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::signed_short: imc::convert_chunk_to_double<imc_Sshort>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::unsigned_long: imc::convert_chunk_to_double<imc_Ulongint>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::signed_long: imc::convert_chunk_to_double<imc_Slongint>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::ffloat: imc::convert_chunk_to_double<imc_float>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::ddouble: imc::convert_chunk_to_double<imc_double>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::two_byte_word_digital: imc::convert_chunk_to_double<imc_digital>(buffer_ + abs_start, start, actual_count, 1.0, 0.0, temp_data); break;
                case numtype::eight_byte_unsigned_long: imc::convert_chunk_to_double<uint64_t>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::six_byte_unsigned_long: imc::convert_chunk_to_double<imc_sixbyte>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                case numtype::eight_byte_signed_long: imc::convert_chunk_to_double<int64_t>(buffer_ + abs_start, start, actual_count, yfactor_, yoffset_, temp_data); break;
                default: throw std::runtime_error("Unsupported type for scaled chunk reading (Y): " + std::to_string(ydatatp_));
            }
            
            memcpy(chunk.y_bytes.data(), temp_data.data(), temp_data.size() * sizeof(double));
        }

        // Handle X data
        if (include_x) {
            if (dimension_ == 2 && raw_mode) {
                int type = (int)xdatatp_;
                unsigned long int bytes_per_sample = xsignbits_ / 8;
                unsigned long int abs_start = buffstrt + xbuffer_offset_ + 1 + start * bytes_per_sample;
                unsigned long int byte_count = actual_count * bytes_per_sample;
                
                if (type == 13) {
                    chunk.x_type = 13;
                    chunk.x_bytes.resize(actual_count * 8);
                    uint64_t* dest = reinterpret_cast<uint64_t*>(chunk.x_bytes.data());
                    for (unsigned long int i = 0; i < actual_count; ++i) {
                        unsigned long int src_idx = abs_start + i * 6;
                        uint64_t val = 0;
                        for (int b = 0; b < 6; ++b) val |= (uint64_t)buffer_[src_idx + b] << (b * 8);
                        dest[i] = val;
                    }
                } else {
                    chunk.x_type = type;
                    chunk.x_bytes.resize(byte_count);
                    std::copy(buffer_ + abs_start, buffer_ + abs_start + byte_count, chunk.x_bytes.begin());
                }
            } else {
                // Generated X or scaled X
                chunk.x_type = 8; // imc::numtype::ddouble
                chunk.x_bytes.resize(actual_count * sizeof(double));
                double* ptr = reinterpret_cast<double*>(chunk.x_bytes.data());
                
                if (dimension_ == 2) {
                     // Read X from file and scale
                     std::vector<double> temp_data;
                     unsigned long int abs_start = buffstrt + xbuffer_offset_ + 1;
                     switch (xdatatp_) {
                        case numtype::unsigned_byte: imc::convert_chunk_to_double<imc_Ubyte>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::signed_byte: imc::convert_chunk_to_double<imc_Sbyte>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::unsigned_short: imc::convert_chunk_to_double<imc_Ushort>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::signed_short: imc::convert_chunk_to_double<imc_Sshort>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::unsigned_long: imc::convert_chunk_to_double<imc_Ulongint>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::signed_long: imc::convert_chunk_to_double<imc_Slongint>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::ffloat: imc::convert_chunk_to_double<imc_float>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::ddouble: imc::convert_chunk_to_double<imc_double>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::two_byte_word_digital: imc::convert_chunk_to_double<imc_digital>(buffer_ + abs_start, start, actual_count, 1.0, 0.0, temp_data); break;
                        case numtype::eight_byte_unsigned_long: imc::convert_chunk_to_double<uint64_t>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::six_byte_unsigned_long: imc::convert_chunk_to_double<imc_sixbyte>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        case numtype::eight_byte_signed_long: imc::convert_chunk_to_double<int64_t>(buffer_ + abs_start, start, actual_count, xfactor_, xoffset_, temp_data); break;
                        default: throw std::runtime_error("Unsupported type for scaled chunk reading (X): " + std::to_string(xdatatp_));
                    }
                    memcpy(ptr, temp_data.data(), temp_data.size() * sizeof(double));
                } else {
                    // Generated X
                    for (unsigned long int i = 0; i < actual_count; ++i) {
                        ptr[i] = xstart_ + (double)(start + i) * xstepwidth_;
                    }
                }
            }
        }
        return chunk;
    }

    // handle data type conversion
    void process_data(std::vector<imc::datatype>& data_, size_t num_values, numtype datatp_, const unsigned char* CSbuffer, size_t CSbuffer_size)
    {
      // adjust size of data
      data_.resize(num_values);

      // handle data type conversion
      switch (datatp_)
      {
          case numtype::unsigned_byte:
              imc::convert_data_to_type<imc_Ubyte>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::signed_byte:
              imc::convert_data_to_type<imc_Sbyte>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::unsigned_short:
              imc::convert_data_to_type<imc_Ushort>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::signed_short:
              imc::convert_data_to_type<imc_Sshort>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::unsigned_long:
              imc::convert_data_to_type<imc_Ulongint>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::signed_long:
              imc::convert_data_to_type<imc_Slongint>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::ffloat:
              imc::convert_data_to_type<imc_float>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::ddouble:
              imc::convert_data_to_type<imc_double>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::two_byte_word_digital:
              imc::convert_data_to_type<imc_digital>(CSbuffer, CSbuffer_size, data_);
              break;
          case numtype::six_byte_unsigned_long:
              imc::convert_data_to_type<imc_sixbyte>(CSbuffer, CSbuffer_size, data_);
              break;
          default:
              throw std::runtime_error(std::string("unsupported/unknown datatype ") + std::to_string(datatp_));
      }
    }

    void transformData(std::vector<imc::datatype>& data, double factor, double offset) {
        if (factor != 1.0 || offset != 0.0) {
            for (imc::datatype& el : data) {
                double fact = (factor == 0.0) ? 1.0 : factor;
                el = imc::datatype(el.as_double() * fact + offset);
            }
        }
    }

    // convert any description, units etc. to UTF-8 (by default)
    void convert_encoding()
    {
      if ( !codepage_.empty() )
      {
        // construct iconv-compatible name for respective codepage
        std::string cpn = std::string("CP") + codepage_;

        // set up converter
        std::string utf = std::string("UTF-8");
        iconverter conv(cpn,utf);

        conv.convert(name_);
        conv.convert(comment_);
        conv.convert(origin_);
        conv.convert(origin_comment_);
        conv.convert(text_);
        conv.convert(language_code_);
        conv.convert(yname_);
        conv.convert(yunit_);
        conv.convert(xname_);
        conv.convert(xunit_);
        conv.convert(group_name_);
        conv.convert(group_comment_);
      }
    }

    void cleanse_text()
    {
      escape_backslash(name_);
      escape_backslash(comment_);
      escape_backslash(origin_);
      escape_backslash(origin_comment_);
      escape_backslash(text_);
      escape_backslash(language_code_);
      escape_backslash(yname_);
      escape_backslash(yunit_);
      escape_backslash(xname_);
      escape_backslash(xunit_);
      escape_backslash(group_name_);
      escape_backslash(group_comment_);
    }

    void escape_backslash(std::string &text)
    {
      char backslash = 0x5c;
      std::string doublebackslash("\\\\");
      for ( std::string::iterator it = text.begin(); it != text.end(); ++it )
      {
	if ( int(*it) == backslash ) {
	  text.replace(it,it+1,doublebackslash);
	  ++it;
	}
      }
    }

    // get info string
    std::string get_info(int width = 20)
    {
      // prepare printable trigger-time
      std::time_t tt = std::chrono::system_clock::to_time_t(trigger_time_);
      std::time_t att = std::chrono::system_clock::to_time_t(absolute_trigger_time_);

      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"uuid:"<<uuid_<<"\n"
        <<std::setw(width)<<std::left<<"name:"<<name_<<"\n"
        <<std::setw(width)<<std::left<<"comment:"<<comment_<<"\n"
        <<std::setw(width)<<std::left<<"origin:"<<origin_<<"\n"
        <<std::setw(width)<<std::left<<"origin-comment:"<<origin_comment_<<"\n"
        <<std::setw(width)<<std::left<<"description:"<<text_<<"\n"
        <<std::setw(width)<<std::left<<"trigger-time-nt:"<<std::put_time(std::gmtime(&tt),"%FT%T")<<"\n"
        <<std::setw(width)<<std::left<<"trigger-time:"<<std::put_time(std::gmtime(&att),"%FT%T")<<"\n"
        <<std::setw(width)<<std::left<<"language-code:"<<language_code_<<"\n"
        <<std::setw(width)<<std::left<<"codepage:"<<codepage_<<"\n"
        <<std::setw(width)<<std::left<<"yname:"<<yname_<<"\n"
        <<std::setw(width)<<std::left<<"yunit:"<<yunit_<<"\n"
        <<std::setw(width)<<std::left<<"channel-type:"<<channel_type()<<"\n"
        <<std::setw(width)<<std::left<<"datatype:"<<ydatatp_<<"\n"
        <<std::setw(width)<<std::left<<"significant bits:"<<ysignbits_<<"\n"
        <<std::setw(width)<<std::left<<"buffer-offset:"<<ybuffer_offset_<<"\n"
        <<std::setw(width)<<std::left<<"buffer-size:"<<ybuffer_size_<<"\n"
        <<std::setw(width)<<std::left<<"xname:"<<xname_<<"\n"
        <<std::setw(width)<<std::left<<"xunit:"<<xunit_<<"\n"
        <<std::setw(width)<<std::left<<"xstepwidth:"<<xstepwidth_<<"\n"
        <<std::setw(width)<<std::left<<"xoffset:"<<xstart_<<"\n"
        <<std::setw(width)<<std::left<<"factor:"<<yfactor_<<"\n"
        <<std::setw(width)<<std::left<<"offset:"<<yoffset_<<"\n"
        <<std::setw(width)<<std::left<<"group:"<<"("<<group_index_<<","<<group_name_
                                                    <<","<<group_comment_<<")"<<"\n"
        <<std::setw(width)<<std::left<<"ydata:"<<imc::joinvec<imc::datatype>(ydata_,6,9,true)<<"\n"
        <<std::setw(width)<<std::left<<"xdata:"<<imc::joinvec<imc::datatype>(xdata_,6,xprec_,true)<<"\n";
        // <<std::setw(width)<<std::left<<"aff. blocks:"<<chnenv_.get_json()<<"\n";
      return ss.str();
    }

    // provide JSON string of metadata
    std::string get_json(bool include_data = false)
    {
      if ( include_data && ydata_.empty() && number_of_samples_ > 0 && !is_numeric_event_channel() ) {
          load_all_data();
      }
      // prepare printable trigger-time
      std::time_t tt = std::chrono::system_clock::to_time_t(trigger_time_);
      std::time_t att = std::chrono::system_clock::to_time_t(absolute_trigger_time_);

      std::stringstream ss;
            ss<<"{"<<"\"uuid\":\""<<imc::escape_json_string(uuid_)
              <<"\",\"name\":\""<<imc::escape_json_string(name_)
              <<"\",\"comment\":\""<<imc::escape_json_string(comment_)
              <<"\",\"origin\":\""<<imc::escape_json_string(origin_)
              <<"\",\"origin-comment\":\""<<imc::escape_json_string(origin_comment_)
              <<"\",\"description\":\""<<imc::escape_json_string(text_)
             <<"\",\"trigger-time-nt\":\""<<std::put_time(std::gmtime(&tt),"%FT%T")
             <<"\",\"trigger-time\":\""<<std::put_time(std::gmtime(&att),"%FT%T")
              <<"\",\"language-code\":\""<<imc::escape_json_string(language_code_)
              <<"\",\"codepage\":\""<<imc::escape_json_string(codepage_)
              <<"\",\"yname\":\""<<imc::escape_json_string(yname_)
              <<"\",\"yunit\":\""<<imc::escape_json_string(yunit_)
             <<"\",\"channel_type\":\""<<channel_type()
             <<"\",\"datatype\":\""<<ydatatp_
             <<"\",\"significantbits\":\""<<ysignbits_
             <<"\",\"buffer-size\":\""<<ybuffer_size_
              <<"\",\"xname\":\""<<imc::escape_json_string(xname_)
              <<"\",\"xunit\":\""<<imc::escape_json_string(xunit_)
             <<"\",\"xstepwidth\":\""<<xstepwidth_
             <<"\",\"xoffset\":\""<<xstart_
             <<"\",\"factor\":\""<<yfactor_
             <<"\",\"offset\":\""<<yoffset_
             <<"\",\"group\":{"<<"\"index\":\""<<group_index_
                 <<"\",\"name\":\""<<imc::escape_json_string(group_name_)
                 <<"\",\"comment\":\""<<imc::escape_json_string(group_comment_)<<"\""<<"}";
      if ( include_data )
      {
        if ( is_tsa_channel() )
        {
          ensure_tsa_loaded();
          ss<<",\"xdata\":"<<imc::joinvec<imc::datatype>(xdata_,0,xprec_,true)
            <<",\"textdata\":"<<imc::join_stringvec_json(textdata_);
        }
        else if ( is_numeric_event_channel() )
        {
          ss<<",\"events\":[";
          for ( size_t event_index = 0; event_index < numeric_event_index_.size(); ++event_index )
          {
            if ( event_index > 0 )
            {
              ss << ",";
            }

            const numeric_event_descriptor& event = numeric_event_index_[event_index];
            std::vector<double> xvalues(event.count);
            for ( unsigned long int sample_index = 0; sample_index < event.count; ++sample_index )
            {
              xvalues[sample_index] = event.xstart + static_cast<double>(sample_index) * event.xstepwidth;
            }
            std::vector<double> yvalues = read_numeric_event_y_values(event.start, event.count);

            ss << "{"
               << "\"timestamp\":" << std::setprecision(17) << event.timestamp
               << ",\"xstart\":" << event.xstart
               << ",\"xstepwidth\":" << event.xstepwidth
               << ",\"xdata\":" << imc::join_doublevec_json(xvalues)
               << ",\"ydata\":" << imc::join_doublevec_json(yvalues)
               << "}";
          }
          ss << "]";
        }
        else
        {
          ss<<",\"ydata\":"<<imc::joinvec<imc::datatype>(ydata_,0,9,true)
            <<",\"xdata\":"<<imc::joinvec<imc::datatype>(xdata_,0,xprec_,true);
        }
      }
      // ss<<"\",\"aff. blocks\":\""<<chnenv_.get_json()
      ss<<"}";

      return ss.str();
    }
    // print channel
    void print(std::string filename, const char sep = ',', int width = 25, int yprec = 9, unsigned long int chunk_size = 100000)
    {
      std::ofstream fou(filename);

      if ( is_tsa_channel() )
      {
        ensure_tsa_loaded();

        if ( sep == ' ' )
        {
          fou<<std::setw(width)<<std::left<<xname_
             <<std::setw(width)<<std::left<<yname_<<"\n"
             <<std::setw(width)<<std::left<<xunit_
             <<std::setw(width)<<std::left<<yunit_<<"\n";
        }
        else
        {
          fou<<xname_<<sep<<yname_<<"\n"<<xunit_<<sep<<yunit_<<"\n";
        }

        for ( size_t index = 0; index < textdata_.size(); ++index )
        {
          double timestamp = xdata_[index].as_double();
          if ( sep == ' ' )
          {
            fou<<std::setprecision(xprec_)<<std::fixed
               <<std::setw(width)<<std::left<<timestamp
               <<textdata_[index]<<"\n";
          }
          else
          {
            fou<<std::setprecision(xprec_)<<std::fixed<<timestamp
               <<sep
               <<imc::escape_csv_field(textdata_[index], sep)<<"\n";
          }
        }

        fou.close();
        return;
      }

      if ( is_numeric_event_channel() )
      {
        const std::string event_label = "event_index";
        const std::string timestamp_label = "event_timestamp";
        const std::string x_label = xname_.empty() ? std::string("x") : xname_;
        const std::string y_label = yname_.empty()
          ? (group_name_.empty() ? std::string("y") : group_name_)
          : yname_;
        const std::string timestamp_unit = "seconds_since_1980";

        if ( sep == ' ' )
        {
          fou<<std::setw(width)<<std::left<<event_label
             <<std::setw(width)<<std::left<<timestamp_label
             <<std::setw(width)<<std::left<<x_label
             <<std::setw(width)<<std::left<<y_label<<"\n"
             <<std::setw(width)<<std::left<<""
             <<std::setw(width)<<std::left<<timestamp_unit
             <<std::setw(width)<<std::left<<xunit_
             <<std::setw(width)<<std::left<<yunit_<<"\n";
        }
        else
        {
          fou<<event_label<<sep<<timestamp_label<<sep<<x_label<<sep<<y_label<<"\n"
             <<sep<<timestamp_unit<<sep<<xunit_<<sep<<yunit_<<"\n";
        }

        for ( size_t event_index = 0; event_index < numeric_event_index_.size(); ++event_index )
        {
          const numeric_event_descriptor& event = numeric_event_index_[event_index];
          std::vector<double> yvalues = read_numeric_event_y_values(event.start, event.count);
          for ( unsigned long int sample_index = 0; sample_index < event.count; ++sample_index )
          {
            double xvalue = event.xstart + static_cast<double>(sample_index) * event.xstepwidth;
            double yvalue = yvalues[sample_index];
            if ( sep == ' ' )
            {
              fou<<std::setw(width)<<std::left<<event_index
                 <<std::setw(width)<<std::left<<std::setprecision(17)<<event.timestamp
                 <<std::setw(width)<<std::left<<std::setprecision(17)<<xvalue
                 <<std::setw(width)<<std::left<<std::setprecision(17)<<yvalue<<"\n";
            }
            else
            {
              fou<<event_index<<sep
                 <<std::setprecision(17)<<event.timestamp<<sep
                 <<std::setprecision(17)<<xvalue<<sep
                 <<std::setprecision(17)<<yvalue<<"\n";
            }
          }
        }

        fou.close();
        return;
      }

      // header
      if ( sep == ' ' )
      {
        fou<<std::setw(width)<<std::left<<xname_
           <<std::setw(width)<<std::left<<yname_<<"\n"
           <<std::setw(width)<<std::left<<xunit_
           <<std::setw(width)<<std::left<<yunit_<<"\n";
      }
      else
      {
        fou<<xname_<<sep<<yname_<<"\n"<<xunit_<<sep<<yunit_<<"\n";
      }

      // Stream data in chunks
      unsigned long int start = 0;
      while (start < number_of_samples_)
      {
        channel_chunk chunk = read_chunk(start, chunk_size, true, false); // include_x=true, raw_mode=false (scaled)
        
        if (chunk.count == 0) break;
        
        // Extract x and y data from chunk
        const double* x_ptr = reinterpret_cast<const double*>(chunk.x_bytes.data());
        const double* y_ptr = reinterpret_cast<const double*>(chunk.y_bytes.data());
        
        // Write chunk data
        for (unsigned long int i = 0; i < chunk.count; i++)
        {
          if ( sep == ' ' )
          {
            fou<<std::setprecision(xprec_)<<std::fixed
               <<std::setw(width)<<std::left<<x_ptr[i]
               <<std::setprecision(yprec)<<std::fixed
               <<std::setw(width)<<std::left<<y_ptr[i]<<"\n";
          }
          else
          {
            fou<<std::setprecision(xprec_)<<std::fixed<<x_ptr[i]
               <<sep
               <<std::setprecision(yprec)<<std::fixed<<y_ptr[i]<<"\n";
          }
        }
        
        start += chunk.count;
      }

      fou.close();
    }
  };

}

#endif

//---------------------------------------------------------------------------//
