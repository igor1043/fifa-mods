#ifndef BENCH_IMPORT_ADAPTER_H
#define BENCH_IMPORT_ADAPTER_H
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>

#define BENCH_IMPORT_RVA 0x414EB83U
#define BENCH_IMPORT_SITE_SIZE 7U
#define BENCH_IMPORT_CODE_SIZE 23U
static const unsigned char bench_import_original[BENCH_IMPORT_SITE_SIZE] =
    {0x41,0x8B,0x9D,0x10,0x0C,0x00,0x00};

typedef struct BenchImportAdapter {
    unsigned char *page;
    uintptr_t image;
    unsigned char site_patch[BENCH_IMPORT_SITE_SIZE];
    RUNTIME_FUNCTION runtime;
    BOOL registered;
    BOOL installed;
} BenchImportAdapter;

/* A native instruction adapter, not a C callback or game-function call:
 * mov dword ptr [r13+C10],12; original mov ebx,[r13+C10]; jmp resume.
 * No stack/flags changes, no ID writes, no write at C14.
 */
static __inline int bench_import_emit(uintptr_t site, uintptr_t stub,
    unsigned char code[BENCH_IMPORT_CODE_SIZE], unsigned char patch[BENCH_IMPORT_SITE_SIZE])
{
    static const unsigned char body[18] = {
        0x41,0xC7,0x85,0x10,0x0C,0x00,0x00,0x0C,0x00,0x00,0x00,
        0x41,0x8B,0x9D,0x10,0x0C,0x00,0x00
    };
    const int64_t outbound=(int64_t)stub-(int64_t)(site+5U);
    const int64_t inbound=(int64_t)(site+BENCH_IMPORT_SITE_SIZE)-
        (int64_t)(stub+BENCH_IMPORT_CODE_SIZE);
    int32_t out32, in32;
    if (!code || !patch || outbound < INT32_MIN || outbound > INT32_MAX ||
        inbound < INT32_MIN || inbound > INT32_MAX) return 0;
    out32=(int32_t)outbound; in32=(int32_t)inbound;
    memcpy(code,body,sizeof(body)); code[18]=0xE9;
    memcpy(code+19,&in32,4U);
    patch[0]=0xE9; memcpy(patch+1,&out32,4U); patch[5]=0x90; patch[6]=0x90;
    return 1;
}

BOOL bench_import_install(BenchImportAdapter *adapter, uintptr_t image, SIZE_T image_size);
BOOL bench_import_remove(BenchImportAdapter *adapter);
/* Shared transactional site writer: callers must verify native ownership,
 * startup timing and complete instructions before requesting a detour. */
unsigned char *bench_adapter_near_page(uintptr_t image, SIZE_T image_size, uintptr_t site);
BOOL bench_adapter_write_site(uintptr_t address,const unsigned char *before,
                              const unsigned char *after);
BOOL bench_adapter_write_bytes(uintptr_t address,const unsigned char *before,
                              const unsigned char *after,SIZE_T length);
#endif
