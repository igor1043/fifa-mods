#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
template<class T>static bool read(uintptr_t a,T& v){SIZE_T n=0;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,&v,sizeof(v),&n)&&n==sizeof(v);}
extern "C" __declspec(dllexport) DWORD WINAPI ResolveVarCabin(void*){
    const uintptr_t image=(uintptr_t)GetModuleHandleA(nullptr);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
    if(!read(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||!read(image+(uintptr_t)dos.e_lfanew,nt)||nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return 2;
    const unsigned char expected[9]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xc3};unsigned char actual[9];SIZE_T n=0;
    if(!ReadProcessMemory(GetCurrentProcess(),(void*)(image+0x43b47c0),actual,9,&n)||n!=9||memcmp(actual,expected,9))return 3;
    unsigned count=0;
    for(unsigned i=0;i<176;++i){
        uintptr_t p=0,s=0;uint16_t type=0,variant=0;unsigned rna=0;
        if(!read(image+0x350e250+i*8,p)||!p||!read(p+12,type)||type!=3||!read(p+14,variant)||variant!=1||!read(p+16,s)||!read(s+0x4c,rna)||rna!=i)continue;
        // This helper completes only our reserved model after every resource
        // is ready. Normal platform prototypes are never changed.
        bool ready=true;
        for(unsigned lod=0;lod<5;++lod){uintptr_t composite=0;unsigned char loaded=0;if(!read(s+0x20+8*lod,composite)||!read(composite+0x10,loaded)||loaded!=1){ready=false;break;}}
        if(!ready)return 4;
        ((void(__fastcall*)(void*))(image+0x43b47c0))((void*)p);++count;
    }
    FILE* f=nullptr;if(!fopen_s(&f,"U:\\fifa 16\\ModCarrerMode\\logs\\var_cabin.log","ab")&&f){fprintf(f,"%llu live_native_loaded_notification count=%u all_five_lods_ready\n",GetTickCount64(),count);fclose(f);}
    return count==1?1:5;
}
BOOL WINAPI DllMain(HINSTANCE dll,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(dll);return TRUE;}
