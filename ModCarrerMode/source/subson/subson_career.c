#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>
#include <limits.h>

#define CAREER_BENCH_RVA 0x5AF8E00U
#define CAREER_SQUAD_CHECK_RVA 0x5910569U
static const unsigned char before[6]={0x8B,0x8A,0x94,0,0,0};
static const unsigned char minimum11[11]={0xBB,0,0,0,0,0x90,0x30,0xC9,0x83,0xC3,0x0B};
static const unsigned char squad_check_before[3]={0x8B,0x58,0x94};
static const unsigned char squad_check_minimum11[3]={0x31,0xDB,0x90};
static char diagnostics[MAX_PATH];
static RUNTIME_FUNCTION record;
static void event(const char *message)
{
    FILE *file=NULL;
    if(diagnostics[0] && !fopen_s(&file,diagnostics,"ab") && file){
        fprintf(file,"career_short_roster_v2 pid=%lu %s\r\n",GetCurrentProcessId(),message);fclose(file);
    }
}
static int read_at(uintptr_t at,void *out,SIZE_T size)
{SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void*)at,out,size,&got) && got==size;}

size_t subson_emit_career(unsigned char *page,uintptr_t resume)
{
    size_t size=(size_t)(SubsonCareerEnd-SubsonCareerBegin);
    if(!page || size>0x200U)return 0;
    memcpy(page,SubsonCareerBegin,size);
    memcpy(page+(SubsonCareerResume-SubsonCareerBegin),&resume,8);
    return size;
}
static int install(uintptr_t image,SIZE_T image_size)
{
    DWORD64 parent_base=0,squad_parent_base=0;PRUNTIME_FUNCTION parent,squad_parent;
    unsigned char header[4],squad_header[4],current[6],squad_current[3],
        applied[6]={0xE9,0,0,0,0,0x90};
    unsigned char *page;size_t size;int64_t distance;int32_t relative;DWORD old;
    if(!read_at(image+CAREER_BENCH_RVA,current,6) || memcmp(current,before,6))return 0;
    parent=RtlLookupFunctionEntry(image+CAREER_BENCH_RVA,&parent_base,NULL);
    if(!parent || parent_base!=image || parent->BeginAddress!=0x5AF8BF0U || parent->EndAddress!=0x5AF91F6U ||
       !read_at(image+parent->UnwindData,header,4) || memcmp(header,"\x21\x19\x06\0",4))return 0;
    if(!read_at(image+CAREER_SQUAD_CHECK_RVA,squad_current,sizeof(squad_current)) ||
       memcmp(squad_current,squad_check_before,sizeof(squad_current)))return 0;
    squad_parent=RtlLookupFunctionEntry(image+CAREER_SQUAD_CHECK_RVA,&squad_parent_base,NULL);
    if(!squad_parent || squad_parent_base!=image || squad_parent->BeginAddress!=0x5910500U ||
       squad_parent->EndAddress!=0x5910673U ||
       !read_at(image+squad_parent->UnwindData,squad_header,4) ||
       memcmp(squad_header,"\x01\x14\x0a\0",4))return 0;
    page=subson_near_page(image,image_size,image+CAREER_BENCH_RVA);
    if(!page)return 0;
    size=subson_emit_career(page,image+CAREER_BENCH_RVA+6U);
    if(!size)return 0;
    /* Two one-byte pushes allocate 16 bytes; chain the original FCE frame. */
    memcpy(page+0x300,"\x21\x02\x01\0\x02\x12\0\0",8);
    memcpy(page+0x308,parent,sizeof(*parent));
    record.BeginAddress=(DWORD)((uintptr_t)page-image);
    record.EndAddress=record.BeginAddress+(DWORD)size;
    record.UnwindData=record.BeginAddress+0x300U;
    distance=(int64_t)(uintptr_t)page-(int64_t)(image+CAREER_BENCH_RVA+5U);
    if(distance<INT32_MIN || distance>INT32_MAX || !VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old) ||
       !FlushInstructionCache(GetCurrentProcess(),page,0x314U) || !RtlAddFunctionTable(&record,1,image))return 0;
    relative=(int32_t)distance;memcpy(applied+1,&relative,4);
    if(!subson_write_bytes(image+CAREER_SQUAD_CHECK_RVA,squad_check_before,
                           squad_check_minimum11,sizeof(squad_check_before)))return 0;
    if(!subson_write_bytes(image+CAREER_BENCH_RVA,before,applied,6)){
        (void)subson_write_bytes(image+CAREER_SQUAD_CHECK_RVA,squad_check_minimum11,
                                 squad_check_before,sizeof(squad_check_before));
        return 0;
    }
    event("career_match_min11 installed squad_check_substitutes=0 starters=11; bench=min(rule,eligible-11) max=12");return 1;
}
static DWORD WINAPI worker(void *unused)
{
    uintptr_t image=(uintptr_t)GetModuleHandleA(NULL);IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
    unsigned attempt;unsigned char guard[11];(void)unused;
    if(!read_at(image,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE || dos.e_lfanew<0 || dos.e_lfanew>0x1000 ||
       !read_at(image+(unsigned)dos.e_lfanew,&nt,sizeof(nt)) || nt.Signature!=IMAGE_NT_SIGNATURE ||
       nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64 || nt.FileHeader.TimeDateStamp!=0x577DE45CU ||
       (nt.OptionalHeader.SizeOfImage!=0x9524000U && nt.OptionalHeader.SizeOfImage!=0x9525000U)){
        event("not_installed unsupported_executable");return 0;
    }
    for(attempt=0;attempt<600U;++attempt){
        if(read_at(image+0x5AF8DBFU,guard,11) && !memcmp(guard,minimum11,11)){
            if(!install(image,nt.OptionalHeader.SizeOfImage))event("not_installed native_signature_or_hook_conflict");
            return 0;
        }
        Sleep(200);
    }
    event("not_installed requires_WorkLab_MIN_PLAYERS_11");return 0;
}
BOOL subson_career_start(unsigned bench,unsigned minimum,const char *log_path)
{
    HANDLE thread;if(bench<7U || bench>12U || !log_path)return FALSE;
    if(minimum!=11U)return TRUE;
    strcpy_s(diagnostics,sizeof(diagnostics),log_path);
    thread=CreateThread(NULL,0,worker,NULL,0,NULL);if(!thread)return FALSE;
    CloseHandle(thread);return TRUE;
}
