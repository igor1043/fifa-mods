#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include "core.h"

#define PATH_CAP 4096
#define GOAL_HOOK_COUNT 5
#define GOAL_PASS_HOOK 10
#define GOAL_PASS_SLOT 0x233ab28u
#define GOAL_PASS_ORIGINAL 0x5309b50u
#define GOAL_PASS_CLONE 0x8200u

static const unsigned goal_hook_indices[GOAL_HOOK_COUNT] = {5, 6, 7, 8, 10};
static const struct { uint32_t slot; uint32_t original; } goal_targets[GOAL_HOOK_COUNT] = {
    {0x33ec880u, 0x517c430u}, /* goal handler */
    {0x22fc908u, 0x4e4d890u}, /* goal constraint */
    {0x2330a60u, 0x51cce30u}, /* goal preparation */
    {0x231c548u, 0x50588d0u}, /* goal movement */
    {GOAL_PASS_SLOT, GOAL_PASS_ORIGINAL}
};
static const char *const required_signatures[] = {
    "goal_handler", "formation_dispatch", "goal_constraint", "goal_prepare",
    "goal_movement", "goal_target_helper", "queue_consume", "kick_ready",
    "ground_solver", "ground_query_speed"
};

static const char expected_hash[] = "889772d3192c74ce4c1f2b7b3467cc96f9f1123aaf347bce7b199333dbac7a9d";
static volatile LONG started;
static volatile LONG stop_requested;
static volatile LONG installed;
static uint64_t image_base;
static unsigned char *allocation;
static Hook hooks[F16_HOOKS];
static unsigned short_pass_percent = 75;
static char log_path[PATH_CAP];
static char ini_path[PATH_CAP];
static HANDLE log_lock;

static int read_at(uint64_t address, void *data, size_t size) {
    SIZE_T got = 0;
    if (address < 0x10000 || address > 0x00007fffffffffffULL - size) return 0;
    return ReadProcessMemory(GetCurrentProcess(), (const void *)(uintptr_t)address, data, size, &got) && got == size;
}

static void log_message(const char *message) {
    FILE *file = NULL;
    if (!message || InterlockedCompareExchange(&stop_requested, 0, 0) == 2) return;
    if (log_lock) WaitForSingleObject(log_lock, INFINITE);
    if (fopen_s(&file, log_path, "ab") == 0 && file) {
        SYSTEMTIME t;
        GetLocalTime(&t);
        fprintf(file, "%04u-%02u-%02u %02u:%02u:%02u %s\r\n",
                t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond, message);
        fclose(file);
    }
    if (log_lock) ReleaseMutex(log_lock);
}

static int make_paths(const char *mods_root) {
    char log_dir[PATH_CAP];
    int n;
    n = _snprintf_s(ini_path, sizeof(ini_path), _TRUNCATE,
                    "%s\\goal_kick_short_pass.ini", mods_root);
    if (n < 0) return 0;
    n = _snprintf_s(log_dir, sizeof(log_dir), _TRUNCATE, "%s\\..\\logs", mods_root);
    if (n < 0) return 0;
    CreateDirectoryA(log_dir, NULL);
    n = _snprintf_s(log_path, sizeof(log_path), _TRUNCATE,
                    "%s\\goal_kick_short_pass.log", log_dir);
    return n >= 0;
}

