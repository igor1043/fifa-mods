#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tournament_capacity.inc"

/* Separate plugin: no changes to the host's startup patch table or DB queries.
 * PID 30756: record +1A8 = league 86, +2B8 = 160. Competition cache
 * +6BE0/+6BE4 also =160; FCE+884F0 writes through a NULL lookup result.
 * L9's complete 61-site patch moves that cache to +8FD0/+8FD4.
 * Only install our CALL after that entire layout transition completes.
 */
#define ROOT_CAPACITY 4096U
#define LOAD_CALL_RVA 0x05B7AC91U
#define LOAD_FUNCTION_RVA 0x05B747B0U
typedef struct Root { int id, league; } Root;
typedef void (*LoadFn)(void *, void *, void *);
static Root roots[ROOT_CAPACITY];
static size_t root_count;
static uint32_t saved_mask;
static LoadFn original_load;
static volatile LONG started;
static BYTE *image;
static char game_dir[MAX_PATH];

static BOOL read_memory(const void *p,void *value,SIZE_T length) {
    SIZE_T got=0;
    return p && ReadProcessMemory(GetCurrentProcess(),p,value,length,&got) && got==length;
}
static BOOL load_roots(const char *path) {
    FILE *file=fopen(path,"rb");char line[2048];
    root_count=0;
    if(!file)return FALSE;
    while(fgets(line,sizeof(line),file)) {
        int id=0,type=0,league=0,used=0;size_t i;
        if(sscanf(line,"%d,%d,C%d,%n",&id,&type,&league,&used)!=3 || used<=0 || type!=3)continue;
        if(id<=0 || league<=0 || root_count==ROOT_CAPACITY)goto invalid;
        for(i=0;i<root_count;i++)if(roots[i].id==id) {
            if(roots[i].league!=league)goto invalid;
            break;
        }
        if(i!=root_count)continue;
        roots[root_count].id=id;roots[root_count++].league=league;
    }
    if(ferror(file))goto invalid;
    fclose(file);return root_count>0;
invalid:
    root_count=0;fclose(file);return FALSE;
}
static BOOL load_save_mask(const char *path) {
    FILE *file=fopen(path,"rb");char *xml,*field,*end,*depth,*low;long n;size_t length;
    saved_mask=0;
    if(!file)return FALSE;
    if(fseek(file,0,SEEK_END) || (n=ftell(file))<=0 || n>4*1024*1024 || fseek(file,0,SEEK_SET)) {
        fclose(file);return FALSE;
    }
    xml=(char*)malloc((size_t)n+1);
    if(!xml){fclose(file);return FALSE;}
    length=fread(xml,1,(size_t)n,file);fclose(file);xml[length]=0;
    field=strstr(xml,"name=\"primarycompobjid\"");
    end=field?strstr(field,"/>"):NULL;
    if(length!=(size_t)n || !end){free(xml);return FALSE;}
    *end=0;depth=strstr(field,"depth=\"");low=strstr(field,"rangelow=\"");
    if(!depth || !low || strtol(low+10,NULL,10)!=0){free(xml);return FALSE;}
    n=strtol(depth+7,NULL,10);
    if(n<1 || n>30){free(xml);return FALSE;}
    saved_mask=(1U<<(unsigned)n)-1U;free(xml);return TRUE;
}
static int resolve_root(int stored,int league) {
    size_t i;int found=0;unsigned matches=0;
    (void)league; /* Club league does not identify the selected tournament. */
    if(stored<0 || !saved_mask)return stored;
    if((uint32_t)stored>saved_mask)return stored;
    for(i=0;i<root_count;i++)if(((uint32_t)roots[i].id&saved_mask)==(uint32_t)stored) {
        found=roots[i].id;matches++;
    }
    return matches==1?found:stored;
}
static BYTE *service(BYTE *registry,unsigned index) {
    BYTE *wrapper=NULL,*object=NULL;
    if(!registry || !read_memory(registry+(size_t)index*32U+24U,&wrapper,sizeof(wrapper)) ||
       !read_memory(wrapper,&object,sizeof(object)))return NULL;
    return object;
}
static BOOL recover_selection(void *session,int *stored_out,int *league_out,int *root_out) {
    BYTE *registry=NULL,*career,*competition,*array=NULL,*row;
    int index,league,primary,club,type,cache[2],root;
    *stored_out=-1;*league_out=0;*root_out=-1;
    if(!session || !read_memory((BYTE*)session+0x1348U,&registry,sizeof(registry)))return FALSE;
    career=service(registry,121U);competition=service(registry,20U);
    if(!career || !competition || !read_memory(career+0x14U,&index,4) || index<0 || index>=64 ||
       !read_memory(career+0x18U,&array,sizeof(array)) || !array)return FALSE;
    row=array+(size_t)index*0x318U;
    if(!read_memory(row+0x1A4U,&club,4) || club<=0 || club>2000000 ||
       !read_memory(row+0x1A8U,&league,4) || league<=0 ||
       !read_memory(row+0x2B8U,&primary,4) ||
       !read_memory(row+0x2BCU,&type,4) || type<=0 ||
       !read_memory(competition+0x8FD0U,cache,sizeof(cache)))return FALSE;
    *stored_out=cache[1];*league_out=league;
    root=resolve_root(cache[1],league);*root_out=root;
    if(cache[0]!=cache[1] || primary!=cache[1] || root==cache[1] ||
       !accessible(competition+0x8FD0U,sizeof(cache),TRUE))return FALSE;
    /* No write to the user record, any database service or packed save.
     * An aligned single store publishes both runtime selection slots. */
    if(((uintptr_t)(competition+0x8FD0U)&7U)!=0)return FALSE;
    {
        LONG64 before,after;int full[2]={root,root};
        memcpy(&before,cache,8);memcpy(&after,full,8);
        return InterlockedCompareExchange64((volatile LONG64*)(competition+0x8FD0U),after,before)==before;
    }
}
static void load_with_identity(void *arg1,void *arg2,void *session) {
    int stored,league,root;
    BOOL changed=recover_selection(session,&stored,&league,&root);
    log_line("LOAD %s saved=%d club_league=%d root=%d policy=unique-root-mask database_writes=0",changed?"RECOVERED":"UNCHANGED",stored,league,root);
    original_load(arg1,arg2,session);
}
static BOOL reload_code_ready(void) {
    static const BYTE stores[12]={0x89,0x99,0xD0,0x8F,0,0,0x89,0x99,0xD4,0x8F,0,0};
    static const BYTE getter[6]={0x8B,0x99,0xD4,0x8F,0,0};
    static const BYTE user[24]={0x48,0x63,0x41,0x14,0x83,0xF8,0xFF,0x75,3,0x31,0xC0,0xC3,
        0x48,0x69,0xC0,0x18,3,0,0,0x48,3,0x41,0x18,0xC3};
    static const BYTE prologue[12]={0x48,0x89,0x5C,0x24,8,0x55,0x57,0x41,0x54,0x41,0x56,0x41};
    BYTE a[24],b[12],c[6],d[12],svc[6];
    return read_memory(image+0x5B7AC4DU,b,12) && !memcmp(b,stores,12) &&
        read_memory(image+0x5B74A1DU,c,6) && !memcmp(c,getter,6) &&
        read_memory(image+0x5AAFFF0U,a,24) && !memcmp(a,user,24) &&
        read_memory(image+LOAD_FUNCTION_RVA,d,12) && !memcmp(d,prologue,12) &&
        read_memory(image+0x4456307U,svc,6) && !memcmp(svc,"\xC7\x01\x14\0\0\0",6) &&
        read_memory(image+0x44575E7U,svc,6) && !memcmp(svc,"\xC7\x01\x79\0\0\0",6);
}
static BYTE *allocate_relay(uintptr_t target) {
    SYSTEM_INFO info;uintptr_t center,step,delta;
    GetSystemInfo(&info);step=info.dwAllocationGranularity;center=target&~(step-1U);
    for(delta=step;delta<0x7FFF0000U;delta+=step) {
        BYTE *p=(BYTE*)VirtualAlloc((void*)(center+delta),0x1000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if(p)return p;
        if(center>delta) {
            p=(BYTE*)VirtualAlloc((void*)(center-delta),0x1000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
            if(p)return p;
        }
    }
    return NULL;
}
static BOOL capacity_complete(void) {
    BYTE *chain=(BYTE*)GetModuleHandleA("dinput8_l9_chain.dll");
    IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
    if(!chain || !read_memory(image,&dos,sizeof(dos)) || dos.e_lfanew<0 || dos.e_lfanew>0x1000 ||
       !read_memory(image+dos.e_lfanew,&nt,sizeof(nt)) ||
       nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64 || nt.FileHeader.TimeDateStamp!=0x577DE45C ||
       !accessible(chain+0x239A0,61*72,FALSE))return FALSE;
    return count_applied(chain+0x239A0,image,nt.OptionalHeader.SizeOfImage)==61;
}
/* The captured creation path requests a count from a missing FAKEEVENT.
 * Guard only that CALL, preserving the original getter everywhere else. */
static const BYTE count_guard_code[]={0x9C,0x48,0x85,0xC9,0x74,0x05,
    0x8B,0x41,0x20,0x9D,0xC3,0x31,0xC0,0x9D,0xC3};
static BOOL install_creation_guard(void) {
    static const BYTE expected[16]={0xCC,0xB9,0x9A,0xFE,0x48,0x89,0xC1,0xE8,
        0x44,0x82,0xE8,0xFF,0xFF,0xC7,0x01,0xC5};
    BYTE *word=image+0x5ABC370U,*relay;BYTE actual[16],getter[4];
    LONG64 compare[2],replacement[2];int64_t distance;int32_t delta;
    DWORD previous,ignored;BOOL changed;
    if(!capacity_complete() || !read_memory(word,actual,16) || memcmp(actual,expected,16) ||
       !read_memory(image+0x59445C0U,getter,4) || memcmp(getter,"\x8B\x41\x20\xC3",4))return FALSE;
    relay=allocate_relay((uintptr_t)word);if(!relay)return FALSE;
    memcpy(relay,count_guard_code,sizeof(count_guard_code));
    distance=(int64_t)(uintptr_t)relay-(int64_t)(uintptr_t)(image+0x5ABC37CU);
    if(distance<INT32_MIN || distance>INT32_MAX || !VirtualProtect(relay,0x1000,PAGE_EXECUTE_READ,&previous)) {
        VirtualFree(relay,0,MEM_RELEASE);return FALSE;
    }
    delta=(int32_t)distance;memcpy(compare,actual,16);memcpy(actual+8,&delta,4);memcpy(replacement,actual,16);
    FlushInstructionCache(GetCurrentProcess(),relay,sizeof(count_guard_code));
    if(!VirtualProtect(word,16,PAGE_EXECUTE_READWRITE,&previous)){VirtualFree(relay,0,MEM_RELEASE);return FALSE;}
    changed=InterlockedCompareExchange128((volatile LONG64*)word,replacement[1],replacement[0],compare)!=0;
    FlushInstructionCache(GetCurrentProcess(),word,16);VirtualProtect(word,16,previous,&ignored);
    if(!changed){VirtualFree(relay,0,MEM_RELEASE);return FALSE;}
    log_line("CREATION GUARD installed call=05ABC377 NULL count returns zero");return TRUE;
}
static BOOL install_load_call(void) {
    BYTE *call=image+LOAD_CALL_RVA,*word=(BYTE*)((uintptr_t)call&~(uintptr_t)7),*relay;
    BYTE bytes[8],replacement[8];LONG64 before,after;int32_t old_delta,new_delta;
    uintptr_t function=(uintptr_t)&load_with_identity;int64_t distance;DWORD previous,ignored;size_t offset=(size_t)(call-word);
    if(offset+5U>8U || !capacity_complete() || !reload_code_ready() || !read_memory(word,bytes,8) || bytes[offset]!=0xE8)return FALSE;
    memcpy(&old_delta,bytes+offset+1,4);
    if((uintptr_t)(call+5)+old_delta!=(uintptr_t)(image+LOAD_FUNCTION_RVA))return FALSE;
    relay=allocate_relay((uintptr_t)call);if(!relay)return FALSE;
    /* Leaf tail-jump: no stack adjustment or changed nonvolatile registers. */
    memcpy(relay,"\xFF\x25\0\0\0\0",6);memcpy(relay+6,&function,8);
    distance=(int64_t)(uintptr_t)relay-(int64_t)(uintptr_t)(call+5);
    if(distance<INT32_MIN || distance>INT32_MAX || !VirtualProtect(relay,0x1000,PAGE_EXECUTE_READ,&previous)) {
        VirtualFree(relay,0,MEM_RELEASE);return FALSE;
    }
    FlushInstructionCache(GetCurrentProcess(),relay,14);
    new_delta=(int32_t)distance;memcpy(replacement,bytes,8);memcpy(replacement+offset+1,&new_delta,4);
    memcpy(&before,bytes,8);memcpy(&after,replacement,8);
    original_load=(LoadFn)(image+LOAD_FUNCTION_RVA);
    if(!VirtualProtect(word,8,PAGE_EXECUTE_READWRITE,&previous)) {VirtualFree(relay,0,MEM_RELEASE);return FALSE;}
    if(InterlockedCompareExchange64((volatile LONG64*)word,after,before)!=before) {
        VirtualProtect(word,8,previous,&ignored);VirtualFree(relay,0,MEM_RELEASE);return FALSE;
    }
    FlushInstructionCache(GetCurrentProcess(),word,8);VirtualProtect(word,8,previous,&ignored);
    log_line("READY version=3 reload_call=%p relay=%p roots=%llu save_mask=%u policy=unique-root-mask",call,relay,(unsigned long long)root_count,saved_mask);
    return TRUE;
}
static DWORD WINAPI plugin_worker(void *unused) {
    char path[MAX_PATH];DWORD result;unsigned attempt;BOOL creation=FALSE;(void)unused;
    image=(BYTE*)GetModuleHandleA(NULL);
    snprintf(path,sizeof(path),"%s\\dlc\\dlc_FootballCompEng\\dlc\\FootballCompEng\\data\\compdata\\compobj.txt",game_dir);
    if(!load_roots(path)){log_line("SKIPPED invalid/missing compobj; no patches");return 1;}
    snprintf(path,sizeof(path),"%s\\data\\db\\fifa_ng_db-meta.xml",game_dir);
    if(!load_save_mask(path) || saved_mask!=2047U){log_line("SKIPPED requires verified 11-bit installed schema; no patches");return 2;}
    {
        size_t i,j;unsigned recoverable=0,ambiguous=0;
        for(i=0;i<root_count;i++)if((uint32_t)roots[i].id>saved_mask) {
            int stored=(int)((uint32_t)roots[i].id&saved_mask);
            if(resolve_root(stored,0)==roots[i].id)recoverable++;
            else {ambiguous++;log_line("AMBIGUOUS full=%d stored=%d; recovery refused",roots[i].id,stored);}
            for(j=0;j<i;j++)if(roots[j].id==roots[i].id)return 2;
        }
        log_line("CATALOG roots=%llu recoverable_high=%u ambiguous_high=%u",(unsigned long long)root_count,recoverable,ambiguous);
    }
    result=compat_worker(NULL);
    if(result){log_line("SKIPPED reload hook: original capacity patch incomplete result=%lu",result);return 3;}
    /* Disabled capacity must not silently authorize an expanded-cache hook. */
    for(attempt=0;attempt<3000U;attempt++) {
        if(!creation)creation=install_creation_guard();
        if(creation && install_load_call())return 0;
        Sleep(20);
    }
    log_line("SKIPPED reload code mismatch; original call retained");return 4;
}
__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void) {return 1U;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root) {
    HANDLE thread;HMODULE pinned=NULL;char *slash;
    if(!mods_root || !mods_root[0])return FALSE;
    if(InterlockedCompareExchange(&started,1,0))return TRUE;
    if(snprintf(game_dir,sizeof(game_dir),"%s",mods_root)<0)return FALSE;
    slash=strrchr(game_dir,'\\');if(!slash)return FALSE;*slash=0; /* ModCarrerMode */
    snprintf(g_log,sizeof(g_log),"%s\\logs\\tournament_compat_native.log",game_dir);
    slash=strrchr(game_dir,'\\');if(!slash)return FALSE;*slash=0; /* game */
    snprintf(g_ini,sizeof(g_ini),"%s\\dinput8_L9.ini",game_dir);
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        (LPCSTR)&started,&pinned))return FALSE;
    log_line("START plugin=3 experimental=1 database_writes=0 save_writes=0 layout_gate=61/61");
    thread=CreateThread(NULL,0,plugin_worker,NULL,0,NULL);
    if(!thread)return FALSE;
    CloseHandle(thread);return TRUE;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved) {
    (void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(instance);return TRUE;
}
