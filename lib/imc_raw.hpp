//---------------------------------------------------------------------------//

#ifndef IMCRAW
#define IMCRAW

#include <fstream>
#include <filesystem>
#include <iostream>

#include "imc_buffer.hpp"
#include "imc_key.hpp"
#include "imc_block.hpp"
#include "imc_datatype.hpp"
#include "imc_object.hpp"
#include "imc_channel.hpp"
#include "imc_imc2.hpp"
#include "imc_imc3.hpp"

//---------------------------------------------------------------------------//

namespace imc
{
  struct channel_events
  {
    bool numeric = false;
    std::vector<double> timestamps;
    std::vector<std::string> texts;
    std::vector<unsigned long int> counts;
    std::vector<double> xstarts;
    std::vector<double> xstepwidths;
    std::vector<double> yvalues;
  };

  struct channel_event_chunk
  {
    bool numeric = false;
    std::vector<double> timestamps;
    std::vector<std::string> texts;
    std::vector<unsigned long int> counts;
    std::vector<double> xstarts;
    std::vector<double> xstepwidths;
    std::vector<double> yvalues;
    unsigned long int start = 0;
    unsigned long int count = 0;
  };

  class raw
  {
    enum class file_format
    {
      imc2,
      imc3
    };

    // (path of) raw-file and its basename
    std::string raw_file_, file_name_;

    // buffer of raw-file
    imc::MemoryMappedFile buffer_;

    file_format format_ = file_format::imc2;
    imc::imc2::dataset imc2_dataset_;
    imc::imc3::dataset imc3_dataset_;

    template<typename ReadTsaFn, typename ReadNumericFn, typename ReadNumericValuesFn>
    static channel_events build_channel_events(unsigned long int total,
                                               ReadTsaFn&& read_tsa,
                                               ReadNumericFn&& read_numeric,
                                               ReadNumericValuesFn&& read_numeric_values,
                                               bool tsa_channel)
    {
      channel_events events;
      if ( tsa_channel )
      {
        std::vector<imc::tsa_event> decoded_events = read_tsa(0, total);
        events.timestamps.reserve(decoded_events.size());
        events.texts.reserve(decoded_events.size());
        for ( const imc::tsa_event& event : decoded_events )
        {
          events.timestamps.push_back(event.timestamp);
          events.texts.push_back(event.text);
        }
        return events;
      }

      events.numeric = true;
      std::vector<imc::numeric_event_descriptor> decoded_events = read_numeric(0, total);
      events.timestamps.reserve(decoded_events.size());
      events.counts.reserve(decoded_events.size());
      events.xstarts.reserve(decoded_events.size());
      events.xstepwidths.reserve(decoded_events.size());
      for ( const imc::numeric_event_descriptor& event : decoded_events )
      {
        events.timestamps.push_back(event.timestamp);
        events.counts.push_back(event.count);
        events.xstarts.push_back(event.xstart);
        events.xstepwidths.push_back(event.xstepwidth);
        std::vector<double> yvalues = read_numeric_values(event.start, event.count);
        events.yvalues.insert(events.yvalues.end(), yvalues.begin(), yvalues.end());
      }
      return events;
    }

    template<typename ReadTsaFn, typename ReadNumericFn, typename ReadNumericValuesFn>
    static channel_event_chunk build_channel_event_chunk(unsigned long int start,
                                                         unsigned long int count,
                                                         ReadTsaFn&& read_tsa,
                                                         ReadNumericFn&& read_numeric,
                                                         ReadNumericValuesFn&& read_numeric_values,
                                                         bool tsa_channel)
    {
      channel_event_chunk chunk;
      chunk.start = start;
      if ( tsa_channel )
      {
        std::vector<imc::tsa_event> events = read_tsa(start, count);
        chunk.count = static_cast<unsigned long int>(events.size());
        chunk.timestamps.reserve(events.size());
        chunk.texts.reserve(events.size());
        for ( const imc::tsa_event& event : events )
        {
          chunk.timestamps.push_back(event.timestamp);
          chunk.texts.push_back(event.text);
        }
        return chunk;
      }

      chunk.numeric = true;
      std::vector<imc::numeric_event_descriptor> events = read_numeric(start, count);
      chunk.count = static_cast<unsigned long int>(events.size());
      chunk.timestamps.reserve(events.size());
      chunk.counts.reserve(events.size());
      chunk.xstarts.reserve(events.size());
      chunk.xstepwidths.reserve(events.size());
      for ( const imc::numeric_event_descriptor& event : events )
      {
        chunk.timestamps.push_back(event.timestamp);
        chunk.counts.push_back(event.count);
        chunk.xstarts.push_back(event.xstart);
        chunk.xstepwidths.push_back(event.xstepwidth);
        std::vector<double> yvalues = read_numeric_values(event.start, event.count);
        chunk.yvalues.insert(chunk.yvalues.end(), yvalues.begin(), yvalues.end());
      }
      return chunk;
    }

  public:

    // constructor
    raw() { };
    raw(std::string raw_file): raw_file_(raw_file) { set_file(raw_file); };

