//---------------------------------------------------------------------------//

#ifndef IMCIMC2
#define IMCIMC2

#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "imc_block.hpp"
#include "imc_channel.hpp"
#include "imc_datatype.hpp"
#include "imc_key.hpp"
#include "imc_object.hpp"

//---------------------------------------------------------------------------//

namespace imc
{
  namespace imc2
  {
    class dataset
    {
      std::string raw_file_;
      const unsigned char* buffer_ = nullptr;
      size_t buffer_size_ = 0;

      std::vector<imc::block> rawblocks_;
      std::map<std::string,imc::block> mapblocks_;
      unsigned long int cplxcnt_ = 0;
      std::map<std::string,imc::channel> channels_;
      std::vector<std::string> channel_order_;
      imc::file_metadata file_metadata_;
      std::vector<imc::group_metadata> groups_metadata_;
      std::vector<imc::text_object_metadata> text_objects_metadata_;

      void collect_container_metadata()
      {
        file_metadata_ = {};
        groups_metadata_.clear();
        text_objects_metadata_.clear();
        for ( imc::block& block : rawblocks_ )
        {
          const std::string key_name = block.get_key().name_;
          if ( key_name == "NO" )
          {
            imc::origin_data origin;
            origin.parse(buffer_, block.get_parameters());
            file_metadata_.producer = origin.generator_;
            file_metadata_.comment = origin.comment_;
          }
          else if ( key_name == "NL" )
          {
            imc::language language;
            language.parse(buffer_, block.get_parameters());
            file_metadata_.language_code = language.language_code_;
            file_metadata_.codepage = language.codepage_;
          }
          else if ( key_name == "CB" )
          {
            imc::groupobj group;
            group.parse(buffer_, block.get_parameters());
            groups_metadata_.push_back({1, group.group_index_, group.name_, group.comment_});
          }
          else if ( key_name == "CT" )
          {
            imc::text text;
            text.parse(buffer_, block.get_parameters());
            text_objects_metadata_.push_back({1, text.group_index_, text.name_, text.comment_, text.text_});
          }
        }
      }

      void check_consistency()
      {
        for ( unsigned long int b = 0; b < this->rawblocks_.size()-1 && this->rawblocks_.size() > 0; b++ )
        {
          if ( this->rawblocks_[b].get_end() >= this->rawblocks_[b+1].get_begin() )
          {
            throw std::runtime_error(
              std::string("inconsistent subsequent blocks:\n")
              + std::to_string(b) + std::string("-th block:\n") + this->rawblocks_[b].get_info()
              + std::string("\n")
              + std::to_string(b+1) + std::string("-th block:\n") + this->rawblocks_[b+1].get_info() );
          }
        }
      }

      void parse_blocks()
      {
        rawblocks_.clear();
        cplxcnt_ = 0;

        for ( unsigned long int i = 0; i < buffer_size_; ++i )
        {
          cplxcnt_++;

          if ( buffer_[i] == ch_bgn_ )
          {
            if ( buffer_[i+1] == imc::key_crit_ || buffer_[i+1] == imc::key_non_crit_ )
            {
              std::string newkey = { (char)buffer_[i+1], (char)buffer_[i+2] };
              imc::key itkey(buffer_[i+1] == imc::key_crit_,newkey);

              if ( buffer_[i+3] == ch_sep_ )
              {
                std::string vers("");
                unsigned long int pos = 4;
                while ( buffer_[i+pos] != ch_sep_ )
                {
                  vers.push_back((char)buffer_[i+pos]);
                  pos++;
                }
                int version = std::stoi(vers);

                itkey.version_ = version;
                itkey = imc::get_key(itkey.critical_,itkey.name_,itkey.version_);

                if ( imc::check_key(itkey) )
                {
                  std::string leng("");
                  pos++;
                  while ( buffer_[i+pos] != ch_sep_ )
                  {
                    leng.push_back((char)buffer_[i+pos]);
                    pos++;
                  }
                  unsigned long int length = std::stoul(leng);

                  imc::block blk(itkey,i,
                                       i+pos+1+length,
                                       raw_file_, buffer_, buffer_size_);

                  rawblocks_.push_back(blk);

                  if ( i+length < buffer_size_ )
                  {
                    i += length;
                  }
                }
                else
                {
                  if ( buffer_[i+1] == imc::key_crit_ )
                  {
                    throw std::runtime_error(
                      std::string("unknown critical key: ") + newkey + std::to_string(version)
                    );
                  }
                  else
                  {
                    std::cout<<"WARNING: unknown noncritical key '"
                             <<newkey<<version<<"' will be ignored\n";
                  }
                }
              }
              else
              {
                throw std::runtime_error(
                    std::string("invalid block or corrupt buffer at byte: ")
                  + std::to_string(i+3)
                );
              }
            }
          }
        }

        this->check_consistency();
      }

