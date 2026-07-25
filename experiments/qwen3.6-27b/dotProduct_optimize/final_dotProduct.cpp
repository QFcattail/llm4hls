#include "dotProduct.h"

FeatureType
dotProduct(FeatureType param[NUM_FEATURES], DataType feature[NUM_FEATURES]) {
    FeatureType result = 0;
    #pragma HLS PIPELINE
    #pragma HLS UNROLL factor=PAR_FACTOR
    for (int i = 0; i < NUM_FEATURES; i++) {
        result += param[i] * feature[i];
    }
    return result;
}