    // Delete copy and move operations because of self-referential pointers in channels_
    raw(const raw&) = delete;
    raw& operator=(const raw&) = delete;
    raw(raw&&) = delete;
    raw& operator=(raw&&) = delete;

    // provide new raw-file
    void set_file(std::string raw_file)
    {
      raw_file_ = raw_file;
      this->fill_buffer();

      if ( this->is_imc3_file() )
      {
        format_ = file_format::imc3;
        imc2_dataset_.reset();
        imc3_dataset_.parse(buffer_.data(), buffer_.size());
      }
      else
      {
        format_ = file_format::imc2;
        imc3_dataset_.reset();
        imc2_dataset_.parse(raw_file_, buffer_.data(), buffer_.size());
      }
    }

  private:

    // open file and stream data into buffer
    void fill_buffer()
    {
      // open file and put data in buffer
      try {
        buffer_.map(raw_file_);
      } catch ( const std::exception& e ) {
        throw std::runtime_error(
          std::string("failed to open raw-file and stream data in buffer: ") + e.what()
        );
      }
    }

    bool is_imc3_file() const
    {
      const unsigned char* data = buffer_.data();
      size_t size = buffer_.size();
      return size >= 8 && std::memcmp(data, "|imc3,1;", 8) == 0;
    }

  public:

    // provide buffer size
    unsigned long int buffer_size()
    {
      return (unsigned long int)buffer_.size();
    }

    // get blocks
    std::vector<imc::block>& blocks()
    {
      return imc2_dataset_.blocks();
    }

    // get computational complexity
    unsigned long int& computational_complexity()
    {
      return imc2_dataset_.computational_complexity();
    }

    // get list of channels with metadata
    std::vector<std::string> get_channels(bool json = false, bool include_data = false)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channels(json, include_data);
      }

