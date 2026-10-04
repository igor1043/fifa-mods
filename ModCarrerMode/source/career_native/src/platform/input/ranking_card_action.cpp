#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>

#include "ranking_card_action.h"
#include "../overlay/mod_overlay_screens.h"

/* Captured from the supported, unpacked FIFA image on 2026-10-01. The NAV
 * binding at 04C2C010 registers this four-argument member callback under
 * executeCMAction. Its fourth argument is the action's null-terminated name.
 * A transition containing only actions leaves the current Hub state active. */
static const size_t k_image_size = 0x09525000;
static const uintptr_t k_callback_rva = 0x04C2A820;
static const uintptr_t k_binding_rva = 0x04C2C010;
static const size_t k_stolen_size = 13;
static const unsigned char k_callback_signature[] = {
    0x48, 0x89, 0x54, 0x24, 0x10,       /* mov [rsp+10h],rdx */
    0x53, 0x55, 0x41, 0x55,             /* push rbx/rbp/r13 */
    0x48, 0x83, 0xEC, 0x70,             /* sub rsp,70h */
    0x4C, 0x89, 0xCD,                   /* mov rbp,r9 */
    0x49, 0x89, 0xCD,                   /* mov r13,rcx */
    0xB3, 0x01,                         /* mov bl,1 */
    0x4D, 0x85, 0xC9                    /* test r9,r9 */
};

typedef bool (__fastcall *ExecuteCmActionFn)(void *owner, void *context,
    void *result, const char *action_name);

static ExecuteCmActionFn g_original_action;
static RankingCardMatchFn g_has_action;
static RankingCardOpenFn g_open_screen;
static RankingCardLogFn g_log_message;
static volatile LONG g_installed;
static volatile LONG g_install_lock;

static bool read_bytes(const void *source, void *destination, size_t count)
{
    SIZE_T bytes_read = 0;
    return source && ReadProcessMemory(GetCurrentProcess(), source,
        destination, count, &bytes_read) && bytes_read == count;
}

static bool registered_action(const char *action_name, char *name)
{
    if (!action_name || !g_has_action) return false;
    for (size_t i = 0; i < MOD_SCREEN_NAME_CAPACITY; ++i) {
        if (!read_bytes(action_name + i, name + i, 1)) return false;
        if (!name[i]) return g_has_action(name);
    }
    return false;
}

static bool __fastcall execute_cm_action_hook(void *owner, void *context,
    void *result, const char *action_name)
{
    char registered_name[MOD_SCREEN_NAME_CAPACITY];
    if (registered_action(action_name, registered_name)) {
        /* Do not bypass the NAV callback's own completion/output handling.
         * Its verified prologue explicitly accepts NULL as a no-op action.
         * Keep that native path, without looking up our private marker as a
         * game action or executing any unrelated Career command. */
        bool completed = g_original_action(owner, context, result, NULL);
        if (g_log_message) g_log_message(completed
            ? "native mod-screen action completed through original no-op callback"
            : "native mod-screen action rejected by original no-op callback");
        if (completed) g_open_screen(registered_name);
        return completed;
    }
    /* All native actions retain their original arguments and return value. */
    return g_original_action(owner, context, result, action_name);
}

static void write_absolute_jump(unsigned char *code, const void *target)
{
    code[0] = 0x48;
    code[1] = 0xB8;
    memcpy(code + 2, &target, sizeof(target));
    code[10] = 0xFF;
    code[11] = 0xE0;
}

RankingCardActionHookResult ranking_card_action_install(
    unsigned char *module_base, size_t image_size,
    RankingCardMatchFn has_action, RankingCardOpenFn open_screen,
    RankingCardLogFn log_message)
{
    unsigned char current[sizeof(k_callback_signature)];
    unsigned char binding[7];
    unsigned char patch[k_stolen_size];
    unsigned char *entry;
    unsigned char *trampoline;
    int32_t displacement;
    DWORD old_protection, ignored;
    if (!module_base || image_size != k_image_size || !has_action || !open_screen)
        return RANKING_CARD_ACTION_UNSUPPORTED;
    if (InterlockedCompareExchange(&g_installed, 0, 0))
        return RANKING_CARD_ACTION_READY;
    if (InterlockedCompareExchange(&g_install_lock, 1, 0))
        return RANKING_CARD_ACTION_PENDING;

    entry = module_base + k_callback_rva;
    if (!read_bytes(entry, current, sizeof(current)) ||
        memcmp(current, k_callback_signature, sizeof(current)) != 0 ||
        !read_bytes(module_base + k_binding_rva, binding, sizeof(binding)) ||
        binding[0] != 0x48 || binding[1] != 0x8D || binding[2] != 0x05)
    {
        InterlockedExchange(&g_install_lock, 0);
        return RANKING_CARD_ACTION_PENDING;
    }
    memcpy(&displacement, binding + 3, sizeof(displacement));
    if (module_base + k_binding_rva + sizeof(binding) + displacement != entry) {
        InterlockedExchange(&g_install_lock, 0);
        return RANKING_CARD_ACTION_PENDING;
    }

    trampoline = (unsigned char *)VirtualAlloc(NULL, k_stolen_size + 12,
        MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!trampoline) {
        InterlockedExchange(&g_install_lock, 0);
        return RANKING_CARD_ACTION_FAILED;
    }
    /* These 13 bytes contain complete instructions and no relative operands. */
    memcpy(trampoline, current, k_stolen_size);
    write_absolute_jump(trampoline + k_stolen_size, entry + k_stolen_size);
    if (!VirtualProtect(trampoline, k_stolen_size + 12,
        PAGE_EXECUTE_READ, &ignored) ||
        !VirtualProtect(entry, k_stolen_size,
            PAGE_EXECUTE_READWRITE, &old_protection))
    {
        VirtualFree(trampoline, 0, MEM_RELEASE);
        InterlockedExchange(&g_install_lock, 0);
        return RANKING_CARD_ACTION_FAILED;
    }
    g_original_action = (ExecuteCmActionFn)trampoline;
    g_has_action = has_action;
    g_open_screen = open_screen;
    g_log_message = log_message;
    write_absolute_jump(patch, (const void *)execute_cm_action_hook);
    patch[12] = 0x90;
    FlushInstructionCache(GetCurrentProcess(), trampoline, k_stolen_size + 12);
    memcpy(entry, patch, sizeof(patch));
    FlushInstructionCache(GetCurrentProcess(), entry, sizeof(patch));
    if (!VirtualProtect(entry, k_stolen_size, old_protection, &ignored) &&
        g_log_message)
        g_log_message("native ranking command hook installed; page protection restoration failed");
    InterlockedExchange(&g_installed, 1);
    InterlockedExchange(&g_install_lock, 0);
    if (g_log_message)
        g_log_message("native mod-screen command hook installed: executeCMAction + exact registered actions only");
    return RANKING_CARD_ACTION_READY;
}
