#include "fir.h"

void fir(const DataT in[LEN], DataT out[LEN]) {
#pragma HLS ARRAY_PARTITION variable=COEFFS complete

outer:
    for (int i = 0; i < LEN; i++) {
#pragma HLS PIPELINE II=1
        DataT acc = 0.0f;
        for (int j = 0; j < TAPS; j++) {
            acc += (i >= j) ? in[i - j] * COEFFS[j] : 0.0f;
        }
        out[i] = acc;
    }
}