      void generate_block_map()
      {
        mapblocks_.clear();

        for ( imc::block blk: rawblocks_ )
        {
          mapblocks_.insert( std::pair<std::string,imc::block>(blk.get_uuid(),blk) );
        }
      }

      std::vector<imc::numeric_event_descriptor> parse_numeric_event_descriptors(imc::block event_block) const
      {
        size_t block_begin = static_cast<size_t>(event_block.get_begin());
        size_t block_end = static_cast<size_t>(event_block.get_end());
        const unsigned char* event_data = buffer_ + block_begin;
        size_t block_size = block_end - block_begin + 1;
        size_t comma_count = 0;
        size_t payload_offset = 0;
        for ( ; payload_offset < block_size; ++payload_offset )
        {
          if ( event_data[payload_offset] == ch_sep_ )
          {
            comma_count++;
            if ( comma_count == 5 )
            {
              payload_offset++;
              break;
            }
          }
        }

        if ( comma_count != 5 || block_size == 0 || event_data[block_size - 1] != ch_end_ )
        {
          throw std::runtime_error("invalid IMC2 numeric event metadata block");
        }

        return imc::parse_imc2_numeric_event_index(
          event_data + payload_offset,
          block_size - payload_offset - 1
        );
      }

      void finalize_numeric_event_channels()
      {
        std::vector<imc::channel*> numeric_event_channels;
        for ( const std::string& uuid : channel_order_ )
        {
          imc::channel& channel = channels_.at(uuid);
          if ( !channel.chnenv_.Cvuuid_.empty() )
          {
            numeric_event_channels.push_back(&channel);
          }
        }

        if ( numeric_event_channels.empty() )
        {
          return;
        }

        std::vector<imc::block*> event_blocks;
        for ( imc::block& blk : rawblocks_ )
        {
          if ( blk.get_key().name_ == "CV" )
          {
            event_blocks.push_back(&blk);
          }
        }

        if ( event_blocks.size() != 1 )
        {
          throw std::runtime_error("invalid IMC2 numeric event metadata: expected a single shared CV block for multi-channel event files");
        }

        std::vector<imc::numeric_event_descriptor> descriptors = parse_numeric_event_descriptors(*event_blocks[0]);

        size_t descriptor_index = 0;
        unsigned long int event_sample_base = 0;
        for ( imc::channel* channel_ptr : numeric_event_channels )
        {
          if ( channel_ptr->ysignbits_ == 0 )
          {
            throw std::runtime_error("invalid IMC2 numeric event channel layout");
          }

          unsigned long int channel_total_samples = channel_ptr->ybuffer_size_ / static_cast<unsigned long int>(channel_ptr->ysignbits_ / 8);
          std::vector<imc::numeric_event_descriptor> channel_events;
          unsigned long int accumulated = 0;

          while ( accumulated < channel_total_samples )
          {
            if ( descriptor_index >= descriptors.size() )
            {
              throw std::runtime_error("invalid IMC2 numeric event metadata: missing event descriptors");
            }

            imc::numeric_event_descriptor descriptor = descriptors[descriptor_index++];
            if ( descriptor.start != event_sample_base + accumulated )
            {
              throw std::runtime_error("invalid IMC2 numeric event metadata: unexpected event start offset");
            }

            descriptor.start -= event_sample_base;
            channel_events.push_back(descriptor);
            accumulated += descriptor.count;
            if ( accumulated > channel_total_samples )
            {
              throw std::runtime_error("invalid IMC2 numeric event metadata: event counts exceed raw sample data");
            }
          }

          channel_ptr->set_numeric_event_payload(channel_events, channel_total_samples);
          event_sample_base += channel_total_samples;
        }

        if ( descriptor_index != descriptors.size() )
        {
          throw std::runtime_error("invalid IMC2 numeric event metadata: trailing descriptors were not assigned to a channel");
        }
      }

