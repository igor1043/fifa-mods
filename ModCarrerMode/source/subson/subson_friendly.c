#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>
#include <limits.h>

#define PLAYNOW_VTABLE 0x21A66D0U
#define PLAYNOW_DISPATCH 0x3D8FD70U
#define IMPORT_RVA 0x414EB83U
#define CAPACITY_RVA 0x415AED7U
typedef uintptr_t (__fastcall *Dispatch)(uintptr_t, unsigned, uintptr_t);
static uintptr_t image;
static SIZE_T image_size;
static unsigned bench_size;
static Dispatch original_dispatch;
static char diagnostics[MAX_PATH];
static volatile LONG ui_calls, import_calls, capacity_calls;
static volatile LONG other_import_calls, other_capacity_calls;
static const unsigned char import_before[7]={0x41,0x8B,0x9D,0x10,0x0C,0,0};
static const unsigned char capacity_before[6]={0x44,0x8D,0x77,7,0x89,0xFB};
typedef struct Hook {
    DWORD rva;
    unsigned length;
    const unsigned char *before;
    unsigned char applied[7];
    unsigned char *page;
    RUNTIME_FUNCTION runtime;
    int registered, installed;
} Hook;
static Hook hooks[2];

static BOOL read_at(uintptr_t at, void *out, SIZE_T size)
{
    SIZE_T n=0;
    return at && ReadProcessMemory(GetCurrentProcess(),(void *)at,out,size,&n) && n==size;
}
static uintptr_t pointer_at(uintptr_t at)
{ uintptr_t out=0;(void)read_at(at,&out,sizeof(out));return out; }
static void event(const char *message)
{
    FILE *file=NULL;
    if(diagnostics[0] && !fopen_s(&file,diagnostics,"ab") && file){
        fprintf(file,"friendly_v2 pid=%lu %s\r\n",GetCurrentProcessId(),message);fclose(file);
    }
}
static uintptr_t active_playnow(void)
{
    uintptr_t main=pointer_at(image+0x34EA0E8U), controller, stack, state;
    int32_t index;
    if(!main || !(controller=pointer_at(main+0x68U)) || !(stack=pointer_at(controller)) ||
       !read_at(stack+0x20U,&index,4) || index<0 || index>3) return 0;
    state=pointer_at(stack+(unsigned)index*8U);
    return state && pointer_at(state)==image+PLAYNOW_VTABLE ? state : 0;
}
static unsigned __fastcall import_policy(uintptr_t settings,unsigned native)
{
    uintptr_t state=active_playnow();
    if(native>=5U && native<=12U && state && pointer_at(state+0x340U)==settings){
        InterlockedIncrement(&import_calls);return bench_size;
    }
    InterlockedIncrement(&other_import_calls);return native;
}
static unsigned __fastcall capacity_policy(void)
{
    if(active_playnow()){InterlockedIncrement(&capacity_calls);return bench_size;}
    InterlockedIncrement(&other_capacity_calls);return 7U;
}
static void update_request(uintptr_t state)
{
    uintptr_t settings=pointer_at(state+0x340U);
    unsigned native, phase;
    if(pointer_at(state)==image+PLAYNOW_VTABLE &&
       read_at(state+0x440U,&phase,4) && phase<=14U && settings &&
       read_at(settings+0xC10U,&native,4) && native>=5U && native<=12U)
        *(unsigned *)(settings+0xC10U)=bench_size;
}
static uintptr_t __fastcall friendly_dispatch(uintptr_t state,unsigned command,uintptr_t output)
{
    uintptr_t result;
    /* Only this specific PlayNow vtable points here. Keep all original
     * commands and their return values, then supply its missing bench rule.
     */
    if(pointer_at(state)!=image+PLAYNOW_VTABLE)
        return original_dispatch(state,command,output);
    update_request(state);
    result=original_dispatch(state,command,output);
    update_request(state);
    if(command==0x6EU && output){
        *(unsigned *)output=bench_size;
        InterlockedIncrement(&ui_calls);
    }
    return result;
}

