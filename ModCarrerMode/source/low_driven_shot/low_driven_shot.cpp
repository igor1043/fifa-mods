#define WIN32_LEAN_AND_MEAN
#include "shot_core.h"
#include <stdio.h>

static SRWLOCK lock=SRWLOCK_INIT;
static ShotState pads[4];
static volatile LONG running;
static char ini[MAX_PATH];
static uint64_t nextRead;
static int enabled=1,height=20,threshold=30,mode=2,finesseTap=300;
static WORD button=XINPUT_GAMEPAD_X;
static int bounded(int n,int lo,int hi){return n<lo?lo:n>hi?hi:n;}
static void reload(uint64_t now) {
    if(now<nextRead)return;nextRead=now+500;
    int prior=enabled;
    enabled=GetPrivateProfileIntA("low_driven_shot","enabled",1,ini)!=0;
    height=bounded(GetPrivateProfileIntA("low_driven_shot","height",20,ini),0,100);
    threshold=bounded(GetPrivateProfileIntA("low_driven_shot","trigger_threshold",30,ini),0,254);
    finesseTap=bounded(GetPrivateProfileIntA("low_driven_shot","finesse_tap_ms",300,ini),60,1000);
    char value[32];GetPrivateProfileStringA("low_driven_shot","shoot_button","X",value,sizeof(value),ini);
    WORD newButton=(value[0]=='B'||value[0]=='b')?XINPUT_GAMEPAD_B:XINPUT_GAMEPAD_X;
    if(prior!=enabled||newButton!=button)memset(pads,0,sizeof(pads));
    button=newButton;
}
static bool live_match() {
    // Read the same verified GameStateInterface used by Server16 match audio.
    __try {
        uintptr_t b=(uintptr_t)GetModuleHandleW(nullptr),p=*(uintptr_t*)(b+0x3517C10);
        if(!p||*(uintptr_t*)p!=b+0x20FF390)return false;
        if(*(uintptr_t*)(*(uintptr_t*)p+0x30)!=b+0x39FEE10 || *(uintptr_t*)(*(uintptr_t*)p+0x70)!=b+0x3A00D60)return false;
        return *(int*)(p+0x3c)==15&&*(BYTE*)(p+0x39)==0;
    } __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *modsRoot) {
    if(!modsRoot)return FALSE;
    HMODULE pinned=nullptr;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        (LPCSTR)&Fifa16ModStart,&pinned))return FALSE;
    AcquireSRWLockExclusive(&lock);
    // The host's root argument differs between old distributions. The INI is
    // always adjacent to this DLL, including junctions and portable installs.
    GetModuleFileNameA(pinned,ini,sizeof(ini));
    char *filename=strrchr(ini,'\\');
    if(!filename){ReleaseSRWLockExclusive(&lock);return FALSE;}
    strcpy_s(filename,size_t(ini+sizeof(ini)-filename),"\\low_driven_shot.ini");
    nextRead=0;memset(pads,0,sizeof(pads));reload(GetTickCount64());InterlockedExchange(&running,1);
    ReleaseSRWLockExclusive(&lock);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){InterlockedExchange(&running,0);return TRUE;}
// Called only by the existing shared input gate, after menu capture/masking.
extern "C" __declspec(dllexport) void WINAPI Fifa16LowDrivenShotFilter(DWORD index,XINPUT_STATE *state,BOOL captured) {
    if(index>=4||!state||!running)return;
    AcquireSRWLockExclusive(&lock);
    uint64_t now=GetTickCount64();reload(now);
    if(!enabled||captured||!live_match())memset(&pads[index],0,sizeof(ShotState));
    else {XINPUT_STATE physical=*state;shot_process(pads[index],physical,*state,now,1,height,threshold,button,mode,finesseTap);}
    ReleaseSRWLockExclusive(&lock);
}
// Pure entry point used by regression tests; never installs hooks.
extern "C" __declspec(dllexport) void WINAPI Fifa16LowDrivenShotProcess(ShotState *s,const XINPUT_STATE *in,XINPUT_STATE *out,
    uint64_t now,int active,int timingHeight,int triggerLimit,WORD shootButton,int shotMode,int finesseDuration) {
    shot_process(*s,*in,*out,now,active,timingHeight,triggerLimit,shootButton,shotMode,finesseDuration);
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(h);return TRUE;}
