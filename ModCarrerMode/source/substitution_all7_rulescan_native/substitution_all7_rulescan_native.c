#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "fifa16_mod_api.h"

/* FIFA 16 match rule observed and confirmed by the paired RAM test. */
#define RULES_VTABLE_RVA ((uintptr_t)0x22D2CF0U)
#define RULES_USED_LOAD_RVA ((uintptr_t)0x4B815D3U)
#define TEAM_RULES_DELTA ((uintptr_t)0x458U)
#define LIMIT_OFFSET ((uintptr_t)0xA78CU)
#define USED_OFFSET ((uintptr_t)0xB03CU)
#define LIMIT_VALUE 7L
#define MAX_PLAUSIBLE_COUNT 64
#define SCAN_CHUNK (1024U * 1024U)
#define MONITOR_INTERVAL_MS 200U
#define SCAN_RETRY_MS 2000ULL
#define SCAN_WHILE_TRACKED_MS 30000ULL

static const unsigned char used_load_signature[8] = {
    0x41, 0x8B, 0xBC, 0x1D, 0x3C, 0xB0, 0x00, 0x00
};

typedef struct RulePair {
    uintptr_t anchor;
    uintptr_t peer;
    int32_t anchor_limit;
    int32_t peer_limit;
    int32_t anchor_used;
    int32_t peer_used;
} RulePair;

static volatile LONG started;
static char log_path[MAX_PATH];
static uintptr_t expected_vtable;

static void write_log(const char *format, ...)
{
    FILE *file = NULL;
    SYSTEMTIME now;
    va_list args;
    if (!log_path[0] || fopen_s(&file, log_path, "ab") != 0 || !file)
        return;
    GetLocalTime(&now);
    fprintf(file, "%04u-%02u-%02u %02u:%02u:%02u ", now.wYear,
        now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond);
    va_start(args, format);
    vfprintf(file, format, args);
    va_end(args);
    fputs("\r\n", file);
    fclose(file);
}

static BOOL read_memory(uintptr_t address, void *out, SIZE_T size)
{
    SIZE_T read = 0;
    return address && out && size &&
        ReadProcessMemory(GetCurrentProcess(), (const void *)address,
            out, size, &read) && read == size;
}

