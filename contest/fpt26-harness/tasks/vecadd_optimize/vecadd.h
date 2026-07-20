#ifndef VECADD_H
#define VECADD_H

typedef float DataT;

const int N = 4096;
#define VEC_UNROLL 8

void vecadd(const DataT a[N], const DataT b[N], DataT c[N]);

#endif