static size_t emit(unsigned char *page,const unsigned char *begin,const unsigned char *end,
                   const unsigned char *policy,const unsigned char *resume,
                   uintptr_t callback,uintptr_t target)
{
    size_t size=(size_t)(end-begin);
    if(!page || size>0x300U)return 0;
    memcpy(page,begin,size);memcpy(page+(policy-begin),&callback,8);
    memcpy(page+(resume-begin),&target,8);return size;
}
size_t subson_emit_import(unsigned char *page,uintptr_t callback,uintptr_t resume)
{return emit(page,SubsonImportBegin,SubsonImportEnd,SubsonImportPolicy,SubsonImportResume,callback,resume);}
size_t subson_emit_capacity(unsigned char *page,uintptr_t callback,uintptr_t resume)
{return emit(page,SubsonCapacityBegin,SubsonCapacityEnd,SubsonCapacityPolicy,SubsonCapacityResume,callback,resume);}
void subson_unwind(unsigned char out[24],const RUNTIME_FUNCTION *parent)
{
    static const unsigned char head[12]={0x21,8,3,0,8,1,0x1D,0,1,2,0,0};
    memcpy(out,head,12);memcpy(out+12,parent,12);
}
static int supported(void)
{
    IMAGE_DOS_HEADER dos; IMAGE_NT_HEADERS64 nt;
    image=(uintptr_t)GetModuleHandleA(NULL);
    if(!read_at(image,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE ||
       dos.e_lfanew<0 || dos.e_lfanew>0x1000 ||
       !read_at(image+(unsigned)dos.e_lfanew,&nt,sizeof(nt)))return 0;
    image_size=nt.OptionalHeader.SizeOfImage;
    return nt.Signature==IMAGE_NT_SIGNATURE && nt.FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64 &&
       nt.FileHeader.TimeDateStamp==0x577DE45CU &&
       (image_size==0x9524000U || image_size==0x9525000U);
}
static int ready(void)
{
    static const unsigned char first[]={0x48,0x89,0xAE,0x60,0x10,0,0};
    static const unsigned char last[]={0x89,0xB9,0x7C,0x10,0,0};
    unsigned char bytes[7];
    return pointer_at(image+PLAYNOW_VTABLE+8U)==image+PLAYNOW_DISPATCH &&
        read_at(image+0x49AA271U,bytes,7) && !memcmp(bytes,first,7) &&
        read_at(image+0x49AD245U,bytes,6) && !memcmp(bytes,last,6) &&
        read_at(image+0x44B434AU,bytes,1) && bytes[0]==bench_size;
}
static int players_loaded(void)
{
    uintptr_t engine=pointer_at(image+0x37477B0U);unsigned side,count;
    if(!engine)return 0;
    if(pointer_at(engine)!=image+0x22D2CF0U)return 1;
    for(side=0;side<2;++side)
        if(!read_at(engine+0xBC0U+side*0x4B60U+0x4B40U,&count,4) || count>1U)return 1;
    return 0;
}
static int exchange_dispatch(uintptr_t expected,uintptr_t target)
{
    void *volatile *slot=(void *volatile *)(image+PLAYNOW_VTABLE+8U);
    DWORD old,ignored;void *previous;
    if(!VirtualProtect((void *)slot,8,PAGE_READWRITE,&old))return 0;
    previous=InterlockedCompareExchangePointer(slot,(void *)target,(void *)expected);
    (void)VirtualProtect((void *)slot,8,old,&ignored);
    return previous==(void *)expected;
}
static int prepare_hook(Hook *hook,unsigned index)
{
    static const unsigned char unwind_headers[2][4]={{0x19,0x2A,0x0B,0},{1,0x1A,0x0A,0}};
    static const DWORD starts[2]={0x414EB20U,0x415AEB0U};
    DWORD64 parent_base=0;PRUNTIME_FUNCTION parent;unsigned char current[7],head[4];
    size_t size;DWORD old;int64_t distance;int32_t relative;
    hook->rva=index?CAPACITY_RVA:IMPORT_RVA;hook->length=index?6U:7U;
    hook->before=index?capacity_before:import_before;
    if(!read_at(image+hook->rva,current,hook->length) || memcmp(current,hook->before,hook->length))return 0;
    parent=RtlLookupFunctionEntry(image+hook->rva,&parent_base,NULL);
    if(!parent || parent_base!=image || parent->BeginAddress!=starts[index] ||
       parent->EndAddress<hook->rva+hook->length ||
       !read_at(image+parent->UnwindData,head,4) || memcmp(head,unwind_headers[index],4))return 0;
    hook->page=subson_near_page(image,image_size,image+hook->rva);
    if(!hook->page)return 0;
    size=index?subson_emit_capacity(hook->page,(uintptr_t)capacity_policy,image+hook->rva+hook->length):
               subson_emit_import(hook->page,(uintptr_t)import_policy,image+hook->rva+hook->length);
    if(!size)return 0;
    subson_unwind(hook->page+0x300U,parent);
    hook->runtime.BeginAddress=(DWORD)((uintptr_t)hook->page-image);
    hook->runtime.EndAddress=hook->runtime.BeginAddress+(DWORD)size;
    hook->runtime.UnwindData=hook->runtime.BeginAddress+0x300U;
    distance=(int64_t)(uintptr_t)hook->page-(int64_t)(image+hook->rva+5U);
    if(distance<INT32_MIN || distance>INT32_MAX ||
       !VirtualProtect(hook->page,0x1000U,PAGE_EXECUTE_READ,&old) ||
       !FlushInstructionCache(GetCurrentProcess(),hook->page,0x318U) ||
       !RtlAddFunctionTable(&hook->runtime,1,image))return 0;
    hook->registered=1;relative=(int32_t)distance;
    memset(hook->applied,0x90,sizeof(hook->applied));hook->applied[0]=0xE9;
    memcpy(hook->applied+1,&relative,4);return 1;
}
static int remove_hooks(void)
{
    int index,ok=1;
    for(index=1;index>=0;--index){Hook *hook=&hooks[index];
        if(hook->installed){
            if(subson_write_bytes(image+hook->rva,hook->applied,hook->before,hook->length))hook->installed=0;
            else ok=0;
        }
        /* Keep registered RX storage until process exit. A suspended caller
         * may still be returning through it even after the entry is restored.
         */
    }
    return ok;
}
static int install(void)
{
    unsigned index;
    if(players_loaded() || !prepare_hook(&hooks[0],0) || !prepare_hook(&hooks[1],1))return 0;
    original_dispatch=(Dispatch)(image+PLAYNOW_DISPATCH);
    for(index=0;index<2;++index){Hook *hook=&hooks[index];
        if(!subson_write_bytes(image+hook->rva,hook->before,hook->applied,hook->length)){
            (void)remove_hooks();return 0;
        }
        hook->installed=1;
    }
    if(!exchange_dispatch(image+PLAYNOW_DISPATCH,(uintptr_t)friendly_dispatch)){
        (void)remove_hooks();return 0;
    }
    return 1;
}
static void observe(void)
{
    LONG previous[5]={-1,-1,-1,-1,-1};
    for(;;){
        LONG now[5]={ui_calls,import_calls,capacity_calls,other_import_calls,other_capacity_calls};
        if(memcmp(now,previous,sizeof(now))){
            char line[256];memcpy(previous,now,sizeof(now));
            _snprintf_s(line,sizeof(line),_TRUNCATE,
                "calls ui=%ld import=%ld capacity=%ld other_import_passthrough=%ld other_capacity_passthrough=%ld bench=%u",
                now[0],now[1],now[2],now[3],now[4],bench_size);event(line);
        }
        Sleep(500U);
    }
}
static DWORD WINAPI worker(void *unused)
{
    unsigned attempt;(void)unused;
    if(!supported()){event("not_installed unsupported_executable");return 0;}
    for(attempt=0;attempt<600U;++attempt){
        if(ready()){
            if(players_loaded()){event("not_installed restart_required match_already_loaded");return 0;}
            if(install()){
                event("installed PlayNow_UI_rule=1 PlayNow_request=1 PlayNow_capacity=1 career_tournament_passthrough=1 rendering=WorkLab C14_unchanged=1");
                observe();
            }
            event("not_installed native_signature_or_hook_conflict");return 0;
        }
        Sleep(200U);
    }
    event("not_installed WorkLab_not_ready");return 0;
}
BOOL subson_friendly_start(unsigned bench,const char *log_path)
{
    HANDLE thread;HMODULE pinned=NULL;
    if(bench<7U || bench>12U || !log_path)return FALSE;
    bench_size=bench;strcpy_s(diagnostics,sizeof(diagnostics),log_path);
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        (LPCSTR)&bench_size,&pinned))return FALSE;
    thread=CreateThread(NULL,0,worker,NULL,0,NULL);
    if(!thread)return FALSE;
    CloseHandle(thread);return TRUE;
}

#ifdef SUBSON_FRIENDLY_TEST
void subson_test_context(uintptr_t base,unsigned bench){image=base;bench_size=bench;}
unsigned subson_test_import(uintptr_t settings,unsigned native){return import_policy(settings,native);}
unsigned subson_test_capacity(void){return capacity_policy();}
void subson_test_dispatch(Dispatch callback){original_dispatch=callback;}
uintptr_t subson_test_command(uintptr_t state,unsigned command,uintptr_t output)
{return friendly_dispatch(state,command,output);}
int subson_test_install(uintptr_t base,unsigned bench)
{image=base;image_size=0x9525000U;bench_size=bench;memset(hooks,0,sizeof(hooks));return install();}
int subson_test_remove(void)
{
    unsigned index;
    if(!exchange_dispatch((uintptr_t)friendly_dispatch,image+PLAYNOW_DISPATCH) || !remove_hooks())return 0;
    for(index=0;index<2;++index){
        if(hooks[index].registered && !RtlDeleteFunctionTable(&hooks[index].runtime))return 0;
        if(hooks[index].page && !VirtualFree(hooks[index].page,0,MEM_RELEASE))return 0;
    }
    return 1;
}
#endif
