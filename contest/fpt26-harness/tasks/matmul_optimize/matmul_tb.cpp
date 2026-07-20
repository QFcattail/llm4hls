#include <cmath>
#include <iostream>

#include "matmul.h"

int main() {
    static DataT A[SIZE][SIZE];
    static DataT B[SIZE][SIZE];
    static DataT C[SIZE][SIZE];

    // Initialize inputs with deterministic values
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            A[i][j] = DataT(1.0f / (i + j + 1));
            B[i][j] = DataT((i == j) ? 1.0f : 0.5f / (i + j + 1));
        }
    }

    matmul(A, B, C);

    // Float reference computation
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            float expected = 0.0f;
            for (int k = 0; k < SIZE; k++) {
                expected += float(A[i][k]) * float(B[k][j]);
            }
            float got = float(C[i][j]);
            if (std::abs(got - expected) > 1e-3) {
                std::cout << "Test failed at (" << i << "," << j
                          << ")! Expected: " << expected << ", Got: " << got
                          << std::endl;
                return 1;
            }
        }
    }

    std::cout << "Test passed!" << std::endl;
    return 0;
}
