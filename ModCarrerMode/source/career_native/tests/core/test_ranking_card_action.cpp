#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../src/platform/input/ranking_card_action.h"

typedef bool (__fastcall *NativeActionFn)(void *, void *, void *, const char *);
static int opened, other_opened, forwarded, failures;
static bool native_result;
static void *expected_owner, *expected_context, *expected_result;
static const char *expected_action;
struct NativeResult { bool completed; int serial; };
static NativeResult command_result;

static void check(bool condition, const char *name)
{
    if (!condition) { ++failures; printf("FAIL: %s\n", name); }
}

static bool has_screen(const char *action)
{
    return !strcmp(action, FIFA16_RANKING_CARD_ACTION_NAME) ||
        !strcmp(action, "FifaModsOpenExample");
}
static void open_screen(const char *action)
{
    if (!strcmp(action, FIFA16_RANKING_CARD_ACTION_NAME)) ++opened;
    else if (!strcmp(action, "FifaModsOpenExample")) ++other_opened;
}

static bool __fastcall native_action(void *owner, void *context, void *result,
    const char *action)
{
    ++forwarded;
    check(owner == expected_owner && context == expected_context &&
        result == expected_result && action == expected_action,
        "the native action receives every original argument unchanged");
    ((NativeResult *)result)->completed = native_result;
    ((NativeResult *)result)->serial = forwarded;
    return native_result;
}

int main(void)
{
    const size_t image_size = 0x09525000;
    const uintptr_t action_rva = 0x04C2A820, binding_rva = 0x04C2C010;
    const unsigned char signature[] = {
        0x48,0x89,0x54,0x24,0x10,0x53,0x55,0x41,0x55,0x48,0x83,0xEC,0x70,
        0x4C,0x89,0xCD,0x49,0x89,0xCD,0xB3,0x01,0x4D,0x85,0xC9
    };
    unsigned char *module = (unsigned char *)VirtualAlloc(NULL, image_size,
        MEM_RESERVE, PAGE_NOACCESS);
    if (!module || !VirtualAlloc(module + (action_rva & ~uintptr_t(4095)),
        4096, MEM_COMMIT, PAGE_EXECUTE_READWRITE) ||
        !VirtualAlloc(module + (binding_rva & ~uintptr_t(4095)),
            4096, MEM_COMMIT, PAGE_READWRITE)) return 2;
    unsigned char *entry = module + action_rva;
    unsigned char *binding = module + binding_rva;
    memcpy(entry, signature, sizeof(signature));
    binding[0]=0x48; binding[1]=0x8D; binding[2]=0x05;
    int32_t delta = (int32_t)(int64_t(action_rva) - int64_t(binding_rva) - 7);
    memcpy(binding+3, &delta, sizeof(delta));
    /* The executable fixture calls a real MSVC callback after the same native
     * prologue, then restores its stack. It exercises the installed detour and
     * trampoline rather than substituting a mock for the hook machinery. */
    unsigned char *body=entry+sizeof(signature);
    const void *callback=(const void *)native_action;
    body[0]=0x48;body[1]=0xB8;memcpy(body+2,&callback,sizeof(callback));
    const unsigned char suffix[]={0xFF,0xD0,0x48,0x83,0xC4,0x70,
        0x41,0x5D,0x5D,0x5B,0xC3};
    memcpy(body+10,suffix,sizeof(suffix));
    FlushInstructionCache(GetCurrentProcess(),entry,128);

    check(ranking_card_action_install(module, image_size-1, has_screen,open_screen, NULL)
        == RANKING_CARD_ACTION_UNSUPPORTED, "unsupported image is rejected");
    entry[0]=0x90;
    check(ranking_card_action_install(module,image_size,has_screen,open_screen,NULL)
        == RANKING_CARD_ACTION_PENDING && entry[0]==0x90,
        "unexpected entry bytes are left untouched");
    entry[0]=signature[0];
    delta+=16;memcpy(binding+3,&delta,sizeof(delta));
    check(ranking_card_action_install(module,image_size,has_screen,open_screen,NULL)
        == RANKING_CARD_ACTION_PENDING && entry[0]==signature[0],
        "a binding to another callback is rejected");
    delta-=16;memcpy(binding+3,&delta,sizeof(delta));
    check(ranking_card_action_install(module,image_size,has_screen,open_screen,NULL)
        == RANKING_CARD_ACTION_READY, "native command detour installs");
    check(ranking_card_action_install(module,image_size,has_screen,open_screen,NULL)
        == RANKING_CARD_ACTION_READY, "repeated installation is harmless");

    expected_owner=(void *)uintptr_t(0x1111222233334444);
    expected_context=(void *)uintptr_t(0x5555666677778888);
    expected_result=&command_result;
    NativeActionFn action=(NativeActionFn)entry;
    expected_action=NULL;native_result=true;
    check(action(expected_owner,expected_context,expected_result,
        "FifaModsOpenRanking") && opened==1 && forwarded==1 &&
        command_result.completed && command_result.serial==1,
        "ranking completes the native no-op callback before opening");
    const char *ordinary[]={"EnterSquadRanking","EnterSquadReport","BrowseJobs",
        "FifaModsOpenRankingExtra","",NULL};
    for(size_t i=0;i<sizeof(ordinary)/sizeof(ordinary[0]);++i) {
        expected_action=ordinary[i];native_result=(i&1)!=0;
        check(action(expected_owner,expected_context,expected_result,
            expected_action)==native_result,
            "native return values survive the trampoline");
    }
    check(opened==1 && forwarded==7,
        "notes and other native actions never open the ranking");
    expected_action=NULL;native_result=true;
    check(action(expected_owner,expected_context,expected_result,
        "FifaModsOpenRanking") && opened==2 && forwarded==8,
        "the card can open the ranking again");
    native_result=false;
    check(!action(expected_owner,expected_context,expected_result,
        "FifaModsOpenRanking") && opened==2 && forwarded==9 &&
        !command_result.completed,
        "a rejected native completion is preserved without opening");
    native_result=true;
    check(action(expected_owner,expected_context,expected_result,
        "FifaModsOpenExample") && other_opened==1 && opened==2,
        "a second registered action shares the same native hook without opening ranking");
    printf("Ranking card native hook: %s (%d failures)\n",
        failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
