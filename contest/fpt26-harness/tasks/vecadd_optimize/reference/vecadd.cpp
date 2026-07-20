#include "vecadd.h"

// Golden optimized reference: cyclic array-partition + unrolled pipelined loop.
void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
#pragma HLS ARRAY_PARTITION variable = a cyclic factor = VEC_UNROLL
#pragma HLS ARRAY_PARTITION variable = b cyclic factor = VEC_UNROLL
#pragma HLS ARRAY_PARTITION variable = c cyclic factor = VEC_UNROLL

VADD:
    for (int i = 0; i < N / VEC_UNROLL; i++) {
#pragma HLS PIPELINE
    VADD_INNER:
        for (int j = 0; j < VEC_UNROLL; j++) {
#pragma HLS UNROLL
            c[i * VEC_UNROLL + j] = a[i * VEC_UNROLL + j] + b[i * VEC_UNROLL + j];
        }
    }
}
