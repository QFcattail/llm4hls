#include "fir.h"

// Optimized FIR filter for Alveo U55C @ 200 MHz
// Strategy 1: Partial Inner Loop Unroll (factor=4) to reduce DSP congestion and improve timing closure.
// Strategy 2: Shift Register Window (manual shift + ARRAY_PARTITION) to eliminate pointer/indexing dependencies.
void fir(const DataT in[LEN], DataT out[LEN]) {
    // Memory interfaces for Alveo DDR/HBM
    #pragma HLS INTERFACE m_axi port=in offset=slave bundle=gmem0
    #pragma HLS INTERFACE m_axi port=out offset=slave bundle=gmem1
    #pragma HLS INTERFACE s_axilite port=return bundle=control

    // Local shift register window for last TAPS samples.
    // Initialized to 0 to handle zero-history condition without branches.
    DataT window[TAPS] = {0};
    #pragma HLS ARRAY_PARTITION variable=window complete dim=1
    
    for (int i = 0; i < LEN; i++) {
        #pragma HLS PIPELINE II=1
        
        // Shift register update: Move data towards higher indices
        // Fully unrolled to execute in parallel (register-to-register moves)
        for (int k = TAPS - 1; k > 0; k--) {
            #pragma HLS UNROLL
            window[k] = window[k-1];
        }
        
        // Insert new sample at the head of the window
        window[0] = in[i];
        
        // Compute FIR output using window contents
        DataT acc = 0;
        for (int j = 0; j < TAPS; j++) {
            #pragma HLS UNROLL factor=4
            
            // Direct access to shift register eliminates modulo/indexing overhead
            acc += window[j] * COEFFS[j];
        }
        out[i] = acc;
    }
}
