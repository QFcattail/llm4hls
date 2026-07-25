#include "fir.h"

void fir(const DataT in[LEN], DataT out[LEN]) {
    // Parallelism factor – compute K = 2 outputs per cycle
    const int K = 2;

    // Shift register with extra depth to provide overlapping windows
    // of length TAPS for all K outputs simultaneously.
    DataT buffer[TAPS + K - 1];   // size = 33 for TAPS=32, K=2
    #pragma HLS ARRAY_PARTITION variable=buffer complete dim=1

    // Coefficients remain fully partitioned for parallel multiply
    #pragma HLS ARRAY_PARTITION variable=COEFFS complete dim=1

    // Initialise the whole buffer with zero history
    init_zero:
    for (int j = 0; j < TAPS + K - 1; ++j) {
        #pragma HLS UNROLL
        buffer[j] = 0.0f;
    }

    // Process the input in blocks of K samples, fully pipelined
    outer_loop:
    for (int i = 0; i < LEN; i += K) {
        #pragma HLS PIPELINE II=1

        // Read the new input samples
        DataT x0 = in[i];
        DataT x1 = in[i + 1];   // LEN is a multiple of K, so safe

        // ---- Shift in the two new samples ----
        // Shift existing entries to the right by K positions (K=2).
        // Buffer order: buffer[0] is the newest sample, buffer[1] the next, …
        shift:
        for (int j = TAPS + K - 2; j >= K; --j) {
            #pragma HLS UNROLL
            buffer[j] = buffer[j - K];
        }
        buffer[1] = x0;   // older of the two new samples
        buffer[0] = x1;   // newest sample

        // ---- Compute K outputs in parallel ----
        DataT acc0 = 0.0f;
        DataT acc1 = 0.0f;

        dot_product:
        for (int j = 0; j < TAPS; ++j) {
            #pragma HLS UNROLL
            // out[i]   uses window starting at buffer[1] (in[i] is the most recent for this output)
            acc0 += buffer[1 + j] * COEFFS[j];
            // out[i+1] uses window starting at buffer[0] (in[i+1] is the most recent)
            acc1 += buffer[0 + j] * COEFFS[j];
        }

        out[i]     = acc0;
        out[i + 1] = acc1;
    }
}
