#include "mod_overlay_screens.h"
#include <string.h>

struct RegisteredScreen {
    char id[MOD_SCREEN_NAME_CAPACITY];
    char action[MOD_SCREEN_NAME_CAPACITY];
    ModOverlayScreen callbacks;
};
static SRWLOCK g_screen_lock = SRWLOCK_INIT;
static RegisteredScreen g_screens[32];
static LONG g_screen_count;
static volatile LONG g_active_screen;
static LONG g_rendered_screen; /* render thread only */
static volatile LONGLONG g_release_at;

static bool valid_name(const char *name)
{
    if (!name || !*name) return false;
    for (size_t i = 0; i < MOD_SCREEN_NAME_CAPACITY; ++i) {
        unsigned char c = (unsigned char)name[i];
        if (!c) return true;
        if (c < 33 || c > 126) return false;
    }
    return false;
}
static LONG find_screen_locked(const char *name, bool action)
{
    if (!name) return 0;
    for (LONG i = 0; i < g_screen_count; ++i)
        if (!strcmp(name, action ? g_screens[i].action : g_screens[i].id)) return i + 1;
    return 0;
}
extern "C" BOOL mod_screen_register(const ModOverlayScreen *screen)
{
    if (!screen || !valid_name(screen->id) || !valid_name(screen->action) ||
        !screen->draw) return FALSE;
    AcquireSRWLockExclusive(&g_screen_lock);
    BOOL added = FALSE;
    if (g_screen_count < 32 && !find_screen_locked(screen->id, false) &&
        !find_screen_locked(screen->action, true)) {
        RegisteredScreen &entry = g_screens[g_screen_count++];
        strcpy_s(entry.id, sizeof(entry.id), screen->id);
        strcpy_s(entry.action, sizeof(entry.action), screen->action);
        entry.callbacks = *screen;
        entry.callbacks.id = entry.id;
        entry.callbacks.action = entry.action;
        added = TRUE;
    }
    ReleaseSRWLockExclusive(&g_screen_lock);
    return added;
}
static BOOL open_named(const char *name, bool action)
{
    AcquireSRWLockShared(&g_screen_lock);
    LONG target = find_screen_locked(name, action);
    ReleaseSRWLockShared(&g_screen_lock);
    if (!target) return FALSE;
    LONG previous = InterlockedCompareExchange(&g_active_screen, target, 0);
    return previous == 0 || previous == target;
}
extern "C" BOOL mod_screen_open(const char *id) { return open_named(id, false); }
extern "C" BOOL mod_screen_open_action(const char *action) { return open_named(action, true); }
extern "C" BOOL mod_screen_has_action(const char *action)
{
    AcquireSRWLockShared(&g_screen_lock);
    BOOL found = find_screen_locked(action, true) != 0;
    ReleaseSRWLockShared(&g_screen_lock);
    return found;
}
extern "C" BOOL mod_screen_close(void)
{
    /* Set the cooldown before clearing the modal: no uncaptured interval. */
    AcquireSRWLockExclusive(&g_screen_lock);
    BOOL closed = InterlockedCompareExchange(&g_active_screen, 0, 0) != 0;
    if (closed) {
        InterlockedExchange64(&g_release_at,
            (LONGLONG)GetTickCount64() + MOD_SCREEN_RELEASE_DELAY_MS);
        InterlockedExchange(&g_active_screen, 0);
    }
    ReleaseSRWLockExclusive(&g_screen_lock);
    return closed;
}
extern "C" BOOL mod_screen_is_open(void)
{ return InterlockedCompareExchange(&g_active_screen, 0, 0) != 0; }
extern "C" BOOL mod_screen_is_active(const char *id)
{
    AcquireSRWLockShared(&g_screen_lock);
    LONG index = find_screen_locked(id, false);
    ReleaseSRWLockShared(&g_screen_lock);
    return index && index == InterlockedCompareExchange(&g_active_screen, 0, 0);
}
extern "C" BOOL mod_screen_captures_input(void)
{
    return mod_screen_is_open() || (LONGLONG)GetTickCount64() <
        InterlockedCompareExchange64(&g_release_at, 0, 0);
}
static ModOverlayScreen screen_callbacks(LONG index)
{
    ModOverlayScreen result = {};
    AcquireSRWLockShared(&g_screen_lock);
    if (index > 0 && index <= g_screen_count) result = g_screens[index - 1].callbacks;
    ReleaseSRWLockShared(&g_screen_lock);
    return result;
}
extern "C" void mod_screen_sync_lifecycle(void)
{
    LONG desired = InterlockedCompareExchange(&g_active_screen, 0, 0);
    if (desired == g_rendered_screen) return;
    ModOverlayScreen old_screen = screen_callbacks(g_rendered_screen);
    g_rendered_screen = 0;
    if (old_screen.on_close) old_screen.on_close(old_screen.context);
    desired = InterlockedCompareExchange(&g_active_screen, 0, 0);
    ModOverlayScreen new_screen = screen_callbacks(desired);
    g_rendered_screen = desired;
    if (new_screen.on_open) new_screen.on_open(new_screen.context);
}
extern "C" void mod_screen_draw(void)
{
    LONG active = InterlockedCompareExchange(&g_active_screen, 0, 0);
    if (active != g_rendered_screen) return;
    ModOverlayScreen screen = screen_callbacks(active);
    if (screen.draw) screen.draw(screen.context);
}
