#include "residual.h"

void residual(data_t in[N], data_t out[N]) {
    #pragma HLS PIPELINE II=1
    for (int i = 0; i < N; i++) {
        out[i] = 3 * in[i];
    }
}