static int executable_hash(const wchar_t *file, char hex[65]) {
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char digest[32], *object = NULL, *buffer = NULL;
    HANDLE input = INVALID_HANDLE_VALUE;
    DWORD length = 0, got = 0;
    int ok = 0;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0) goto done;
    if (BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&length, sizeof(length), &got, 0) < 0) goto done;
    object = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, length);
    buffer = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, 65536);
    if (!object || !buffer || BCryptCreateHash(alg, &hash, object, length, NULL, 0, 0) < 0) goto done;
    input = CreateFileW(file, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                        NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (input == INVALID_HANDLE_VALUE) goto done;
    for (;;) {
        if (!ReadFile(input, buffer, 65536, &got, NULL)) goto done;
        if (!got) break;
        if (BCryptHashData(hash, buffer, got, 0) < 0) goto done;
    }
    if (BCryptFinishHash(hash, digest, sizeof(digest), 0) < 0) goto done;
    static const char digits[] = "0123456789abcdef";
    for (unsigned i = 0; i < 32; ++i) {
        hex[i * 2] = digits[digest[i] >> 4];
        hex[i * 2 + 1] = digits[digest[i] & 15];
    }
    hex[64] = 0;
    ok = 1;
done:
    if (input != INVALID_HANDLE_VALUE) CloseHandle(input);
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    if (object) HeapFree(GetProcessHeap(), 0, object);
    if (buffer) HeapFree(GetProcessHeap(), 0, buffer);
    return ok;
}

static int image_identity(void) {
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    if (!read_at(image_base, &dos, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew <= 0 || dos.e_lfanew > 0x100000 ||
        !read_at(image_base + (uint32_t)dos.e_lfanew, &nt, sizeof(nt))) return 0;
    return nt.Signature == IMAGE_NT_SIGNATURE &&
           nt.FileHeader.Machine == IMAGE_FILE_MACHINE_AMD64 &&
           nt.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC &&
           (nt.OptionalHeader.SizeOfImage == F16_IMAGE_SIZE || nt.OptionalHeader.SizeOfImage == 0x9524000);
}

static int active_restart(void) {
    int state = -1;
    if (!read_at(image_base + 0x3293d28, &state, sizeof(state))) return 1;
    return state == 2 || state == 6 || state < 0;
}

static int target_ready(char *reason, size_t cap) {
    const Signature *signature = NULL;
    uint64_t target = 0;
    unsigned char *actual = NULL;
    for (size_t n = 0; n < sizeof(required_signatures) / sizeof(required_signatures[0]); ++n) {
        signature = NULL;
        for (size_t i = 0; i < f16_nsignatures; ++i) {
            if (strcmp(f16_signatures[i].name, required_signatures[n]) == 0) {
                signature = &f16_signatures[i];
                break;
            }
        }
        if (!signature) {
            _snprintf_s(reason, cap, _TRUNCATE, "required signature missing: %s", required_signatures[n]);
            return 0;
        }
        actual = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, signature->length);
        if (!actual) {
            _snprintf_s(reason, cap, _TRUNCATE, "signature buffer allocation failed");
            return 0;
        }
        int matches = read_at(image_base + signature->rva, actual, signature->length) &&
                      memcmp(actual, signature->bytes, signature->length) == 0;
        HeapFree(GetProcessHeap(), 0, actual);
        if (!matches) {
            _snprintf_s(reason, cap, _TRUNCATE, "code signature mismatch: %s", required_signatures[n]);
            return 0;
        }
    }
    for (size_t n = 0; n < GOAL_HOOK_COUNT; ++n) {
        if (!read_at(image_base + goal_targets[n].slot, &target, sizeof(target)) ||
            target != image_base + goal_targets[n].original) {
            _snprintf_s(reason, cap, _TRUNCATE, "goal hook slot 0x%08X is already owned", goal_targets[n].slot);
            return 0;
        }
    }
    reason[0] = 0;
    return 1;
}

static uint64_t align_up(uint64_t value, uint64_t size) {
    return (value + size - 1) & ~(size - 1);
}

