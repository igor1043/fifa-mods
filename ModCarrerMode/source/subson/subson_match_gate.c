#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>
#include <limits.h>

/* Only the three calls to GetSquadStatusForTeam used by career match entry
 * and the return from team selection. Do not edit that shared function, the
 * competition rule, any provider/card, or any player record.
 */
#define SQUAD_STATUS_RVA 0x5C44990U
typedef struct GateSite {
    DWORD rva,begin,end;
    unsigned char unwind[4],original[5],applied[5];
    int installed;
} GateSite;
static GateSite sites[3]={
    {0x59105B6U,0x5910500U,0x5910673U,{1,0x14,0x0A,0},{0xE8,0xD5,0x43,0x33,0},{0},0},
    {0x59105CCU,0x5910500U,0x5910673U,{1,0x14,0x0A,0},{0xE8,0xBF,0x43,0x33,0},{0},0},
    {0x59586BDU,0x5957DE0U,0x595876BU,{0x19,0x2A,0x0B,0},{0xE8,0xCE,0xC2,0x2E,0},{0},0}
};
static char diagnostics[MAX_PATH];
static volatile LONG started;
static RUNTIME_FUNCTION leaf_runtime;
__declspec(dllexport) volatile LONG Fifa16OptionalBenchGateReady;

static int read_at(uintptr_t at,void *out,SIZE_T size)
{SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void*)at,out,size,&got)&&got==size;}
static void event(const char *text)
{
    FILE *file=NULL;
    if(diagnostics[0]&&!fopen_s(&file,diagnostics,"ab")&&file){
        fprintf(file,"career_match_gate_v5 pid=%lu %s\r\n",GetCurrentProcessId(),text);fclose(file);
    }
}
size_t subson_emit_match_gate(unsigned char *out,uintptr_t target)
{
    /* A tail call changes only numSubs (R8D). No flags, stack slots, player
     * counts, nonvolatile registers, or return values are fabricated.
     */
    static const unsigned char code[20]={0x41,0xB8,0,0,0,0,0xFF,0x25,0,0,0,0,0,0,0,0,0,0,0,0};
    if(!out)return 0;
    memcpy(out,code,sizeof(code));memcpy(out+12,&target,8);return sizeof(code);
}
static int bench_ready(uintptr_t image)
{
    static const unsigned char minimum[11]={0xBB,0,0,0,0,0x90,0x30,0xC9,0x83,0xC3,0x0B};
    unsigned char actual[0x200],expected[0x200],call[6],guard[11];
    int32_t delta;uintptr_t destination;size_t size;
    if(!read_at(image+0x5AF8DBFU,guard,11)||memcmp(guard,minimum,11)||
       !read_at(image+0x5AF8E00U,call,6)||call[0]!=0xE9||call[5]!=0x90)return 0;
    memcpy(&delta,call+1,4);destination=(uintptr_t)((int64_t)(image+0x5AF8E05U)+delta);
    size=subson_emit_career(expected,image+0x5AF8E06U);
    return size&&read_at(destination,actual,size)&&!memcmp(actual,expected,size);
}
static int remove_gates(uintptr_t image)
{
    unsigned i;int ok=1;
    for(i=3;i>0;--i){GateSite *s=&sites[i-1];
        if(s->installed){
            if(subson_write_bytes(image+s->rva,s->applied,s->original,5))s->installed=0;
            else ok=0;
        }
    }
    return ok;
}
static int install_gates(uintptr_t image,SIZE_T image_size)
{
    unsigned i;unsigned char current[6],head[4];unsigned char *page;
    DWORD protection;size_t size;
    /* Explicitly reject the retired/truncated patches and keep their entire
     * original instructions intact, including the six-byte EBX load.
     */
    if(!read_at(image+0x5910569U,current,6)||memcmp(current,"\x8B\x98\x94\0\0\0",6)||
       !read_at(image+0x5C449ACU,current,3)||memcmp(current,"\x44\x89\xC5",3))return 0;
    for(i=0;i<3;++i){
        GateSite *s=&sites[i];DWORD64 owner=0;PRUNTIME_FUNCTION parent;
        if(!read_at(image+s->rva,current,5)||memcmp(current,s->original,5))return 0;
        parent=RtlLookupFunctionEntry(image+s->rva,&owner,NULL);
        if(!parent||owner!=image||parent->BeginAddress!=s->begin||parent->EndAddress!=s->end||
           !read_at(image+parent->UnwindData,head,4)||memcmp(head,s->unwind,4))return 0;
    }
    page=subson_near_page(image,image_size,image+sites[0].rva);
    if(!page)return 0;
    size=subson_emit_match_gate(page,image+SQUAD_STATUS_RVA);
    memcpy(page+0x300,"\x01\0\0\0",4); /* leaf: no stack adjustment */
    leaf_runtime.BeginAddress=(DWORD)((uintptr_t)page-image);
    leaf_runtime.EndAddress=leaf_runtime.BeginAddress+(DWORD)size;
    leaf_runtime.UnwindData=leaf_runtime.BeginAddress+0x300U;
    for(i=0;i<3;++i){
        GateSite *s=&sites[i];int64_t distance=(int64_t)(uintptr_t)page-(int64_t)(image+s->rva+5U);int32_t relative;
        if(distance<INT32_MIN||distance>INT32_MAX)return 0;
        relative=(int32_t)distance;s->applied[0]=0xE8;memcpy(s->applied+1,&relative,4);
    }
    if(!VirtualProtect(page,4096,PAGE_EXECUTE_READ,&protection)||
       !FlushInstructionCache(GetCurrentProcess(),page,0x304U)||
       !RtlAddFunctionTable(&leaf_runtime,1,image))return 0;
    for(i=0;i<3;++i){GateSite *s=&sites[i];
        if(!subson_write_bytes(image+s->rva,s->original,s->applied,5)){
            if(!remove_gates(image))return -1;
            RtlDeleteFunctionTable(&leaf_runtime);VirtualFree(page,0,MEM_RELEASE);return 0;
        }
        s->installed=1;
    }
    InterlockedExchange(&Fifa16OptionalBenchGateReady,1);
    event("installed calls=059105B6,059105CC,059586BD numSubs_validation=0 min_starters=11 max_bench=12 bench_clamp_verified=1 shared_checker_unchanged=1 competition_unchanged=1");
    return 1;
}
#ifndef SUBSON_MATCH_GATE_TEST
static DWORD WINAPI worker(void *unused)
{
    uintptr_t image=(uintptr_t)GetModuleHandleA(NULL);IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;unsigned attempt;
    (void)unused;
    if(!read_at(image,&dos,sizeof(dos))||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<0||dos.e_lfanew>0x1000||
       !read_at(image+(unsigned)dos.e_lfanew,&nt,sizeof(nt))||nt.Signature!=IMAGE_NT_SIGNATURE||
       nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt.FileHeader.TimeDateStamp!=0x577DE45CU||
       (nt.OptionalHeader.SizeOfImage!=0x9524000U&&nt.OptionalHeader.SizeOfImage!=0x9525000U)){
        event("not_installed unsupported_executable");return 0;
    }
    for(attempt=0;attempt<600;++attempt){
        static const unsigned char minimum[11]={0xBB,0,0,0,0,0x90,0x30,0xC9,0x83,0xC3,0x0B};
        unsigned char guard[11];
        if(!bench_ready(image)&&read_at(image+0x5AF8DBFU,guard,11)&&!memcmp(guard,minimum,11)){
            if(!subson_career_ensure_now(image,nt.OptionalHeader.SizeOfImage,diagnostics)){Sleep(1000);continue;}
        }
        if(bench_ready(image)){
            int result=install_gates(image,nt.OptionalHeader.SizeOfImage);
            if(result>0)return 0;
            if(result<0){event("not_installed incomplete_rollback_restart_required");return 0;}
            if(attempt%25U==0)event("waiting guarded_gate_install_retry");
        }
        Sleep(200);
    }
    event("not_installed requires_WorkLab_MIN_PLAYERS_11_and_optional_bench_v1");return 0;
}
__declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(void){return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *root)
{
    HMODULE pinned=NULL;HANDLE thread;
    if(!root||!root[0])return FALSE;
    if(InterlockedCompareExchange(&started,1,0))return TRUE;
    _snprintf_s(diagnostics,sizeof(diagnostics),_TRUNCATE,"%s\\..\\logs\\subson_match_gate.log",root);
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       (LPCSTR)&started,&pinned))return FALSE;
    thread=CreateThread(NULL,0,worker,NULL,0,NULL);
    if(!thread)return FALSE;
    CloseHandle(thread);return TRUE;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved)
{(void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(instance);return TRUE;}
#else
int subson_gate_test_install(uintptr_t image,SIZE_T image_size){return install_gates(image,image_size);}
int subson_gate_test_remove(uintptr_t image){return remove_gates(image);}
int subson_gate_test_bench_ready(uintptr_t image){return bench_ready(image);}
#endif
