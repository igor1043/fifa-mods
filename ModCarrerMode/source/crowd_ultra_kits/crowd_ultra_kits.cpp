#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <initializer_list>
#include <limits.h>
#include <stdlib.h>
#include "crowd_policy.h"
#include <vector>
#include <unordered_map>
#include <string>
#include "country_policy.h"
#include "scene_policy.h"

static HMODULE ownModule;
static uintptr_t image;
static volatile LONG started, drawReports;
static char logPath[MAX_PATH];
static SRWLOCK logLock = SRWLOCK_INIT;
static UltraConfig config;
static const char* payload;
static size_t payloadSize;

static void log_event(const char* format, ...) {
    AcquireSRWLockExclusive(&logLock);
    FILE* file = nullptr;
    if (logPath[0] && !fopen_s(&file, logPath, "ab")) {
        fprintf(file, "%lu thread=%lu ", GetTickCount(), GetCurrentThreadId());
        va_list args; va_start(args, format); vfprintf(file, format, args); va_end(args);
        fputs("\r\n", file); fclose(file);
    }
    ReleaseSRWLockExclusive(&logLock);
}

static bool accessible(uintptr_t address, size_t size, bool writing = false) {
    if (address < 0x10000 || !size || address + size < address) return false;
    const uintptr_t end = address + size;
    while (address < end) {
        MEMORY_BASIC_INFORMATION info{};
        if (!VirtualQuery((void*)address, &info, sizeof(info)) || info.State != MEM_COMMIT ||
            (info.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
        if (writing && !(info.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))) return false;
        const uintptr_t next = (uintptr_t)info.BaseAddress + info.RegionSize;
        if (next <= address) return false;
        address = next;
    }
    return true;
}

template<class T> static bool read(uintptr_t address, T& value) {
    if (!accessible(address, sizeof(value))) return false;
    __try { memcpy(&value, (const void*)address, sizeof(value)); return true; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}

#include "live_country_db.h"

static bool same_native(uintptr_t address, uintptr_t expected) {
    uintptr_t value = 0; return read(address, value) && value == expected;
}
static bool scene_fixture(void* renderer, UltraSceneTeams& teams) {
    teams = {};
    // The frontend preview and match have different crowd objects. Match the
    // renderer, not whichever Lua row or game registry happens to exist first.
    for (int i = 0; i < 2; ++i) {
        uintptr_t object = 0, state = 0, wrapper = 0, actual = 0;
        int index = -1; int32_t fields[32]{};
        if (!read(image + 0x3504748 + i * 8, object) || !same_native(object, image + 0x220c3a0) ||
            !read(object + 0x10, state) || !read(state + 0x84, index) || index != i ||
            !read(state + 0x90, wrapper) || !read(wrapper, actual) || actual != (uintptr_t)renderer ||
            !read(state + 4, fields) || !ultra_scene_teams(fields, teams) || teams.index != i) continue;
        return true;
    }
    teams = {}; return false;
}

static void brazil_sides(void* renderer, bool (&sides)[2]) {
    UltraSceneTeams teams;
    sides[0] = sides[1] = false;
    if (scene_fixture(renderer, teams)) {
        sides[0] = live_brazil_club(teams.home);
        sides[1] = live_brazil_club(teams.away);
    }
}

using RunLua = void (__fastcall*)(const char*, size_t, const char*);
using BindLua = void (__fastcall*)(const char*, const char*, void*);
using BuildInstances = void (__fastcall*)(void*);
using DrawInstances = void (__fastcall*)(void*, void*, void*, unsigned, unsigned, int);
using DrawBatch = void (__fastcall*)(void*, int, void*, void*, void*, uintptr_t);
using ResolveAsset = void* (__fastcall*)(void*, const char*);
using BindTexture = void (__fastcall*)(void*, const char*, const char*, void*);

static void publish_country_scope() {
    const std::string scope = live_country_lua();
    ((RunLua)(image + 0x4ac35e0))(scope.data(), scope.size(), "crowd_country_scope");
}

static void __fastcall crowd_bind_hook(const char* name, const char* format, void* object) {
    // Refresh membership from the live DB at scene creation; publish the same
    // result to Lua before registering/resolving crowd resources.
    refresh_live_countries();
    publish_country_scope();
    // Same thread and lock discipline as the engine's Crowd3dAssetBind call.
    ((RunLua)(image + 0x4ac35e0))(payload, payloadSize, "crowd_ultra_kits_v5");
    ((BindLua)(image + 0x4ac3460))(name, format, object);
    log_event("crowd_asset_bind registered primary=0 secondary=1 third=3 goalkeeper=2 fallback=0");
}

static void prepare_scene(void* object, void* input) {
    uintptr_t state = 0; int index = -1; int32_t fields[32]{};
    UltraSceneTeams teams;
    if (!same_native((uintptr_t)object, image + 0x220c3a0) ||
        !read((uintptr_t)object + 0x10, state) || !read(state + 0x84, index) ||
        !read((uintptr_t)input, fields) || !ultra_scene_teams(fields, teams) || teams.index != index) return;
    refresh_live_countries(true);
    publish_country_scope();
    // The host may load after the two crowd constructors. This event still
    // precedes the resource jobs and instance allocation for the new fixture.
    ((RunLua)(image + 0x4ac35e0))(payload, payloadSize, "crowd_ultra_kits_v5");
    ((BindLua)(image + 0x4ac3460))("FIFA16UltraExtraAssetBind", "%p", object);
    log_event("country_scope source=crowd_scene index=%d home=%d home_brazil=%u away=%d away_brazil=%u lua_prepare_called=1",
              teams.index, teams.home, live_brazil_club(teams.home) ? 1U : 0U,
              teams.away, live_brazil_club(teams.away) ? 1U : 0U);
}

static void __fastcall scene_prepare_hook(void* object, void* input) {
    __try { prepare_scene(object, input); }
    __except (EXCEPTION_EXECUTE_HANDLER) { log_event("scene_prepare_fault native_update_continues"); }
    ((void (__fastcall*)(void*, void*))(image + 0x4398560))(object, input);
}

static void remap_instances(void* object) {
    const uintptr_t renderer = (uintptr_t)object;
    uint32_t count = 0; uintptr_t records = 0;
    if (!read(renderer + 0x1438, count) || !read(renderer + 0x1458, records) ||
        !count || count > 300000 || !accessible(records, (size_t)count * 23, true)) return;
    bool allowed[2]{}; brazil_sides(object, allowed);
    UltraSceneTeams teams; const bool fixture = scene_fixture(object, teams);
    if (!allowed[0] && !allowed[1]) {
        log_event("instances_original scope=brazil_only renderer=%p fixture=%u index=%d home=%d away=%d", object, fixture ? 1U : 0U, teams.index, teams.home, teams.away);
        return;
    }
    unsigned empty = 0, changed = 0, normalBefore = 0, ultraBefore = 0, groups[4]{};
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t before;
        memcpy(&before, (void*)(records + (size_t)i * 23 + 12), 4);
        if (((before >> 22) & 3U) == 2U) { ++empty; continue; }
        if (before & 0x80000U) ++ultraBefore; else ++normalBefore;
        const uint32_t after = ultra_scoped_flags(before, i, config, allowed[0], allowed[1]);
        if (before != after) { memcpy((void*)(records + (size_t)i * 23 + 12), &after, 4); ++changed; }
        if (after & 0x80000U) ++groups[(after >> 20) & 3U];
    }
    log_event("instances_remapped renderer=%p total=%u empty_preserved=%u normal_before=%u ultra_before=%u changed=%u home_primary=%u away_primary=%u home_secondary=%u away_secondary=%u", object, count, empty, normalBefore, ultraBefore, changed, groups[0], groups[1], groups[2], groups[3]);
}

static void __fastcall build_instances_hook(void* object) {
    __try { remap_instances(object); }
    __except (EXCEPTION_EXECUTE_HANDLER) { log_event("remap_fault native_build_continues"); }
    // Called BEFORE native per-prototype instance buffer sizing, never after it.
    ((BuildInstances)(image + 0x5cb9560))(object);
}

struct JerseyContext {
    bool active;
    uintptr_t meshes, textures;
    void* third[2];
    void* goalkeeper[2];
    bool allowed[2];
};
static thread_local JerseyContext jerseyContext{};

static void* resolve_third_texture(void* renderer, const char* name) {
    uintptr_t descriptor = 0;
    if (!read((uintptr_t)renderer + 0x1258, descriptor) || !descriptor) return nullptr;
    void* resource = ((ResolveAsset)(image + 0x4adca00))((void*)descriptor, name);
    uintptr_t vtable = 0, getter = 0;
    if (!resource || !read((uintptr_t)resource, vtable) || !read(vtable + 0x70, getter) ||
        getter < image + 0x1000 || getter >= image + 0x9500000) return nullptr;
    return ((void* (__fastcall*)(void*, const char*))getter)(resource, "jersey_cm");
}

static void __fastcall jersey_batch_hook(void* renderer, int group, void* meshes, void* textures, void* effect, uintptr_t opaque) {
    const JerseyContext previous = jerseyContext;
    jerseyContext = {true, (uintptr_t)meshes, (uintptr_t)textures, {nullptr, nullptr}, {nullptr, nullptr}, {false, false}};
    brazil_sides(renderer, jerseyContext.allowed);
    __try {
        jerseyContext.third[0] = resolve_third_texture(renderer, "ultra_kit3_home");
        jerseyContext.third[1] = resolve_third_texture(renderer, "ultra_kit3_away");
        jerseyContext.goalkeeper[0] = resolve_third_texture(renderer, "ultra_gk_home");
        jerseyContext.goalkeeper[1] = resolve_third_texture(renderer, "ultra_gk_away");
    } __except (EXCEPTION_EXECUTE_HANDLER) { jerseyContext.third[0] = jerseyContext.third[1] = nullptr; jerseyContext.goalkeeper[0] = jerseyContext.goalkeeper[1] = nullptr; }
    ((DrawBatch)(image + 0x5cbc310))(renderer, group, meshes, textures, effect, opaque);
    jerseyContext = previous;
}

static void __fastcall draw_instances_hook(void* mesh, void* buffer, void* effect, unsigned first, unsigned count, int pass) {
    const uintptr_t address = (uintptr_t)mesh;
    if (!jerseyContext.active || address < jerseyContext.meshes ||
        address >= jerseyContext.meshes + 20 * 8 || (address - jerseyContext.meshes) % 8) {
        ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first, count, pass); return;
    }
    const unsigned variant = (unsigned)((address - jerseyContext.meshes) / 8 / 5);
    if (!jerseyContext.allowed[variant & 1U]) {
        ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first, count, pass); return;
    }
    unsigned thirdCount = variant >= 2 ? ultra_third_count(count, config) : 0;
    unsigned goalkeeperCount = variant >= 2 ? ultra_goalkeeper_count(count, config) : 0;
    if (thirdCount > count) thirdCount = count;
    if (goalkeeperCount > count - thirdCount) goalkeeperCount = count - thirdCount;
    void* third = jerseyContext.third[variant & 1U];
    void* goalkeeper = jerseyContext.goalkeeper[variant & 1U];
    uintptr_t original = 0;
    if ((!thirdCount && !goalkeeperCount) || !read(jerseyContext.textures + variant * 40, original) || !original) {
        ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first, count, pass); return;
    }
    const unsigned secondCount = count - thirdCount - goalkeeperCount;
    if (secondCount) ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first, secondCount, pass);
    if (thirdCount) {
        ((BindTexture)(image + 0x4acdd30))(effect, "textures", "diffuseTexture", third ? third : (void*)original);
        ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first + secondCount, thirdCount, pass);
    }
    if (goalkeeperCount) {
        ((BindTexture)(image + 0x4acdd30))(effect, "textures", "diffuseTexture", goalkeeper ? goalkeeper : (void*)original);
        ((DrawInstances)(image + 0x5cc36e0))(mesh, buffer, effect, first + secondCount + thirdCount, goalkeeperCount, pass);
    }
    ((BindTexture)(image + 0x4acdd30))(effect, "textures", "diffuseTexture", (void*)original);
    if (InterlockedIncrement(&drawReports) <= 8) log_event("kit_variation_draw variant=%u instances=%u kit2=%u kit3=%u goalkeeper=%u third_resolved=%u goalkeeper_resolved=%u", variant, count, secondCount, thirdCount, goalkeeperCount, third ? 1U : 0U, goalkeeper ? 1U : 0U);

}

