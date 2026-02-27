//---------------------------------------------------------------------------//

#ifndef IMCOBJECT
#define IMCOBJECT

#include <cstring>
#include <time.h>
#include <math.h>
#include "imc_key.hpp"

//---------------------------------------------------------------------------//

namespace imc
{
  // obtain specific parameters as string
  std::string get_parameter(const unsigned char* buffer, const imc::parameter* param)
  {
    std::string prm("");
    for ( unsigned long int i = param->begin()+1; i <= param->end(); i++ )
    {
      prm.push_back((char)buffer[i]);
    }
    return prm;
  }

  // format and processor (corresponds to key CF)
  struct format
  {
    int fileformat_;
    int processor_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 3 ) throw std::runtime_error("invalid number of parameters in CF");
      fileformat_ = std::stoi(get_parameter(buffer,&parameters[0]));
      processor_ = std::stoi(get_parameter(buffer,&parameters[2]));
    }

    format(): fileformat_(-1), processor_(-1) {}

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"format:"<<fileformat_<<"\n"
        <<std::setw(width)<<std::left<<"processor:"<<processor_<<"\n";
      return ss.str();
    }
  };

  // start of group of keys (corresponds to key CK)
  struct keygroup
  {
    int version_;
    int length_;
    bool closed_;  // corresponds to true = 1 and false = 0 in file

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 2 ) throw std::runtime_error("invalid number of parameters in CK");
      version_ = std::stoi(get_parameter(buffer,&parameters[0]));
      length_ = std::stoi(get_parameter(buffer,&parameters[1]));
      closed_ = ( get_parameter(buffer,&parameters[3])==std::string("1") );
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"version:"<<version_<<"\n"
        <<std::setw(width)<<std::left<<"length:"<<length_<<"\n"
        <<std::setw(width)<<std::left<<"closed:"<<(closed_?"yes":"no")<<"\n";
      return ss.str();
    }
  };

  // group definition (corresponds to key CB)
  struct groupobj
  {
    unsigned long int group_index_;
    std::string name_;
    std::string comment_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 7 ) throw std::runtime_error("invalid number of parameters in CB");
      group_index_ = std::stoul(get_parameter(buffer,&parameters[2]));
      name_ = get_parameter(buffer,&parameters[4]);
      comment_ = get_parameter(buffer,&parameters[6]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"group-index:"<<group_index_<<"\n"
        <<std::setw(width)<<std::left<<"name:"<<name_<<"\n"
        <<std::setw(width)<<std::left<<"comment:"<<comment_<<"\n";
      return ss.str();
    }
  };

  // text definition (corresponds to key CT)
  struct text
  {
    unsigned long int group_index_; // corresponding to group-index in CB block
    std::string name_;
    std::string text_;
    std::string comment_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 9 ) throw std::runtime_error("invalid number of parameters in CT");
      group_index_ = std::stoul(get_parameter(buffer,&parameters[2]));
      name_ = get_parameter(buffer,&parameters[4]);
      text_ = get_parameter(buffer,&parameters[6]);
      comment_ = get_parameter(buffer,&parameters[8]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"group-index:"<<group_index_<<"\n"
        <<std::setw(width)<<std::left<<"name:"<<name_<<"\n"
        <<std::setw(width)<<std::left<<"text:"<<text_<<"\n"
        <<std::setw(width)<<std::left<<"comment:"<<comment_<<"\n";
      return ss.str();
    }
  };

  enum fieldtype {
    realnumber = 1,       // 1
    xmonotony,            // 2
    xy,                   // 3
    complexrealimag,      // 4
    complexabsphase,      // 5
    complexdbphase        // 6
  };

  // definition of data field (corresponds to key CG)
  struct datafield
  {
    unsigned long int number_components_;
    fieldtype fldtype_;
    int dimension_; // corresponding to fieldtype \in {1,}

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 5 ) throw std::runtime_error("invalid number of parameters in CG");
      number_components_ = std::stoul(get_parameter(buffer,&parameters[2]));
      fldtype_ = (fieldtype)std::stoi(get_parameter(buffer,&parameters[3]));
      dimension_ = std::stoi(get_parameter(buffer,&parameters[4]));
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"#components:"<<number_components_<<"\n"
        <<std::setw(width)<<std::left<<"fieldtype:"<<fldtype_<<"\n"
        <<std::setw(width)<<std::left<<"dimension:"<<dimension_<<"\n";
      return ss.str();
    }
  };

  // definition of abscissa (corresponds to key CD1)
  struct abscissa
  {
    double dx_;
    bool calibration_;
    std::string unit_;

    abscissa(): dx_(1.0), calibration_(false), unit_("") {}

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 6 ) throw std::runtime_error("invalid number of parameters in CD1");
      dx_ = std::stod(get_parameter(buffer,&parameters[2]));
      calibration_ = ( get_parameter(buffer,&parameters[3]) == std::string("1") );
      unit_ = get_parameter(buffer,&parameters[5]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"dx:"<<dx_<<"\n"
        <<std::setw(width)<<std::left<<"calibration:"<<(calibration_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"unit:"<<unit_<<"\n";
      return ss.str();
    }
  };

  // definition of abscissa (corresponds to key CD2)
  struct abscissa2
  {
    double dx_;
    bool calibration_;
    std::string unit_;
    bool reduction_;
    bool ismultievent_;
    bool sortbuffer_;
    double x0_;
    int pretriggerapp_;

    abscissa2(): dx_(1.0), calibration_(false), unit_(""), reduction_(false),
           ismultievent_(false), sortbuffer_(false), x0_(0.0), pretriggerapp_(0) {}

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 11 ) throw std::runtime_error("invalid number of parameters in CD2");
      dx_ = std::stod(get_parameter(buffer,&parameters[2]));
      calibration_ = ( get_parameter(buffer,&parameters[3]) == std::string("1") );
      unit_ = get_parameter(buffer,&parameters[5]);
      reduction_ = ( get_parameter(buffer,&parameters[6]) == std::string("1") );
      ismultievent_ = ( get_parameter(buffer,&parameters[7]) == std::string("1") );
      sortbuffer_ = ( get_parameter(buffer,&parameters[8]) == std::string("1") );
      x0_ = std::stod(get_parameter(buffer,&parameters[9]));
      pretriggerapp_ = std::stoi( get_parameter(buffer,&parameters[10]) );
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"dx:"<<dx_<<"\n"
        <<std::setw(width)<<std::left<<"calibration:"<<(calibration_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"unit:"<<unit_<<"\n"
        <<std::setw(width)<<std::left<<"reduction:"<<reduction_<<"\n"
        <<std::setw(width)<<std::left<<"ismultievent:"<<ismultievent_<<"\n"
        <<std::setw(width)<<std::left<<"sortbuffer:"<<sortbuffer_<<"\n"
        <<std::setw(width)<<std::left<<"x0:"<<x0_<<"\n"
        <<std::setw(width)<<std::left<<"pretriggerapp:"<<pretriggerapp_<<"\n";
      return ss.str();
    }
  };

  // start of component (corresponds to key CC)
  struct component
  {
    int component_index_;
    bool analog_digital_; // 1 => false (analog), 2 => true (digital)

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 4 ) throw std::runtime_error("invalid number of parameters in CC");
      component_index_ = std::stoi(get_parameter(buffer,&parameters[2]));
      analog_digital_ = ( std::stoi(get_parameter(buffer,&parameters[3])) == 2 );
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"index:"<<component_index_<<"\n"
        <<std::setw(width)<<std::left<<"analog/digital:"<<(analog_digital_?"digital":"analog")<<"\n";
      return ss.str();
    }
  };

  enum numtype {
    unsigned_byte = 1,
    signed_byte,
    unsigned_short,
    signed_short,
    unsigned_long,
    signed_long,
    ffloat,
    ddouble,
    imc_devices_transitional_recording,
    timestamp_ascii,
    two_byte_word_digital,
    eight_byte_unsigned_long,
    six_byte_unsigned_long,
    eight_byte_signed_long
  };

  // packaging information of component (corresponds to key CP)
  struct packaging
  {
    unsigned long int buffer_reference_;
    int bytes_;
    numtype numeric_type_;
    int signbits_;
    int mask_;
    unsigned long int offset_;
    unsigned long int number_subsequent_samples_;
    unsigned long int distance_bytes_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 10 ) throw std::runtime_error("invalid number of parameters in CP");
      buffer_reference_ = std::stoi(get_parameter(buffer,&parameters[2]));
      bytes_ = std::stoi(get_parameter(buffer,&parameters[3]));
      numeric_type_ = (numtype)std::stoi(get_parameter(buffer,&parameters[4]));
      signbits_ = std::stoi(get_parameter(buffer,&parameters[5]));
      mask_ = std::stoi(get_parameter(buffer,&parameters[6]));
      offset_ = std::stoul(get_parameter(buffer,&parameters[7]));
      number_subsequent_samples_ = std::stoul(get_parameter(buffer,&parameters[8]));
      distance_bytes_ = std::stoul(get_parameter(buffer,&parameters[9]));
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"buffer-reference:"<<buffer_reference_<<"\n"
        <<std::setw(width)<<std::left<<"datatype:"<<numeric_type_<<"\n"
        <<std::setw(width)<<std::left<<"significant bits:"<<signbits_<<"\n"
        <<std::setw(width)<<std::left<<"mask:"<<mask_<<"\n"
        <<std::setw(width)<<std::left<<"offset:"<<offset_<<"\n"
        <<std::setw(width)<<std::left<<"#subseq.-samples:"<<number_subsequent_samples_<<"\n"
        <<std::setw(width)<<std::left<<"distance in bytes:"<<distance_bytes_<<"\n";
      return ss.str();
    }
  };

  // buffer description (corresponds to key Cb)
  struct buffer
  {
    unsigned long int number_buffers_;
    unsigned long int bytes_userinfo_;
    // for every single buffer
    unsigned long int buffer_reference_; // corresponds to buffer_reference_ in key CP
    unsigned long int sample_index_;     // corresponds to index of CS key
    unsigned long int offset_buffer_;    // number of bytes from beginning of CS key
    unsigned long int number_bytes_;     // number of bytes in buffer
    unsigned long int offset_first_sample_;
    unsigned long int number_filled_bytes_;
    double x0_;
    double add_time_;                    // start of trigger time = NT + add_time
    // bool user_info_;
    // bool new_event_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 13 ) throw std::runtime_error("invalid number of parameters in Cb");
      number_buffers_ = std::stoul(get_parameter(buffer,&parameters[2]));
      bytes_userinfo_ = std::stoul(get_parameter(buffer,&parameters[3]));
      buffer_reference_ = std::stoul(get_parameter(buffer,&parameters[4]));
      sample_index_ = std::stoul(get_parameter(buffer,&parameters[5]));
      offset_buffer_ = std::stoul(get_parameter(buffer,&parameters[6]));
      number_bytes_ = std::stoul(get_parameter(buffer,&parameters[7]));
      offset_first_sample_ = std::stoul(get_parameter(buffer,&parameters[8]));
      number_filled_bytes_ = std::stoul(get_parameter(buffer,&parameters[9]));
      x0_ = std::stod(get_parameter(buffer,&parameters[11]));
      add_time_ = std::stod(get_parameter(buffer,&parameters[12]));
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"#buffers:"<<number_buffers_<<"\n"
        <<std::setw(width)<<std::left<<"bytes user info:"<<bytes_userinfo_<<"\n"
        <<std::setw(width)<<std::left<<"buffer reference:"<<buffer_reference_<<"\n"
        <<std::setw(width)<<std::left<<"sample index:"<<sample_index_<<"\n"
        <<std::setw(width)<<std::left<<"offset buffer:"<<offset_buffer_<<"\n"
        <<std::setw(width)<<std::left<<"buffer size:"<<number_bytes_<<"\n"
        <<std::setw(width)<<std::left<<"offset sample:"<<offset_first_sample_<<"\n"
        <<std::setw(width)<<std::left<<"#filled bytes:"<<number_filled_bytes_<<"\n"
        <<std::setw(width)<<std::left<<"time offset:"<<x0_<<"\n"
        <<std::setw(width)<<std::left<<"add time:"<<add_time_<<"\n";
      return ss.str();
    }
  };

  // range of values of component (corresponds to key CR)
  struct range
  {
    bool transform_;         // 1 = true: yes, requires offset + factor, 0 = false: no
    double factor_, offset_; // value = raw value * factor + offset
    bool calibration_;       // 1 = true: calibration, 0 = false: no calibration
    std::string unit_;

    range(): transform_(false), factor_(1.0), offset_(0.0), calibration_(false), unit_("") {}

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 8 ) throw std::runtime_error("invalid number of parameters in CR");
      transform_ = (get_parameter(buffer,&parameters[2]) == std::string("1"));
      factor_ = std::stod(get_parameter(buffer,&parameters[3]));
      offset_ = std::stod(get_parameter(buffer,&parameters[4]));
      calibration_ = (get_parameter(buffer,&parameters[5]) == std::string("1"));
      unit_ = get_parameter(buffer,&parameters[7]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"transform:"<<(transform_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"factor:"<<factor_<<"\n"
        <<std::setw(width)<<std::left<<"offset:"<<offset_<<"\n"
        <<std::setw(width)<<std::left<<"calibration:"<<(calibration_?"yes":"no")<<"\n"
        <<std::setw(width)<<std::left<<"unit:"<<unit_<<"\n";
      return ss.str();
    }
  };

  // channel (corresponds to key CN)
  struct channelobj
  {
    unsigned long int group_index_;  // corresponds to group-index in CB key
    bool index_bit_;                 // true =  1: digital, false = 0: analog
    std::string name_;
    std::string comment_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 9 ) throw std::runtime_error("invalid number of parameters in CN");
      group_index_ = std::stoul(get_parameter(buffer,&parameters[2]));
      index_bit_ = (get_parameter(buffer,&parameters[4]) == std::string("1"));
      name_ = get_parameter(buffer,&parameters[6]);
      comment_ = get_parameter(buffer,&parameters[8]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"group-index:"<<group_index_<<"\n"
        <<std::setw(width)<<std::left<<"index-bit:"<<index_bit_<<"\n"
        <<std::setw(width)<<std::left<<"name:"<<name_<<"\n"
        <<std::setw(width)<<std::left<<"comment:"<<comment_<<"\n";
      return ss.str();
    }
  };

  // rawdata (corresponds to key CS)
  struct data
  {
    unsigned long int index_;  // starting from 1 in first CS block in file
    // std::vector<unsigned char> rawdata_;
    // unsigned long int begin_buffer_, end_buffer_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 4 ) throw std::runtime_error("invalid number of parameters in CS");
      index_ = std::stoul(get_parameter(buffer,&parameters[2]));
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"index:"<<index_<<"\n";
        // <<std::setw(width)<<std::left<<"(begin,end) buffer:"
        //                              <<"("<<begin_buffer_<<","<<end_buffer_<<")"<<"\n";
      return ss.str();
    }
  };

  struct event_description
  {
    unsigned long int index_event_list_key_;
    unsigned long int offset_in_event_list_;
    unsigned long int direct_follow_count_;
    unsigned long int event_stride_;
    unsigned long int event_count_;
    int valid_nt_;
    int valid_cd_;
    int valid_cr1_;
    int valid_cr2_;

    event_description(): index_event_list_key_(0), offset_in_event_list_(0),
      direct_follow_count_(0), event_stride_(0), event_count_(0),
      valid_nt_(0), valid_cd_(0), valid_cr1_(0), valid_cr2_(0) {}

    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 11 ) throw std::runtime_error("invalid number of parameters in Cv");
      index_event_list_key_ = std::stoul(get_parameter(buffer,&parameters[2]));
      offset_in_event_list_ = std::stoul(get_parameter(buffer,&parameters[3]));
      direct_follow_count_ = std::stoul(get_parameter(buffer,&parameters[4]));
      event_stride_ = std::stoul(get_parameter(buffer,&parameters[5]));
      event_count_ = std::stoul(get_parameter(buffer,&parameters[6]));
      valid_nt_ = std::stoi(get_parameter(buffer,&parameters[7]));
      valid_cd_ = std::stoi(get_parameter(buffer,&parameters[8]));
      valid_cr1_ = std::stoi(get_parameter(buffer,&parameters[9]));
      valid_cr2_ = std::stoi(get_parameter(buffer,&parameters[10]));
    }

    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"event-list-index:"<<index_event_list_key_<<"\n"
        <<std::setw(width)<<std::left<<"event-offset:"<<offset_in_event_list_<<"\n"
        <<std::setw(width)<<std::left<<"direct-follow:"<<direct_follow_count_<<"\n"
        <<std::setw(width)<<std::left<<"event-stride:"<<event_stride_<<"\n"
        <<std::setw(width)<<std::left<<"event-count:"<<event_count_<<"\n"
        <<std::setw(width)<<std::left<<"valid-nt:"<<valid_nt_<<"\n"
        <<std::setw(width)<<std::left<<"valid-cd:"<<valid_cd_<<"\n"
        <<std::setw(width)<<std::left<<"valid-cr1:"<<valid_cr1_<<"\n"
        <<std::setw(width)<<std::left<<"valid-cr2:"<<valid_cr2_<<"\n";
      return ss.str();
    }
  };

  struct event_entry
  {
    uint64_t offset_samples_;
    uint64_t length_samples_;
    double time_seconds_;
    double y_offset_;
    double x_offset_;
    double x0_;
    double y_factor_;
    double x_factor_;
    double dx_;
  };

  struct event_list
  {
    unsigned long int index_;
    unsigned long int event_count_;
    std::vector<event_entry> entries_;

    event_list(): index_(0), event_count_(0) {}

    static uint32_t read_u32_le(const unsigned char* ptr)
    {
      return (uint32_t)ptr[0]
           | ((uint32_t)ptr[1] << 8)
           | ((uint32_t)ptr[2] << 16)
           | ((uint32_t)ptr[3] << 24);
    }

    static double read_f64_le(const unsigned char* ptr)
    {
      uint64_t bits = 0;
      for ( int i = 0; i < 8; i++ ) bits |= ((uint64_t)ptr[i] << (8*i));
      double out = 0.0;
      std::memcpy(&out, &bits, sizeof(double));
      return out;
    }

    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 5 ) throw std::runtime_error("invalid number of parameters in CV");

      size_t idx_pos = 2;
      size_t cnt_pos = 3;
      size_t raw_pos = 4;
      if ( parameters.size() >= 6 )
      {
        idx_pos = 3;
        cnt_pos = 4;
        raw_pos = 5;
      }

      index_ = std::stoul(get_parameter(buffer,&parameters[idx_pos]));
      event_count_ = std::stoul(get_parameter(buffer,&parameters[cnt_pos]));

      const parameter &raw = parameters[raw_pos];
      if ( raw.end() <= raw.begin() ) return;

      const unsigned char* payload = buffer + raw.begin() + 1;
      size_t payload_size = raw.end() - raw.begin();
      size_t event_size = 64;
      if ( event_count_ > 0 && payload_size / event_count_ >= 72 ) event_size = 72;
      else if ( event_count_ > 0 && payload_size / event_count_ >= 64 ) event_size = 64;
      else if ( payload_size % 72 == 0 ) event_size = 72;

      size_t max_events_from_payload = payload_size / event_size;
      size_t parse_count = (std::min)((size_t)event_count_, max_events_from_payload);

      entries_.clear();
      entries_.reserve(parse_count);

      for ( size_t i = 0; i < parse_count; i++ )
      {
        const unsigned char* ev = payload + i*event_size;
        uint64_t off_lo = read_u32_le(ev + 0);
        uint64_t len_lo = read_u32_le(ev + 4);
        double time = read_f64_le(ev + 8);
        double off1 = read_f64_le(ev + 16);
        double off2 = read_f64_le(ev + 24);
        double x0 = read_f64_le(ev + 32);
        double fac1 = read_f64_le(ev + 40);
        double fac2 = read_f64_le(ev + 48);
        double dx = read_f64_le(ev + 56);
        uint64_t off_hi = 0;
        uint64_t len_hi = 0;
        if ( event_size >= 72 )
        {
          off_hi = read_u32_le(ev + 64);
          len_hi = read_u32_le(ev + 68);
        }

        event_entry entry;
        entry.offset_samples_ = (off_hi << 32) | off_lo;
        entry.length_samples_ = (len_hi << 32) | len_lo;
        entry.time_seconds_ = time;
        entry.y_offset_ = off1;
        entry.x_offset_ = off2;
        entry.x0_ = x0;
        entry.y_factor_ = fac1;
        entry.x_factor_ = fac2;
        entry.dx_ = dx;
        entries_.push_back(entry);
      }
    }

    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"index:"<<index_<<"\n"
        <<std::setw(width)<<std::left<<"event-count:"<<event_count_<<"\n"
        <<std::setw(width)<<std::left<<"parsed-events:"<<entries_.size()<<"\n";
      return ss.str();
    }
  };

  // language (corresponds to key NL)
  struct language
  {
    std::string codepage_;
    std::string language_code_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if (parameters.size() < 4) throw std::runtime_error("invalid number of parameters in NL");
      codepage_ = get_parameter(buffer, &parameters[2]);
      language_code_ = get_parameter(buffer, &parameters[3]);
    }
  };

  // origin of data (corresponds to key NO)
  struct origin_data
  {
    bool origin_;  // corresponds to true = 1 ("verrechnet") and false = 0 ("Original")
    std::string generator_;
    std::string comment_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 7 ) throw std::runtime_error("invalid number of parameters in NO");
      origin_ = ( get_parameter(buffer,&parameters[2]) == std::string("1") );
      generator_ = get_parameter(buffer,&parameters[4]);
      comment_ = get_parameter(buffer,&parameters[6]);
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"origin:"<<(origin_?"verrechnet":"Original")<<"\n"
        <<std::setw(width)<<std::left<<"generator:"<<generator_<<"\n"
        <<std::setw(width)<<std::left<<"comment:"<<comment_<<"\n";
      return ss.str();
    }
  };

  // trigger timestamp (corresponds to key NT1)
  struct triggertime
  {
    std::tm tms_;
    double trigger_time_frac_secs_;

    // construct members by parsing particular parameters from buffer
    void parse(const unsigned char* buffer, const std::vector<parameter>& parameters)
    {
      if ( parameters.size() < 8 ) throw std::runtime_error("invalid number of parameters in NT1");
      tms_ = std::tm();
      tms_.tm_mday = std::stoi( get_parameter(buffer,&parameters[2]) );
      tms_.tm_mon = std::stoi( get_parameter(buffer,&parameters[3]) ) - 1;
      tms_.tm_year = std::stoi( get_parameter(buffer,&parameters[4]) ) - 1900;
      tms_.tm_hour = std::stoi( get_parameter(buffer,&parameters[5]) );
      tms_.tm_min = std::stoi( get_parameter(buffer,&parameters[6]) );
      long double secs = std::stold( get_parameter(buffer,&parameters[7]) );
      double secs_int;
      trigger_time_frac_secs_ = modf((double)secs,&secs_int);
      tms_.tm_sec = (int)secs_int;
    }

    // get info string
    std::string get_info(int width = 20)
    {
      std::stringstream ss;
      ss<<std::setw(width)<<std::left<<"timestamp:"<<std::put_time(&tms_, "%Y-%m-%dT%H:%M:%S")<<"\n";
      return ss.str();
    }
  };

}