      void generate_channel_env()
      {
        channels_.clear();
        channel_order_.clear();
        file_metadata_ = {};
        groups_metadata_.clear();
        text_objects_metadata_.clear();

        imc::channel_env chnenv;
        chnenv.reset();

        imc::component_env *compenv_ptr = nullptr;
        std::vector<std::string> pending_property_uuids;

        auto finalize_channel = [&]()
        {
          if ( chnenv.CNuuid_.empty() )
          {
            return;
          }

          chnenv.uuid_ = chnenv.CNuuid_;

          if ( chnenv.CSuuid_.empty() )
          {
            for ( imc::block blkCS: rawblocks_ )
            {
              if ( blkCS.get_key().name_ == "CS"
                && blkCS.get_begin() > static_cast<unsigned long int>(stol(chnenv.uuid_)) )
              {
                chnenv.CSuuid_ = blkCS.get_uuid();
              }
            }
          }

          const std::string channel_uuid = chnenv.CNuuid_;
          channels_.insert( std::pair<std::string,imc::channel>
            (channel_uuid,imc::channel(chnenv,&mapblocks_,buffer_))
          );
          channel_order_.push_back(channel_uuid);

          chnenv.CNuuid_.clear();

          chnenv.CBuuid_.clear();
          chnenv.CGuuid_.clear();
          chnenv.CIuuid_.clear();
          chnenv.CTuuid_.clear();
          chnenv.CSuuid_.clear();
          chnenv.Cvuuid_.clear();
          chnenv.CVuuid_.clear();
          chnenv.Npuuids_.clear();

          chnenv.compenv1_.reset();
          chnenv.compenv2_.reset();

          compenv_ptr = nullptr;
        };

        for ( imc::block blk: rawblocks_ )
        {
          if ( blk.get_key().name_ == "Np" )
          {
            if ( chnenv.CNuuid_.empty() )
            {
              pending_property_uuids.push_back(blk.get_uuid());
            }
            else
            {
              chnenv.Npuuids_.push_back(blk.get_uuid());
            }
            continue;
          }
          if ( blk.get_key().name_ == "CT" )
          {
            if ( !chnenv.CNuuid_.empty() )
            {
              finalize_channel();
            }
            continue;
          }

          if ( blk.get_key().name_ == "NO" ) chnenv.NOuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "NL" ) chnenv.NLuuid_ = blk.get_uuid();

          else if ( blk.get_key().name_ == "CB" ) chnenv.CBuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CG" ) chnenv.CGuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CI" ) chnenv.CIuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CN" )
          {
            chnenv.CNuuid_ = blk.get_uuid();
            chnenv.Npuuids_ = std::move(pending_property_uuids);
            pending_property_uuids.clear();
          }
          else if ( blk.get_key().name_ == "CS" ) chnenv.CSuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "Cv" ) chnenv.Cvuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CV" ) chnenv.CVuuid_ = blk.get_uuid();

