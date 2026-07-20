#ifndef MATMUL_H
#define MATMUL_H

typedef float DataT;

#define SIZE 32

void matmul(const DataT A[SIZE][SIZE], const DataT B[SIZE][SIZE],
            DataT C[SIZE][SIZE]);

#endif
