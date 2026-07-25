#include "residual.h"

void residual(data_t in[N], data_t out[N]) {
#pragma HLS ARRAY_PARTITION variable=in cyclic factor=2
#pragma HLS ARRAY_PARTITION variable=out cyclic factor=2

    for (int i = 0; i < N / 2; i++) {
#pragma HLS PIPELINE
        out[2 * i]     = 2 * in[2 * i]     + in[2 * i];
        out[2 * i + 1] = 2 * in[2 * i + 1] + in[2 * i + 1];
    }
}
