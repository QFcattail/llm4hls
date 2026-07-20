#include <cmath>
#include <iostream>

#include "vecadd.h"

// Hidden grading testbench: pseudo-random data (LCG), different from the public
// bench. Any functionally correct implementation must pass.
int main() {
    DataT a[N];
    DataT b[N];
    DataT c[N];

    unsigned int seed = 12345u;
    for (int i = 0; i < N; i++) {
        seed = seed * 1664525u + 1013904223u; // LCG
        a[i] = DataT((int(seed >> 8) % 8192 - 4096) / 512.0f); // [-8, 8)
        seed = seed * 1664525u + 1013904223u;
        b[i] = DataT((int(seed >> 8) % 8192 - 4096) / 512.0f);
    }

    vecadd(a, b, c);

    for (int i = 0; i < N; i++) {
        float expected = float(a[i]) + float(b[i]);
        float got = float(c[i]);
        if (std::abs(got - expected) > 1e-3) {
            std::cout << "Test failed at i=" << i << "! Expected: " << expected
                      << ", Got: " << got << std::endl;
            return 1;
        }
    }

    std::cout << "Test passed!" << std::endl;
    return 0;
}
