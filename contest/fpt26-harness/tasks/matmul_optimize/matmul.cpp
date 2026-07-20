#include "matmul.h"

// Baseline: functionally correct but unoptimized (no HLS pragmas).
void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]) {
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            DataT acc = 0;
            for (int k = 0; k < SIZE; k++) {
                acc += A[i][k] * B[k][j];
            }
            C[i][j] = acc;
        }
    }
}