struct CallHook { uintptr_t rva, target; void* replacement; unsigned char expected[18]; size_t length = 5; };
static const CallHook hooks[] = {
    {0x4397c47, 0x4ac3460, (void*)crowd_bind_hook, {0xe8,0x14,0xb8,0x72,0x00,0x48,0x8b,0x6c,0x24,0x48,0x48,0x8b,0x74,0x24,0x50,0x48}},
    {0x5cb9f03, 0x5cb9560, (void*)build_instances_hook, {0xe8,0x58,0xf6,0xff,0xff,0x44,0x8b,0x87,0x38,0x14,0x00,0x00,0x48,0x8b,0x97,0x58}},
    {0x5cbc0a2, 0x5cbc310, (void*)jersey_batch_hook, {0xe8,0x69,0x02,0x00,0x00,0xe8,0x84,0xc9,0xe0,0xfe,0x48,0x8d,0x0d,0xad,0xcf,0x3d}},
    {0x5cbc483, 0x5cc36e0, (void*)draw_instances_hook, {0xe8,0x58,0x72,0x00,0x00,0x44,0x8b,0x6f,0x08,0x4c,0x8b,0x84,0x24,0x80,0x00,0x00}},
    {0x43989c7, 0x4398560, (void*)scene_prepare_hook, {0xe8,0x94,0xfb,0xff,0xff,0xb0,0x01,0x48,0x8b,0x8c,0x24,0x40,0x03,0x00,0x00,0x48}},
    {0x58e2ea4, 0x4461f10, (void*)capture_country_registration, {0xe8,0x67,0xf0,0xb7,0xfe,0x48,0x8b,0x5e,0x08,0x48,0x8d,0x4d,0xd0,0xe8,0xaa,0x36}},
    {0x5b8e430, 0, (void*)capture_team_name, {0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57,0x48,0x81,0xec,0x90,0x00,0x00,0x00}, 18}
};
static constexpr size_t hookCount = sizeof(hooks) / sizeof(hooks[0]);

