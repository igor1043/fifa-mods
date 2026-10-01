/* Shared host/Ranking adapter regression; no running game or OS window. */
#include "integration/ranking_overlay.cpp"
static XINPUT_STATE raw;
static int failures;
static void check(bool ok,const char *name) { if(!ok) { ++failures;printf("FAIL: %s\n",name); } }
static DWORD WINAPI real_controller(DWORD index,XINPUT_STATE *state)
{ if(index) return ERROR_DEVICE_NOT_CONNECTED;*state=raw;return ERROR_SUCCESS; }
int main(void)
{
    g_original_xinput_get_state=real_controller;
    check(register_builtin_screens(),"ranking adapter registers on the shared screen host");
    overlay_open("test");mod_screen_sync_lifecycle();
    g_modal_input_session=true;
    check(mod_screen_is_active("ranking") && ranking_overlay_captures_input(),
        "native/shortcut opens use the common modal input owner");
    raw.Gamepad.sThumbLY=20000;
    raw.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_UP;
    handle_ranking_gamepad(20);
    check(g_analog_scroll_axis>0 && g_discrete_scroll_rows==-1,
        "real controller feed scrolls only the ranking adapter");
    overlay_close("test",XINPUT_GAMEPAD_B);mod_screen_sync_lifecycle();finish_modal_input_session();
    check(!mod_screen_is_open() && ranking_overlay_captures_input() &&
        !g_analog_scroll_axis && !g_discrete_scroll_rows,
        "close clears local navigation and keeps the shared release delay");
    Sleep(MOD_SCREEN_RELEASE_DELAY_MS+20);
    check(!ranking_overlay_captures_input(),"capture restores automatically after closing");
    raw.Gamepad.wButtons=XINPUT_GAMEPAD_LEFT_SHOULDER |
        XINPUT_GAMEPAD_RIGHT_SHOULDER | XINPUT_GAMEPAD_BACK;
    poll_gamepad_shortcut();mod_screen_sync_lifecycle();
    check(mod_screen_is_active("ranking"),"raw shortcut still opens ranking without relying on FIFA input reads");
    overlay_close("test",0);mod_screen_sync_lifecycle();
    raw.Gamepad.wButtons=0;poll_gamepad_shortcut();
    printf("Ranking shared-host adapter: %s (%d failures)\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}
