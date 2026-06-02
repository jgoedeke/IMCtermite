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
    std::vector<double> timestamps;
    std::vector<std::string> texts;
  };

  struct channel_event_chunk
  {
    std::vector<double> timestamps;
    std::vector<std::string> texts;
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
      unsigned long int total = get_channel_length(uuid);
      std::vector<imc::tsa_event> decoded_events = format_ == file_format::imc3
        ? imc3_dataset_.read_channel_events(uuid, 0, total)
        : imc2_dataset_.read_channel_events(uuid, 0, total);

      channel_events events;
      events.timestamps.reserve(decoded_events.size());
      events.texts.reserve(decoded_events.size());
      for ( const imc::tsa_event& event : decoded_events )
      {
        events.timestamps.push_back(event.timestamp);
        events.texts.push_back(event.text);
      }
      return events;
    }

    channel_event_chunk read_channel_event_chunk(std::string uuid, unsigned long int start, unsigned long int count)
    {
      std::vector<imc::tsa_event> events = format_ == file_format::imc3
        ? imc3_dataset_.read_channel_events(uuid, start, count)
        : imc2_dataset_.read_channel_events(uuid, start, count);

      channel_event_chunk chunk;
      chunk.start = start;
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