static unsigned char *allocate_near(void) {
    SYSTEM_INFO si;
    uint64_t lo, hi;
    GetSystemInfo(&si);
    if (si.dwPageSize != 4096 ||
        !f16_bounds(image_base, (uintptr_t)si.lpMinimumApplicationAddress,
                    (uintptr_t)si.lpMaximumApplicationAddress, &lo, &hi)) return NULL;
    uint64_t at = align_up(lo, si.dwAllocationGranularity);
    while (at <= hi) {
        MEMORY_BASIC_INFORMATION region;
        if (!VirtualQuery((void *)(uintptr_t)at, &region, sizeof(region))) return NULL;
        uint64_t end = (uintptr_t)region.BaseAddress + region.RegionSize;
        if (end <= at) return NULL;
        if (region.State == MEM_FREE && end >= F16_SIZE) {
            uint64_t last = end - F16_SIZE;
            if (last > hi) last = hi;
            for (uint64_t p = align_up(at, si.dwAllocationGranularity); p <= last;
                 p += si.dwAllocationGranularity) {
                void *memory = VirtualAlloc((void *)(uintptr_t)p, F16_SIZE,
                                            MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
                if (memory) return (unsigned char *)memory;
                if (GetLastError() != ERROR_INVALID_ADDRESS) return NULL;
            }
        }
        at = align_up(end, si.dwAllocationGranularity);
    }
    return NULL;
}

static int protect_payload_code(void) {
    static const unsigned pages[] = {0x0000,0x2000,0x3000,0x4000,0x5000,0x6000,
                                     0x7000,0x8000,0x9000,0xb000,0xc000};
    for (size_t i = 0; i < sizeof(pages) / sizeof(pages[0]); ++i) {
        DWORD old_protect;
        if (!VirtualProtect(allocation + pages[i], 4096, PAGE_EXECUTE_READ, &old_protect)) return 0;
    }
    return FlushInstructionCache(GetCurrentProcess(), allocation, F16_SIZE) != 0;
}

static int valid_hook_page(uintptr_t address, MEMORY_BASIC_INFORMATION *memory) {
    return address % sizeof(uint64_t) == 0 &&
           VirtualQuery((const void *)address, memory, sizeof(*memory)) &&
           memory->State == MEM_COMMIT && memory->Type == MEM_IMAGE &&
           (memory->Protect & (PAGE_GUARD | PAGE_NOACCESS)) == 0 &&
           (uintptr_t)memory->AllocationBase == image_base;
}

static int install_goal_pass(void) {
    char reason[160] = "preflight";
    MEMORY_BASIC_INFORMATION memory;
    DWORD old_protect[GOAL_HOOK_COUNT] = {0};
    unsigned char protected[GOAL_HOOK_COUNT] = {0};
    unsigned char published[GOAL_HOOK_COUNT] = {0};
    if (!image_identity()) {
        log_message("NOT_APPLIED: FIFA image headers are unsupported");
        return 0;
    }
    if (!target_ready(reason, sizeof(reason))) {
        log_message(reason);
        return 0;
    }
    if (active_restart()) {
        log_message("NOT_APPLIED: launch from the main menu; a restart is already active");
        return 0;
    }
    allocation = allocate_near();
    if (!allocation) {
        log_message("NOT_APPLIED: allocation failed");
        return 0;
    }
    if (!f16_build(allocation, image_base, (uintptr_t)allocation) ||
        !f16_plan(hooks, image_base, (uintptr_t)allocation)) {
        log_message("NOT_APPLIED: payload relocation failed");
        VirtualFree(allocation, 0, MEM_RELEASE);
        allocation = NULL;
        return 0;
    }
    for (size_t n = 0; n < GOAL_HOOK_COUNT; ++n) {
        unsigned index = goal_hook_indices[n];
        if (hooks[index].rva != goal_targets[n].slot || hooks[index].width != sizeof(uint64_t) ||
            hooks[index].original != image_base + goal_targets[n].original ||
            hooks[index].replacement != (uintptr_t)allocation +
                (index == GOAL_PASS_HOOK ? GOAL_PASS_CLONE :
                 (index == 5 ? F16_GOAL : index == 6 ? F16_GOAL + 0x300 :
                  index == 7 ? F16_GOAL + 0x2000 : F16_GOAL + 0x3000))) {
            log_message("NOT_APPLIED: goal-kick hook plan mismatch");
            VirtualFree(allocation, 0, MEM_RELEASE);
            allocation = NULL;
            return 0;
        }
        uintptr_t slot = (uintptr_t)(image_base + hooks[index].rva);
        if (!valid_hook_page(slot, &memory)) {
            log_message("NOT_APPLIED: a goal-kick hook slot is not a verified image page");
            VirtualFree(allocation, 0, MEM_RELEASE);
            allocation = NULL;
            return 0;
        }
    }
    memcpy(allocation + 0x1668, &short_pass_percent, sizeof(short_pass_percent));
    if (!protect_payload_code()) {
        log_message("NOT_APPLIED: payload code protection failed");
        VirtualFree(allocation, 0, MEM_RELEASE);
        allocation = NULL;
        return 0;
    }
    if (active_restart() || !target_ready(reason, sizeof(reason))) {
        log_message(reason[0] ? reason : "NOT_APPLIED: final preflight, restart gate or page protection failed");
        VirtualFree(allocation, 0, MEM_RELEASE);
        allocation = NULL;
        return 0;
    }
    for (size_t n = 0; n < GOAL_HOOK_COUNT; ++n) {
        unsigned index = goal_hook_indices[n];
        uintptr_t slot = (uintptr_t)(image_base + hooks[index].rva);
        if (!valid_hook_page(slot, &memory) ||
            !VirtualProtect((void *)slot, sizeof(uint64_t), PAGE_READWRITE, &old_protect[n])) {
            for (size_t j = n; j > 0; --j) {
                DWORD ignored;
                if (protected[j - 1])
                    VirtualProtect((void *)(uintptr_t)(image_base + hooks[goal_hook_indices[j - 1]].rva),
                                   sizeof(uint64_t), old_protect[j - 1], &ignored);
            }
            log_message("NOT_APPLIED: goal-kick hook page protection failed");
            VirtualFree(allocation, 0, MEM_RELEASE);
            allocation = NULL;
            return 0;
        }
        protected[n] = 1;
    }
    for (size_t n = 0; n < GOAL_HOOK_COUNT; ++n) {
        unsigned index = goal_hook_indices[n];
        uintptr_t slot = (uintptr_t)(image_base + hooks[index].rva);
        uint64_t seen = (uint64_t)InterlockedCompareExchange64((volatile LONG64 *)slot,
                                                              (LONG64)hooks[index].replacement,
                                                              (LONG64)hooks[index].original);
        if (seen != hooks[index].original) {
            int rollback_ok = 1;
            for (size_t j = n; j > 0; --j) {
                unsigned previous = goal_hook_indices[j - 1];
                uintptr_t previous_slot = (uintptr_t)(image_base + hooks[previous].rva);
                if (published[j - 1]) {
                    uint64_t restored = (uint64_t)InterlockedCompareExchange64(
                        (volatile LONG64 *)previous_slot, (LONG64)hooks[previous].original,
                        (LONG64)hooks[previous].replacement);
                    if (restored != hooks[previous].replacement && restored != hooks[previous].original)
                        rollback_ok = 0;
                }
            }
            for (size_t j = GOAL_HOOK_COUNT; j > 0; --j) {
                DWORD ignored;
                if (protected[j - 1])
                    if (!VirtualProtect((void *)(uintptr_t)(image_base + hooks[goal_hook_indices[j - 1]].rva),
                                        sizeof(uint64_t), old_protect[j - 1], &ignored)) rollback_ok = 0;
            }
            log_message("NOT_APPLIED: one goal-kick hook slot changed during installation; published hooks were rolled back");
            if (rollback_ok) {
                VirtualFree(allocation, 0, MEM_RELEASE);
                allocation = NULL;
            } else {
                InterlockedExchange(&installed, 1);
                log_message("WARNING: rollback was incomplete; payload retained to keep any remaining hook valid");
            }
            return 0;
        }
        published[n] = 1;
    }
    int protection_ok = 1;
    for (size_t n = GOAL_HOOK_COUNT; n > 0; --n) {
        DWORD ignored;
        if (protected[n - 1] &&
            !VirtualProtect((void *)(uintptr_t)(image_base + hooks[goal_hook_indices[n - 1]].rva),
                            sizeof(uint64_t), old_protect[n - 1], &ignored)) protection_ok = 0;
    }
    if (!protection_ok) {
        log_message("WARNING: goal-kick hooks are active but a code page protection could not be restored");
    }
    InterlockedExchange((volatile LONG *)(allocation + 0x1000), 1);
    InterlockedExchange((volatile LONG *)(allocation + F16_GOAL + 0x1008), 1);
    InterlockedExchange(&installed, 1);
    char message[220];
    _snprintf_s(message, sizeof(message), _TRUNCATE,
                "APPLIED: goal-kick positioning and short ground-pass speed=%u%%; hooks=4 goal routines+ground solver; kickoff hooks=0",
                short_pass_percent);
    log_message(message);
    return 1;
}

static uint64_t private_u64(const unsigned char *memory, size_t offset) {
    uint64_t value;
    memcpy(&value, memory + offset, sizeof(value));
    return value;
}

static void monitor_goal_pass(void) {
    uint64_t previous_candidates = UINT64_MAX;
    uint64_t previous_adjusted = UINT64_MAX;
    while (!InterlockedCompareExchange(&stop_requested, 0, 0)) {
        unsigned char data[0x1700];
        Sleep(5000);
        if (!read_at((uintptr_t)allocation, data, sizeof(data))) return;
        uint64_t candidates = private_u64(data, 0x1670);
        uint64_t adjusted = private_u64(data, 0x1678);
        if (candidates != previous_candidates || adjusted != previous_adjusted) {
            float old_speed, new_speed, distance;
            memcpy(&old_speed, data + 0x1680, sizeof(old_speed));
            memcpy(&new_speed, data + 0x1684, sizeof(new_speed));
            memcpy(&distance, data + 0x1688, sizeof(distance));
            char message[240];
            _snprintf_s(message, sizeof(message), _TRUNCATE,
                        "GOAL_SHORT_PASS candidates=%llu adjusted=%llu stage=%u receiver=%u speed=%.2f->%.2f distance=%.2f percent=%u",
                        (unsigned long long)candidates, (unsigned long long)adjusted,
                        *(uint32_t *)(data + 0x166c), *(uint32_t *)(data + 0x168c),
                        (double)old_speed, (double)new_speed, (double)distance, short_pass_percent);
            log_message(message);
            previous_candidates = candidates;
            previous_adjusted = adjusted;
        }
    }
}

static DWORD WINAPI install_worker(void *unused) {
    wchar_t exe[PATH_CAP];
    DWORD length;
    char hash[65], reason[160] = "runtime code not ready";
    unsigned stable = 0;
    (void)unused;
    length = GetModuleFileNameW(NULL, exe, PATH_CAP);
    if (!length || length >= PATH_CAP) {
        log_message("NOT_APPLIED: cannot resolve FIFA executable path");
        return 0;
    }
    wchar_t *name = wcsrchr(exe, L'\\');
    if (!name || _wcsicmp(name + 1, L"fifa16.exe") != 0) return 0;
    if (!executable_hash(exe, hash) || strcmp(hash, expected_hash) != 0) {
        log_message("NOT_APPLIED: unsupported FIFA executable SHA-256");
        return 0;
    }
    image_base = (uintptr_t)GetModuleHandleW(NULL);
    if (!image_identity()) {
        log_message("NOT_APPLIED: FIFA image headers differ from supported build");
        return 0;
    }
    log_message("SUPPORTED_EXE: exact FIFA 16 hash matched; waiting for goal-kick routines");
    ULONGLONG started_at = GetTickCount64(), reported_at = started_at;
    while (GetTickCount64() - started_at < 180000 &&
           !InterlockedCompareExchange(&stop_requested, 0, 0)) {
        if (target_ready(reason, sizeof(reason))) ++stable;
        else stable = 0;
        if (stable >= 3) break;
        if (GetTickCount64() - reported_at >= 10000) {
            char message[220];
            _snprintf_s(message, sizeof(message), _TRUNCATE, "WAITING: %s", reason);
            log_message(message);
            reported_at = GetTickCount64();
        }
        Sleep(200);
    }
    if (stable < 3) {
        log_message("NOT_APPLIED: goal-kick routines did not become ready within 180 seconds");
        return 0;
    }
    if (install_goal_pass()) monitor_goal_pass();
    return 0;
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void) { return 1; }

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root) {
    HMODULE pinned = NULL;
    HANDLE thread;
    if (!mods_root || InterlockedCompareExchange(&started, 1, 0)) return FALSE;
    log_lock = CreateMutexA(NULL, FALSE, NULL);
    if (!make_paths(mods_root)) return FALSE;
    unsigned enabled = GetPrivateProfileIntA("General", "Enabled", 1, ini_path);
    short_pass_percent = (unsigned)GetPrivateProfileIntA("GoalKick", "ShortPassSpeedPercent", 75, ini_path);
    if (short_pass_percent < 50 || short_pass_percent > 100) short_pass_percent = 75;
    if (!enabled) {
        log_message("DISABLED: goal-kick positioning and pass adjustment are disabled by configuration");
        return TRUE;
    }
    if (short_pass_percent == 100)
        log_message("CONFIG: short-pass speed adjustment is off; goal-kick positioning remains enabled");
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                            (LPCSTR)&Fifa16ModStart, &pinned)) {
        log_message("NOT_APPLIED: module pin failed");
        return FALSE;
    }
    thread = CreateThread(NULL, 0, install_worker, NULL, 0, NULL);
    if (!thread) {
        log_message("NOT_APPLIED: worker thread creation failed");
        return FALSE;
    }
    CloseHandle(thread);
    log_message("START: goal-kick positioning/pass module; kickoff v20 remains independent");
    return TRUE;
}

