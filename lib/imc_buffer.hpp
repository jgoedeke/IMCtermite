#ifndef IMCBUFFER
#define IMCBUFFER

#include <string>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>

namespace imc
{
    class MemoryMappedFile
    {
    private:
        const unsigned char* data_;
        size_t size_;
        int fd_;

    public:
        MemoryMappedFile() : data_(nullptr), size_(0), fd_(-1) {}

        ~MemoryMappedFile()
        {
            close_file();
        }

        // Delete copy constructor and assignment operator to prevent double-free
        MemoryMappedFile(const MemoryMappedFile&) = delete;
        MemoryMappedFile& operator=(const MemoryMappedFile&) = delete;

        // Implement move constructor
        MemoryMappedFile(MemoryMappedFile&& other) noexcept
            : data_(other.data_), size_(other.size_), fd_(other.fd_)
        {
            other.data_ = nullptr;
            other.size_ = 0;
            other.fd_ = -1;
        }

        // Implement move assignment operator
        MemoryMappedFile& operator=(MemoryMappedFile&& other) noexcept
        {
            if (this != &other)
            {
                close_file();
                data_ = other.data_;
                size_ = other.size_;
                fd_ = other.fd_;
                other.data_ = nullptr;
                other.size_ = 0;
                other.fd_ = -1;
            }
            return *this;
        }

        void map(const std::string& filename)
        {
            close_file();

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
        }

        void close_file()
        {
            if (data_)
            {
                munmap(const_cast<unsigned char*>(data_), size_);
                data_ = nullptr;
            }
            if (fd_ != -1)
            {
                close(fd_);
                fd_ = -1;
            }
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
