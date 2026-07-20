#include <cmath>
#include <iostream>

#include "vecadd.h"

int main() {
    DataT a[N];
    DataT b[N];
    DataT c[N];

    // Initialize inputs with some test values
    for (int i = 0; i < N; i++) {
        a[i] = DataT(1.0f / (i + 1));      // decreasing positive values
        b[i] = DataT(-2.0f / (i + 1) + i); // mixed sign, growing magnitude
    }

    vecadd(a, b, c);

    // Compare against a float reference (element-wise add is exact, but allow
    // a small margin in case of datatype changes)
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
