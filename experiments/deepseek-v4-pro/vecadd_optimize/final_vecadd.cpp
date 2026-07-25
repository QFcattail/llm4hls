#include "vecadd.h"

void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
    #pragma HLS array_partition variable=a cyclic factor=16
    #pragma HLS array_partition variable=b cyclic factor=16
    #pragma HLS array_partition variable=c cyclic factor=16

    for (int i = 0; i < N; i++) {
        #pragma HLS pipeline II=1
        #pragma HLS unroll factor=16
        c[i] = a[i] + b[i];
    }
}
