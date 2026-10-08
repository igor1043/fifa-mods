#ifndef BENCH_NATIVE12_CORE_H
#define BENCH_NATIVE12_CORE_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define BENCH_NATIVE12_PATCH_COUNT 2U
#define BENCH_NATIVE12_MAX_SIGNATURE 20U
typedef struct BenchNativePatch {
    const char *name;
    uintptr_t rva;
    size_t size;
    size_t immediate;
    unsigned char before[BENCH_NATIVE12_MAX_SIGNATURE];
} BenchNativePatch;

/* The complete file routines and private execution are documented in Estudos.
 * These are two LIMITS in native player preparation, not a UI count reply.
 * Each replacement changes exactly one immediate byte of an instruction.
 * No ID, actor pointer, GameSettings C14 or substitution counter is written.
 */
static const BenchNativePatch bench_native12_patches[BENCH_NATIVE12_PATCH_COUNT] = {
    {"FCE_role_limit", (uintptr_t)0x415AED7U, 4U, 3U,
        {0x44,0x8D,0x77,0x07}},
    {"actor_preparation_role_limit", (uintptr_t)0x44B4340U, 20U, 10U,
        {0x41,0x83,0x38,0x1C,0x75,0x0E,0xFF,0xC6,0x83,0xFE,
         0x07,0x7E,0x07,0x41,0xC7,0x00,0x1D,0x00,0x00,0x00}}
};

/* Retain the v3 loader that constructed twelve real, usable reserves.
 * Reducing the late AI copy to seven (v5) blocked match initialization.
 * Visual filtering now belongs exclusively to the native renderer adapter. */
static const unsigned char bench_native12_targets[BENCH_NATIVE12_PATCH_COUNT]={12U,12U};

/* 7 and 12 are the only accepted complete instruction signatures. */
static int bench_native12_signature(const BenchNativePatch *patch,
    const unsigned char *bytes, size_t size)
{
    size_t index;
    if (!patch || !bytes || size != patch->size ||
        patch->size > BENCH_NATIVE12_MAX_SIGNATURE || patch->immediate >= size)
        return 0;
    for (index=0; index<size; ++index) {
        if (index == patch->immediate) {
            if (bytes[index] != 7U && bytes[index] != 12U) return 0;
        } else if (bytes[index] != patch->before[index]) return 0;
    }
    return 1;
}
#endif