static BOOL writable_private_range(uintptr_t address, SIZE_T size,
    uintptr_t *allocation_out)
{
    MEMORY_BASIC_INFORMATION info;
    DWORD protection;
    uintptr_t start;
    uintptr_t end;

    if (address < 0x10000U || !size ||
        !VirtualQuery((const void *)address, &info, sizeof(info)) ||
        info.State != MEM_COMMIT || info.Type != MEM_PRIVATE ||
        (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
        return FALSE;
    protection = info.Protect & 0xFFU;
    if (protection != PAGE_READWRITE && protection != PAGE_WRITECOPY &&
        protection != PAGE_EXECUTE_READWRITE &&
        protection != PAGE_EXECUTE_WRITECOPY)
        return FALSE;
    start = (uintptr_t)info.BaseAddress;
    if (info.RegionSize > UINTPTR_MAX - start)
        return FALSE;
    end = start + info.RegionSize;
    if (address < start || address >= end || size > end - address)
        return FALSE;
    if (allocation_out)
        *allocation_out = (uintptr_t)info.AllocationBase;
    return TRUE;
}

static BOOL field_in_allocation(uintptr_t address, SIZE_T size,
    uintptr_t expected_allocation)
{
    uintptr_t allocation = 0;
    return writable_private_range(address, size, &allocation) &&
        allocation == expected_allocation;
}

static BOOL read_rule_pair(uintptr_t anchor, uintptr_t peer,
    RulePair *pair_out)
{
    uintptr_t anchor_vtable = 0;
    uintptr_t peer_vtable = 0;
    uintptr_t anchor_allocation = 0;
    uintptr_t peer_allocation = 0;
    RulePair pair;

    if (!pair_out || !expected_vtable || anchor < 0x10000U ||
        peer < 0x10000U || (anchor & 7U) || (peer & 7U) ||
        anchor > UINTPTR_MAX - USED_OFFSET - sizeof(int32_t) ||
        peer > UINTPTR_MAX - USED_OFFSET - sizeof(int32_t) ||
        (anchor > peer ? anchor - peer : peer - anchor) !=
            TEAM_RULES_DELTA ||
        !writable_private_range(anchor, sizeof(uintptr_t),
            &anchor_allocation) ||
        !writable_private_range(peer, sizeof(uintptr_t),
            &peer_allocation) ||
        anchor_allocation != peer_allocation ||
        !field_in_allocation(anchor + LIMIT_OFFSET, sizeof(int32_t),
            anchor_allocation) ||
        !field_in_allocation(anchor + USED_OFFSET, sizeof(int32_t),
            anchor_allocation) ||
        !field_in_allocation(peer + LIMIT_OFFSET, sizeof(int32_t),
            anchor_allocation) ||
        !field_in_allocation(peer + USED_OFFSET, sizeof(int32_t),
            anchor_allocation) ||
        !read_memory(anchor, &anchor_vtable, sizeof(anchor_vtable)) ||
        anchor_vtable != expected_vtable ||
        !read_memory(peer, &peer_vtable, sizeof(peer_vtable)) ||
        (peer_vtable != 0 && peer_vtable != expected_vtable) ||
        !read_memory(anchor + LIMIT_OFFSET, &pair.anchor_limit,
            sizeof(pair.anchor_limit)) ||
        !read_memory(peer + LIMIT_OFFSET, &pair.peer_limit,
            sizeof(pair.peer_limit)) ||
        !read_memory(anchor + USED_OFFSET, &pair.anchor_used,
            sizeof(pair.anchor_used)) ||
        !read_memory(peer + USED_OFFSET, &pair.peer_used,
            sizeof(pair.peer_used)) ||
        pair.anchor_limit < 0 || pair.anchor_limit > MAX_PLAUSIBLE_COUNT ||
        pair.peer_limit < 0 || pair.peer_limit > MAX_PLAUSIBLE_COUNT ||
        pair.anchor_used < 0 || pair.anchor_used > MAX_PLAUSIBLE_COUNT ||
        pair.peer_used < 0 || pair.peer_used > MAX_PLAUSIBLE_COUNT)
        return FALSE;

    pair.anchor = anchor;
    pair.peer = peer;
    *pair_out = pair;
    return TRUE;
}

static BOOL pair_active(const RulePair *pair)
{
    return pair && (pair->anchor_limit != 0 || pair->peer_limit != 0);
}

static BOOL verify_game_layout(void)
{
    const uintptr_t base = (uintptr_t)GetModuleHandleA(NULL);
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    unsigned char signature[sizeof(used_load_signature)];
    uintptr_t entries[3];
    unsigned int i;
    uintptr_t image_end;

    if (!base || !read_memory(base, &dos, sizeof(dos)) ||
        dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0 ||
        (uintptr_t)dos.e_lfanew > 0x1000U ||
        !read_memory(base + (uintptr_t)dos.e_lfanew, &nt, sizeof(nt)) ||
        nt.Signature != IMAGE_NT_SIGNATURE ||
        nt.OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        nt.OptionalHeader.SizeOfImage <= RULES_USED_LOAD_RVA +
            sizeof(used_load_signature) ||
        nt.OptionalHeader.SizeOfImage <= RULES_VTABLE_RVA +
            sizeof(entries) ||
        nt.OptionalHeader.SizeOfImage > UINTPTR_MAX - base)
        return FALSE;
    image_end = base + nt.OptionalHeader.SizeOfImage;
    if (!read_memory(base + RULES_USED_LOAD_RVA, signature,
            sizeof(signature)) ||
        memcmp(signature, used_load_signature, sizeof(signature)) != 0 ||
        !read_memory(base + RULES_VTABLE_RVA, entries,
            sizeof(entries)))
        return FALSE;
    for (i = 0; i < 3U; ++i)
        if (entries[i] < base || entries[i] >= image_end)
            return FALSE;
    expected_vtable = base + RULES_VTABLE_RVA;
    write_log("layout_ok image_base=0x%llX expected_vtable=0x%llX",
        (unsigned long long)base,
        (unsigned long long)expected_vtable);
    return TRUE;
}

static void consider_candidate(uintptr_t anchor, uintptr_t peer,
    RulePair *found, unsigned int *count)
{
    RulePair candidate;
    if (!read_rule_pair(anchor, peer, &candidate) ||
        !pair_active(&candidate))
        return;
    if (*count == 0U) {
        *found = candidate;
        *count = 1U;
    } else if (candidate.anchor != found->anchor ||
            candidate.peer != found->peer) {
        *count = 2U;
    }
}

static unsigned int scan_for_unique_pair(RulePair *found_out)
{
    SYSTEM_INFO system_info;
    unsigned char *buffer;
    MEMORY_BASIC_INFORMATION scratch_info;
    uintptr_t scratch_allocation = 0;
    uintptr_t cursor;
    uintptr_t maximum;
    unsigned int count = 0;
    RulePair found = { 0 };

    if (!found_out || !expected_vtable)
        return 0U;
    buffer = (unsigned char *)VirtualAlloc(NULL, SCAN_CHUNK,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!buffer) {
        write_log("scan_failed scratch_alloc error=%lu",
            (unsigned long)GetLastError());
        return 0U;
    }
    if (VirtualQuery(buffer, &scratch_info, sizeof(scratch_info)))
        scratch_allocation = (uintptr_t)scratch_info.AllocationBase;

    GetSystemInfo(&system_info);
    cursor = (uintptr_t)system_info.lpMinimumApplicationAddress;
    maximum = (uintptr_t)system_info.lpMaximumApplicationAddress;
    while (cursor < maximum && count < 2U) {
        MEMORY_BASIC_INFORMATION info;
        uintptr_t base;
        uintptr_t region_size;
        uintptr_t offset;
        DWORD protection;

        if (!VirtualQuery((const void *)cursor, &info, sizeof(info)))
            break;
        base = (uintptr_t)info.BaseAddress;
        region_size = info.RegionSize;
        if (!region_size || region_size > UINTPTR_MAX - base)
            break;
        protection = info.Protect & 0xFFU;
        if (info.State == MEM_COMMIT && info.Type == MEM_PRIVATE &&
            (uintptr_t)info.AllocationBase != scratch_allocation &&
            !(info.Protect & (PAGE_GUARD | PAGE_NOACCESS)) &&
            (protection == PAGE_READWRITE || protection == PAGE_WRITECOPY ||
             protection == PAGE_EXECUTE_READWRITE ||
             protection == PAGE_EXECUTE_WRITECOPY)) {
            for (offset = 0; offset < region_size && count < 2U;) {
                SIZE_T take = (SIZE_T)(region_size - offset);
                SIZE_T read = 0;
                SIZE_T position;
                if (take > SCAN_CHUNK)
                    take = SCAN_CHUNK;
                if (ReadProcessMemory(GetCurrentProcess(),
                        (const void *)(base + offset), buffer, take, &read) &&
                    read == take) {
                    for (position = 0;
                         position + sizeof(uintptr_t) <= take &&
                            count < 2U;
                         position += sizeof(uintptr_t)) {
                        uintptr_t value = 0;
                        uintptr_t anchor = base + offset + position;
                        memcpy(&value, buffer + position, sizeof(value));
                        if (value != expected_vtable)
                            continue;
                        if (anchor <= UINTPTR_MAX - TEAM_RULES_DELTA)
                            consider_candidate(anchor,
                                anchor + TEAM_RULES_DELTA, &found, &count);
                        if (anchor >= TEAM_RULES_DELTA && count < 2U)
                            consider_candidate(anchor,
                                anchor - TEAM_RULES_DELTA, &found, &count);
                    }
                }
                offset += take;
            }
        }
        cursor = base + region_size;
    }
    VirtualFree(buffer, 0, MEM_RELEASE);
    if (count == 1U)
        *found_out = found;
    return count;
}

static BOOL apply_pair(const RulePair *candidate, const char *reason,
    RulePair *after_out)
{
    RulePair before;
    RulePair after;
    if (!candidate || !read_rule_pair(candidate->anchor, candidate->peer,
            &before) || !pair_active(&before))
        return FALSE;

    InterlockedExchange((volatile LONG *)(before.peer + LIMIT_OFFSET),
        LIMIT_VALUE);
    InterlockedExchange((volatile LONG *)(before.anchor + LIMIT_OFFSET),
        LIMIT_VALUE);
    if (!read_rule_pair(before.anchor, before.peer, &after)) {
        write_log("pair_write_readback_failed reason=%s anchor=0x%llX peer=0x%llX",
            reason, (unsigned long long)before.anchor,
            (unsigned long long)before.peer);
        return FALSE;
    }
    write_log("pair_write reason=%s anchor=0x%llX peer=0x%llX A78C=%ld/%ld->%ld/%ld B03C=%ld/%ld->%ld/%ld",
        reason, (unsigned long long)before.anchor,
        (unsigned long long)before.peer,
        (long)before.anchor_limit, (long)before.peer_limit,
        (long)after.anchor_limit, (long)after.peer_limit,
        (long)before.anchor_used, (long)before.peer_used,
        (long)after.anchor_used, (long)after.peer_used);
    if (after_out)
        *after_out = after;
    return after.anchor_limit == LIMIT_VALUE &&
        after.peer_limit == LIMIT_VALUE;
}

static DWORD WINAPI worker(void *unused)
{
    RulePair tracked = { 0 };
    int32_t highest_anchor_used = 0;
    int32_t highest_peer_used = 0;
    BOOL saw_dormant = FALSE;
    ULONGLONG last_scan_ms = 0;
    int last_scan_status = -1;
    unsigned int attempt;
    (void)unused;

    for (attempt = 0; attempt < 120U; ++attempt) {
        if (verify_game_layout())
            break;
        Sleep(1000U);
    }
    if (attempt == 120U) {
        write_log("not_started incompatible_game_layout");
        return 0;
    }

    for (;;) {
        ULONGLONG now = GetTickCount64();
        RulePair live;
        if (tracked.anchor) {
            if (!read_rule_pair(tracked.anchor, tracked.peer, &live)) {
                write_log("tracked_pair_invalid anchor=0x%llX peer=0x%llX",
                    (unsigned long long)tracked.anchor,
                    (unsigned long long)tracked.peer);
                memset(&tracked, 0, sizeof(tracked));
                highest_anchor_used = highest_peer_used = 0;
                saw_dormant = FALSE;
            } else if (!pair_active(&live)) {
                saw_dormant = TRUE;
            } else {
                BOOL counters_reset = live.anchor_used < highest_anchor_used ||
                    live.peer_used < highest_peer_used;
                BOOL default_limits = live.anchor_used == 0 &&
                    live.peer_used == 0 && live.anchor_limit <= 3 &&
                    live.peer_limit <= 3;
                if (saw_dormant || counters_reset || default_limits) {
                    RulePair after;
                    const char *reason = saw_dormant ? "dormant_to_active" :
                        counters_reset ? "counters_reset" :
                        "new_default_limits";
                    if (apply_pair(&live, reason, &after)) {
                        highest_anchor_used = after.anchor_used;
                        highest_peer_used = after.peer_used;
                        saw_dormant = FALSE;
                    }
                }
                if (live.anchor_used > highest_anchor_used)
                    highest_anchor_used = live.anchor_used;
                if (live.peer_used > highest_peer_used)
                    highest_peer_used = live.peer_used;
            }
        }

        if (!last_scan_ms || now - last_scan_ms >=
                (tracked.anchor ? SCAN_WHILE_TRACKED_MS : SCAN_RETRY_MS)) {
            RulePair found;
            ULONGLONG scan_started = GetTickCount64();
            unsigned int result = scan_for_unique_pair(&found);
            last_scan_ms = GetTickCount64();
            if ((int)result != last_scan_status) {
                write_log("pair_scan result=%u duration_ms=%llu", result,
                    (unsigned long long)(last_scan_ms - scan_started));
                last_scan_status = (int)result;
            }
            if (result == 1U &&
                (found.anchor != tracked.anchor ||
                 found.peer != tracked.peer)) {
                RulePair after;
                tracked = found;
                highest_anchor_used = found.anchor_used;
                highest_peer_used = found.peer_used;
                saw_dormant = FALSE;
                write_log("pair_found anchor=0x%llX peer=0x%llX A78C=%ld/%ld B03C=%ld/%ld",
                    (unsigned long long)found.anchor,
                    (unsigned long long)found.peer,
                    (long)found.anchor_limit, (long)found.peer_limit,
                    (long)found.anchor_used, (long)found.peer_used);
                (void)apply_pair(&found, "unique_vtable_pair", &after);
            }
        }
        Sleep(MONITOR_INTERVAL_MS);
    }
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void)
{
    return FIFA16_MOD_API_VERSION;
}

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    HANDLE thread;
    char logs_dir[MAX_PATH];
    if (!mods_root || !mods_root[0] ||
        InterlockedCompareExchange(&started, 1, 0) != 0)
        return mods_root && mods_root[0];
    _snprintf_s(logs_dir, sizeof(logs_dir), _TRUNCATE,
        "%s\\..\\logs", mods_root);
    CreateDirectoryA(logs_dir, NULL);
    _snprintf_s(log_path, sizeof(log_path), _TRUNCATE,
        "%s\\substitution_all7_rulescan_native.log", logs_dir);
    write_log("plugin_start method=unique_vtable_pair_scan limit=%ld delta=0x%X",
        LIMIT_VALUE, (unsigned int)TEAM_RULES_DELTA);
    thread = CreateThread(NULL, 0, worker, NULL, 0, NULL);
    if (!thread) {
        write_log("thread_start_failed error=%lu",
            (unsigned long)GetLastError());
        InterlockedExchange(&started, 0);
        return FALSE;
    }
    CloseHandle(thread);
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH)
        DisableThreadLibraryCalls(instance);
    return TRUE;
}
