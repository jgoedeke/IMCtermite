//---------------------------------------------------------------------------//

#ifndef IMCMETADATA
#define IMCMETADATA

#include <chrono>
#include <cstdint>
#include <string>

//---------------------------------------------------------------------------//

namespace imc
{
  enum class channel_kind
  {
    numeric,
    tsa_event,
    numeric_event
  };

  struct channel_metadata
  {
    int schema_version = 1;
    std::string uuid;
    std::string name;
    std::string source_name;
    std::string comment;
    std::string origin;
    std::string origin_comment;
    std::string description;
    std::string language_code;
    std::string codepage;
    std::string y_name;
    std::string y_unit;
    std::string x_name;
    std::string x_unit;
    std::string group_name;
    std::string group_comment;
    channel_kind kind = channel_kind::numeric;
    int dimension = 0;
    int x_numeric_type = 0;
    int y_numeric_type = 0;
    int x_significant_bits = 0;
    int y_significant_bits = 0;
    uint64_t sample_count = 0;
    uint64_t group_index = 0;
    bool has_group = false;
    double trigger_time = 0.0;
    double absolute_trigger_time = 0.0;
    double x_step_width = 1.0;
    double x_offset = 0.0;
    double x_factor = 1.0;
    double x_scaling_offset = 0.0;
    double y_factor = 1.0;
    double y_offset = 0.0;

    int kind_code() const
    {
      return static_cast<int>(kind);
    }
  };

  inline double seconds_since_1980(const std::chrono::system_clock::time_point& value)
  {
    constexpr double unix_to_imc_epoch_seconds = 315532800.0;
    return std::chrono::duration<double>(value.time_since_epoch()).count()
      - unix_to_imc_epoch_seconds;
  }
}

#endif

//---------------------------------------------------------------------------//