      return imc2_dataset_.get_channels(json, include_data);
    }

    channel_metadata get_channel_metadata(const std::string& uuid) const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channel_metadata(uuid);
      }

      return imc2_dataset_.get_channel_metadata(uuid);
    }

    channel_representation get_channel_representation(const std::string& uuid) const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channel_representation(uuid);
      }

      return imc2_dataset_.get_channel_representation(uuid);
    }

    file_metadata get_file_metadata() const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_file_metadata();
      }
      return imc2_dataset_.get_file_metadata();
    }

    std::vector<group_metadata> get_groups_metadata() const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_groups_metadata();
      }
      return imc2_dataset_.get_groups_metadata();
    }

    std::vector<text_object_metadata> get_text_objects_metadata() const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_text_objects_metadata();
      }
      return imc2_dataset_.get_text_objects_metadata();
    }

    uint64_t get_tsa_payload_size_bytes(const std::string& uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_tsa_payload_size_bytes(uuid);
      }

      return imc2_dataset_.get_tsa_payload_size_bytes(uuid);
    }

    std::vector<unsigned char> read_tsa_payload(const std::string& uuid,
                                                 uint64_t offset_bytes,
                                                 uint64_t length_bytes)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.read_tsa_payload(uuid, offset_bytes, length_bytes);
      }

      return imc2_dataset_.read_tsa_payload(uuid, offset_bytes, length_bytes);
    }

    std::vector<tsa_record_descriptor> read_tsa_record_descriptors(
      const std::string& uuid,
      uint64_t start_record_ordinal,
      uint64_t record_count
    )
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.read_tsa_record_descriptors(uuid, start_record_ordinal, record_count);
      }

      return imc2_dataset_.read_tsa_record_descriptors(uuid, start_record_ordinal, record_count);
    }

    std::vector<unsigned char> read_tsa_record_payload(const std::string& uuid,
                                                        uint64_t record_ordinal)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.read_tsa_record_payload(uuid, record_ordinal);
      }

      return imc2_dataset_.read_tsa_record_payload(uuid, record_ordinal);
    }

    std::vector<unsigned char> read_component_payload(const std::string& uuid,
                                                       channel_component component,
                                                       uint64_t offset_bytes,
                                                       uint64_t length_bytes) const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.read_component_payload(uuid, component, offset_bytes, length_bytes);
      }
      return imc2_dataset_.read_component_payload(uuid, component, offset_bytes, length_bytes);
    }

    std::vector<tsa_channel_segment> get_tsa_channel_segments(const std::string& uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_tsa_channel_segments(uuid);
      }

      return imc2_dataset_.get_tsa_channel_segments(uuid);
    }

    std::vector<numeric_channel_segment> get_numeric_channel_segments(const std::string& uuid) const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_numeric_channel_segments(uuid);
      }

      return imc2_dataset_.get_numeric_channel_segments(uuid);
    }

    std::vector<channel_metadata> get_channels_metadata() const
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channels_metadata();
      }

      return imc2_dataset_.get_channels_metadata();
    }

    // get particular channel including data by its uuid
    imc::channel get_channel(std::string uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_legacy_channel(uuid);
      }

      return imc2_dataset_.get_channel(uuid);
    }

    // list a particular type of block
    std::vector<imc::block> list_blocks(const imc::key &mykey)
    {
      return imc2_dataset_.list_blocks(mykey);
    }

    // list all groups (associated to blocks "CB")
    std::vector<imc::block> list_groups()
    {
      return imc2_dataset_.list_groups();
    }

    // list all channels
    std::vector<std::string> list_channels()
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.list_channels();
      }

      return imc2_dataset_.list_channels();
    }

    // get length of a channel
    unsigned long int get_channel_length(std::string uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channel_length(uuid);
      }

      return imc2_dataset_.get_channel_length(uuid);
    }

    // get numeric type of a channel
    int get_channel_numeric_type(std::string uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channel_numeric_type(uuid);
      }

      return imc2_dataset_.get_channel_numeric_type(uuid);
    }

    bool is_event_channel(std::string uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.get_channel(uuid).is_event_channel();
      }

      return imc2_dataset_.get_channel(uuid).is_event_channel();
    }

    // read a chunk of channel data
    channel_chunk read_channel_chunk(std::string uuid, unsigned long int start, unsigned long int count, bool include_x, bool raw_mode)
    {
      if ( format_ == file_format::imc3 )
      {
        return imc3_dataset_.read_channel_chunk(uuid, start, count, include_x, raw_mode);
      }

      return imc2_dataset_.read_channel_chunk(uuid, start, count, include_x, raw_mode);
    }

    channel_events get_channel_events(std::string uuid)
    {
      if ( format_ == file_format::imc3 )
      {
        const imc::imc3::channel& channel = imc3_dataset_.get_channel(uuid);
        if ( !channel.is_event_channel() )
        {
          throw std::runtime_error("channel is numeric; use read_channel_chunk() instead");
        }

        unsigned long int total = get_channel_length(uuid);
        return build_channel_events(
          total,
          [&](unsigned long int start, unsigned long int count) { return channel.read_tsa_events(start, count); },
          [&](unsigned long int start, unsigned long int count) { return channel.read_numeric_events(start, count); },
          [&](unsigned long int start, unsigned long int count) { return channel.read_numeric_event_y_values(start, count); },
          channel.is_tsa_channel()
        );
      }

      imc::channel channel = imc2_dataset_.get_channel(uuid);
      if ( !channel.is_event_channel() )
      {
        throw std::runtime_error("channel is numeric; use read_channel_chunk() instead");
      }

      unsigned long int total = get_channel_length(uuid);
      return build_channel_events(
        total,
        [&](unsigned long int start, unsigned long int count) { return channel.read_tsa_events(start, count); },
        [&](unsigned long int start, unsigned long int count) { return channel.read_numeric_events(start, count); },
        [&](unsigned long int start, unsigned long int count) { return channel.read_numeric_event_y_values(start, count); },
        channel.is_tsa_channel()
      );
    }

    channel_event_chunk read_channel_event_chunk(std::string uuid, unsigned long int start, unsigned long int count)
    {
      if ( format_ == file_format::imc3 )
      {
        const imc::imc3::channel& channel = imc3_dataset_.get_channel(uuid);
        if ( !channel.is_event_channel() )
        {
          throw std::runtime_error("channel is numeric; use read_channel_chunk() instead");
        }

        return build_channel_event_chunk(
          start,
          count,
          [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_tsa_events(event_start, event_count); },
          [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_numeric_events(event_start, event_count); },
          [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_numeric_event_y_values(event_start, event_count); },
          channel.is_tsa_channel()
        );
      }

      imc::channel channel = imc2_dataset_.get_channel(uuid);
      if ( !channel.is_event_channel() )
      {
        throw std::runtime_error("channel is numeric; use read_channel_chunk() instead");
      }

      return build_channel_event_chunk(
        start,
        count,
        [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_tsa_events(event_start, event_count); },
        [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_numeric_events(event_start, event_count); },
        [&](unsigned long int event_start, unsigned long int event_count) { return channel.read_numeric_event_y_values(event_start, event_count); },
        channel.is_tsa_channel()
      );
    }

    // print single specific channel
    void print_channel(std::string channeluuid, std::string outputfile, const char sep, unsigned long int chunk_size = 100000)
    {
      if ( format_ == file_format::imc3 )
      {
        imc3_dataset_.print_channel(channeluuid, outputfile, sep, chunk_size);
        return;
      }

      imc2_dataset_.print_channel(channeluuid, outputfile, sep, chunk_size);
    }

    // print all channels into given directory
    void print_channels(std::string output, const char sep, unsigned long int chunk_size = 100000)
    {
      if ( format_ == file_format::imc3 )
      {
        imc3_dataset_.print_channels(output, sep, chunk_size);
        return;
      }

      imc2_dataset_.print_channels(output, sep, chunk_size);
    }

    unsigned long int channel_count()
    {
      return format_ == file_format::imc3
        ? static_cast<unsigned long int>(imc3_dataset_.channel_count())
        : imc2_dataset_.channel_count();
    }

  };

}

#endif

//---------------------------------------------------------------------------//