namespace imc {

  // create wrapper for imc_object types
  // (not particularly memory-efficient but it simplifies the remaining stuff
  // considerably and the structs are pretty small anyway!)
  class rawobject
  {
    format fmt_;      // 0
    keygroup kyg_;    // 1
    groupobj grp_;       // 2
    text txt_;        // 3
    datafield dtf_;   // 4
    abscissa abs_;    // 5
    component cmt_;   // 6
    packaging pkg_;   // 7
    buffer bfr_;      // 8
    range rng_;       // 9
    channelobj chn_;     // 10
    data dat_;        // 11
    origin_data org_; // 12
    triggertime trt_; // 13
    abscissa2 abs2_;  // 14
    event_description evd_; // 15
    event_list evl_;        // 16
    int objidx_;

  public:

    rawobject(): objidx_(-1) { }

    void parse(imc::key key, const unsigned char* buffer,
                             const std::vector<parameter>& parameters)
    {
      if ( key.name_ == std::string("CF") )
      {
        fmt_.parse(buffer,parameters);
        objidx_ = 0;
      }
      else if ( key.name_ == std::string("CK") )
      {
        kyg_.parse(buffer,parameters);
        objidx_ = 1;
      }
      else if ( key.name_ == std::string("CB") )
      {
        grp_.parse(buffer,parameters);
        objidx_ = 2;
      }
      else if ( key.name_ == std::string("CT") )
      {
        txt_.parse(buffer,parameters);
        objidx_ = 3;
      }
      else if ( key.name_ == std::string("CG") )
      {
        dtf_.parse(buffer,parameters);
        objidx_ = 4;
      }
      else if ( key.name_ == std::string("CD") && key.version_ == 1 )
      {
        abs_.parse(buffer,parameters);
        objidx_ = 5;
      }
      else if ( key.name_ == std::string("CC") )
      {
        cmt_.parse(buffer,parameters);
        objidx_ = 6;
      }
      else if ( key.name_ == std::string("CP") )
      {
        pkg_.parse(buffer,parameters);
        objidx_ = 7;
      }
      else if ( key.name_ == std::string("Cb") )
      {
        bfr_.parse(buffer,parameters);
        objidx_ = 8;
      }
      else if ( key.name_ == std::string("CR") )
      {
        rng_.parse(buffer,parameters);
        objidx_ = 9;
      }
      else if ( key.name_ == std::string("CN") )
      {
        chn_.parse(buffer,parameters);
        objidx_ = 10;
      }
      else if ( key.name_ == std::string("CS") )
      {
        dat_.parse(buffer,parameters);
        objidx_ = 11;
      }
      else if ( key.name_ == std::string("NO") )
      {
        org_.parse(buffer,parameters);
        objidx_ = 12;
      }
      else if ( key.name_ == std::string("NT") && key.version_ == 1 )
      {
        trt_.parse(buffer,parameters);
        objidx_ = 13;
      }
      else if ( key.name_ == std::string("CD") && key.version_ == 2 )
      {
        abs2_.parse(buffer,parameters);
        objidx_ = 14;
      }
      else if ( key.name_ == std::string("Cv") )
      {
        evd_.parse(buffer,parameters);
        objidx_ = 15;
      }
      else if ( key.name_ == std::string("CV") )
      {
        evl_.parse(buffer,parameters);
        objidx_ = 16;
      }
      else
      {
        if ( key.name_.at(0) == 'C' )
        {
          throw std::logic_error(
            std::string("unsupported block associated to critical key ")
            + key.name_ + std::to_string(key.version_)
          );
        }
        else
        {
          std::cout<<"WARNING: unsupported block associated to noncritical key "
                   <<key.name_<<key.version_<<"\n";
        }
      }
    }

    // provide info string
    std::string get_info(int width = 20)
    {
      switch (objidx_) {
        case 0:
          return fmt_.get_info();
        case 1:
          return kyg_.get_info();
        case 2:
          return grp_.get_info();
        case 3:
          return txt_.get_info();
        case 4:
          return dtf_.get_info();
        case 5:
          return abs_.get_info();
        case 6:
          return cmt_.get_info();
        case 7:
          return pkg_.get_info();
        case 8:
          return bfr_.get_info();
        case 9:
          return rng_.get_info();
        case 10:
          return chn_.get_info();
        case 11:
          return dat_.get_info();
        case 12:
          return org_.get_info();
        case 13:
          return trt_.get_info();
        case 14:
          return abs2_.get_info();
        case 15:
          return evd_.get_info();
        case 16:
          return evl_.get_info();
        default:
          return std::string("");
      }
    }

  };

}

#endif

//---------------------------------------------------------------------------//
