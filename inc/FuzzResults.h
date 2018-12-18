//
// Created by derrick on 12/6/18.
//

#ifndef FOSBIN_FUZZRESULTS_H
#define FOSBIN_FUZZRESULTS_H

#ifdef __cplusplus
#include <cstdint>
#else
#include <stdint.h>
#endif

#define NREGS           6
#define MAX_TRIES       NREGS
#define BUF_PAGE_SZ     1

struct FuzzingBuffer {
    uintptr_t location;
    size_t length;
};

struct FuzzingRegister {
    uint8_t is_pointer;
    union {
        uint64_t value;
        struct FuzzingBuffer buffer;
    };
};

struct X86FuzzingContext {
    struct FuzzingRegister regs[NREGS];
    struct FuzzingRegister ret;
};

struct FuzzingResult {
    uintptr_t target_addr;
    struct X86FuzzingContext preexecution;
    struct X86FuzzingContext postexecution;
};

struct BasicBlock {
    uintptr_t addr;
    size_t size;
};

#endif //FOSBIN_FUZZRESULTS_H
