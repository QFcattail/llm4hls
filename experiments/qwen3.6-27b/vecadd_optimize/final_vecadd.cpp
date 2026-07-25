#include "vecadd.h"

void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
#pragma HLS UNROLL factor=VEC_UNROLL
    for (int i = 0; i < N; i++) {
        c[i] = a[i] + b[i];
    }
}
