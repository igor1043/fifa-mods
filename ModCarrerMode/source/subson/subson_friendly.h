#ifndef SUBSON_FRIENDLY_H
#define SUBSON_FRIENDLY_H
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stddef.h>

#define SUBSON_PATCH_MAX_BYTES 7U
unsigned char *subson_near_page(uintptr_t image, SIZE_T size, uintptr_t site);
BOOL subson_write_bytes(uintptr_t site, const unsigned char *before,
                        const unsigned char *after, SIZE_T size);
BOOL subson_friendly_start(unsigned bench, const char *log_path);
BOOL subson_career_start(unsigned bench, const char *log_path);
BOOL subson_career_ensure_now(uintptr_t image, SIZE_T image_size,const char *log_path);
size_t subson_emit_career(unsigned char *page, uintptr_t resume);
size_t subson_emit_import(unsigned char *page, uintptr_t callback, uintptr_t resume);
size_t subson_emit_capacity(unsigned char *page, uintptr_t callback, uintptr_t resume);
void subson_unwind(unsigned char out[24], const RUNTIME_FUNCTION *original);

extern const unsigned char SubsonImportBegin[], SubsonImportEnd[];
extern const unsigned char SubsonImportPolicy[], SubsonImportResume[];
extern const unsigned char SubsonCapacityBegin[], SubsonCapacityEnd[];
extern const unsigned char SubsonCapacityPolicy[], SubsonCapacityResume[];
extern const unsigned char SubsonCareerBegin[], SubsonCareerEnd[], SubsonCareerResume[];
#endif
