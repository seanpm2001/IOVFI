//
// Created by derrick on 9/17/18.
//

#ifndef FOSBIN_ITESTCASE_H
#define FOSBIN_ITESTCASE_H

#include <string>
#include <random>

namespace fbf {
    class ITestCase {
    public:
        ITestCase();
        virtual const std::string get_test_name() = 0;
        virtual int run_test() = 0;

        const static int PASS = 0;
        const static int FAIL = 1;

    protected:
        int rand();

    private:
        std::random_device rd_;
        std::mt19937 mt_;
        std::uniform_int_distribution<int> dist_;
    };
}

#endif //FOSBIN_ITESTCASE_H
