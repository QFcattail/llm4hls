Kernel Description:
`fir` applies a `TAPS`-tap FIR filter with fixed coefficients `COEFFS` to a
length-`LEN` float input block `in`, writing the filtered block to `out`:
`out[i] = sum_{j=0..TAPS-1} in[i-j] * COEFFS[j]`, with zero history (samples
before index 0 are treated as 0).

Top-Level Function: `fir`

Complete Function Signature:
`void fir(const DataT in[LEN], DataT out[LEN]);`

Inputs:
- `in`: array of `LEN` `DataT` (float) input samples.

Output:
- `out`: array of `LEN` `DataT` (float) filtered samples.

Constants (in the header, do not change):
- `LEN = 1024`, `TAPS = 32`, and the coefficient table `COEFFS[TAPS]`.

Numerical tolerance: the testbench accepts an absolute error up to 1e-3 versus a
float reference (accumulation-order differences are expected).

Initial condition:
The provided implementation is functionally correct but UNOPTIMIZED — a nested
loop over outputs and taps with no HLS pragmas, so its synthesized latency is
high. Your goal is to reduce latency (while keeping it correct and synthesizable)
on the target Alveo U55C at 200 MHz.
