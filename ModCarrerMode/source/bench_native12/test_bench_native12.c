#include <stdio.h>
#include "bench_native12_core.h"

int main(void)
{
    size_t patch_index, index;
    unsigned int checks=0;
    if (bench_native12_targets[0]!=12U || bench_native12_targets[1]!=12U) return 6;
    for (patch_index=0; patch_index<BENCH_NATIVE12_PATCH_COUNT; ++patch_index) {
        const BenchNativePatch *patch=&bench_native12_patches[patch_index];
        unsigned char bytes[BENCH_NATIVE12_MAX_SIGNATURE];
        memcpy(bytes,patch->before,patch->size);
        if (!bench_native12_signature(patch,bytes,patch->size)) return 1;
        ++checks; bytes[patch->immediate]=12U;
        if (!bench_native12_signature(patch,bytes,patch->size)) return 2;
        ++checks; bytes[patch->immediate]=8U;
        if (bench_native12_signature(patch,bytes,patch->size)) return 3;
        ++checks; bytes[patch->immediate]=7U;
        for (index=0; index<patch->size; ++index) {
            if (index == patch->immediate) continue;
            bytes[index]^=1U;
            if (bench_native12_signature(patch,bytes,patch->size)) return 4;
            ++checks; bytes[index]^=1U;
        }
        if (bench_native12_signature(patch,bytes,patch->size-1U)) return 5;
        ++checks;
    }
    printf("bench_native12: %u signature checks passed; working v3 loader targets 12/12; gameplay not tested\n",checks);
    return 0;
}
