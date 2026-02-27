//---------------------------------------------------------------------------//

#ifndef IMCCHANNEL
#define IMCCHANNEL

#include "imc_datatype.hpp"
#include "imc_conversion.hpp"
#include "imc_block.hpp"
#include <sstream>
#include <math.h>
#include <algorithm>
#include <cstdint>
#include <chrono>
#include <cmath>
#include <ctime>
#include <time.h>
#include <cstring>
#if defined(__linux__) || defined(__APPLE__)
#include <iconv.h>
#elif defined(__WIN32__) || defined(_WIN32)
#define timegm _mkgmtime
#endif

//---------------------------------------------------------------------------//

namespace imc
{
  struct channel_chunk {
    std::vector<unsigned char> x_bytes;
    std::vector<unsigned char> y_bytes;
    unsigned long int start;
    unsigned long int count;
    bool has_x;
    int x_type;
    int y_type;
  };

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
    std::string CBuuid_, CGuuid_, CIuuid_, CTuuid_, Cvuuid_, CVuuid_;
    std::string CNuuid_, CDuuid_, NTuuid_;
    std::string CSuuid_;

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
      Cvuuid_.clear();
      CVuuid_.clear();
      CNuuid_.clear();
      CDuuid_.clear();
      NTuuid_.clear();
      CSuuid_.clear();
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
        <<std::setw(width)<<std::left<<"Cvuuid:"<<Cvuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CVuuid:"<<CVuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CNuuid:"<<CNuuid_<<"\n"
        //
        <<std::setw(width)<<std::left<<"CCuuid:"<<compenv1_.CCuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CPuuid:"<<compenv1_.CPuuid_<<"\n"
        //
        <<std::setw(width)<<std::left<<"CDuuid:"<<compenv1_.CDuuid_<<"\n"
        <<std::setw(width)<<std::left<<"Cbuuid:"<<compenv1_.Cbuuid_<<"\n"
        <<std::setw(width)<<std::left<<"CRuuid:"<<compenv1_.CRuuid_<<"\n"
        <<std::setw(width)<<std::left<<"NTuuid:"<<compenv1_.NTuuid_<<"\n"
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
             <<"\",\"Cvuuid\":\""<<Cvuuid_
             <<"\",\"CVuuid\":\""<<CVuuid_
             <<"\",\"CNuuid\":\""<<CNuuid_
             <<"\",\"CCuuid\":\""<<compenv1_.CCuuid_
             <<"\",\"CPuuid\":\""<<compenv1_.CPuuid_
             <<"\",\"CDuuid\":\""<<compenv1_.CDuuid_
             <<"\",\"Cbuuid\":\""<<compenv1_.Cbuuid_
             <<"\",\"CRuuid\":\""<<compenv1_.CRuuid_
             <<"\",\"NTuuid\":\""<<compenv1_.NTuuid_
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

    // range, factor and offset
    double xfactor_, yfactor_;
    double xoffset_, yoffset_;
    
    unsigned long int number_of_samples_ = 0;
    bool has_event_description_ = false;
    bool has_event_list_ = false;
    bool event_overrides_present_ = false;
    unsigned long int event_list_index_ = 0;
    unsigned long int event_count_declared_ = 0;
    unsigned long int event_count_parsed_ = 0;
    int event_valid_nt_ = 0;
    int event_valid_cd_ = 0;
    int event_valid_cr1_ = 0;
    int event_valid_cr2_ = 0;
    std::vector<imc::event_entry> event_entries_;
    bool trigger_time_from_events_ = false;
    double first_event_time_seconds_ = 0.0;

    static constexpr int EVENT_VALID_BIT_1 = 0x1;
    static constexpr int EVENT_VALID_BIT_2 = 0x2;

    static std::chrono::system_clock::time_point epoch_1980()
    {
      std::tm base = std::tm();
      base.tm_year = 80;
      base.tm_mon = 0;
      base.tm_mday = 1;
      std::time_t ts = timegm(&base);
      return std::chrono::system_clock::from_time_t(ts);
    }

    void apply_event_time_override_if_available()
    {
      if ( !(event_valid_nt_ & EVENT_VALID_BIT_1) || event_entries_.empty() ) return;

      double secs = event_entries_.front().time_seconds_;
      double whole_part = std::floor(secs);
      double frac_part = secs - whole_part;
      if ( frac_part < 0.0 ) frac_part = 0.0;

      trigger_time_ = epoch_1980() + std::chrono::seconds((long long)whole_part);
      absolute_trigger_time_ = trigger_time_;
      trigger_time_frac_secs_ = frac_part;
      trigger_time_from_events_ = true;
      first_event_time_seconds_ = secs;
    }

