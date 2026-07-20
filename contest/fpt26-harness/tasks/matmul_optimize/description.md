Kernel Description:
`matmul` multiplies two `SIZE`x`SIZE` float matrices `A` and `B`, writing the
product to `C`: `C[i][j] = sum_{k=0..SIZE-1} A[i][k] * B[k][j]`.

Top-Level Function: `matmul`

Complete Function Signature:
`void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE], DataT C[SIZE][SIZE]);`

Inputs:
- `A`: `SIZE`x`SIZE` matrix of `DataT` (float) values.
- `B`: `SIZE`x`SIZE` matrix of `DataT` (float) values.

Output:
- `C`: `SIZE`x`SIZE` matrix of `DataT` (float) values, the matrix product.

Constants (in the header, do not change):
- `SIZE = 32`.

Numerical tolerance: the testbench accepts an absolute error up to 1e-2 versus a
float reference (accumulation-order differences are expected).

Initial condition:
The provided implementation is functionally correct but UNOPTIMIZED — a
triple-nested loop with no HLS pragmas, so its synthesized latency is high.
Your goal is to reduce latency (while keeping it correct and synthesizable) on
the target Alveo U55C at 200 MHz.
