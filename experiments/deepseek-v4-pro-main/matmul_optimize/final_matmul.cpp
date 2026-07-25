#include "matmul.h"

// Helper functions for each stage to enable DATAFLOW
static void load_A(const DataT A[SIZE][SIZE], DataT A_local[SIZE][SIZE]) {
    #pragma HLS INLINE off
    for (int idx = 0; idx < SIZE * SIZE; ++idx) {
        #pragma HLS PIPELINE II=1
        int i = idx / SIZE;
        int j = idx % SIZE;
        A_local[i][j] = A[i][j];
    }
}

static void load_B(const DataT B[SIZE][SIZE], DataT B_local[SIZE][SIZE]) {
    #pragma HLS INLINE off
    for (int idx = 0; idx < SIZE * SIZE; ++idx) {
        #pragma HLS PIPELINE II=1
        int i = idx / SIZE;
        int j = idx % SIZE;
        B_local[i][j] = B[i][j];
    }
}

static void compute(const DataT A_local[SIZE][SIZE],
                    const DataT B_local[SIZE][SIZE],
                    DataT C_local[SIZE][SIZE]) {
    #pragma HLS INLINE off
    for (int i = 0; i < SIZE; ++i) {
        for (int j = 0; j < SIZE; ++j) {
            #pragma HLS PIPELINE II=1
            DataT temp[SIZE];
            #pragma HLS ARRAY_PARTITION variable=temp complete dim=1

            // Multiply row i of A with column j of B (all 32 products in parallel)
            for (int k = 0; k < SIZE; ++k) {
                #pragma HLS UNROLL
                temp[k] = A_local[i][k] * B_local[k][j];
            }

            // Balanced adder tree to sum the 32 products
            for (int stride = SIZE / 2; stride > 0; stride /= 2) {
                for (int k = 0; k < stride; ++k) {
                    #pragma HLS UNROLL
                    temp[k] = temp[k] + temp[k + stride];
                }
            }

            C_local[i][j] = temp[0];
        }
    }
}

static void store_C(DataT C[SIZE][SIZE], const DataT C_local[SIZE][SIZE]) {
    #pragma HLS INLINE off
    for (int idx = 0; idx < SIZE * SIZE; ++idx) {
        #pragma HLS PIPELINE II=1
        int i = idx / SIZE;
        int j = idx % SIZE;
        C[i][j] = C_local[i][j];
    }
}

void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]) {
    #pragma HLS INTERFACE m_axi port=A depth=1024 bundle=gmem0
    #pragma HLS INTERFACE m_axi port=B depth=1024 bundle=gmem1
    #pragma HLS INTERFACE m_axi port=C depth=1024 bundle=gmem2
    #pragma HLS INTERFACE s_axilite port=return bundle=control

    // Local buffers to hold the matrices on-chip
    DataT A_local[SIZE][SIZE];
    DataT B_local[SIZE][SIZE];
    DataT C_local[SIZE][SIZE];

    // Keep the same partitioning as before to allow parallel access in compute
    #pragma HLS ARRAY_PARTITION variable=A_local complete dim=2
    #pragma HLS ARRAY_PARTITION variable=B_local complete dim=1

    // Task-level parallelism: all four stages run concurrently
    #pragma HLS DATAFLOW
    load_A(A, A_local);
    load_B(B, B_local);
    compute(A_local, B_local, C_local);
    store_C(C, C_local);
}
