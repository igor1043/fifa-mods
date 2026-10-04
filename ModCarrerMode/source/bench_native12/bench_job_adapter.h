#ifndef BENCH_JOB_ADAPTER_H
#define BENCH_JOB_ADAPTER_H
#include "bench_import_adapter.h"

extern const unsigned char bench_job_template_begin[],bench_job_template_end[];
extern const unsigned char bench_job_flush_pointer[];
extern const unsigned char bench_job_original_instruction[],bench_job_counter_pointer[];
extern const unsigned char bench_job_owner_before[],bench_job_owner_after[];
extern const unsigned char bench_job_flags_restore[];
extern const unsigned char bench_job_owner_shift_before[],bench_job_owner_shift_after[];
extern const unsigned char bench_job_stack_release[];

#define BENCH_JOB_ADAPTER_COUNT 4U
typedef struct BenchJobAdapter {
    BenchImportAdapter entry;
    uintptr_t rva;
    unsigned char original[7];
    RUNTIME_FUNCTION runtime[2];
    volatile LONG64 batch_counter;
    BOOL published;
} BenchJobAdapter;

BOOL bench_job_install(BenchJobAdapter *adapter, uintptr_t image, SIZE_T image_size,
                      unsigned int kind);
BOOL bench_job_remove(BenchJobAdapter *adapter);
BOOL bench_job_emit(uintptr_t page, uintptr_t native_flush,
                    const unsigned char original[7],unsigned int kind,
                    volatile LONG64 *counter);
SIZE_T bench_job_code_size(void);
BOOL bench_job_code_ready(uintptr_t image);
#endif
