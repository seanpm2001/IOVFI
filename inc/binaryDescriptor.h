//
// Created by derrick on 9/17/18.
//

#ifndef FOSBIN_BINARYDESCRIPTOR_H
#define FOSBIN_BINARYDESCRIPTOR_H
#include <set>
#include <map>
#include "binSection.h"
#include <experimental/filesystem>

namespace fs = std::experimental::filesystem;

namespace fbf {
    class BinaryDescriptor {
    protected:
        std::set<uintptr_t> offsets_;
        fs::path bin_path_, desc_path_;
        BinSection text_;
        BinSection data_;
        BinSection bss_;
        std::map<uintptr_t, std::string> syms_;

        uintptr_t parse_offset(std::string &offset);

    public:
        BinaryDescriptor(fs::path path);
        ~BinaryDescriptor();
        BinSection& getText();
        BinSection& getData();
        BinSection& getBss();
        fs::path& getPath();
        std::set<uintptr_t> getOffsets();
        const std::string getSym(uintptr_t location);
        bool isSharedLibrary();
    };
}

#endif //FOSBIN_BINARYDESCRIPTOR_H
