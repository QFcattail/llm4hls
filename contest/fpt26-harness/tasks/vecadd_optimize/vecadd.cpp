#include "vecadd.h"

// Baseline: functionally correct but unoptimized (no HLS pragmas).
void vecadd(const DataT a[N], const DataT b[N], DataT c[N]) {
    for (int i = 0; i < N; i++) {
        c[i] = a[i] + b[i];
    }
}
