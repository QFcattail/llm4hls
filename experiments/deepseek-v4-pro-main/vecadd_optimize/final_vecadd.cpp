#include "vecadd.h"

void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
    // AXI4 master interfaces for external memory
    #pragma HLS INTERFACE m_axi port=a bundle=gmem0 offset=slave
    #pragma HLS INTERFACE m_axi port=b bundle=gmem1 offset=slave
    #pragma HLS INTERFACE m_axi port=c bundle=gmem2 offset=slave
    #pragma HLS INTERFACE s_axilite port=return

    // Tile the loop by VEC_UNROLL to exploit burst-wide memory transfers.
    // The inner loop is completely unrolled, enabling the tool to coalesce
    // multiple scalar accesses into wide (256-bit) AXI bursts.
    for (int i = 0; i < N; i += VEC_UNROLL) {
        #pragma HLS PIPELINE II=1
        for (int j = 0; j < VEC_UNROLL; j++) {
            #pragma HLS UNROLL
            c[i + j] = a[i + j] + b[i + j];
        }
    }
}
