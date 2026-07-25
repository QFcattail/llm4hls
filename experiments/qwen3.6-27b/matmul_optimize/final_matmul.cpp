#include "matmul.h"

void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]) {
    #pragma HLS ARRAY_PARTITION variable=A dim=1 complete
    #pragma HLS ARRAY_PARTITION variable=B dim=2 complete
    #pragma HLS ARRAY_PARTITION variable=C dim=1 complete

    for (int j = 0; j < SIZE; j++) {
        #pragma HLS PIPELINE
        for (int i = 0; i < SIZE; i++) {
            DataT acc = 0;
            for (int k = 0; k < SIZE; k++) {
                #pragma HLS UNROLL complete
                acc += A[i][k] * B[k][j];
            }
            C[i][j] = acc;
        }
    }
}