    template<typename T>
    static double read_scalar_as_double(const unsigned char* ptr)
    {
      T val;
      uint8_t* dst = reinterpret_cast<uint8_t*>(&val);
      for ( size_t i = 0; i < sizeof(T); i++ ) dst[i] = ptr[i];
      return static_cast<double>(val);
    }

    static double read_sample_as_double(numtype t, const unsigned char* ptr)
    {
      switch (t)
      {
        case numtype::unsigned_byte: return read_scalar_as_double<imc_Ubyte>(ptr);
        case numtype::signed_byte: return read_scalar_as_double<imc_Sbyte>(ptr);
        case numtype::unsigned_short: return read_scalar_as_double<imc_Ushort>(ptr);
        case numtype::signed_short: return read_scalar_as_double<imc_Sshort>(ptr);
        case numtype::unsigned_long: return read_scalar_as_double<imc_Ulongint>(ptr);
        case numtype::signed_long: return read_scalar_as_double<imc_Slongint>(ptr);
        case numtype::ffloat: return read_scalar_as_double<imc_float>(ptr);
        case numtype::ddouble: return read_scalar_as_double<imc_double>(ptr);
        case numtype::two_byte_word_digital: return read_scalar_as_double<imc_digital>(ptr);
        case numtype::eight_byte_unsigned_long: return read_scalar_as_double<uint64_t>(ptr);
        case numtype::eight_byte_signed_long: return read_scalar_as_double<int64_t>(ptr);
        case numtype::six_byte_unsigned_long:
        {
          uint64_t val = 0;
          for ( int i = 0; i < 6; i++ ) val |= ((uint64_t)ptr[i] << (8*i));
          return static_cast<double>(val);
        }
        default:
          throw std::runtime_error("Unsupported type for event-aware sample decoding: " + std::to_string(t));
      }
    }

    bool use_event_direct_decode() const
    {
      return has_event_list_ && !event_entries_.empty() && dimension_ == 1;
    }

    void build_event_lookup(unsigned long int start,
                            unsigned long int actual_count,
                            std::vector<uint64_t>& raw_indices,
                            std::vector<unsigned long int>& local_indices,
                            std::vector<size_t>& event_indices)
    {
      raw_indices.assign(actual_count, 0);
      local_indices.assign(actual_count, 0);
      event_indices.assign(actual_count, 0);

      uint64_t remaining = start;
      size_t ev_idx = 0;
      while (ev_idx < event_entries_.size() && remaining >= event_entries_[ev_idx].length_samples_)
      {
        remaining -= event_entries_[ev_idx].length_samples_;
        ev_idx++;
      }

      for (unsigned long int i = 0; i < actual_count; ++i)
      {
        const imc::event_entry &ev = event_entries_[ev_idx];
        raw_indices[i] = ev.offset_samples_ + remaining;
        local_indices[i] = (unsigned long int)remaining;
        event_indices[i] = ev_idx;
        remaining++;
        if (remaining >= ev.length_samples_ && ev_idx + 1 < event_entries_.size())
        {
          ev_idx++;
          remaining = 0;
        }
      }
    }

    void decode_event_y(channel_chunk& chunk,
                        bool raw_mode,
                        unsigned long int actual_count,
                        unsigned long int y_base,
                        const std::vector<uint64_t>& raw_indices,
                        const std::vector<size_t>& event_indices)
    {
      unsigned long int y_bytes_per_sample = ysignbits_ / 8;

      if (raw_mode)
      {
        int type = (int)ydatatp_;
        chunk.y_type = type;
        if (type == 13)
        {
          chunk.y_bytes.resize(actual_count * 8);
          uint64_t* dest = reinterpret_cast<uint64_t*>(chunk.y_bytes.data());
          for (unsigned long int i = 0; i < actual_count; ++i)
          {
            const unsigned char* src = buffer_ + y_base + raw_indices[i] * 6;
            uint64_t val = 0;
            for (int b = 0; b < 6; ++b) val |= (uint64_t)src[b] << (b * 8);
            dest[i] = val;
          }
        }
        else
        {
          chunk.y_bytes.resize(actual_count * y_bytes_per_sample);
          for (unsigned long int i = 0; i < actual_count; ++i)
          {
            const unsigned char* src = buffer_ + y_base + raw_indices[i] * y_bytes_per_sample;
            unsigned char* dst = chunk.y_bytes.data() + i * y_bytes_per_sample;
            std::copy(src, src + y_bytes_per_sample, dst);
          }
        }
      }
      else
      {
        chunk.y_type = 8;
        chunk.y_bytes.resize(actual_count * sizeof(double));
        double* ydst = reinterpret_cast<double*>(chunk.y_bytes.data());
        for (unsigned long int i = 0; i < actual_count; ++i)
        {
          const imc::event_entry &ev = event_entries_[event_indices[i]];
          double factor = yfactor_;
          double offset = yoffset_;
          if (event_valid_cr1_ & EVENT_VALID_BIT_1) factor = ev.y_factor_;
          if (event_valid_cr1_ & EVENT_VALID_BIT_2) offset = ev.y_offset_;
          if (factor == 0.0) factor = 1.0;

          const unsigned char* src = buffer_ + y_base + raw_indices[i] * y_bytes_per_sample;
          double raw_val = read_sample_as_double(ydatatp_, src);
          ydst[i] = raw_val * factor + offset;
        }
      }
    }

