/* Real registry/lifecycle tests with a deterministic clock; no game/UI. */
#include <windows.h>
#include <stdio.h>
static ULONGLONG now_ms = 1000;
static ULONGLONG test_clock(void) { return now_ms; }
#define GetTickCount64 test_clock
#include "../../src/platform/overlay/mod_overlay_screens.cpp"
#undef GetTickCount64
static int failures;
struct Counts { int opens,draws,closes,backs,child; };
static void check(bool ok,const char *name) { if(!ok) { ++failures;printf("FAIL: %s\n",name); } }
static void opened(void *data) { ++((Counts *)data)->opens; }
static void draw(void *data) { ++((Counts *)data)->draws; }
static void closed(void *data) { ++((Counts *)data)->closes; }
static BOOL backed(void *data) {auto*c=(Counts*)data;++c->backs;if(c->child){c->child=0;return TRUE;}return FALSE;}
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
    mod_screen_close();mod_screen_sync_lifecycle();
    Counts nested={};nested.child=1;
    const ModOverlayScreen third={"nested","FifaModsOpenNested",opened,draw,closed,&nested,backed};
    check(mod_screen_register(&third)&&mod_screen_open("nested"),"screen can register its own child-view Back handler");
    mod_screen_sync_lifecycle();
    check(mod_screen_request_back()&&mod_screen_request_back()&&!nested.backs,"input threads only queue, never execute a UI callback");
    mod_screen_sync_lifecycle();
    check(nested.backs==1&&!nested.child&&!nested.closes&&mod_screen_is_open()&&mod_screen_captures_input(),"one Back returns from child without releasing input or closing the modal");
    check(mod_screen_request_back(),"second deliberate Back can close parent");mod_screen_sync_lifecycle();
    check(nested.backs==2&&nested.closes==1&&!mod_screen_is_open()&&mod_screen_captures_input(),"parent close retains the same 250-ms release guard");
    check(!mod_screen_request_back(),"Back while hidden cannot affect another screen");
    check(mod_screen_open("nested"),"nested view can reopen");mod_screen_sync_lifecycle();
    mod_screen_request_back();mod_screen_close();mod_screen_open("nested");mod_screen_sync_lifecycle();
    check(mod_screen_is_open(),"stale Back request from a closed session cannot close a reopened screen");
    mod_screen_close();mod_screen_sync_lifecycle();
    check(!mod_screen_push_action("FifaModsOpenExample"),"push requires a rendered parent");
    mod_screen_open("ranking");mod_screen_sync_lifecycle();
    check(!mod_screen_push_action("missing")&&!mod_screen_push_action("FifaModsOpenRanking"),"push rejects missing/self routes");
    check(mod_screen_push_action("FifaModsOpenExample")&&mod_screen_captures_input(),"nested route retains immediate capture");
    mod_screen_sync_lifecycle();
    check(mod_screen_is_active("example")&&!mod_screen_push_action("FifaModsOpenRanking"),"recursive parent routes rejected");
    check(!mod_screen_open("ranking"),"plain open remains isolated from navigation stack");
    mod_screen_request_back();mod_screen_sync_lifecycle();
    check(mod_screen_is_active("ranking")&&mod_screen_captures_input(),"Back restores original modal without exposing game");
    check(mod_screen_push_action("FifaModsOpenNested"),"route can contain its own child view");nested.child=1;mod_screen_sync_lifecycle();
    mod_screen_request_back();mod_screen_sync_lifecycle();
    check(mod_screen_is_active("nested"),"child Back runs before parent stack pop");
    mod_screen_request_back();mod_screen_sync_lifecycle();check(mod_screen_is_active("ranking"),"second Back restores parent");
    mod_screen_push_action("FifaModsOpenExample");mod_screen_sync_lifecycle();mod_screen_close();mod_screen_sync_lifecycle();
    mod_screen_open("example");mod_screen_sync_lifecycle();mod_screen_request_back();mod_screen_sync_lifecycle();
    check(!mod_screen_is_open(),"explicit close clears history, never resurrects parent later");
    printf("Reusable mod screens: %s (%d failures)\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}
