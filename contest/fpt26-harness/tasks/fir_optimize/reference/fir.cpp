#include "fir.h"

// Golden optimized reference: fully-partitioned shift register + unrolled MAC
// tree inside a pipelined outer loop (classic FIR optimization).
void fir(const DataT in[LEN], DataT out[LEN]) {
#pragma HLS ARRAY_PARTITION variable = COEFFS complete

    DataT shift_reg[TAPS];
#pragma HLS ARRAY_PARTITION variable = shift_reg complete

    // Zero the sample history
    for (int j = 0; j < TAPS; j++) {
#pragma HLS UNROLL
        shift_reg[j] = 0;
    }

FIR_OUTER:
    for (int i = 0; i < LEN; i++) {
#pragma HLS PIPELINE
        // Shift in the new sample
    SHIFT:
        for (int j = TAPS - 1; j > 0; j--) {
#pragma HLS UNROLL
            shift_reg[j] = shift_reg[j - 1];
        }
        shift_reg[0] = in[i];

        // Multiply-accumulate over all taps
        DataT acc = 0;
    MAC:
        for (int j = 0; j < TAPS; j++) {
#pragma HLS UNROLL
            acc += shift_reg[j] * COEFFS[j];
        }
        out[i] = acc;
    }
}