    void decode_event_x(channel_chunk& chunk,
                        unsigned long int actual_count,
                        const std::vector<unsigned long int>& local_indices,
                        const std::vector<size_t>& event_indices)
    {
      chunk.x_type = 8;
      chunk.x_bytes.resize(actual_count * sizeof(double));
      double* xdst = reinterpret_cast<double*>(chunk.x_bytes.data());
      for (unsigned long int i = 0; i < actual_count; ++i)
      {
        const imc::event_entry &ev = event_entries_[event_indices[i]];
        double dx = (event_valid_cd_ & EVENT_VALID_BIT_1) ? ev.dx_ : xstepwidth_;
        double x0 = (event_valid_cd_ & EVENT_VALID_BIT_2) ? ev.x0_ : xstart_;
        xdst[i] = x0 + (double)local_indices[i] * dx;
      }
    }

    const char* trigger_time_source_label() const
    {
      return trigger_time_from_events_ ? "CV" : "NT/Cb";
    }

    void append_event_json(std::stringstream& ss) const
    {
      ss<<",\"events\":{"
        <<"\"has-description\":"<<(has_event_description_?"true":"false")
        <<",\"has-list\":"<<(has_event_list_?"true":"false")
        <<",\"list-index\":"<<event_list_index_
        <<",\"count-declared\":"<<event_count_declared_
        <<",\"count-parsed\":"<<event_count_parsed_
        <<",\"valid-nt\":"<<event_valid_nt_
        <<",\"valid-cd\":"<<event_valid_cd_
        <<",\"valid-cr1\":"<<event_valid_cr1_
        <<",\"valid-cr2\":"<<event_valid_cr2_
        <<",\"trigger-time-source\":\""<<trigger_time_source_label()<<"\""
        <<",\"first-time-seconds\":"<<first_event_time_seconds_
        <<",\"overrides\":"<<(event_overrides_present_?"true":"false")
        <<"}";
    }

    // group reference the channel belongs to
    unsigned long int group_index_;
    std::string group_uuid_, group_name_, group_comment_;

    // constructor takes channel's block environment
    channel(channel_env &chnenv, std::map<std::string,imc::block>* blocks,
                                 const unsigned char* buffer):
      chnenv_(chnenv), blocks_(blocks), buffer_(buffer),
      trigger_time_frac_secs_(0.0),
      xstepwidth_(1.0), xstart_(0.0), xprec_(0), dimension_(0),
      xsignbits_(0), xnum_bytes_(0), ysignbits_(0), ynum_bytes_(0),
      xbuffer_offset_(0), ybuffer_offset_(0), xbuffer_size_(0), ybuffer_size_(0),
      addtime_(0), xdatatp_(numtype::unsigned_byte), ydatatp_(numtype::unsigned_byte),
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

      if ( blocks_->count(chnenv_.Cvuuid_) == 1 )
      {
        imc::event_description evd;
        evd.parse(buffer_, blocks_->at(chnenv_.Cvuuid_).get_parameters());
        has_event_description_ = true;
        event_list_index_ = evd.index_event_list_key_;
        event_count_declared_ = evd.event_count_;
        event_valid_nt_ = evd.valid_nt_;
        event_valid_cd_ = evd.valid_cd_;
        event_valid_cr1_ = evd.valid_cr1_;
        event_valid_cr2_ = evd.valid_cr2_;
        event_overrides_present_ = (event_valid_nt_ != 0 || event_valid_cd_ != 0
            || event_valid_cr1_ != 0 || event_valid_cr2_ != 0);
      }

