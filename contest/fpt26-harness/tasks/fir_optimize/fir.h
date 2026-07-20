#ifndef FIR_H
#define FIR_H

typedef float DataT;

const int LEN = 1024;
#define TAPS 32

// Fixed FIR coefficients (do not change).
static const DataT COEFFS[TAPS] = {
    0.0085f, -0.0123f, 0.0179f, -0.0246f, 0.0314f, -0.0398f, 0.0472f, -0.0551f,
    0.0629f, -0.0687f, 0.0745f, -0.0793f, 0.0841f, -0.0879f, 0.0917f, -0.0945f,
    0.0963f,  0.0945f, -0.0917f, 0.0879f, -0.0841f, 0.0793f, -0.0745f, 0.0687f,
   -0.0629f,  0.0551f, -0.0472f, 0.0398f, -0.0314f, 0.0246f, -0.0179f, 0.0123f,
};

void fir(const DataT in[LEN], DataT out[LEN]);

#endif