          else if ( blk.get_key().name_ == "CC" )
          {
            imc::component component;
            component.parse(buffer_, blk.get_parameters());
            if ( component.component_index_ == 1 ) compenv_ptr = &chnenv.compenv1_;
            else if ( component.component_index_ == 2 ) compenv_ptr = &chnenv.compenv2_;
            else throw std::runtime_error("invalid component index in CC block");
            compenv_ptr->CCuuid_ = blk.get_uuid();
            compenv_ptr->uuid_ = compenv_ptr->CCuuid_;
          }
          else if ( blk.get_key().name_ == "CD" )
          {
            if (compenv_ptr == nullptr) chnenv.CDuuid_ = blk.get_uuid();
            else compenv_ptr->CDuuid_ = blk.get_uuid();
          }
          else if ( blk.get_key().name_ == "NT" )
          {
            if (compenv_ptr == nullptr) chnenv.NTuuid_ = blk.get_uuid();
            else compenv_ptr->NTuuid_ = blk.get_uuid();
          }
          else if ( blk.get_key().name_ == "Cb" ) compenv_ptr->Cbuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CP" ) compenv_ptr->CPuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CR" ) compenv_ptr->CRuuid_ = blk.get_uuid();

          if ( !chnenv.CNuuid_.empty() )
          {
            if ( blk.get_key().name_ == "CB" || blk.get_key().name_ == "CG"
              || blk.get_key().name_ == "CI" )
            {
              finalize_channel();
            }
          }

