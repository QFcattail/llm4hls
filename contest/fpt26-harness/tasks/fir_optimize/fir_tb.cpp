#include <cmath>
#include <iostream>

#include "fir.h"

int main() {
    DataT in[LEN];
    DataT out[LEN];

    // Initialize input with a deterministic mixed signal
    for (int i = 0; i < LEN; i++) {
        in[i] = DataT(std::sin(i * 0.1) + 0.5 * std::cos(i * 0.03));
    }

    fir(in, out);

    // Float reference computation
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
