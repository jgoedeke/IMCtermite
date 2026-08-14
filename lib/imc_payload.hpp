//---------------------------------------------------------------------------//

#ifndef IMCPAYLOAD
#define IMCPAYLOAD

#include <cstdint>
#include <string>

//---------------------------------------------------------------------------//

namespace imc
{
  enum class source_format
  {
    imc2,
    imc3
  };

  enum class channel_storage_kind
  {
    generated_numeric,
    explicit_xy,
    tsa,
    numeric_segmented
  };

  enum class channel_component
  {
    x,
    y
  };

  struct channel_representation
  {
    int schema_version = 1;
    source_format format = source_format::imc2;
    channel_storage_kind storage_kind = channel_storage_kind::generated_numeric;
    std::string uuid;
    std::string codepage;
    bool has_generated_x_axis = true;
    int x_numeric_type = 0;
    int y_numeric_type = 0;
    int x_significant_bits = 0;
    int y_significant_bits = 0;
    uint64_t x_sample_width_bytes = 0;
    uint64_t y_sample_width_bytes = 0;
    uint64_t x_payload_size_bytes = 0;
    uint64_t y_payload_size_bytes = 0;
    uint64_t numeric_sample_count = 0;
    uint64_t segment_count = 0;
    uint64_t tsa_payload_size_bytes = 0;
    double timestamp_factor = 1.0;
    double timestamp_offset = 0.0;
  };

  struct tsa_record_descriptor
  {
    int schema_version = 1;
    uint64_t record_ordinal = 0;
    uint64_t raw_timestamp = 0;
    double timestamp = 0.0;
    uint64_t logical_payload_offset_bytes = 0;
    uint64_t payload_length_bytes = 0;
  };

  struct tsa_channel_segment
  {
    int schema_version = 1;
    uint64_t segment_ordinal = 0;
    uint64_t raw_payload_offset_bytes = 0;
    uint64_t raw_payload_length_bytes = 0;
    double trigger_time_seconds_since_1980 = 0.0;
    double pretrigger_seconds = 0.0;
    bool has_source_trigger_time = false;
    bool has_source_pretrigger = false;
    bool is_source_defined = false;
  };

  struct numeric_channel_segment
  {
    int schema_version = 1;
    uint64_t segment_ordinal = 0;
    uint64_t sample_offset = 0;
    uint64_t sample_count = 0;
    double trigger_time_seconds_since_1980 = 0.0;
    double x_start = 0.0;
    double x_step_width = 1.0;
    double pretrigger_seconds = 0.0;
    bool has_source_pretrigger = false;
    bool is_source_defined = true;
  };
}

#endif

//---------------------------------------------------------------------------//