__declspec(dllexport) BOOL WINAPI Fifa16ModStop(void) {
    int restored_all = 1;
    if (!InterlockedCompareExchange(&installed, 0, 0)) {
        InterlockedExchange(&stop_requested, 1);
        return TRUE;
    }
    InterlockedExchange(&stop_requested, 1);
    if (allocation) {
        InterlockedExchange((volatile LONG *)(allocation + 0x1000), 0);
        InterlockedExchange((volatile LONG *)(allocation + F16_GOAL + 0x1008), 0);
    }
    for (size_t n = GOAL_HOOK_COUNT; n > 0; --n) {
        unsigned index = goal_hook_indices[n - 1];
        uintptr_t slot = (uintptr_t)(image_base + hooks[index].rva);
        MEMORY_BASIC_INFORMATION memory;
        DWORD old_protect = 0, ignored = 0;
        if (!valid_hook_page(slot, &memory) ||
            !VirtualProtect((void *)slot, sizeof(uint64_t), PAGE_READWRITE, &old_protect)) {
            restored_all = 0;
            continue;
        }
        uint64_t seen = (uint64_t)InterlockedCompareExchange64((volatile LONG64 *)slot,
                                                              (LONG64)hooks[index].original,
                                                              (LONG64)hooks[index].replacement);
        if (seen != hooks[index].replacement && seen != hooks[index].original) restored_all = 0;
        if (!VirtualProtect((void *)slot, sizeof(uint64_t), old_protect, &ignored)) restored_all = 0;
    }
    if (!restored_all) return FALSE;
    InterlockedExchange(&installed, 0);
    log_message("STOPPED: goal-kick hooks restored; private payload retained until process exit");
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(module);
    return TRUE;
}