          if ( blk.get_key().name_ == "CB" ) chnenv.CBuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CG" ) chnenv.CGuuid_ = blk.get_uuid();
          else if ( blk.get_key().name_ == "CI" ) chnenv.CIuuid_ = blk.get_uuid();
        }

        finalize_channel();
        finalize_numeric_event_channels();
      }

    public:
      dataset() = default;

      void clear()
      {
        raw_file_.clear();
        buffer_ = nullptr;
        buffer_size_ = 0;
        rawblocks_.clear();
        mapblocks_.clear();
        cplxcnt_ = 0;
        channels_.clear();
        channel_order_.clear();
      }

      void reset()
      {
        clear();
      }

      void parse(const std::string& raw_file, const unsigned char* buffer, size_t buffer_size)
      {
        clear();
        raw_file_ = raw_file;
        buffer_ = buffer;
        buffer_size_ = buffer_size;
        parse_blocks();
        generate_block_map();
        generate_channel_env();
        collect_container_metadata();
      }

      std::vector<imc::block>& blocks()
      {
        return rawblocks_;
      }

      unsigned long int& computational_complexity()
      {
        return cplxcnt_;
      }

      std::vector<std::string> get_channels(bool json = false, bool include_data = false)
      {
        std::vector<std::string> chns;
        for ( const std::string& uuid : channel_order_ )
        {
          imc::channel& channel = channels_.at(uuid);
          if ( !json )
          {
            chns.push_back(channel.get_info());
          }
          else
          {
            chns.push_back(channel.get_json(include_data));
          }
        }
        return chns;
      }

      imc::channel get_channel(const std::string& uuid)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      imc::channel_metadata get_channel_metadata(const std::string& uuid) const
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).metadata();
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      imc::channel_representation get_channel_representation(const std::string& uuid) const
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).representation();
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      imc::file_metadata get_file_metadata() const
      {
        return file_metadata_;
      }

      std::vector<imc::group_metadata> get_groups_metadata() const
      {
        return groups_metadata_;
      }

      std::vector<imc::text_object_metadata> get_text_objects_metadata() const
      {
        return text_objects_metadata_;
      }

      uint64_t get_tsa_payload_size_bytes(const std::string& uuid)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).tsa_payload_size_bytes();
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<unsigned char> read_tsa_payload(const std::string& uuid,
                                                   uint64_t offset_bytes,
                                                   uint64_t length_bytes)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).read_tsa_payload(offset_bytes, length_bytes);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<imc::tsa_record_descriptor> read_tsa_record_descriptors(
        const std::string& uuid,
        uint64_t start_record_ordinal,
        uint64_t record_count
      )
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).read_tsa_record_descriptors(start_record_ordinal, record_count);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<unsigned char> read_tsa_record_payload(const std::string& uuid,
                                                          uint64_t record_ordinal)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).read_tsa_record_payload(record_ordinal);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<unsigned char> read_component_payload(const std::string& uuid,
                                                         channel_component component,
                                                         uint64_t offset_bytes,
                                                         uint64_t length_bytes) const
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).read_component_payload(component, offset_bytes, length_bytes);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<imc::tsa_channel_segment> get_tsa_channel_segments(const std::string& uuid)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).get_tsa_channel_segments();
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<imc::numeric_channel_segment> get_numeric_channel_segments(const std::string& uuid) const
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).get_numeric_channel_segments();
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      std::vector<imc::channel_metadata> get_channels_metadata() const
      {
        std::vector<imc::channel_metadata> metadata;
        metadata.reserve(channel_order_.size());
        for ( const std::string& uuid : channel_order_ )
        {
          metadata.push_back(channels_.at(uuid).metadata());
        }
        return metadata;
      }

      std::vector<imc::block> list_blocks(const imc::key &mykey)
      {
        std::vector<imc::block> myblocks;
        for ( imc::block blk: this->rawblocks_ )
        {
          if ( blk.get_key() == mykey ) myblocks.push_back(blk);
        }
        return myblocks;
      }

      std::vector<imc::block> list_groups()
      {
        return this->list_blocks(imc::get_key(true,"CB"));
      }

      std::vector<std::string> list_channels()
      {
        std::vector<std::string> channels;
        for ( const std::string& uuid : channel_order_ )
        {
          channels.push_back(channels_.at(uuid).name_);
        }
        return channels;
      }

      unsigned long int get_channel_length(const std::string& uuid)
      {
        if ( channels_.count(uuid) )
        {
          return channels_.at(uuid).number_of_samples_;
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      int get_channel_numeric_type(const std::string& uuid)
      {
        if ( channels_.count(uuid) )
        {
          return static_cast<int>(channels_.at(uuid).ydatatp_);
        }
        throw std::runtime_error(std::string("channel does not exist:") + uuid);
      }

      channel_chunk read_channel_chunk(const std::string& uuid, unsigned long int start,
                                       unsigned long int count, bool include_x, bool raw_mode)
      {
        if ( !channels_.count(uuid) )
        {
          throw std::runtime_error(std::string("channel does not exist:") + uuid);
        }

        return channels_.at(uuid).read_chunk(start, count, include_x, raw_mode);
      }

      std::vector<imc::tsa_event> read_channel_events(const std::string& uuid,
                                                      unsigned long int start,
                                                      unsigned long int count)
      {
        if ( !channels_.count(uuid) )
        {
          throw std::runtime_error(std::string("channel does not exist:") + uuid);
        }

        return channels_.at(uuid).read_tsa_events(start, count);
      }

      void print_channel(const std::string& channeluuid, const std::string& outputfile,
                         const char sep, unsigned long int chunk_size = 100000)
      {
        std::filesystem::path pdf = outputfile;
        if ( !std::filesystem::is_directory(pdf.parent_path()) )
        {
          throw std::runtime_error(std::string("required directory does not exist: ")
                                   + pdf.parent_path().u8string() );
        }

        if ( channels_.count(channeluuid) == 1 )
        {
          channels_.at(channeluuid).print(outputfile,sep,25,9,chunk_size);
        }
        else
        {
          throw std::runtime_error(std::string("channel does not exist:")
                                   + channeluuid);
        }
      }

      void print_channels(const std::string& output, const char sep,
                          unsigned long int chunk_size = 100000)
      {
        std::filesystem::path pd = output;
        if ( !std::filesystem::is_directory(pd) )
        {
          throw std::runtime_error(std::string("given directory does not exist: ")
                                   + output);
        }

        for ( const std::string& uuid : channel_order_ )
        {
          imc::channel& channel = channels_.at(uuid);
          std::string chid = std::string("channel_") + uuid;
          std::string filenam = channel.name_.empty() ? chid + std::string(".csv")
                                             : channel.name_ + std::string(".csv");
          std::filesystem::path pf = pd / filenam;

          channel.print(pf.u8string(),sep,25,9,chunk_size);
        }

      }

      unsigned long int channel_count()
      {
        return static_cast<unsigned long int>(channel_order_.size());
      }
    };
  }
}

#endif

//---------------------------------------------------------------------------//