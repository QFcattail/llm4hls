#include <cmath>
#include <iostream>

#include "matmul.h"

// Hidden grading testbench: pseudo-random matrices (LCG), different from the
// public bench. Any functionally correct implementation must pass.
int main() {
    static DataT A[SIZE][SIZE];
    static DataT B[SIZE][SIZE];
    static DataT C[SIZE][SIZE];

    unsigned int seed = 999u;
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            seed = seed * 1664525u + 1013904223u; // LCG
            A[i][j] = DataT((int(seed >> 8) % 2048 - 1024) / 512.0f); // [-2, 2)
            seed = seed * 1664525u + 1013904223u;
            B[i][j] = DataT((int(seed >> 8) % 2048 - 1024) / 512.0f);
        }
    }

    matmul(A, B, C);

    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            float expected = 0.0f;
            for (int k = 0; k < SIZE; k++) {
                expected += float(A[i][k]) * float(B[k][j]);
            }
            float got = float(C[i][j]);
            // Sums of 32 products of O(1) values; allow for reordering error
            if (std::abs(got - expected) > 1e-2) {
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
