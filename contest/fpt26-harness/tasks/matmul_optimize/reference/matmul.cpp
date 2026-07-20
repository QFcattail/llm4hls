#include "matmul.h"

// Golden optimized reference: partition the varying inner-loop dimensions so
// the unrolled dot product reads all operands in parallel, inside a pipelined
// column loop.
void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]) {
    // Inner k-loop reads A[i][k] (dim 2 varies) and B[k][j] (dim 1 varies)
#pragma HLS ARRAY_PARTITION variable = A complete dim = 2
#pragma HLS ARRAY_PARTITION variable = B complete dim = 1

ROW:
    for (int i = 0; i < SIZE; i++) {
    COL:
        for (int j = 0; j < SIZE; j++) {
#pragma HLS PIPELINE
            DataT acc = 0;
        PROD:
            for (int k = 0; k < SIZE; k++) {
#pragma HLS UNROLL
                acc += A[i][k] * B[k][j];
            }
            C[i][j] = acc;
        }
    }
}
