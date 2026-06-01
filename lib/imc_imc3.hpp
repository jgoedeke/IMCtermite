//---------------------------------------------------------------------------//

#ifndef IMCIMC3
#define IMCIMC3

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "imc_channel.hpp"
#include "imc_conversion.hpp"

//---------------------------------------------------------------------------//

namespace imc
{
  namespace imc3
  {
    constexpr uint32_t make_key(char a, char b, char c, char d)
    {
      return static_cast<uint32_t>(static_cast<unsigned char>(a))
        | (static_cast<uint32_t>(static_cast<unsigned char>(b)) << 8)
        | (static_cast<uint32_t>(static_cast<unsigned char>(c)) << 16)
        | (static_cast<uint32_t>(static_cast<unsigned char>(d)) << 24);
    }

    constexpr uint32_t key_cb1 = make_key('|','C','B','1');
    constexpr uint32_t key_cl1 = make_key('|','C','L','1');
    constexpr uint32_t key_co1 = make_key('|','C','O','1');
    constexpr uint32_t key_cd1 = make_key('|','C','d','1');
    constexpr uint32_t key_CD1 = make_key('|','C','D','1');
    constexpr uint32_t key_cp1 = make_key('|','C','P','1');
    constexpr uint32_t key_rr1 = make_key('|','R','R','1');
    constexpr uint32_t key_rn1 = make_key('|','R','N','1');
    constexpr uint32_t key_ri1 = make_key('|','R','i','1');
    constexpr uint32_t key_rt1 = make_key('|','R','T','1');
    constexpr uint32_t key_rc5 = make_key('|','R','C','5');
    constexpr uint32_t key_re1 = make_key('|','R','E','1');
    constexpr uint32_t key_cs1 = make_key('|','C','S','1');
    constexpr uint32_t key_ca1 = make_key('|','C','A','1');
    constexpr uint32_t key_cg1 = make_key('|','C','G','1');
    constexpr uint32_t key_cc1 = make_key('|','C','C','1');
    constexpr uint32_t key_cm1 = make_key('|','C','M','1');
    constexpr uint32_t key_ch1 = make_key('|','C','H','1');
    constexpr uint32_t key_ch2 = make_key('|','C','H','2');
    constexpr uint32_t key_cz1 = make_key('|','C','Z','1');
    constexpr uint32_t key_cn1 = make_key('|','C','N','1');
    constexpr uint32_t key_cj1 = make_key('|','C','J','1');
    constexpr uint32_t key_ce1 = make_key('|','C','E','1');

    inline void ensure_available(size_t offset, size_t needed, size_t size, const std::string& context)
    {
      if ( offset + needed > size )
      {
        throw std::runtime_error("truncated IMC3 file while reading " + context);
      }
    }

    inline uint8_t read_u8(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      ensure_available(offset, 1, size, context);
      return data[offset++];
    }

    inline uint16_t read_u16(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      ensure_available(offset, 2, size, context);
      uint16_t value = static_cast<uint16_t>(data[offset])
        | static_cast<uint16_t>(data[offset + 1] << 8);
      offset += 2;
      return value;
    }

    inline int16_t read_i16(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      return static_cast<int16_t>(read_u16(data, size, offset, context));
    }

    inline uint32_t read_u32(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      ensure_available(offset, 4, size, context);
      uint32_t value = static_cast<uint32_t>(data[offset])
        | (static_cast<uint32_t>(data[offset + 1]) << 8)
        | (static_cast<uint32_t>(data[offset + 2]) << 16)
        | (static_cast<uint32_t>(data[offset + 3]) << 24);
      offset += 4;
      return value;
    }

    inline int32_t read_i32(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      return static_cast<int32_t>(read_u32(data, size, offset, context));
    }

    inline uint64_t read_u64(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      ensure_available(offset, 8, size, context);
      uint64_t value = 0;
      for ( int i = 0; i < 8; ++i )
      {
        value |= static_cast<uint64_t>(data[offset + i]) << (8 * i);
      }
      offset += 8;
      return value;
    }

    inline double read_double(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      ensure_available(offset, sizeof(double), size, context);
      double value = 0.0;
      std::memcpy(&value, data + offset, sizeof(double));
      offset += sizeof(double);
      return value;
    }

    inline std::string read_string_u16(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      uint16_t length = read_u16(data, size, offset, context + " length");
      ensure_available(offset, length, size, context);
      std::string value(reinterpret_cast<const char*>(data + offset), reinterpret_cast<const char*>(data + offset + length));
      offset += length;
      return value;
    }

