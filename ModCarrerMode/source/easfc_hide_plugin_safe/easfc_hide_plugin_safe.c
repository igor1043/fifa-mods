#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define FIFA16_MOD_API_VERSION 1U
#define EASFC_SIGNATURE_SIZE 0x50U
#define EASFC_PATCH_SIZE 0x11U
#define EASFC_SCAN_ATTEMPTS 120U
#define EASFC_SCAN_INTERVAL_MS 250U

/* This is the original widget signature. The three conditional bytes at
 * offsets 0x1E, 0x26, and 0x2E change from JAE (0x73) to JE (0x74). */
static const unsigned char k_widget_signature[EASFC_SIGNATURE_SIZE] = {
    0x2C, 0x00, 0x00, 0x00, 0xB9, 0x01, 0xAF, 0x0C,
    0xA2, 0x28, 0x74, 0x4F, 0xB9, 0x01, 0xAF, 0x14,
    0xAF, 0x4F, 0xA2, 0x28, 0x74, 0x4F, 0xB9, 0x01,
    0xAF, 0x14, 0xAF, 0x97, 0xA2, 0x28, 0x73, 0x4F,
    0xB9, 0x01, 0xAF, 0x13, 0xA2, 0x28, 0x73, 0x4F,
    0xB9, 0x01, 0xAF, 0x14, 0xA2, 0x28, 0x73, 0x4F,
    0x73, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x04, 0x00, 0x00, 0x00, 0x17, 0xB9, 0x03, 0xAE,
    0x01, 0xAF, 0x07, 0xAF, 0x85, 0xAF, 0x86, 0x49,
    0x12, 0x9D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

static volatile LONG g_started = 0;
static char g_log_path[MAX_PATH];

typedef enum SafeCompareResult {
    SAFE_NO_MATCH = 0,
    SAFE_MATCH = 1,
    SAFE_FAULT = 2
} SafeCompareResult;

typedef enum PatchResult {
    PATCH_NOT_APPLIED = 0,
    PATCH_APPLIED = 1,
    PATCH_FAULT = 2
} PatchResult;

static void write_log(const char *format, ...)
{
    SYSTEMTIME now;
    FILE *log_file;
    va_list arguments;
    char message[768];

    if (!g_log_path[0] || !format)
        return;

    va_start(arguments, format);
    _vsnprintf_s(message, sizeof(message), _TRUNCATE, format, arguments);
    va_end(arguments);

    log_file = fopen(g_log_path, "ab");
    if (!log_file)
        return;

    GetLocalTime(&now);
    fprintf(log_file, "%04u-%02u-%02u %02u:%02u:%02u %s\n",
        (unsigned int)now.wYear, (unsigned int)now.wMonth,
        (unsigned int)now.wDay, (unsigned int)now.wHour,
        (unsigned int)now.wMinute, (unsigned int)now.wSecond, message);
    fclose(log_file);
}

static BOOL is_readable_committed_region(const MEMORY_BASIC_INFORMATION *info)
{
    DWORD protection;

    if (!info || info->State != MEM_COMMIT || !info->RegionSize)
        return FALSE;

    protection = info->Protect & 0xFFU;
    if ((info->Protect & PAGE_GUARD) || protection == PAGE_NOACCESS)
        return FALSE;

    switch (protection) {
    case PAGE_READONLY:
    case PAGE_READWRITE:
    case PAGE_WRITECOPY:
    case PAGE_EXECUTE_READ:
    case PAGE_EXECUTE_READWRITE:
    case PAGE_EXECUTE_WRITECOPY:
        return TRUE;
    default:
        return FALSE;
    }
}

/* A VirtualQuery result is only a snapshot: FIFA can release or change a
 * region while the worker is walking it. The old plugin passed that stale
 * pointer directly to memcmp, which is the access violation seen in the dump.
 */
static SafeCompareResult safe_signature_compare(const unsigned char *candidate)
{
    __try {
        return memcmp(candidate, k_widget_signature, EASFC_SIGNATURE_SIZE) == 0
            ? SAFE_MATCH
            : SAFE_NO_MATCH;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return SAFE_FAULT;
    }
}

static BOOL candidate_has_original_jumps(const unsigned char *candidate)
{
    BOOL is_original = FALSE;

    __try {
        is_original = candidate[0x1EU] == 0x73U
            && candidate[0x26U] == 0x73U
            && candidate[0x2EU] == 0x73U;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return FALSE;
    }

    return is_original;
}

static PatchResult patch_candidate(unsigned char *candidate)
{
    DWORD original_protection = 0;
    DWORD ignored_protection = 0;
    BOOL access_fault = FALSE;
    BOOL patched = FALSE;

    if (!candidate_has_original_jumps(candidate))
        return PATCH_NOT_APPLIED;

    if (!VirtualProtect(candidate + 0x1EU, EASFC_PATCH_SIZE,
            PAGE_EXECUTE_READWRITE, &original_protection))
        return PATCH_NOT_APPLIED;

    __try {
        /* Recheck after acquiring write access in case another game thread
         * replaced the widget between the signature test and this point. */
        if (candidate_has_original_jumps(candidate)) {
            candidate[0x1EU] = 0x74U;
            candidate[0x26U] = 0x74U;
            candidate[0x2EU] = 0x74U;
            FlushInstructionCache(GetCurrentProcess(), candidate,
                EASFC_SIGNATURE_SIZE);
            patched = TRUE;
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        access_fault = TRUE;
    }

    (void)VirtualProtect(candidate + 0x1EU, EASFC_PATCH_SIZE,
        original_protection, &ignored_protection);

    return access_fault ? PATCH_FAULT
        : (patched ? PATCH_APPLIED : PATCH_NOT_APPLIED);
}

static void scan_region(const MEMORY_BASIC_INFORMATION *info,
    SIZE_T *matches_out, SIZE_T *faults_out)
{
    uintptr_t first;
    uintptr_t last;
    uintptr_t candidate_address;

    if (!info || !matches_out || !faults_out
        || info->RegionSize < EASFC_SIGNATURE_SIZE)
        return;

    first = (uintptr_t)info->BaseAddress;
    if (first > UINTPTR_MAX - info->RegionSize)
        return;
    last = first + info->RegionSize - EASFC_SIGNATURE_SIZE;

    for (candidate_address = first; candidate_address <= last;) {
        unsigned char *candidate = (unsigned char *)candidate_address;
        SafeCompareResult comparison = safe_signature_compare(candidate);

        if (comparison == SAFE_FAULT) {
            ++*faults_out;
            return;
        }

        if (comparison == SAFE_MATCH) {
            PatchResult patch_result = patch_candidate(candidate);
            if (patch_result == PATCH_FAULT) {
                ++*faults_out;
                return;
            }
            if (patch_result == PATCH_APPLIED) {
                ++*matches_out;
                if (candidate_address > last - (EASFC_SIGNATURE_SIZE - 1U))
                    return;
                candidate_address += EASFC_SIGNATURE_SIZE - 1U;
            }
        }

        if (candidate_address == last)
            break;
        ++candidate_address;
    }
}

static DWORD WINAPI patch_worker(LPVOID unused)
{
    SYSTEM_INFO system_info;
    unsigned int attempt;

    (void)unused;
    GetSystemInfo(&system_info);

    for (attempt = 1U; attempt <= EASFC_SCAN_ATTEMPTS; ++attempt) {
        uintptr_t cursor = (uintptr_t)system_info.lpMinimumApplicationAddress;
        uintptr_t maximum = (uintptr_t)system_info.lpMaximumApplicationAddress;
        SIZE_T matches = 0;
        SIZE_T faults = 0;

        while (cursor < maximum) {
            MEMORY_BASIC_INFORMATION info;
            SIZE_T queried = VirtualQuery((const void *)cursor, &info,
                sizeof(info));
            uintptr_t base;
            uintptr_t next;

            if (queried != sizeof(info))
                break;

            base = (uintptr_t)info.BaseAddress;
            if (!info.RegionSize || base > UINTPTR_MAX - info.RegionSize)
                break;
            next = base + info.RegionSize;
            if (next <= cursor)
                break;

            if (is_readable_committed_region(&info))
                scan_region(&info, &matches, &faults);

            if (matches) {
                write_log("EASFC banner hidden safely; matches=%zu faults=%zu",
                    matches, faults);
                return 0;
            }

            cursor = next;
        }

        if (faults)
            write_log("scan %u skipped %zu unstable memory region(s)",
                attempt, faults);
        Sleep(EASFC_SCAN_INTERVAL_MS);
    }

    write_log("EASFC widget signature not found after %u scans; no memory was changed",
        EASFC_SCAN_ATTEMPTS);
    return 0;
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void)
{
    return FIFA16_MOD_API_VERSION;
}

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    HANDLE worker;
    char logs_directory[MAX_PATH];

    if (!mods_root || !mods_root[0])
        return FALSE;
    if (InterlockedCompareExchange(&g_started, 1, 0) != 0)
        return TRUE;

    _snprintf_s(logs_directory, sizeof(logs_directory), _TRUNCATE,
        "%s\\..\\logs", mods_root);
    CreateDirectoryA(logs_directory, NULL);
    _snprintf_s(g_log_path, sizeof(g_log_path), _TRUNCATE,
        "%s\\easfc_hide_plugin.log", logs_directory);

    write_log("startup: safe EASFC reconnect-widget patcher");
    worker = CreateThread(NULL, 0, patch_worker, NULL, 0, NULL);
    if (!worker) {
        write_log("failed to start patch worker; error=%lu",
            (unsigned long)GetLastError());
        InterlockedExchange(&g_started, 0);
        return FALSE;
    }

    CloseHandle(worker);
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH)
        DisableThreadLibraryCalls(instance);
    return TRUE;
}
