#include "vecadd.h"

void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
    #pragma HLS INTERFACE m_axi port=a offset=slave bundle=gmem0
    #pragma HLS INTERFACE m_axi port=b offset=slave bundle=gmem1
    #pragma HLS INTERFACE m_axi port=c offset=slave bundle=gmem2
    #pragma HLS INTERFACE s_axilite port=return bundle=control

    // Partition arrays to enable parallel memory access across iterations
    // Cyclic partitioning distributes elements across banks to avoid bank conflicts
    #pragma HLS ARRAY_PARTITION variable=a cyclic factor=VEC_UNROLL dim=1
    #pragma HLS ARRAY_PARTITION variable=b cyclic factor=VEC_UNROLL dim=1
    #pragma HLS ARRAY_PARTITION variable=c cyclic factor=VEC_UNROLL dim=1

    // Pipeline the loop with initiation interval of 1 for maximum throughput
    // Array partitioning enables II=1 by allowing parallel memory accesses
    #pragma HLS PIPELINE II=1

    for (int i = 0; i < N; i++) {
        c[i] = a[i] + b[i];
    }
}
