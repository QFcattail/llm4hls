#include "fir.h"

// Baseline: functionally correct but unoptimized (no HLS pragmas).
// Block FIR filter: out[i] = sum_{j=0..TAPS-1} in[i-j] * COEFFS[j]
// with zero history for i < j.
void fir(const DataT in[LEN], DataT out[LEN]) {
    for (int i = 0; i < LEN; i++) {
        DataT acc = 0;
        for (int j = 0; j < TAPS; j++) {
            if (i >= j) {
                acc += in[i - j] * COEFFS[j];
            }
        }
        out[i] = acc;
    }
}
