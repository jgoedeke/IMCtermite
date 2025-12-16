# distutils: language = c++
# cython: language_level = 3

from imctermite cimport cppimctermite, channel_chunk
cimport numpy as cnp
import numpy as np
from libc.string cimport memcpy

import json as jn
import decimal
import platform

# auxiliary function for codepage conversion
def get_codepage(chn) :
    if platform.system() == 'Windows' :
        try:
            chndec = jn.loads(chn.decode(errors="ignore"))
            chncdp = chndec.get("codepage")
            if not chncdp:
                return 'utf-8'
            # If it's a number like "1252", Python expects "cp1252"
            if str(chncdp).isdigit():
                return 'cp' + str(chncdp)
            return str(chncdp)
        except:
            return 'utf-8'
    else :
        return 'utf-8'

cdef bytes _as_bytes(obj):
    if isinstance(obj, bytes):
        return obj
    elif isinstance(obj, str):
        return obj.encode('utf-8')
    else:
        return str(obj).encode('utf-8')

cdef class imctermite:

  # C++ instance of class
  cdef cppimctermite* cppimc

  # constructor
  def __cinit__(self, rawfile):
    self.cppimc = new cppimctermite(_as_bytes(rawfile))

  def __dealloc__(self):
    if self.cppimc != NULL:
        del self.cppimc

  # provide raw file
  def submit_file(self, rawfile):
    self.cppimc.set_file(_as_bytes(rawfile))

  # get JSON list of channels
  def get_channels(self, bool include_data):
    chnlst = self.cppimc.get_channels(True,include_data)
    chnlstjn = [jn.loads(chn.decode(get_codepage(chn),errors="ignore")) for chn in chnlst]
    return chnlstjn

  def iter_channel_numpy(self, string channeluuid, bool include_x=True, int chunk_rows=1000000, str mode="scaled"):
    cdef unsigned long int total_len = self.cppimc.get_channel_length(_as_bytes(channeluuid))
    cdef unsigned long int start = 0
    cdef channel_chunk chunk
    cdef cnp.ndarray x_arr
    cdef cnp.ndarray y_arr
    cdef bool raw_mode = (mode == "raw")
    
    # Map imc::numtype to numpy dtype
    # Types 9 (imc_devices_transitional_recording) and 10 (timestamp_ascii) 
    # are not currently supported by the underlying C++ library.
    dtype_map = {
        1: np.uint8,   # unsigned_byte
        2: np.int8,    # signed_byte
        3: np.uint16,  # unsigned_short
        4: np.int16,   # signed_short
        5: np.uint32,  # unsigned_long (imc_Ulongint is unsigned int (32-bit) on x86_64 usually)
        6: np.int32,   # signed_long (imc_Slongint is signed int)
        7: np.float32, # ffloat
        8: np.float64, # ddouble
        11: np.uint16, # two_byte_word_digital
        12: np.uint64, # eight_byte_unsigned_long
        13: np.uint64, # six_byte_unsigned_long (promoted to 8 bytes in C++)
        14: np.int64   # eight_byte_signed_long
    }

    while start < total_len:
        chunk = self.cppimc.read_channel_chunk(_as_bytes(channeluuid), start, chunk_rows, include_x, raw_mode)
        
        # Create numpy arrays from bytes
        y_dtype = dtype_map.get(chunk.y_type, np.float64)
        
        y_arr = np.empty(chunk.count, dtype=y_dtype)
             
        if chunk.y_bytes.size() > 0:
            memcpy(<void*> cnp.PyArray_DATA(y_arr), 
                   <void*> chunk.y_bytes.data(), 
                   chunk.y_bytes.size())
        
        result = {
            "start": chunk.start,
            "y": y_arr
        }
        
        if include_x:
            x_dtype = dtype_map.get(chunk.x_type, np.float64)
            x_arr = np.empty(chunk.count, dtype=x_dtype)
            
            if chunk.x_bytes.size() > 0:
                memcpy(<void*> cnp.PyArray_DATA(x_arr), 
                       <void*> chunk.x_bytes.data(), 
                       chunk.x_bytes.size())
            
            result["x"] = x_arr
            
        yield result
        
        start += chunk.count
        if chunk.count == 0:
            break

  # print single channel/all channels
  def print_channel(self, channeluuid, outputfile, char delimiter, unsigned long int chunk_size=100000):
    self.cppimc.print_channel(_as_bytes(channeluuid),_as_bytes(outputfile),delimiter,chunk_size)
  def print_channels(self, outputdir, char delimiter, unsigned long int chunk_size=100000):
    self.cppimc.print_channels(_as_bytes(outputdir),delimiter,chunk_size)

  # print table including channels
  def print_table(self, outputfile):
    chnlst = self.cppimc.get_channels(True,True)
    chnlstjn = [jn.loads(chn.decode(errors="ignore")) for chn in chnlst]
    with open(outputfile,'w') as fout:
      for chn in chnlstjn:
        fout.write('#' +str(chn['xname']).rjust(19)+str(chn['yname']).rjust(20)+'\n')
        fout.write('#'+str(chn['xunit']).rjust(19)+str(chn['yunit']).rjust(20)+'\n')
        for n in range(0,len(chn['ydata'])):
          fout.write(str(chn['xdata'][n]).rjust(20)+
                     str(chn['ydata'][n]).rjust(20)+'\n')
