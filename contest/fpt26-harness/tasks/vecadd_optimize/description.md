Kernel Description:
`vecadd` computes the element-wise sum of two length-`N` float vectors, `a` and
`b`, writing the result into `c`: `c[i] = a[i] + b[i]`.

Top-Level Function: `vecadd`

Complete Function Signature:
`void vecadd(const DataT a[N], const DataT b[N], DataT c[N]);`

Inputs:
- `a`: array of `N` `DataT` (float) values.
- `b`: array of `N` `DataT` (float) values.

Output:
- `c`: array of `N` `DataT` (float) values, the element-wise sum.

Constants (in the header, do not change):
- `N = 4096`, `VEC_UNROLL = 8`.

Numerical tolerance: the testbench accepts an absolute error up to 1e-3 versus a
float reference.

Initial condition:
The provided implementation is functionally correct but UNOPTIMIZED — a single
sequential element-wise loop with no HLS pragmas, so its synthesized latency is
high. Your goal is to reduce latency (while keeping it correct and synthesizable)
on the target Alveo U55C at 200 MHz.
