//
// Created by derrick on 12/20/18.
//

#ifndef FOSBIN_FOSBIN_ZERGLING_H
#define FOSBIN_FOSBIN_ZERGLING_H

#include <cstdlib>

#define DEFAULT_ALLOCATION_SIZE 512

struct X86Context {
    ADDRINT rax;
    ADDRINT rbx;
    ADDRINT rcx;
    ADDRINT rdx;
    ADDRINT rdi;
    ADDRINT rsi;
    ADDRINT r8;
    ADDRINT r9;
    ADDRINT r10;
    ADDRINT r11;
    ADDRINT r12;
    ADDRINT r13;
    ADDRINT r14;
    ADDRINT r15;
    ADDRINT rip;
    ADDRINT rbp;

    friend std::ostream &operator<<(std::ostream &out, const struct X86Context &ctx);

    void prettyPrint(std::ostream &out);

    ADDRINT get_reg_value(REG reg);
};

class AllocatedArea {
public:
    AllocatedArea();

    ~AllocatedArea();

    void reset();

    ADDRINT getAddr();

    size_t size();

    void fuzz();

    bool fix_pointer(ADDRINT faulting_addr);

    /* Used to indicate if a memory area is another AllocatedArea */
    static ADDRINT MAGIC_VALUE;

    friend std::ostream &operator<<(std::ostream &out, class AllocatedArea *ctx);

    friend std::istream &operator>>(std::istream &in, class AllocatedArea *ctx);

protected:
    ADDRINT addr;
    std::vector<bool> mem_map;
    std::vector<AllocatedArea *> subareas;

    void setup_for_round(bool fuzz);
};

class FBZergContext {
public:
    FBZergContext();

    ~FBZergContext();

    std::ostream &operator<<(std::ostream &out);

    std::istream &operator>>(std::istream &in, FBZergContext &ctx);

    CONTEXT *operator>>(CONTEXT *ctx);

    const static REG argument_regs[] = {LEVEL_BASE::REG_RDI, LEVEL_BASE::REG_RSI, LEVEL_BASE::REG_RDX,
                                        LEVEL_BASE::REG_RCX, LEVEL_BASE::REG_R8, LEVEL_BASE::REG_R9};
protected:
    std::map <REG, ADDRINT> values;
    std::map<REG, AllocatedArea *> pointer_registers;
};

struct TaintedObject {
    BOOL isRegister;
    union {
        REG reg;
        ADDRINT addr;
    };
};

class PinLogger {
public:
    PinLogger(THREADID tid, std::string fname);

    ~PinLogger();

    VOID DumpBufferToFile(struct X86Context *contexts, UINT64 numElements, THREADID tid);

    std::ostream &operator<<(const AllocatedArea *aa);

    std::ostream &operator<<(ADDRINT addr);

private:
    std::ofstream _ofile;
};

VOID displayCurrentContext(const CONTEXT *ctx, UINT32 sig = 0);

#include "PinLogger.cpp"
#include "X86Context.cpp"
#include "AllocatedArea.cpp"

#endif //FOSBIN_FOSBIN_ZERGLING_H
