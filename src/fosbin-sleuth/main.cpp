#include <iostream>
#include <fosbin-sleuth/fullSleuthTest.h>
#include "fosbin-sleuth.h"

#include "argumentTestCase.h"
#include "binaryDescriptor.h"

void usage() {
    std::cout << "fosbin-sleuth /path/to/binary/descriptor" << std::endl;
}

int main(int argc, char **argv) {
    std::cout << SLEUTH_NAME
              << " v. " << FOSBIN_VERSION_MAJOR << "." << FOSBIN_VERSION_MINOR
              << " starting. Good luck, Sherlock." << std::endl;

    if (argc != 2) {
        usage();
        exit(1);
    }

    fbf::BinaryDescriptor binDesc(argv[1]);

    fbf::FullSleuthTest test(argv[1], DEFAULT_INT, DEFAULT_DOUBLE, STR_LEN, PTR_LEN);
    test.run();
    test.output(std::cout);

    return 0;
}