static bool code_ready() {
    const unsigned char luaGuard[] = {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x30};
    if (!accessible(image + 0x4ac35e0, sizeof(luaGuard)) || memcmp((void*)(image + 0x4ac35e0), luaGuard, sizeof(luaGuard))) return false;
    for (const CallHook& hook : hooks) {
        if (!accessible(image + hook.rva, (hook.length == 18 ? 18U : 16U)) ||
            memcmp((void*)(image + hook.rva), hook.expected, (hook.length == 18 ? 18U : 16U))) return false;
        if (hook.length == 18) continue;
        const int32_t displacement = *(int32_t*)(image + hook.rva + 1);
        if ((intptr_t)(image + hook.rva + 5) + displacement != (intptr_t)(image + hook.target)) return false;
    }
    return true;
}

static void* allocate_near() {
    const uintptr_t origin = (image + 0x5000000) & ~(uintptr_t)0xffff;
    for (uintptr_t delta = 0x10000; delta < 0x60000000; delta += 0x10000) {
        for (int direction : {-1, 1}) {
            const uintptr_t address = direction < 0 ? origin - delta : origin + delta;
            MEMORY_BASIC_INFORMATION info{};
            if (!VirtualQuery((void*)address, &info, sizeof(info)) || info.State != MEM_FREE) continue;
            void* page = VirtualAlloc((void*)address, 4096, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
            if (page) return page;
        }
    }
    return nullptr;
}

static bool install_hooks(unsigned char* relay) {
    HANDLE handles[256]{}; size_t threadCount = 0, protectedCount = 0;
    DWORD protections[hookCount]{}; bool okay = true;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snapshot == INVALID_HANDLE_VALUE) return false;
    THREADENTRY32 entry{}; entry.dwSize = sizeof(entry);
    for (BOOL more = Thread32First(snapshot, &entry); more; more = Thread32Next(snapshot, &entry)) {
        if (entry.th32OwnerProcessID != GetCurrentProcessId() || entry.th32ThreadID == GetCurrentThreadId()) continue;
        if (threadCount == 256) { okay = false; break; }
        HANDLE thread = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, entry.th32ThreadID);
        if (!thread) { okay = false; break; }
        if (SuspendThread(thread) == (DWORD)-1) { CloseHandle(thread); okay = false; break; }
        handles[threadCount++] = thread;
        CONTEXT context{}; context.ContextFlags = CONTEXT_CONTROL;
        if (!GetThreadContext(thread, &context)) { okay = false; break; }
        for (const CallHook& hook : hooks) if (context.Rip >= image + hook.rva && context.Rip < image + hook.rva + hook.length) okay = false;
        if (!okay) break;
    }
    CloseHandle(snapshot);
    if (okay) okay = code_ready();
    if (okay) for (size_t i = 0; i < hookCount; ++i) {
        if (!VirtualProtect((void*)(image + hooks[i].rva), hooks[i].length, PAGE_EXECUTE_READWRITE, &protections[i])) { okay = false; break; }
        ++protectedCount;
    }
    if (okay) for (size_t i = 0; i < hookCount; ++i) {
        if (hooks[i].length == 18) {
            unsigned char patch[18]; memset(patch, 0x90, sizeof(patch));
            patch[0]=0xff; patch[1]=0x25; memset(patch+2,0,4);
            memcpy(patch+6,&hooks[i].replacement,8);
            memcpy((void*)(image+hooks[i].rva),patch,sizeof(patch));
            FlushInstructionCache(GetCurrentProcess(),(void*)(image+hooks[i].rva),sizeof(patch));
            continue;
        }
        unsigned char patch[5] = {0xe8,0,0,0,0};
        const int64_t distance = (int64_t)(uintptr_t)(relay + i * 32) - (int64_t)(image + hooks[i].rva + 5);
        const int32_t relative = (int32_t)distance;
        memcpy(patch + 1, &relative, 4);
        memcpy((void*)(image + hooks[i].rva), patch, 5);
        FlushInstructionCache(GetCurrentProcess(), (void*)(image + hooks[i].rva), 5);
    }
    // Two call sites share a page; reverse restoration preserves its original
    // protection rather than leaving the second site's temporary RWX value.
    for (size_t i = protectedCount; i; --i) { DWORD ignored; VirtualProtect((void*)(image + hooks[i - 1].rva), hooks[i - 1].length, protections[i - 1], &ignored); }
    for (size_t i = threadCount; i; --i) { ResumeThread(handles[i - 1]); CloseHandle(handles[i - 1]); }
    return okay;
}

