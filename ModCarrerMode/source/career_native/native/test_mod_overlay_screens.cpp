/* Real registry/lifecycle tests with a deterministic clock; no game/UI. */
#include <windows.h>
#include <stdio.h>
static ULONGLONG now_ms = 1000;
static ULONGLONG test_clock(void) { return now_ms; }
#define GetTickCount64 test_clock
#include "integration/mod_overlay_screens.cpp"
#undef GetTickCount64
static int failures;
struct Counts { int opens,draws,closes; };
static void check(bool ok,const char *name) { if(!ok) { ++failures;printf("FAIL: %s\n",name); } }
static void opened(void *data) { ++((Counts *)data)->opens; }
static void draw(void *data) { ++((Counts *)data)->draws; }
static void closed(void *data) { ++((Counts *)data)->closes; }
int main(void)
{
    Counts a={},b={};
    const ModOverlayScreen first={"ranking","FifaModsOpenRanking",opened,draw,closed,&a};
    const ModOverlayScreen second={"example","FifaModsOpenExample",opened,draw,closed,&b};
    check(mod_screen_register(&first) && mod_screen_register(&second),"two independent screens register");
    check(!mod_screen_register(&first),"duplicate IDs/actions cannot replace working screens");
    ModOverlayScreen duplicate=second; duplicate.id="other";
    check(!mod_screen_register(&duplicate),"duplicate action also rejected with a different ID");
    check(!mod_screen_captures_input() && !mod_screen_open("missing") &&
        !mod_screen_has_action("FifaModsOpenRankingExtra"),"missing/prefix actions do not open or capture");
    check(mod_screen_open_action("FifaModsOpenRanking") && mod_screen_captures_input(),"opening immediately captures input");
    check(!a.opens,"native input thread does not run render callbacks");
    mod_screen_sync_lifecycle(); mod_screen_draw();
    check(a.opens==1 && a.draws==1 && !b.draws,"only active screen receives lifecycle/draw");
    check(mod_screen_open("ranking") && !mod_screen_open("example"),"same open is idempotent, second modal is rejected");
    mod_screen_sync_lifecycle(); mod_screen_draw();
    check(a.opens==1 && a.draws==2,"no duplicate initialization");
    check(mod_screen_close() && !mod_screen_is_open() && mod_screen_captures_input(),"closing preserves the release guard");
    mod_screen_sync_lifecycle(); mod_screen_draw();
    check(a.closes==1 && a.draws==2,"close callback runs once, hidden screen is not drawn");
    check(!mod_screen_close(),"repeated close does not extend cooldown");
    now_ms+=MOD_SCREEN_RELEASE_DELAY_MS-1;
    check(mod_screen_captures_input(),"input stays captured for the complete 250 ms delay");
    ++now_ms;
    check(!mod_screen_captures_input(),"input returns when delay expires");
    check(mod_screen_open("example"),"different screen opens independently after closing");
    mod_screen_sync_lifecycle(); mod_screen_draw();
    check(b.opens==1 && b.draws==1 && a.opens==1,"second screen does not reuse ranking callbacks");
    mod_screen_close();mod_screen_sync_lifecycle();
    check(b.closes==1,"second screen closes normally");
    check(mod_screen_open("ranking"),"ranking can reopen during cooldown without losing capture");
    mod_screen_sync_lifecycle();mod_screen_draw();
    check(a.opens==2 && a.draws==3,"reopen reinitializes selection once");
    printf("Reusable mod screens: %s (%d failures)\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}
