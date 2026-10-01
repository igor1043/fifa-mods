/* Real export detours + cached function-pointer paths in executable fixtures.
 * No Microsoft DLL bytes, running FIFA memory or desktop input are modified. */
#include <windows.h>
#include <stdio.h>
static ULONGLONG now_ms=1000;
static ULONGLONG test_clock(void) { return now_ms; }
#define GetTickCount64 test_clock
#include "integration/mod_overlay_screens.cpp"
#undef GetTickCount64
#include "integration/mod_xinput_gate.cpp"
static XINPUT_STATE source[4];
static StateFn delegated_state;
static int failures;
static void check(bool ok,const char *name) { if(!ok) { ++failures;printf("FAIL: %s\n",name); } }
static void draw(void *) {}
static DWORD WINAPI real_state(DWORD index,XINPUT_STATE *state)
{
    if(index>=4) return ERROR_DEVICE_NOT_CONNECTED;
    if(!state) return ERROR_BAD_ARGUMENTS;
    *state=source[index];return ERROR_SUCCESS;
}
static DWORD WINAPI delegating_state(DWORD index,XINPUT_STATE *state)
{ return delegated_state(index,state); }
static unsigned char *fixture(XInputEntry &entry,int version)
{
    unsigned char *code=(unsigned char *)VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
    if(!code) return NULL;
    memcpy(code,entry.signature,13);
    jump_to(code+13,(void *)real_state);
    /* call instead of jmp, then restore the exact tested entry's stack. */
    code[23]=0xFF;code[24]=0xD0;
    const unsigned char restore91[]={0x48,0x8B,0x5C,0x24,0x30,0x48,0x83,0xC4,0x20,0x5F,0xC3};
    const unsigned char restore14[]={0x48,0x8B,0x5C,0x24,0x50,0x48,0x83,0xC4,0x30,0x41,0x5E,0x5F,0x5E,0xC3};
    memcpy(code+25,version==0?restore91:restore14,version==0?sizeof(restore91):sizeof(restore14));
    FlushInstructionCache(GetCurrentProcess(),code,64);
    return code;
}
static HMODULE import_fixture(const char *dll,StateFn cached)
{
    unsigned char *base=(unsigned char *)VirtualAlloc(NULL,8192,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER *)base;dos->e_magic=IMAGE_DOS_SIGNATURE;dos->e_lfanew=128;
    IMAGE_NT_HEADERS64 *nt=(IMAGE_NT_HEADERS64 *)(base+128);nt->Signature=IMAGE_NT_SIGNATURE;
    nt->OptionalHeader.Magic=IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress=0x400;
    IMAGE_IMPORT_DESCRIPTOR *imp=(IMAGE_IMPORT_DESCRIPTOR *)(base+0x400);
    imp->Name=0x600;imp->FirstThunk=0x800;imp->OriginalFirstThunk=0x900;
    strcpy_s((char *)(base+0x600),64,dll);
    ((IMAGE_THUNK_DATA64 *)(base+0x800))->u1.Function=(uintptr_t)cached;
    ((IMAGE_THUNK_DATA64 *)(base+0x900))->u1.AddressOfData=0xA00;
    strcpy_s((char *)(base+0xA02),64,"XInputGetState");
    return (HMODULE)base;
}
int main(void)
{
    const ModOverlayScreen screen={"ranking","FifaModsOpenRanking",NULL,draw,NULL,NULL};
    check(mod_screen_register(&screen)!=FALSE,"modal registered");
    for(DWORD i=0;i<4;++i) {
        source[i].dwPacketNumber=i+10; source[i].Gamepad.wButtons=XINPUT_GAMEPAD_A|XINPUT_GAMEPAD_DPAD_UP;
        source[i].Gamepad.sThumbLX=12000;source[i].Gamepad.sThumbLY=-15000;
        source[i].Gamepad.sThumbRX=-16000;source[i].Gamepad.sThumbRY=20000;
        source[i].Gamepad.bLeftTrigger=120;source[i].Gamepad.bRightTrigger=210;
    }
    unsigned char *code[2];StateFn cached[2];
    for(int v=0;v<2;++v) {
        code[v]=fixture(g_entries[v],v);if(!code[v])return 2;
        cached[v]=(StateFn)code[v];
        XINPUT_STATE out={};
        check(cached[v](0,&out)==ERROR_SUCCESS && !memcmp(&out,&source[0],sizeof(out)),"fixture ABI preserves all controller fields");
        unsigned char original=code[v][0];code[v][0]=0x90;
        check(!install_export(g_entries[v],code[v]) && code[v][0]==0x90,"unknown prologue is untouched");
        code[v][0]=original;
        check(install_export(g_entries[v],code[v]) && install_export(g_entries[v],code[v]),"export detour installs once for both versions");
        check(cached[v](0,&out)==ERROR_SUCCESS && !memcmp(&out,&source[0],sizeof(out)),"closed modal preserves cached-pointer return state");
    }
    mod_screen_open("ranking");
    XINPUT_GAMEPAD neutral={};
    XINPUT_STATE out={};
    for(int v=0;v<2;++v) for(DWORD i=0;i<4;++i) {
        check(cached[v](i,&out)==ERROR_SUCCESS && !memcmp(&out.Gamepad,&neutral,sizeof(neutral)),"cached XInput pointers cannot bypass active modal");
        check(g_entries[v].raw(i,&out)==ERROR_SUCCESS && !memcmp(&out,&source[i],sizeof(out)),"raw trampoline preserves overlay controls");
    }
    check(mod_xinput_read_raw(0,&out)==ERROR_SUCCESS && out.Gamepad.sThumbLY==-15000,"shared host still receives real analog input");
    StateFn previous_raw=g_entries[0].raw;
    delegated_state=cached[1];g_entries[0].raw=delegating_state;
    check(mod_xinput_read_raw(0,&out)==ERROR_SUCCESS && out.Gamepad.sThumbLY==-15000,
        "raw feed stays unfiltered when XInput 9.1 delegates to hooked 1.4");
    check(cached[0](0,&out)==ERROR_SUCCESS && !memcmp(&out.Gamepad,&neutral,sizeof(neutral)),
        "nested XInput versions filter native input exactly once");
    g_entries[0].raw=previous_raw;
    for(int v=0;v<2;++v) {
        HMODULE image=import_fixture(g_entries[v].name,cached[v]);
        check(patch_game_imports(image) && !patch_game_imports(image),"both supported XInput IAT variants are idempotently patched");
        StateFn delivered=(StateFn)((IMAGE_THUNK_DATA64 *)((unsigned char *)image+0x800))->u1.Function;
        check(delivered(0,&out)==ERROR_SUCCESS && !memcmp(&out.Gamepad,&neutral,sizeof(neutral)),"IAT and cached-pointer paths share exclusive gate");
        VirtualFree(image,0,MEM_RELEASE);
    }
    source[0].Gamepad.wButtons |= XINPUT_GAMEPAD_B;
    cached[0](0,&out);
    mod_screen_close();now_ms+=MOD_SCREEN_RELEASE_DELAY_MS-1;
    cached[1](0,&out);
    check(!memcmp(&out.Gamepad,&neutral,sizeof(neutral)),"250 ms close cooldown captures all controls");
    ++now_ms;
    cached[0](0,&out);
    check(!memcmp(&out.Gamepad,&neutral,sizeof(neutral)),"held buttons, sticks and triggers stay quarantined after cooldown");
    memset(&source[0].Gamepad,0,sizeof(source[0].Gamepad));cached[1](0,&out);
    source[0].Gamepad.wButtons=XINPUT_GAMEPAD_B;source[0].Gamepad.sThumbLY=12000;
    cached[0](0,&out);
    check(out.Gamepad.wButtons==XINPUT_GAMEPAD_B && out.Gamepad.sThumbLY==12000,"new input works after physical release without closing game");
    check(cached[0](4,&out)==ERROR_DEVICE_NOT_CONNECTED && cached[1](0,NULL)==ERROR_BAD_ARGUMENTS,"original error codes preserved");
    for(int v=0;v<2;++v) VirtualFree(code[v],0,MEM_RELEASE);
    printf("Shared XInput export/cached-pointer gate: %s (%d failures)\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}