static DWORD WINAPI worker(void*) {
    unsigned char* relay = nullptr;
    for (unsigned attempt = 0; attempt < 600; ++attempt) {
        if (!code_ready()) { Sleep(100); continue; }
        if (!relay) {
            relay = (unsigned char*)allocate_near();
            if (!relay) { log_event("not_installed relay_allocation_failed"); return 1; }
            for (size_t i = 0; i < hookCount; ++i) {
                unsigned char* jump = relay + i * 32;
                const int64_t distance = (int64_t)(uintptr_t)jump - (int64_t)(image + hooks[i].rva + 5);
                if (distance < INT32_MIN || distance > INT32_MAX) { VirtualFree(relay, 0, MEM_RELEASE); return 2; }
                const unsigned char prefix[] = {0xff,0x25,0,0,0,0};
                memcpy(jump, prefix, sizeof(prefix)); memcpy(jump + 6, &hooks[i].replacement, 8);
            }
            // The team resolver prologue contains no relative instructions.
            unsigned char* trampoline=relay+hookCount*32;
            memcpy(trampoline,(void*)(image+0x5b8e430),18);
            const unsigned char absoluteJump[6]={0xff,0x25,0,0,0,0};
            memcpy(trampoline+18,absoluteJump,6);
            const uintptr_t continuation=image+0x5b8e442;
            memcpy(trampoline+24,&continuation,8);
            originalTeamName=(ResolveTeamName)trampoline;
            DWORD ignored;
            if (!VirtualProtect(relay, 4096, PAGE_EXECUTE_READ, &ignored)) { VirtualFree(relay, 0, MEM_RELEASE); return 3; }
            FlushInstructionCache(GetCurrentProcess(), relay, 4096);
        }
        if (install_hooks(relay)) {
            log_event("installed version=5 scope=country_database_brazil_only scene_team_identity=1 late_lua_bind=1 replace_percent=%u kit1=%u kit2=%u kit3=%u goalkeeper=%u native_ultra_instances=1 seat_state_preserved=1 third_kit_type=3 split_instanced_draw=1", config.replacePercent, config.kit1Percent, config.kit2Percent, config.kit3Percent, config.goalkeeperPercent);
            return 0;
        }
        Sleep(100);
    }
    if (relay) VirtualFree(relay, 0, MEM_RELEASE);
    log_event("not_installed unsupported_or_conflicting_native_code"); return 4;
}