      std::string event_list_uuid = chnenv_.CVuuid_;
      if ( has_event_description_ && event_list_uuid.empty() )
      {
        for ( std::map<std::string,imc::block>::iterator it = blocks_->begin();
              it != blocks_->end(); ++it )
        {
          imc::block &blk = it->second;
          if ( blk.get_key().name_ == "CV" )
          {
            imc::event_list evl;
            evl.parse(buffer_, blk.get_parameters());
            if ( evl.index_ == event_list_index_ )
            {
              event_list_uuid = blk.get_uuid();
              break;
            }
          }
        }
      }

      if ( !event_list_uuid.empty() && blocks_->count(event_list_uuid) == 1 )
      {
        imc::event_list evl;
        evl.parse(buffer_, blocks_->at(event_list_uuid).get_parameters());
        has_event_list_ = true;
        event_count_parsed_ = (unsigned long int)evl.entries_.size();
        if ( event_count_declared_ == 0 ) event_count_declared_ = evl.event_count_;
        event_entries_ = evl.entries_;
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
        if (comp_group1.has_cr_ && ydatatp_ != numtype::two_byte_word_digital)
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
        std::time_t ts = timegm(&comp_group1.NT_.tms_); // std::mktime(&tms);
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
        std::time_t ts = timegm(&comp_group2.NT_.tms_); // std::mktime(&tms);
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

      // for event channels, trigger-time can be defined per event list (ValidNT)
      apply_event_time_override_if_available();

      // convert any non-UTF-8 codepage to UTF-8 and cleanse any text
      convert_encoding();
      cleanse_text();
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

      // determine number of values in buffer
      unsigned long int ynum_values = (unsigned long int)(yCSbuffer_size/(ysignbits_/8));
      if ( ynum_values*(ysignbits_/8) != yCSbuffer_size )
      {
        throw std::runtime_error("CSbuffer and significant bits of y datatype don't match");
      }
      
      number_of_samples_ = ynum_values;

      if ( has_event_list_ && !event_entries_.empty() )
      {
        std::vector<imc::event_entry> normalized_entries;
        normalized_entries.reserve(event_entries_.size());
        unsigned long int total_event_samples = 0;
        for ( const imc::event_entry &ev: event_entries_ )
        {
          if ( ev.offset_samples_ >= ynum_values ) continue;
          uint64_t max_len = (uint64_t)ynum_values - ev.offset_samples_;
          uint64_t eff_len = (std::min)(ev.length_samples_, max_len);
          if ( eff_len == 0 ) continue;
          imc::event_entry copy = ev;
          copy.length_samples_ = eff_len;
          normalized_entries.push_back(copy);
          total_event_samples += (unsigned long int)eff_len;
        }
        if ( !normalized_entries.empty() && total_event_samples > 0 )
        {
          event_entries_ = normalized_entries;
          event_count_parsed_ = (unsigned long int)event_entries_.size();
          number_of_samples_ = total_event_samples;
        }
      }

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
      if ( has_event_list_ && !event_entries_.empty() && dimension_ == 1 )
      {
        ydata_.clear();
        xdata_.clear();
        channel_chunk all = read_chunk(0, number_of_samples_, true, false);
        const double* yptr = reinterpret_cast<const double*>(all.y_bytes.data());
        const double* xptr = reinterpret_cast<const double*>(all.x_bytes.data());
        ydata_.reserve(number_of_samples_);
        xdata_.reserve(number_of_samples_);
        for ( unsigned long int i = 0; i < number_of_samples_; i++ )
        {
          ydata_.push_back(yptr[i]);
          xdata_.push_back(xptr[i]);
        }
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

        bool event_direct_decode = use_event_direct_decode();

        // Handle Y data
        if (event_direct_decode)
        {
          std::vector<uint64_t> raw_indices;
          std::vector<unsigned long int> local_indices;
          std::vector<size_t> event_indices;
          build_event_lookup(start, actual_count, raw_indices, local_indices, event_indices);

          unsigned long int y_base = buffstrt + ybuffer_offset_ + 1;
          decode_event_y(chunk, raw_mode, actual_count, y_base, raw_indices, event_indices);

          if (include_x)
          {
            decode_event_x(chunk, actual_count, local_indices, event_indices);
          }

          return chunk;
        }

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
        <<std::setw(width)<<std::left<<"has-event-description:"<<(has_event_description_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"has-event-list:"<<(has_event_list_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"event-list-index:"<<event_list_index_<<"\n"
        <<std::setw(width)<<std::left<<"event-count-declared:"<<event_count_declared_<<"\n"
        <<std::setw(width)<<std::left<<"event-count-parsed:"<<event_count_parsed_<<"\n"
        <<std::setw(width)<<std::left<<"event-overrides:"<<(event_overrides_present_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"trigger-time-source:"<<trigger_time_source_label()<<"\n"
        <<std::setw(width)<<std::left<<"first-event-time-seconds:"<<first_event_time_seconds_<<"\n"
        <<std::setw(width)<<std::left<<"ydata:"<<imc::joinvec<imc::datatype>(ydata_,6,9,true)<<"\n"
        <<std::setw(width)<<std::left<<"xdata:"<<imc::joinvec<imc::datatype>(xdata_,6,xprec_,true)<<"\n";
        // <<std::setw(width)<<std::left<<"aff. blocks:"<<chnenv_.get_json()<<"\n";
      return ss.str();
    }

    // provide JSON string of metadata
    std::string get_json(bool include_data = false)
    {
      if (include_data && ydata_.empty() && number_of_samples_ > 0) {
          load_all_data();
      }
      // prepare printable trigger-time
      std::time_t tt = std::chrono::system_clock::to_time_t(trigger_time_);
      std::time_t att = std::chrono::system_clock::to_time_t(absolute_trigger_time_);

      std::stringstream ss;
      ss<<"{"<<"\"uuid\":\""<<uuid_
             <<"\",\"name\":\""<<prepjsonstr(name_)
             <<"\",\"comment\":\""<<prepjsonstr(comment_)
             <<"\",\"origin\":\""<<prepjsonstr(origin_)
             <<"\",\"origin-comment\":\""<<prepjsonstr(origin_comment_)
             <<"\",\"description\":\""<<prepjsonstr(text_)
             <<"\",\"trigger-time-nt\":\""<<std::put_time(std::gmtime(&tt),"%FT%T")
             <<"\",\"trigger-time\":\""<<std::put_time(std::gmtime(&att),"%FT%T")
             <<"\",\"language-code\":\""<<prepjsonstr(language_code_)
             <<"\",\"codepage\":\""<<prepjsonstr(codepage_)
             <<"\",\"yname\":\""<<prepjsonstr(yname_)
             <<"\",\"yunit\":\""<<prepjsonstr(yunit_)
             <<"\",\"datatype\":\""<<ydatatp_
             <<"\",\"significantbits\":\""<<ysignbits_
             <<"\",\"buffer-size\":\""<<ybuffer_size_
             <<"\",\"xname\":\""<<prepjsonstr(xname_)
             <<"\",\"xunit\":\""<<prepjsonstr(xunit_)
             <<"\",\"xstepwidth\":\""<<xstepwidth_
             <<"\",\"xoffset\":\""<<xstart_
             <<"\",\"factor\":\""<<yfactor_
             <<"\",\"offset\":\""<<yoffset_
             <<"\",\"group\":{"<<"\"index\":\""<<group_index_
             <<"\",\"name\":\""<<prepjsonstr(group_name_)
             <<"\",\"comment\":\""<<prepjsonstr(group_comment_)<<"\""<<"}";
      append_event_json(ss);
      if ( include_data )
      {
        ss<<",\"ydata\":"<<imc::joinvec<imc::datatype>(ydata_,0,9,true)
          <<",\"xdata\":"<<imc::joinvec<imc::datatype>(xdata_,0,xprec_,true);
      }
      // ss<<"\",\"aff. blocks\":\""<<chnenv_.get_json()
      ss<<"}";

      return ss.str();
    }

    // prepare string value for usage in JSON dump
    std::string prepjsonstr(std::string value)
    {
      std::stringstream ss;
      ss<<quoted(value);
      return strip_quotes(ss.str());
    }

    // remove any leading or trailing double quotes
    std::string strip_quotes(std::string astring)
    {
      // head
      if ( astring.front() == '"' ) astring.erase(astring.begin()+0);
      // tail
      if ( astring.back() == '"' ) astring.erase(astring.end()-1);

      return astring;
    }

    // print channel
    void print(std::string filename, const char sep = ',', int width = 25, int yprec = 9, unsigned long int chunk_size = 100000)
    {
      std::ofstream fou(filename);

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
