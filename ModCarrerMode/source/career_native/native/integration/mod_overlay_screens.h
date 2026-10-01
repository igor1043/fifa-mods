#ifndef FIFA16_MOD_OVERLAY_SCREENS_H
#define FIFA16_MOD_OVERLAY_SCREENS_H
#include <windows.h>

#define MOD_SCREEN_NAME_CAPACITY 96
#define MOD_SCREEN_RELEASE_DELAY_MS 250

typedef void (*ModScreenCallback)(void *context);
typedef struct ModOverlayScreen {
    const char *id;
    const char *action;
    ModScreenCallback on_open;
    ModScreenCallback draw;
    ModScreenCallback on_close;
    void *context;
} ModOverlayScreen;

#ifdef __cplusplus
extern "C" {
#endif
/* Register persistent callbacks/data once before exposing the corresponding
 * NAV event. Names are copied; context and callback code must outlive the DLL.
 * One modal screen at a time; opening a different active screen is rejected. */
BOOL mod_screen_register(const ModOverlayScreen *screen);
BOOL mod_screen_open(const char *id);
BOOL mod_screen_has_action(const char *action);
BOOL mod_screen_open_action(const char *action);
BOOL mod_screen_close(void);
BOOL mod_screen_is_active(const char *id);
BOOL mod_screen_is_open(void);
BOOL mod_screen_captures_input(void);
/* Only the shared Present host calls these, on its render thread. Lifecycle
 * callbacks do not require an ImGui frame. draw runs inside an existing frame. */
void mod_screen_sync_lifecycle(void);
void mod_screen_draw(void);
#ifdef __cplusplus
}
#endif
#endif
