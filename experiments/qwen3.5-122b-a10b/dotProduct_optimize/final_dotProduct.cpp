#include "dotProduct.h"

FeatureType
dotProduct(FeatureType param[NUM_FEATURES], DataType feature[NUM_FEATURES]) {
    #pragma HLS INTERFACE m_axi port=param offset=slave bundle=gmem0
    #pragma HLS INTERFACE m_axi port=feature offset=slave bundle=gmem1
    #pragma HLS INTERFACE s_axilite port=return bundle=control

    // Partition arrays into PAR_FACTOR banks for parallel access
    #pragma HLS ARRAY_PARTITION variable=param cyclic factor=PAR_FACTOR dim=1
    #pragma HLS ARRAY_PARTITION variable=feature cyclic factor=PAR_FACTOR dim=1

    FeatureType result = 0;

    // Pipeline outer loop with II=1 for continuous throughput
    #pragma HLS PIPELINE II=1

    for (int i = 0; i < NUM_FEATURES; i += PAR_FACTOR) {
        FeatureType partial_sum = 0;
        // Fully unroll inner loop to process PAR_FACTOR elements in parallel
        #pragma HLS UNROLL factor=PAR_FACTOR

        for (int j = 0; j < PAR_FACTOR; j++) {
            partial_sum += param[i + j] * feature[i + j];
        }
        result += partial_sum;
    }

    return result;
}
