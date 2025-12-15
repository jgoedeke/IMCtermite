//---------------------------------------------------------------------------//

#ifndef IMCCONVERSION
#define IMCCONVERSION

#include <vector>

//---------------------------------------------------------------------------//

namespace imc
{
  // convert raw data in buffer into specific datatype
  template<typename datatype>
  void convert_data_to_type(const unsigned char* subbuffer, size_t subbuffer_size,
                            std::vector<imc::datatype>& channel)
  {
    // check number of elements of type "datatype" in buffer
    if ( subbuffer_size != channel.size()*sizeof(datatype) )
    {
      throw std::runtime_error( std::string("size mismatch between subbuffer (")
                              + std::to_string(subbuffer_size)
                              + std::string(") and datatype (")
                              + std::to_string(channel.size()) + std::string("*")
                              + std::to_string(sizeof(datatype)) + std::string(")") );
    }

    // extract every single number of type "datatype" from buffer
    for ( unsigned long int i = 0; i < channel.size(); i++ )
    {
      // declare number of required type and point it to first byte in buffer
      // representing the number
      datatype df;
      uint8_t* dfcast = reinterpret_cast<uint8_t*>(&df);

      for ( unsigned long int j = 0; j < sizeof(datatype); j++ )
      {
        dfcast[j] = (int)subbuffer[i*sizeof(datatype)+j];
      }

      // save number in channel
      channel[i] = df;
    }

    // for ( auto el: channel ) std::cout<<el<<"\n";
  }

  // convert raw chunk to double with scaling
  template<typename SourceType>
  void convert_chunk_to_double(const unsigned char* buffer, size_t start_index, size_t count,
                               double factor, double offset, std::vector<double>& out)
  {
      size_t type_size = sizeof(SourceType);
      const unsigned char* start_ptr = buffer + start_index * type_size;
      
      out.resize(count);
      
      for (size_t i = 0; i < count; ++i) {
          SourceType val;
          
          const unsigned char* val_ptr = start_ptr + i * type_size;
          uint8_t* dest_ptr = reinterpret_cast<uint8_t*>(&val);
          for(size_t j=0; j<type_size; ++j) {
              dest_ptr[j] = val_ptr[j];
          }
          
          // Convert to double and scale
          double dval = static_cast<double>(val);
          if (factor != 1.0 || offset != 0.0) {
              double fact = (factor == 0.0) ? 1.0 : factor;
              dval = dval * fact + offset;
          }
          out[i] = dval;
      }
  }

  // Specialization for imc_sixbyte
  template<>
  inline void convert_chunk_to_double<imc_sixbyte>(const unsigned char* buffer, size_t start_index, size_t count,
                               double factor, double offset, std::vector<double>& out)
  {
      size_t type_size = 6;
      const unsigned char* start_ptr = buffer + start_index * type_size;
      
      out.resize(count);
      
      for (size_t i = 0; i < count; ++i) {
          const unsigned char* val_ptr = start_ptr + i * type_size;
          uint64_t val = 0;
          for(int j=0; j<6; ++j) {
              val |= (uint64_t)val_ptr[j] << (j*8);
          }
          
          double dval = static_cast<double>(val);
          if (factor != 1.0 || offset != 0.0) {
              double fact = (factor == 0.0) ? 1.0 : factor;
              dval = dval * fact + offset;
          }
          out[i] = dval;
      }
  }

}

#endif

//---------------------------------------------------------------------------//
