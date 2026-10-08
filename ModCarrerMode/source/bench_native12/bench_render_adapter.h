#ifndef BENCH_RENDER_ADAPTER_H
#define BENCH_RENDER_ADAPTER_H
#include <windows.h>
#include <stdint.h>
#define BENCH_RENDER_LOAD_CALL 0x43600A3U
#define BENCH_RENDER_LOAD_NATIVE 0x437D290U
#define BENCH_RENDER_SHOW_NATIVE 0x437E8D0U
#define BENCH_RENDER_HIDE_NATIVE 0x437B630U
#define BENCH_RENDER_SHOW_SLOT 0x2207288U
#define BENCH_RENDER_TABLE 0x34FBF70U
#define BENCH_RENDER_IDENTITIES 0x34FBDA0U
#define BENCH_RENDER_ACTIVITY_CALL 0x4359830U
#define BENCH_RENDER_ACTIVITY_NATIVE 0x437CDE0U
BOOL bench_render_code_ready(uintptr_t image);
BOOL bench_render_install(uintptr_t image,SIZE_T size);
BOOL bench_render_remove(void);
void bench_render_reset_if_unloaded(void);
void bench_render_counters(LONG64 *loads,LONG64 *blocked_shows,LONG64 *released);
#ifdef BENCH_RENDER_TEST
typedef unsigned char (__fastcall *BenchRenderLoadFn)(void *,const void *);
typedef void (__fastcall *BenchRenderVisibilityFn)(void *);
typedef unsigned char (__fastcall *BenchRenderLoadBridgeFn)(void *,const void *,unsigned char);
void bench_render_test_functions(BenchRenderLoadFn load,BenchRenderVisibilityFn show,
                                 BenchRenderVisibilityFn hide);
void *bench_render_test_load_page(void);
void *bench_render_test_activity_page(void);
#endif
#endif