    inline std::string read_string_u32(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
    {
      uint32_t length = read_u32(data, size, offset, context + " length");
      ensure_available(offset, length, size, context);
      std::string value(reinterpret_cast<const char*>(data + offset), reinterpret_cast<const char*>(data + offset + length));
      offset += length;
      return value;
    }

    inline std::string read_fixed_string(const unsigned char* data, size_t size, size_t& offset, size_t length, const std::string& context)
    {
      ensure_available(offset, length, size, context);
      std::string value(reinterpret_cast<const char*>(data + offset), reinterpret_cast<const char*>(data + offset + length));
      offset += length;
      size_t null_pos = value.find('\0');
      if ( null_pos != std::string::npos )
      {
        value.resize(null_pos);
      }
      return value;
    }

    inline uint32_t peek_u32(const unsigned char* data, size_t size, size_t offset, const std::string& context)
    {
      ensure_available(offset, 4, size, context);
      return static_cast<uint32_t>(data[offset])
        | (static_cast<uint32_t>(data[offset + 1]) << 8)
        | (static_cast<uint32_t>(data[offset + 2]) << 16)
        | (static_cast<uint32_t>(data[offset + 3]) << 24);
    }

    inline size_t bytes_per_numeric_type(imc::numtype type)
    {
      switch ( type )
      {
        case imc::numtype::unsigned_byte:
        case imc::numtype::signed_byte:
          return 1;
        case imc::numtype::unsigned_short:
        case imc::numtype::signed_short:
        case imc::numtype::two_byte_word_digital:
          return 2;
        case imc::numtype::unsigned_long:
        case imc::numtype::signed_long:
        case imc::numtype::ffloat:
          return 4;
        case imc::numtype::ddouble:
        case imc::numtype::eight_byte_unsigned_long:
        case imc::numtype::eight_byte_signed_long:
          return 8;
        case imc::numtype::six_byte_unsigned_long:
          return 6;
        case imc::numtype::timestamp_ascii:
          return 6;
        default:
          throw std::runtime_error("unsupported IMC3 numeric type: " + std::to_string(static_cast<int>(type)));
      }
    }

    inline int significant_bits(imc::numtype type, uint8_t additional_specifier)
    {
      if ( additional_specifier > 0 && type != imc::numtype::two_byte_word_digital )
      {
        return additional_specifier;
      }
      return static_cast<int>(bytes_per_numeric_type(type) * 8);
    }

    inline imc::numtype parse_numeric_type(uint8_t numeric_format)
    {
      if ( numeric_format == static_cast<uint8_t>(imc::numtype::imc_devices_transitional_recording) )
      {
        throw std::runtime_error("unsupported IMC3 data type: timestamp/event payloads are not implemented");
      }

      if ( numeric_format < static_cast<uint8_t>(imc::numtype::unsigned_byte)
        || numeric_format > static_cast<uint8_t>(imc::numtype::eight_byte_signed_long) )
      {
        throw std::runtime_error("unsupported IMC3 data type: " + std::to_string(numeric_format));
      }

      return static_cast<imc::numtype>(numeric_format);
    }

    inline std::chrono::system_clock::time_point trigger_time_to_time_point(double seconds_since_1980)
    {
      std::tm epoch_tm = {};
      epoch_tm.tm_year = 80;
      epoch_tm.tm_mon = 0;
      epoch_tm.tm_mday = 1;
      std::time_t epoch = imc::utc_timegm(&epoch_tm);
      auto base = std::chrono::system_clock::from_time_t(epoch);
      auto duration = std::chrono::duration_cast<std::chrono::system_clock::duration>(
        std::chrono::duration<double>(seconds_since_1980)
      );
      return base + duration;
    }

    struct group
    {
      uint32_t index_ = 0;
      std::string name_;
      std::string comment_;
    };

    struct component
    {
      imc::numtype numeric_type_ = imc::numtype::unsigned_byte;
      uint8_t additional_specifier_ = 0;
      double scale_factor_ = 1.0;
      double scale_offset_ = 0.0;
      std::string unit_;
      int significant_bits_ = 8;
    };

    struct channel
    {
      std::string uuid_;
      std::string name_;
      std::string comment_;
      std::string origin_;
      std::string origin_comment_;
      std::string language_code_;
      std::string codepage_;
      std::string yname_;
      std::string yunit_;
      std::string xname_;
      std::string xunit_;
      std::string group_name_;
      std::string group_comment_;
      std::string text_;
      std::chrono::system_clock::time_point trigger_time_;
      std::chrono::system_clock::time_point absolute_trigger_time_;
      double xstepwidth_ = 1.0;
      double xstart_ = 0.0;
      int xprec_ = 9;
      int dimension_ = 1;
      int xsignbits_ = 0;
      int ysignbits_ = 0;
      unsigned long int xbuffer_offset_ = 0;
      unsigned long int ybuffer_offset_ = 0;
      unsigned long int xbuffer_size_ = 0;
      unsigned long int ybuffer_size_ = 0;
      imc::numtype xdatatp_ = imc::numtype::unsigned_byte;
      imc::numtype ydatatp_ = imc::numtype::unsigned_byte;
      double xfactor_ = 1.0;
      double yfactor_ = 1.0;
      double xoffset_ = 0.0;
      double yoffset_ = 0.0;
      unsigned long int number_of_samples_ = 0;
      unsigned long int group_index_ = 0;
      const unsigned char* raw_data_ = nullptr;
      mutable std::vector<unsigned char> tsa_logical_stream_;
      mutable std::vector<imc::tsa_event_descriptor> tsa_event_index_;
      mutable bool tsa_index_built_ = false;

      bool is_tsa_channel() const
      {
        return ydatatp_ == imc::numtype::timestamp_ascii;
      }

      std::string channel_type() const
      {
        return is_tsa_channel() ? std::string("event") : std::string("numeric");
      }

      void ensure_tsa_index() const
      {
        if ( !is_tsa_channel() || tsa_index_built_ )
        {
          return;
        }

        if ( raw_data_ == nullptr )
        {
          throw std::runtime_error("TSA raw-data buffer is not available");
        }

        imc::tsa_index_data index = imc::build_tsa_index(raw_data_ + ybuffer_offset_, ybuffer_size_);
        tsa_logical_stream_ = std::move(index.logical_stream);
        tsa_event_index_ = std::move(index.events);
        tsa_index_built_ = true;
      }

      std::vector<imc::tsa_event> read_tsa_events(unsigned long int start, unsigned long int count) const
      {
        if ( !is_tsa_channel() )
        {
          throw std::runtime_error("channel is numeric; use read_chunk() instead");
        }

        ensure_tsa_index();
        return imc::decode_tsa_event_slice(tsa_logical_stream_, tsa_event_index_, xfactor_, xoffset_, start, count);
      }

      void append_raw_bytes(std::vector<unsigned char>& out, const unsigned char* base, unsigned long int start,
                            unsigned long int count, int type) const
      {
        size_t bytes_per_sample = bytes_per_numeric_type(static_cast<imc::numtype>(type));
        size_t byte_offset = static_cast<size_t>(start) * bytes_per_sample;
        size_t byte_count = static_cast<size_t>(count) * bytes_per_sample;
        if ( type == static_cast<int>(imc::numtype::six_byte_unsigned_long) )
        {
          out.resize(static_cast<size_t>(count) * sizeof(uint64_t));
          for ( unsigned long int i = 0; i < count; ++i )
          {
            uint64_t value = 0;
            for ( int b = 0; b < 6; ++b )
            {
              value |= static_cast<uint64_t>(base[byte_offset + i * 6 + b]) << (8 * b);
            }
            std::memcpy(out.data() + static_cast<size_t>(i) * sizeof(uint64_t), &value, sizeof(uint64_t));
          }
          return;
        }

        out.resize(byte_count);
        std::copy(base + byte_offset, base + byte_offset + byte_count, out.begin());
      }

      template<typename SourceType>
      void append_scaled_bytes(std::vector<unsigned char>& out, const unsigned char* base, unsigned long int start,
                               unsigned long int count, double factor, double offset) const
      {
        std::vector<double> values;
        imc::convert_chunk_to_double<SourceType>(base, start, count, factor, offset, values);
        out.resize(values.size() * sizeof(double));
        std::memcpy(out.data(), values.data(), out.size());
      }

      void append_scaled_values(std::vector<double>& values, const unsigned char* base, unsigned long int start,
                                unsigned long int count, imc::numtype type, double factor, double offset) const
      {
        switch ( type )
        {
          case imc::numtype::unsigned_byte:
            imc::convert_chunk_to_double<imc_Ubyte>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::signed_byte:
            imc::convert_chunk_to_double<imc_Sbyte>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::unsigned_short:
            imc::convert_chunk_to_double<imc_Ushort>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::signed_short:
            imc::convert_chunk_to_double<imc_Sshort>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::unsigned_long:
            imc::convert_chunk_to_double<imc_Ulongint>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::signed_long:
            imc::convert_chunk_to_double<imc_Slongint>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::ffloat:
            imc::convert_chunk_to_double<imc_float>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::ddouble:
            imc::convert_chunk_to_double<imc_double>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::two_byte_word_digital:
            imc::convert_chunk_to_double<imc_digital>(base, start, count, 1.0, 0.0, values);
            break;
          case imc::numtype::eight_byte_unsigned_long:
            imc::convert_chunk_to_double<uint64_t>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::six_byte_unsigned_long:
            imc::convert_chunk_to_double<imc_sixbyte>(base, start, count, factor, offset, values);
            break;
          case imc::numtype::eight_byte_signed_long:
            imc::convert_chunk_to_double<int64_t>(base, start, count, factor, offset, values);
            break;
          default:
            throw std::runtime_error("unsupported IMC3 numeric type for scaling: " + std::to_string(static_cast<int>(type)));
        }
      }

      channel_chunk read_chunk(unsigned long int start, unsigned long int count, bool include_x, bool raw_mode) const
      {
        if ( is_tsa_channel() )
        {
          throw std::runtime_error("TSA event streaming via iter_channel_numpy is not implemented");
        }

        if ( start >= number_of_samples_ )
        {
          return { {}, {}, start, 0, include_x, 0, 0 };
        }

        unsigned long int end = start + count;
        if ( end > number_of_samples_ ) end = number_of_samples_;
        unsigned long int actual_count = end - start;

        channel_chunk chunk;
        chunk.start = start;
        chunk.count = actual_count;
        chunk.has_x = include_x;
        chunk.x_type = 0;
        chunk.y_type = 0;

        const unsigned char* y_base = raw_data_ + ybuffer_offset_;
        if ( raw_mode )
        {
          chunk.y_type = static_cast<int>(ydatatp_);
          append_raw_bytes(chunk.y_bytes, y_base, start, actual_count, chunk.y_type);
        }
        else
        {
          chunk.y_type = static_cast<int>(imc::numtype::ddouble);
          std::vector<double> y_values;
          append_scaled_values(y_values, y_base, start, actual_count, ydatatp_, yfactor_, yoffset_);
          chunk.y_bytes.resize(y_values.size() * sizeof(double));
          std::memcpy(chunk.y_bytes.data(), y_values.data(), chunk.y_bytes.size());
        }

        if ( include_x )
        {
          if ( dimension_ == 2 )
          {
            const unsigned char* x_base = raw_data_ + xbuffer_offset_;
            if ( raw_mode )
            {
              chunk.x_type = static_cast<int>(xdatatp_);
              append_raw_bytes(chunk.x_bytes, x_base, start, actual_count, chunk.x_type);
            }
            else
            {
              chunk.x_type = static_cast<int>(imc::numtype::ddouble);
              std::vector<double> x_values;
              append_scaled_values(x_values, x_base, start, actual_count, xdatatp_, xfactor_, xoffset_);
              chunk.x_bytes.resize(x_values.size() * sizeof(double));
              std::memcpy(chunk.x_bytes.data(), x_values.data(), chunk.x_bytes.size());
            }
          }
          else
          {
            chunk.x_type = static_cast<int>(imc::numtype::ddouble);
            chunk.x_bytes.resize(actual_count * sizeof(double));
            double* x_ptr = reinterpret_cast<double*>(chunk.x_bytes.data());
            for ( unsigned long int i = 0; i < actual_count; ++i )
            {
              x_ptr[i] = xstart_ + static_cast<double>(start + i) * xstepwidth_;
            }
          }
        }

        return chunk;
      }

      std::string get_info(int width = 20) const
      {
        std::time_t tt = std::chrono::system_clock::to_time_t(trigger_time_);
        std::stringstream ss;
        ss << std::setw(width) << std::left << "uuid:" << uuid_ << "\n"
           << std::setw(width) << std::left << "name:" << name_ << "\n"
           << std::setw(width) << std::left << "comment:" << comment_ << "\n"
           << std::setw(width) << std::left << "origin:" << origin_ << "\n"
           << std::setw(width) << std::left << "origin-comment:" << origin_comment_ << "\n"
           << std::setw(width) << std::left << "trigger-time:" << std::put_time(std::gmtime(&tt), "%FT%T") << "\n"
           << std::setw(width) << std::left << "codepage:" << codepage_ << "\n"
           << std::setw(width) << std::left << "yname:" << yname_ << "\n"
           << std::setw(width) << std::left << "yunit:" << yunit_ << "\n"
           << std::setw(width) << std::left << "channel-type:" << channel_type() << "\n"
           << std::setw(width) << std::left << "datatype:" << ydatatp_ << "\n"
           << std::setw(width) << std::left << "significant bits:" << ysignbits_ << "\n"
           << std::setw(width) << std::left << "buffer-size:" << ybuffer_size_ << "\n"
           << std::setw(width) << std::left << "xname:" << xname_ << "\n"
           << std::setw(width) << std::left << "xunit:" << xunit_ << "\n"
           << std::setw(width) << std::left << "xstepwidth:" << xstepwidth_ << "\n"
           << std::setw(width) << std::left << "xoffset:" << xstart_ << "\n"
           << std::setw(width) << std::left << "factor:" << yfactor_ << "\n"
           << std::setw(width) << std::left << "offset:" << yoffset_ << "\n"
           << std::setw(width) << std::left << "group:" << "(" << group_index_ << "," << group_name_ << "," << group_comment_ << ")" << "\n";
        return ss.str();
      }

      std::string get_json(bool include_data = false) const
      {
        std::time_t tt = std::chrono::system_clock::to_time_t(trigger_time_);
        std::time_t att = std::chrono::system_clock::to_time_t(absolute_trigger_time_);

        std::stringstream ss;
          ss << "{" << "\"uuid\":\"" << imc::escape_json_string(uuid_)
            << "\",\"name\":\"" << imc::escape_json_string(name_)
            << "\",\"comment\":\"" << imc::escape_json_string(comment_)
            << "\",\"origin\":\"" << imc::escape_json_string(origin_)
            << "\",\"origin-comment\":\"" << imc::escape_json_string(origin_comment_)
            << "\",\"description\":\"" << imc::escape_json_string(text_)
           << "\",\"trigger-time-nt\":\"" << std::put_time(std::gmtime(&tt), "%FT%T")
           << "\",\"trigger-time\":\"" << std::put_time(std::gmtime(&att), "%FT%T")
            << "\",\"language-code\":\"" << imc::escape_json_string(language_code_)
            << "\",\"codepage\":\"" << imc::escape_json_string(codepage_)
            << "\",\"yname\":\"" << imc::escape_json_string(yname_)
            << "\",\"yunit\":\"" << imc::escape_json_string(yunit_)
            << "\",\"channel_type\":\"" << channel_type()
           << "\",\"datatype\":\"" << static_cast<int>(ydatatp_)
           << "\",\"significantbits\":\"" << ysignbits_
           << "\",\"buffer-size\":\"" << ybuffer_size_
            << "\",\"xname\":\"" << imc::escape_json_string(xname_)
            << "\",\"xunit\":\"" << imc::escape_json_string(xunit_)
           << "\",\"xstepwidth\":\"" << xstepwidth_
           << "\",\"xoffset\":\"" << xstart_
           << "\",\"factor\":\"" << yfactor_
           << "\",\"offset\":\"" << yoffset_
           << "\",\"group\":{" << "\"index\":\"" << group_index_
            << "\",\"name\":\"" << imc::escape_json_string(group_name_)
            << "\",\"comment\":\"" << imc::escape_json_string(group_comment_) << "\"}";

        if ( include_data )
        {
          if ( is_tsa_channel() )
          {
            std::vector<imc::tsa_event> events = read_tsa_events(0, number_of_samples_);
            std::vector<double> x_values;
            std::vector<std::string> text_values;
            x_values.reserve(events.size());
            text_values.reserve(events.size());
            for ( const imc::tsa_event& event : events )
            {
              x_values.push_back(event.timestamp);
              text_values.push_back(event.text);
            }
            ss << ",\"xdata\":" << imc::joinvec<double>(x_values, 0, xprec_, true)
               << ",\"textdata\":" << imc::join_stringvec_json(text_values);
          }
          else
          {
            channel_chunk chunk = read_chunk(0, number_of_samples_, true, false);
            const double* y_ptr = reinterpret_cast<const double*>(chunk.y_bytes.data());
            std::vector<double> y_values(y_ptr, y_ptr + chunk.count);
            ss << ",\"ydata\":" << imc::joinvec<double>(y_values, 0, 9, true);

            const double* x_ptr = reinterpret_cast<const double*>(chunk.x_bytes.data());
            std::vector<double> x_values(x_ptr, x_ptr + chunk.count);
            ss << ",\"xdata\":" << imc::joinvec<double>(x_values, 0, xprec_, true);
          }
        }

        ss << "}";
        return ss.str();
      }

      void print(const std::string& filename, const char sep = ',', int width = 25, int yprec = 9,
                 unsigned long int chunk_size = 100000) const
      {
        std::ofstream fout(filename);

        if ( is_tsa_channel() )
        {
          std::vector<imc::tsa_event> events = read_tsa_events(0, number_of_samples_);

          if ( sep == ' ' )
          {
            fout << std::setw(width) << std::left << xname_
                 << std::setw(width) << std::left << yname_ << "\n"
                 << std::setw(width) << std::left << xunit_
                 << std::setw(width) << std::left << yunit_ << "\n";
          }
          else
          {
            fout << xname_ << sep << yname_ << "\n"
                 << xunit_ << sep << yunit_ << "\n";
          }

          for ( const imc::tsa_event& event : events )
          {
            if ( sep == ' ' )
            {
              fout << std::setprecision(xprec_) << std::fixed
                   << std::setw(width) << std::left << event.timestamp
                   << event.text << "\n";
            }
            else
            {
              fout << std::setprecision(xprec_) << std::fixed << event.timestamp
                   << sep
                   << imc::escape_csv_field(event.text, sep) << "\n";
            }
          }
          return;
        }

        if ( sep == ' ' )
        {
          fout << std::setw(width) << std::left << xname_
               << std::setw(width) << std::left << yname_ << "\n"
               << std::setw(width) << std::left << xunit_
               << std::setw(width) << std::left << yunit_ << "\n";
        }
        else
        {
          fout << xname_ << sep << yname_ << "\n"
               << xunit_ << sep << yunit_ << "\n";
        }

        unsigned long int start = 0;
        while ( start < number_of_samples_ )
        {
          channel_chunk chunk = read_chunk(start, chunk_size, true, false);
          if ( chunk.count == 0 ) break;

          const double* x_ptr = reinterpret_cast<const double*>(chunk.x_bytes.data());
          const double* y_ptr = reinterpret_cast<const double*>(chunk.y_bytes.data());
          for ( unsigned long int i = 0; i < chunk.count; ++i )
          {
            if ( sep == ' ' )
            {
              fout << std::setprecision(xprec_) << std::fixed
                   << std::setw(width) << std::left << x_ptr[i]
                   << std::setprecision(yprec) << std::fixed
                   << std::setw(width) << std::left << y_ptr[i] << "\n";
            }
            else
            {
              fout << std::setprecision(xprec_) << std::fixed << x_ptr[i]
                   << sep
                   << std::setprecision(yprec) << std::fixed << y_ptr[i] << "\n";
            }
          }

          start += chunk.count;
        }
      }
    };

    class dataset
    {
      std::string codepage_;
      std::string language_code_;
      std::string origin_;
      std::string origin_comment_;
      uint32_t magic1_ = 0;
      uint32_t magic2_ = 0;
      uint8_t variant_ = 0;
      bool unicode_ = false;
      size_t header_end_ = 0;
      size_t raw_begin_ = 0;
      size_t raw_end_ = 0;
      std::map<uint32_t, group> groups_;
      std::map<std::string, channel> channels_;
      std::vector<std::string> channel_order_;
      std::map<std::string,std::vector<unsigned char>> streamed_raw_data_;

      void clear()
      {
        codepage_.clear();
        language_code_.clear();
        origin_.clear();
        origin_comment_.clear();
        magic1_ = 0;
        magic2_ = 0;
        variant_ = 0;
        unicode_ = false;
        header_end_ = 0;
        raw_begin_ = 0;
        raw_end_ = 0;
        groups_.clear();
        channels_.clear();
        channel_order_.clear();
        streamed_raw_data_.clear();
      }

      size_t parse_header(const unsigned char* data, size_t size)
      {
        if ( size < 8 || std::memcmp(data, "|imc3,1;", 8) != 0 )
        {
          throw std::runtime_error("invalid IMC3 file header");
        }

        size_t offset = 8;

        if ( read_u32(data, size, offset, "CB1 key") != key_cb1 )
        {
          throw std::runtime_error("invalid IMC3 file: missing |CB1 header");
        }

        magic1_ = read_u32(data, size, offset, "CB1 magic1");
        magic2_ = read_u32(data, size, offset, "CB1 magic2");
        variant_ = read_u8(data, size, offset, "CB1 variant");
        uint8_t checksum = read_u8(data, size, offset, "CB1 bCS");
        unicode_ = read_u8(data, size, offset, "CB1 bUnicode") != 0;
        uint8_t compression = read_u8(data, size, offset, "CB1 compression");
        (void)checksum;
        (void)read_i16(data, size, offset, "CB1 timezone");
        (void)read_u16(data, size, offset, "CB1 summertime");
        uint16_t version_major = read_u16(data, size, offset, "CB1 version major");
        uint16_t version_minor = read_u16(data, size, offset, "CB1 version minor");

        if ( variant_ != 0 && variant_ != 2 )
        {
          throw std::runtime_error("unsupported IMC3 variant: " + std::to_string(variant_));
        }
        if ( version_major != 1 || version_minor > 2 )
        {
          throw std::runtime_error("unsupported IMC3 version");
        }
        if ( compression != 0 )
        {
          throw std::runtime_error("unsupported IMC3 compression: " + std::to_string(compression));
        }

        if ( read_u32(data, size, offset, "CL1 key") != key_cl1 )
        {
          throw std::runtime_error("invalid IMC3 file: missing |CL1 language key");
        }
        codepage_ = std::to_string(read_u16(data, size, offset, "CL1 codepage"));
        language_code_ = std::to_string(read_u16(data, size, offset, "CL1 language"));

        if ( read_u32(data, size, offset, "CO1 key") != key_co1 )
        {
          throw std::runtime_error("invalid IMC3 file: missing |CO1 origin key");
        }
        origin_ = read_string_u16(data, size, offset, "CO1 producer");
        origin_comment_ = read_string_u16(data, size, offset, "CO1 comment");

        if ( peek_u32(data, size, offset, "header next key") == key_cd1 )
        {
          (void)read_u32(data, size, offset, "Cd1 key");
          (void)read_fixed_string(data, size, offset, 16, "Cd1 version");
          (void)read_fixed_string(data, size, offset, 4, "Cd1 platform");
          (void)read_fixed_string(data, size, offset, 8, "Cd1 compile");
          (void)read_u16(data, size, offset, "Cd1 app code");
          (void)read_u16(data, size, offset, "Cd1 system language");
        }

        header_end_ = offset;
        return offset;
      }

      size_t parse_jump_back(const unsigned char* data, size_t size)
      {
        if ( size < 32 )
        {
          throw std::runtime_error("truncated IMC3 file: missing jump-back footer");
        }

        size_t offset = size - 32;
        if ( peek_u32(data, size, offset, "CJ1 footer key") != key_cj1 )
        {
          throw std::runtime_error("unsupported IMC3 layout: missing |CJ1 footer");
        }
        (void)read_u32(data, size, offset, "CJ1 key");
        uint32_t footer_magic1 = read_u32(data, size, offset, "CJ1 magic1");
        uint64_t re_offset = read_u64(data, size, offset, "CJ1 RE offset");
        uint32_t footer_magic2 = read_u32(data, size, offset, "CJ1 magic2");
        uint32_t cj_length = read_u32(data, size, offset, "CJ1 key length");
        (void)read_u32(data, size, offset, "CJ1 reserved");
        uint32_t footer_end = read_u32(data, size, offset, "CJ1 footer end");

        if ( footer_magic1 != magic1_ || footer_magic2 != magic2_ )
        {
          throw std::runtime_error("invalid IMC3 footer: jump-back magic values do not match header");
        }
        if ( cj_length != 32 || footer_end != key_ce1 )
        {
          throw std::runtime_error("invalid IMC3 footer: malformed jump-back trailer");
        }
        if ( re_offset >= size || re_offset < header_end_ )
        {
          throw std::runtime_error("invalid IMC3 footer: RE offset out of range");
        }
        return static_cast<size_t>(re_offset);
      }

      void parse_ca1_counts(const unsigned char* data, size_t size, size_t& offset, const std::string& context)
      {
        if ( read_u32(data, size, offset, context + " CA1 key") != key_ca1 )
        {
          throw std::runtime_error("unsupported IMC3 metadata layout: missing |CA1");
        }
        (void)read_u32(data, size, offset, context + " group count");
        (void)read_u32(data, size, offset, context + " named channel count");
        (void)read_u32(data, size, offset, context + " index channel count");
        (void)read_u32(data, size, offset, context + " text var count");
        (void)read_u32(data, size, offset, context + " single value count");
      }

      void parse_group_key(const unsigned char* data, size_t size, size_t& offset)
      {
        (void)read_u32(data, size, offset, "CG1 key");
        group grp;
        grp.index_ = read_u32(data, size, offset, "CG1 index");
        grp.name_ = read_string_u16(data, size, offset, "CG1 name");
        grp.comment_ = read_string_u16(data, size, offset, "CG1 comment");
        groups_[grp.index_] = grp;
      }

      void skip_display_key(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "CD1 display key") != key_CD1 )
        {
          throw std::runtime_error("invalid IMC3 display metadata key");
        }
        (void)read_u8(data, size, offset, "CD1 color fix");
        (void)read_u8(data, size, offset, "CD1 color red");
        (void)read_u8(data, size, offset, "CD1 color green");
        (void)read_u8(data, size, offset, "CD1 color blue");
        (void)read_double(data, size, offset, "CD1 y min");
        (void)read_double(data, size, offset, "CD1 y max");
      }

