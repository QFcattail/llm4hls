#include "matmul.h"

void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]) {
    #pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmem0
    #pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmem1
    #pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmem2
    #pragma HLS INTERFACE s_axilite port=return bundle=ctrl

    #pragma HLS ARRAY_PARTITION variable=A complete dim=1
    #pragma HLS ARRAY_PARTITION variable=B complete dim=2

    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            DataT acc = 0;
            #pragma HLS PIPELINE II=1
            for (int k = 0; k < SIZE; k++) {
                acc += A[i][k] * B[k][j];
            }
            C[i][j] = acc;
        }
    }
}
