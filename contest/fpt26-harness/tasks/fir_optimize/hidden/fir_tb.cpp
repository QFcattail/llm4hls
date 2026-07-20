#include <cmath>
#include <iostream>

#include "fir.h"

// Hidden grading testbench: pseudo-random impulse/step mixture (LCG), different
// from the public bench. Any functionally correct implementation must pass.
int main() {
    DataT in[LEN];
    DataT out[LEN];

    unsigned int seed = 777u;
    for (int i = 0; i < LEN; i++) {
        seed = seed * 1103515245u + 12345u; // LCG
        in[i] = DataT((int(seed >> 9) % 4096 - 2048) / 1024.0f); // [-2, 2)
    }
    // Inject an impulse to probe the zero-history boundary condition
    in[0] = DataT(3.0f);

    fir(in, out);

    for (int i = 0; i < LEN; i++) {
        float expected = 0.0f;
        for (int j = 0; j < TAPS; j++) {
            if (i >= j) {
                expected += float(in[i - j]) * float(COEFFS[j]);
            }
        }
        float got = float(out[i]);
        if (std::abs(got - expected) > 1e-3) {
            std::cout << "Test failed at i=" << i << "! Expected: " << expected
                      << ", Got: " << got << std::endl;
            return 1;
        }
    }

    std::cout << "Test passed!" << std::endl;
    return 0;
}