extern "C" __declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion() { return 1; }
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* modsRoot) {
    if (!modsRoot || !modsRoot[0]) return FALSE;
    if (InterlockedCompareExchange(&started, 1, 0)) return TRUE;
    image = (uintptr_t)GetModuleHandleW(nullptr);
    char logs[MAX_PATH], ini[MAX_PATH];
    _snprintf_s(logs, sizeof(logs), _TRUNCATE, "%s\\..\\logs", modsRoot); CreateDirectoryA(logs, nullptr);
    _snprintf_s(logPath, sizeof(logPath), _TRUNCATE, "%s\\crowd_ultra_kits.log", logs);
    _snprintf_s(ini, sizeof(ini), _TRUNCATE, "%s\\crowd_ultra_kits\\crowd_ultra_kits.ini", modsRoot);
    if (!GetPrivateProfileIntA("crowd_ultra_kits", "enabled", 1, ini)) { log_event("disabled_by_ini"); return TRUE; }
    config.replacePercent = GetPrivateProfileIntA("crowd_ultra_kits", "replace_percent", 96, ini);
    config.kit1Percent = GetPrivateProfileIntA("crowd_ultra_kits", "kit1_percent", 88, ini);
    config.kit2Percent = GetPrivateProfileIntA("crowd_ultra_kits", "kit2_percent", 8, ini);
    config.kit3Percent = GetPrivateProfileIntA("crowd_ultra_kits", "kit3_percent", 3, ini);
    config.goalkeeperPercent = GetPrivateProfileIntA("crowd_ultra_kits", "goalkeeper_percent", 1, ini);
    if (config.replacePercent > 100 || config.kit1Percent > 100 || config.kit2Percent > 100 || config.kit3Percent > 100 || config.goalkeeperPercent > 100 ||
        config.kit1Percent + config.kit2Percent + config.kit3Percent + config.goalkeeperPercent != 100) { config = UltraConfig{}; log_event("invalid_ini defaults_restored"); }
    HRSRC resource = FindResourceW(ownModule, MAKEINTRESOURCEW(101), MAKEINTRESOURCEW(10));
    if (!resource) return FALSE;
    payloadSize = SizeofResource(ownModule, resource);
    payload = (const char*)LockResource(LoadResource(ownModule, resource));
    if (!payload || !payloadSize) return FALSE;
    HMODULE pinned;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, (LPCSTR)&started, &pinned)) return FALSE;
    log_event("plugin_start independent_dll=1");
    HANDLE thread = CreateThread(nullptr, 0, worker, nullptr, 0, nullptr);
    if (!thread) return FALSE;
    CloseHandle(thread); return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) { ownModule = instance; DisableThreadLibraryCalls(instance); }
    return TRUE;
}