      void skip_properties_key(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "CP1 key") != key_cp1 )
        {
          throw std::runtime_error("invalid IMC3 property metadata key");
        }

        (void)read_u32(data, size, offset, "CP1 channel index");
        (void)read_u16(data, size, offset, "CP1 index bit");
        uint16_t count_elements = read_u16(data, size, offset, "CP1 element count");
        for ( uint16_t i = 0; i < count_elements; ++i )
        {
          (void)read_u16(data, size, offset, "CP1 option");
          (void)read_string_u16(data, size, offset, "CP1 property name");
          (void)read_string_u32(data, size, offset, "CP1 property value");
        }
      }

      component parse_component(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "CM1 key") != key_cm1 )
        {
          throw std::runtime_error("unsupported IMC3 metadata layout: expected |CM1 component");
        }

        component comp;
        uint8_t numeric_format = read_u8(data, size, offset, "CM1 numeric format");
        comp.numeric_type_ = parse_numeric_type(numeric_format);
        comp.additional_specifier_ = read_u8(data, size, offset, "CM1 additional specifier");
        (void)read_u16(data, size, offset, "CM1 zero");
        comp.scale_factor_ = read_double(data, size, offset, "CM1 scale factor");
        comp.scale_offset_ = read_double(data, size, offset, "CM1 scale offset");
        comp.unit_ = read_string_u16(data, size, offset, "CM1 unit");
        comp.significant_bits_ = significant_bits(comp.numeric_type_, comp.additional_specifier_);
        return comp;
      }

      channel parse_channel_descriptor(const unsigned char* data, size_t size, size_t& offset,
                                       bool expect_contiguous_chunk, unsigned long int* current_raw_offset)
      {
        if ( read_u32(data, size, offset, "CC1 key") != key_cc1 )
        {
          throw std::runtime_error("unsupported IMC3 metadata layout: expected |CC1");
        }

        uint32_t index_channel = read_u32(data, size, offset, "CC1 index channel");
        double dx = read_double(data, size, offset, "CC1 dx");
        double x0 = read_double(data, size, offset, "CC1 x0");
        uint32_t group_index = read_u32(data, size, offset, "CC1 group index");
        uint32_t default_chunk_bytes = read_u32(data, size, offset, "CC1 default chunk bytes");
        uint8_t flags = read_u8(data, size, offset, "CC1 flags");
        uint8_t pretrigger_use = read_u8(data, size, offset, "CC1 pretrigger use");
        uint8_t component_combination = read_u8(data, size, offset, "CC1 component combination");
        (void)read_u8(data, size, offset, "CC1 zero");
        std::string xunit = read_string_u16(data, size, offset, "CC1 x unit");

        if ( (flags & 0x05U) != 0U )
        {
          throw std::runtime_error("unsupported IMC3 channel flags: multi-event and color-value channels are not implemented");
        }
        (void)default_chunk_bytes;
        (void)pretrigger_use;

        component y_component = parse_component(data, size, offset);
        bool has_second_component = component_combination != 1 && component_combination != 7;
        component x_component;
        if ( has_second_component )
        {
          x_component = parse_component(data, size, offset);
        }

        uint32_t trigger_key = 0;
        double trigger_value = 0.0;
        uint64_t chunk_bytes = 0;
        if ( expect_contiguous_chunk )
        {
          trigger_key = read_u32(data, size, offset, "CH key");
          if ( trigger_key != key_ch1 && trigger_key != key_ch2 )
          {
            throw std::runtime_error("unsupported IMC3 metadata layout: expected |CH1 or |CH2");
          }
          uint32_t envelope_reduction = read_u32(data, size, offset, "CH envelope reduction");
          trigger_value = read_double(data, size, offset, "CH trigger time");
          uint64_t effective_length = read_u64(data, size, offset, "CH effective length");
          chunk_bytes = read_u64(data, size, offset, "CH chunk bytes");
          uint64_t envelope_bytes = read_u64(data, size, offset, "CH envelope bytes");

          if ( envelope_reduction != 0 || envelope_bytes != 0 || effective_length != chunk_bytes )
          {
            throw std::runtime_error("unsupported IMC3 raw-data layout: envelopes and multi-event chunks are not implemented");
          }
        }

        if ( peek_u32(data, size, offset, "optional CZ1 key") == key_cz1 )
        {
          (void)read_u32(data, size, offset, "CZ1 key");
          (void)read_u32(data, size, offset, "CZ1 zero");
          (void)read_double(data, size, offset, "CZ1 dz");
          (void)read_double(data, size, offset, "CZ1 z0");
          (void)read_u64(data, size, offset, "CZ1 segment length");
          (void)read_string_u16(data, size, offset, "CZ1 z unit");
        }

        while ( peek_u32(data, size, offset, "optional display key") == key_CD1 )
        {
          skip_display_key(data, size, offset);
        }

        if ( read_u32(data, size, offset, "CN1 key") != key_cn1 )
        {
          throw std::runtime_error("unsupported IMC3 metadata layout: expected |CN1 name");
        }

        uint8_t index_bit = read_u8(data, size, offset, "CN1 index bit");
        if ( index_bit != 0 )
        {
          throw std::runtime_error("unsupported IMC3 channel layout: bit channels are not implemented");
        }

        std::string name = read_string_u16(data, size, offset, "CN1 name");
        std::string comment = read_string_u16(data, size, offset, "CN1 comment");

        while ( offset < size && peek_u32(data, size, offset, "optional property key") == key_cp1 )
        {
          skip_properties_key(data, size, offset);
        }

        channel chn;
        chn.uuid_ = std::to_string(index_channel);
        chn.name_ = name;
        chn.comment_ = comment;
        chn.origin_ = origin_;
        chn.origin_comment_ = origin_comment_;
        chn.language_code_ = language_code_;
        chn.codepage_ = codepage_;
        chn.text_.clear();
        chn.group_index_ = group_index;
        if ( groups_.count(group_index) == 1 )
        {
          chn.group_name_ = groups_.at(group_index).name_;
          chn.group_comment_ = groups_.at(group_index).comment_;
        }

        chn.dimension_ = has_second_component ? 2 : 1;
        chn.xstepwidth_ = dx;
        chn.xstart_ = x0;
        chn.xunit_ = xunit;
        chn.yname_ = name;
        chn.yunit_ = y_component.unit_;
        chn.ydatatp_ = y_component.numeric_type_;
        chn.ysignbits_ = y_component.significant_bits_;
        chn.yfactor_ = y_component.scale_factor_;
        chn.yoffset_ = y_component.scale_offset_;

        if ( has_second_component )
        {
          chn.xdatatp_ = x_component.numeric_type_;
          chn.xsignbits_ = x_component.significant_bits_;
          chn.xfactor_ = x_component.scale_factor_;
          chn.xoffset_ = x_component.scale_offset_;
          chn.xname_ = "x";
        }
        else
        {
          chn.xname_ = "x";
        }

        if ( chn.is_tsa_channel() )
        {
          chn.xname_ = "time";
          chn.xfactor_ = y_component.scale_factor_;
          chn.xoffset_ = y_component.scale_offset_;
          chn.yfactor_ = y_component.scale_factor_;
          chn.yoffset_ = y_component.scale_offset_;
          chn.xstepwidth_ = chn.xfactor_;
          chn.xstart_ = chn.xoffset_;
          chn.xunit_ = xunit.empty() ? y_component.unit_ : xunit;
          chn.yunit_.clear();
        }

        if ( component_combination == 7 )
        {
          chn.xstepwidth_ = dx * 2.0;
        }

        if ( expect_contiguous_chunk )
        {
          size_t y_bytes_per_sample = bytes_per_numeric_type(y_component.numeric_type_);
          size_t x_bytes_per_sample = has_second_component ? bytes_per_numeric_type(x_component.numeric_type_) : 0;
          size_t bytes_per_sample = y_bytes_per_sample + x_bytes_per_sample;
          if ( !chn.is_tsa_channel() && (bytes_per_sample == 0 || chunk_bytes % bytes_per_sample != 0) )
          {
            throw std::runtime_error("invalid IMC3 channel size: raw chunk bytes do not match component widths");
          }

          chn.ybuffer_offset_ = *current_raw_offset;
          chn.raw_data_ = nullptr;
          chn.number_of_samples_ = chn.is_tsa_channel()
            ? 0
            : static_cast<unsigned long int>(chunk_bytes / bytes_per_sample);
          chn.ybuffer_size_ = chn.is_tsa_channel()
            ? static_cast<unsigned long int>(chunk_bytes)
            : static_cast<unsigned long int>(chn.number_of_samples_ * y_bytes_per_sample);
          chn.trigger_time_ = trigger_key == key_ch2
            ? trigger_time_to_time_point(trigger_value / 1.0e9)
            : trigger_time_to_time_point(trigger_value);
          chn.absolute_trigger_time_ = chn.trigger_time_;

          if ( has_second_component )
          {
            chn.xbuffer_offset_ = *current_raw_offset + chn.ybuffer_size_;
            chn.xbuffer_size_ = static_cast<unsigned long int>(chn.number_of_samples_ * x_bytes_per_sample);
          }

          *current_raw_offset += static_cast<unsigned long int>(chunk_bytes);
        }

        convert_strings(chn);
        return chn;
      }

      void register_channel(const channel& chn)
      {
        if ( channels_.count(chn.uuid_) == 0 )
        {
          channel_order_.push_back(chn.uuid_);
        }
        channels_[chn.uuid_] = chn;
      }

      void convert_strings(channel& chn)
      {
        if ( !codepage_.empty() )
        {
          try
          {
            iconverter converter("CP" + codepage_, "UTF-8");
            converter.convert(chn.name_);
            converter.convert(chn.comment_);
            converter.convert(chn.origin_);
            converter.convert(chn.origin_comment_);
            converter.convert(chn.yname_);
            converter.convert(chn.yunit_);
            converter.convert(chn.xname_);
            converter.convert(chn.xunit_);
            converter.convert(chn.group_name_);
            converter.convert(chn.group_comment_);
          }
          catch ( const std::exception& )
          {
            // Keep original bytes if iconv cannot handle the declared codepage.
          }
        }
      }

      void parse_post_raw_metadata(const unsigned char* data, size_t size, size_t metadata_begin, size_t metadata_end)
      {
        size_t offset = metadata_begin;
        if ( read_u32(data, size, offset, "RE1 key") != key_re1 )
        {
          throw std::runtime_error("invalid IMC3 footer target: missing |RE1");
        }

        raw_end_ = metadata_begin;
        parse_ca1_counts(data, size, offset, "post-raw");

        unsigned long int current_raw_offset = 0;
        while ( offset < metadata_end )
        {
          uint32_t next_key = peek_u32(data, size, offset, "metadata key");
          if ( next_key == key_cg1 )
          {
            parse_group_key(data, size, offset);
            continue;
          }

          if ( next_key == key_cp1 )
          {
            skip_properties_key(data, size, offset);
            continue;
          }

          if ( next_key != key_cc1 )
          {
            throw std::runtime_error("unsupported IMC3 metadata key while parsing channel descriptors");
          }

          channel chn = parse_channel_descriptor(data, size, offset, true, &current_raw_offset);
          chn.raw_data_ = data + raw_begin_;
          if ( chn.is_tsa_channel() )
          {
            chn.ensure_tsa_index();
            chn.number_of_samples_ = static_cast<unsigned long int>(chn.tsa_event_index_.size());
          }
          register_channel(chn);
        }

        if ( raw_begin_ + current_raw_offset != raw_end_ )
        {
          throw std::runtime_error("unsupported IMC3 raw-data layout: descriptor sizes do not consume the raw data section");
        }
      }

      void parse_rt1(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "RT1 key") != key_rt1 )
        {
          throw std::runtime_error("invalid IMC3 trigger record");
        }

        uint32_t entries = read_u32(data, size, offset, "RT1 entry count");
        uint64_t trigger_time_ns = read_u64(data, size, offset, "RT1 trigger time");
        auto trigger_tp = trigger_time_to_time_point(static_cast<double>(trigger_time_ns) / 1.0e9);
        for ( uint32_t i = 0; i < entries; ++i )
        {
          (void)read_double(data, size, offset, "RT1 pretrigger");
          uint32_t index_channel = read_u32(data, size, offset, "RT1 channel index");
          int32_t envelope_delayed = read_i32(data, size, offset, "RT1 envelope delay");
          if ( envelope_delayed != 0 )
          {
            throw std::runtime_error("unsupported IMC3 RT1 envelope delay");
          }

          std::string uuid = std::to_string(index_channel);
          if ( channels_.count(uuid) == 1 )
          {
            channels_.at(uuid).trigger_time_ = trigger_tp;
            channels_.at(uuid).absolute_trigger_time_ = trigger_tp;
          }
        }
      }

      void parse_rc5(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "RC5 key") != key_rc5 )
        {
          throw std::runtime_error("invalid IMC3 chunk record");
        }

        uint32_t entries = read_u32(data, size, offset, "RC5 entry count");
        std::vector<std::pair<uint32_t, uint32_t>> chunks;
        chunks.reserve(entries);
        for ( uint32_t i = 0; i < entries; ++i )
        {
          uint32_t index_channel = read_u32(data, size, offset, "RC5 channel index");
          uint32_t chunk_bytes = read_u32(data, size, offset, "RC5 chunk bytes");
          chunks.push_back(std::pair<uint32_t, uint32_t>(index_channel, chunk_bytes));
        }

        for ( const std::pair<uint32_t, uint32_t>& chunk : chunks )
        {
          ensure_available(offset, chunk.second, size, "RC5 chunk payload");
          std::string uuid = std::to_string(chunk.first);
          std::vector<unsigned char>& destination = streamed_raw_data_[uuid];
          destination.insert(destination.end(), data + offset, data + offset + chunk.second);
          offset += chunk.second;
        }
      }

      void skip_ri1_entry(const unsigned char* data, size_t size, size_t& offset)
      {
        uint32_t nested_key = peek_u32(data, size, offset, "Ri1 nested key");
        if ( nested_key == key_rt1 )
        {
          (void)read_u32(data, size, offset, "Ri1 RT1 key");
          uint32_t entries = read_u32(data, size, offset, "Ri1 RT1 entry count");
          (void)read_u64(data, size, offset, "Ri1 RT1 trigger time");
          for ( uint32_t i = 0; i < entries; ++i )
          {
            (void)read_double(data, size, offset, "Ri1 RT1 pretrigger");
            (void)read_u32(data, size, offset, "Ri1 RT1 channel index");
            (void)read_i32(data, size, offset, "Ri1 RT1 envelope delay");
          }
          return;
        }

        if ( nested_key == key_rc5 )
        {
          (void)read_u32(data, size, offset, "Ri1 RC5 key");
          uint32_t entries = read_u32(data, size, offset, "Ri1 RC5 entry count");
          for ( uint32_t i = 0; i < entries; ++i )
          {
            (void)read_u32(data, size, offset, "Ri1 RC5 channel index");
            (void)read_u32(data, size, offset, "Ri1 RC5 chunk bytes");
          }
          return;
        }

        throw std::runtime_error("unsupported IMC3 Ri1 nested key");
      }

      void parse_ri1(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "Ri1 key") != key_ri1 )
        {
          throw std::runtime_error("invalid IMC3 index chain record");
        }

        (void)read_u32(data, size, offset, "Ri1 preceding length");
        uint32_t entries = read_u32(data, size, offset, "Ri1 entry count");
        for ( uint32_t i = 0; i < entries; ++i )
        {
          skip_ri1_entry(data, size, offset);
        }
      }

      void finalize_streamed_channels()
      {
        for ( const std::string& uuid : channel_order_ )
        {
          channel& chn = channels_.at(uuid);
          if ( chn.dimension_ != 1 )
          {
            throw std::runtime_error("unsupported IMC3 streamed layout: only single-component channels are implemented");
          }

          std::vector<unsigned char>& raw = streamed_raw_data_[uuid];
          size_t y_bytes_per_sample = bytes_per_numeric_type(chn.ydatatp_);
          if ( !chn.is_tsa_channel() && raw.size() % y_bytes_per_sample != 0 )
          {
            throw std::runtime_error("invalid IMC3 streamed raw-data size for channel " + uuid);
          }

          chn.raw_data_ = raw.empty() ? nullptr : raw.data();
          chn.ybuffer_offset_ = 0;
          chn.xbuffer_offset_ = 0;
          chn.ybuffer_size_ = static_cast<unsigned long int>(raw.size());
          chn.xbuffer_size_ = 0;
          chn.number_of_samples_ = chn.is_tsa_channel()
            ? (chn.ensure_tsa_index(), static_cast<unsigned long int>(chn.tsa_event_index_.size()))
            : static_cast<unsigned long int>(raw.size() / y_bytes_per_sample);
        }
      }

      void parse_streamed_raw_section(const unsigned char* data, size_t size, size_t& offset, size_t re_offset)
      {
        while ( offset < re_offset )
        {
          uint32_t next_key = peek_u32(data, size, offset, "streamed raw-data key");
          if ( next_key == key_rt1 )
          {
            parse_rt1(data, size, offset);
          }
          else if ( next_key == key_rc5 )
          {
            parse_rc5(data, size, offset);
          }
          else if ( next_key == key_ri1 )
          {
            parse_ri1(data, size, offset);
          }
          else
          {
            throw std::runtime_error("unsupported IMC3 streamed raw-data key");
          }
        }

        finalize_streamed_channels();
      }

      void parse_pre_raw_metadata(const unsigned char* data, size_t size, size_t& offset, size_t re_offset)
      {
        parse_ca1_counts(data, size, offset, "pre-raw");

        while ( offset < re_offset )
        {
          uint32_t next_key = peek_u32(data, size, offset, "pre-raw metadata key");
          if ( next_key == key_cg1 )
          {
            parse_group_key(data, size, offset);
            continue;
          }

          if ( next_key == key_cc1 )
          {
            channel chn = parse_channel_descriptor(data, size, offset, false, nullptr);
            register_channel(chn);
            continue;
          }

          if ( next_key == key_cp1 )
          {
            skip_properties_key(data, size, offset);
            continue;
          }

          if ( next_key == key_rr1 )
          {
            (void)read_u32(data, size, offset, "RR1 key");
            raw_begin_ = offset;
            parse_streamed_raw_section(data, size, offset, re_offset);
            return;
          }

          throw std::runtime_error("unsupported IMC3 pre-raw metadata key");
        }

        throw std::runtime_error("invalid IMC3 layout: missing |RR1 after metadata");
      }

      void parse_cs1_summary(const unsigned char* data, size_t size, size_t& offset)
      {
        if ( read_u32(data, size, offset, "CS1 key") != key_cs1 )
        {
          throw std::runtime_error("invalid IMC3 summary key");
        }

        (void)read_u32(data, size, offset, "CS1 preceding Ri length");
        (void)read_u64(data, size, offset, "CS1 count Ri");
        for ( const std::string& uuid : channel_order_ )
        {
          uint64_t total_bytes = read_u64(data, size, offset, "CS1 total bytes");
          (void)read_u64(data, size, offset, "CS1 chunk count");
          uint64_t total_envelope_bytes = read_u64(data, size, offset, "CS1 total envelope bytes");
          uint64_t count_envelope_chunks = read_u64(data, size, offset, "CS1 envelope chunk count");
          (void)read_u32(data, size, offset, "CS1 event count");
          (void)read_u32(data, size, offset, "CS1 reserved");

          if ( total_envelope_bytes != 0 || count_envelope_chunks != 0 )
          {
            throw std::runtime_error("unsupported IMC3 summary: envelope data is not implemented");
          }

          if ( channels_.count(uuid) == 1 )
          {
            const channel& chn = channels_.at(uuid);
            if ( chn.dimension_ == 1 && total_bytes != chn.ybuffer_size_ )
            {
              throw std::runtime_error("IMC3 summary total bytes do not match parsed chunk data");
            }
          }
        }
      }

      void parse_trailing_summary(const unsigned char* data, size_t size, size_t metadata_begin, size_t metadata_end)
      {
        size_t offset = metadata_begin;
        if ( read_u32(data, size, offset, "RE1 key") != key_re1 )
        {
          throw std::runtime_error("invalid IMC3 footer target: missing |RE1");
        }

        raw_end_ = metadata_begin;
        while ( offset < metadata_end )
        {
          uint32_t next_key = peek_u32(data, size, offset, "post-RE key");
          if ( next_key == key_cs1 )
          {
            parse_cs1_summary(data, size, offset);
            continue;
          }
          if ( next_key == key_cp1 )
          {
            skip_properties_key(data, size, offset);
            continue;
          }
          throw std::runtime_error("unsupported IMC3 trailing metadata key");
        }
      }

    public:
      dataset() = default;
      dataset(const dataset&) = delete;
      dataset& operator=(const dataset&) = delete;
      dataset(dataset&&) = delete;
      dataset& operator=(dataset&&) = delete;

      void reset()
      {
        clear();
      }

      void parse(const unsigned char* data, size_t size)
      {
        clear();
        size_t offset = parse_header(data, size);
        size_t re_offset = parse_jump_back(data, size);
        uint32_t next_key = peek_u32(data, size, offset, "key after IMC3 header");
        if ( next_key == key_ca1 )
        {
          parse_pre_raw_metadata(data, size, offset, re_offset);
          parse_trailing_summary(data, size, re_offset, size - 32);
        }
        else if ( next_key == key_rr1 )
        {
          (void)read_u32(data, size, offset, "RR1 key");
          if ( read_u32(data, size, offset, "RN1 key") != key_rn1 )
          {
            throw std::runtime_error("unsupported IMC3 raw-data layout: only |RN1 is supported in contiguous mode");
          }
          raw_begin_ = offset;
          parse_post_raw_metadata(data, size, re_offset, size - 32);
        }
        else
        {
          throw std::runtime_error("unsupported IMC3 layout after header");
        }
      }

      size_t channel_count() const
      {
        return channel_order_.size();
      }

      std::vector<std::string> get_channels(bool json, bool include_data) const
      {
        std::vector<std::string> result;
        for ( const std::string& uuid : channel_order_ )
        {
          const channel& chn = channels_.at(uuid);
          result.push_back(json ? chn.get_json(include_data) : chn.get_info());
        }
        return result;
      }

      std::vector<std::string> list_channels() const
      {
        std::vector<std::string> names;
        for ( const std::string& uuid : channel_order_ )
        {
          names.push_back(channels_.at(uuid).name_);
        }
        return names;
      }

      imc::channel get_legacy_channel(const std::string& uuid) const
      {
        const channel& src = get_channel(uuid);

        imc::channel dst;
        dst.uuid_ = src.uuid_;
        dst.name_ = src.name_;
        dst.comment_ = src.comment_;
        dst.origin_ = src.origin_;
        dst.origin_comment_ = src.origin_comment_;
        dst.text_ = src.text_;
        dst.trigger_time_ = src.trigger_time_;
        dst.absolute_trigger_time_ = src.absolute_trigger_time_;
        dst.language_code_ = src.language_code_;
        dst.codepage_ = src.codepage_;
        dst.yname_ = src.yname_;
        dst.yunit_ = src.yunit_;
        dst.xname_ = src.xname_;
        dst.xunit_ = src.xunit_;
        dst.xstepwidth_ = src.xstepwidth_;
        dst.xstart_ = src.xstart_;
        dst.xprec_ = src.xprec_;
        dst.dimension_ = src.dimension_;
        dst.xsignbits_ = src.xsignbits_;
        dst.ysignbits_ = src.ysignbits_;
        dst.xnum_bytes_ = static_cast<int>(imc::imc3::bytes_per_numeric_type(src.xdatatp_));
        dst.ynum_bytes_ = static_cast<int>(imc::imc3::bytes_per_numeric_type(src.ydatatp_));
        dst.xbuffer_offset_ = src.xbuffer_offset_;
        dst.ybuffer_offset_ = src.ybuffer_offset_;
        dst.xbuffer_size_ = src.xbuffer_size_;
        dst.ybuffer_size_ = src.ybuffer_size_;
        dst.xdatatp_ = src.xdatatp_;
        dst.ydatatp_ = src.ydatatp_;
        dst.xfactor_ = src.xfactor_;
        dst.yfactor_ = src.yfactor_;
        dst.xoffset_ = src.xoffset_;
        dst.yoffset_ = src.yoffset_;
        dst.number_of_samples_ = src.number_of_samples_;
        dst.group_index_ = src.group_index_;
        dst.group_name_ = src.group_name_;
        dst.group_comment_ = src.group_comment_;
        if ( src.is_tsa_channel() )
        {
          dst.set_tsa_raw_payload(src.raw_data_ + src.ybuffer_offset_, src.ybuffer_size_);
        }
        dst.set_chunk_reader([this, uuid](unsigned long int start, unsigned long int count, bool include_x, bool raw_mode)
        {
          return read_channel_chunk(uuid, start, count, include_x, raw_mode);
        });
        return dst;
      }

      unsigned long int get_channel_length(const std::string& uuid) const
      {
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }
        return channels_.at(uuid).number_of_samples_;
      }

      std::vector<imc::tsa_event> read_channel_events(const std::string& uuid,
                                                      unsigned long int start,
                                                      unsigned long int count) const
      {
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }

        return channels_.at(uuid).read_tsa_events(start, count);
      }

      int get_channel_numeric_type(const std::string& uuid) const
      {
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }
        return static_cast<int>(channels_.at(uuid).ydatatp_);
      }

      const channel& get_channel(const std::string& uuid) const
      {
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }
        return channels_.at(uuid);
      }

      channel_chunk read_channel_chunk(const std::string& uuid, unsigned long int start, unsigned long int count,
                                       bool include_x, bool raw_mode) const
      {
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }
        return channels_.at(uuid).read_chunk(start, count, include_x, raw_mode);
      }

      void print_channel(const std::string& uuid, const std::string& outputfile, char delimiter,
                         unsigned long int chunk_size) const
      {
        std::filesystem::path pdf = outputfile;
        if ( !std::filesystem::is_directory(pdf.parent_path()) )
        {
          throw std::runtime_error("required directory does not exist: " + pdf.parent_path().u8string());
        }
        if ( channels_.count(uuid) == 0 )
        {
          throw std::runtime_error("channel does not exist:" + uuid);
        }
        channels_.at(uuid).print(outputfile, delimiter, 25, 9, chunk_size);
      }

      void print_channels(const std::string& outputdir, char delimiter, unsigned long int chunk_size) const
      {
        std::filesystem::path pd = outputdir;
        if ( !std::filesystem::is_directory(pd) )
        {
          throw std::runtime_error("given directory does not exist: " + outputdir);
        }

        for ( const std::string& uuid : channel_order_ )
        {
          const channel& chn = channels_.at(uuid);
          std::string channel_id = std::string("channel_") + uuid;
          std::string filename = chn.name_.empty() ? channel_id + ".csv" : chn.name_ + ".csv";
          std::filesystem::path output = pd / filename;
          chn.print(output.u8string(), delimiter, 25, 9, chunk_size);
        }
      }
    };
  }
}

#endif

//---------------------------------------------------------------------------//