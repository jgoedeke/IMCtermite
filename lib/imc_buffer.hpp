#ifndef IMCBUFFER
#define IMCBUFFER

#include <string>
#include <stdexcept>
#include <iostream>

#if defined(_WIN32) || defined(_WIN64)
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
#else
    #include <sys/mman.h>
    #include <sys/stat.h>
    #include <fcntl.h>
    #include <unistd.h>
#endif

namespace imc
{
    class MemoryMappedFile
    {
    private:
        const unsigned char* data_;
        size_t size_;
#if defined(_WIN32) || defined(_WIN64)
        HANDLE hFile_;
        HANDLE hMap_;
#else
        int fd_;
#endif

    public:
#if defined(_WIN32) || defined(_WIN64)
        MemoryMappedFile() : data_(nullptr), size_(0), hFile_(INVALID_HANDLE_VALUE), hMap_(NULL) {}
#else
        MemoryMappedFile() : data_(nullptr), size_(0), fd_(-1) {}
#endif

        ~MemoryMappedFile()
        {
            close_file();
        }

        // Delete copy constructor and assignment operator to prevent double-free
        MemoryMappedFile(const MemoryMappedFile&) = delete;
        MemoryMappedFile& operator=(const MemoryMappedFile&) = delete;

        // Implement move constructor
        MemoryMappedFile(MemoryMappedFile&& other) noexcept
#if defined(_WIN32) || defined(_WIN64)
            : data_(other.data_), size_(other.size_), hFile_(other.hFile_), hMap_(other.hMap_)
        {
            other.data_ = nullptr;
            other.size_ = 0;
            other.hFile_ = INVALID_HANDLE_VALUE;
            other.hMap_ = NULL;
        }
#else
            : data_(other.data_), size_(other.size_), fd_(other.fd_)
        {
            other.data_ = nullptr;
            other.size_ = 0;
            other.fd_ = -1;
        }
#endif

        // Implement move assignment operator
        MemoryMappedFile& operator=(MemoryMappedFile&& other) noexcept
        {
            if (this != &other)
            {
                close_file();
                data_ = other.data_;
                size_ = other.size_;
#if defined(_WIN32) || defined(_WIN64)
                hFile_ = other.hFile_;
                hMap_ = other.hMap_;
                other.hFile_ = INVALID_HANDLE_VALUE;
                other.hMap_ = NULL;
#else
                fd_ = other.fd_;
                other.fd_ = -1;
#endif
                other.data_ = nullptr;
                other.size_ = 0;
            }
            return *this;
        }

        void map(const std::string& filename)
        {
            close_file();

#if defined(_WIN32) || defined(_WIN64)
            hFile_ = CreateFileA(filename.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
            if (hFile_ == INVALID_HANDLE_VALUE)
            {
                throw std::runtime_error("Failed to open file: " + filename);
            }

            LARGE_INTEGER fileSize;
            if (!GetFileSizeEx(hFile_, &fileSize))
            {
                CloseHandle(hFile_);
                hFile_ = INVALID_HANDLE_VALUE;
                throw std::runtime_error("Failed to get file size: " + filename);
            }
            size_ = (size_t)fileSize.QuadPart;

            if (size_ == 0)
            {
                data_ = nullptr;
                return;
            }

            hMap_ = CreateFileMappingA(hFile_, NULL, PAGE_READONLY, 0, 0, NULL);
            if (hMap_ == NULL)
            {
                CloseHandle(hFile_);
                hFile_ = INVALID_HANDLE_VALUE;
                throw std::runtime_error("Failed to create file mapping: " + filename);
            }

            data_ = static_cast<const unsigned char*>(MapViewOfFile(hMap_, FILE_MAP_READ, 0, 0, 0));
            if (data_ == NULL)
            {
                CloseHandle(hMap_);
                hMap_ = NULL;
                CloseHandle(hFile_);
                hFile_ = INVALID_HANDLE_VALUE;
                throw std::runtime_error("Failed to map view of file: " + filename);
            }
#else
            fd_ = open(filename.c_str(), O_RDONLY);
            if (fd_ == -1)
            {
                throw std::runtime_error("Failed to open file: " + filename);
            }

            struct stat sb;
            if (fstat(fd_, &sb) == -1)
            {
                close(fd_);
                fd_ = -1;
                throw std::runtime_error("Failed to get file size: " + filename);
            }
            size_ = sb.st_size;

            if (size_ == 0)
            {
                data_ = nullptr;
                return;
            }

            void* mapped = mmap(NULL, size_, PROT_READ, MAP_PRIVATE, fd_, 0);
            if (mapped == MAP_FAILED)
            {
                close(fd_);
                fd_ = -1;
                size_ = 0;
                throw std::runtime_error("Failed to mmap file: " + filename);
            }

            data_ = static_cast<const unsigned char*>(mapped);
#endif
        }

        void close_file()
        {
            if (data_)
            {
#if defined(_WIN32) || defined(_WIN64)
                UnmapViewOfFile(data_);
#else
                munmap(const_cast<unsigned char*>(data_), size_);
#endif
                data_ = nullptr;
            }
            
#if defined(_WIN32) || defined(_WIN64)
            if (hMap_)
            {
                CloseHandle(hMap_);
                hMap_ = NULL;
            }
            if (hFile_ != INVALID_HANDLE_VALUE)
            {
                CloseHandle(hFile_);
                hFile_ = INVALID_HANDLE_VALUE;
            }
#else
            if (fd_ != -1)
            {
                close(fd_);
                fd_ = -1;
            }
#endif
            size_ = 0;
        }

        const unsigned char* data() const
        {
            return data_;
        }

        size_t size() const
        {
            return size_;
        }

        const unsigned char& operator[](size_t index) const
        {
            return data_[index];
        }
    };
}

#endif
