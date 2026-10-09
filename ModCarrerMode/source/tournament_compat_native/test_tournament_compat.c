#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static BYTE *fixture_exe,*fixture_chain;
static ULONGLONG fixture_ticks;
static unsigned published,forwarded;
static void *forwarded_args[3];
static HMODULE WINAPI fixture_module(LPCSTR name) {return (HMODULE)(name?fixture_chain:fixture_exe);}
static ULONGLONG WINAPI fixture_time(void) {return fixture_ticks;}
static void WINAPI fixture_sleep(DWORD ms) {
    unsigned i;BYTE *ds=fixture_chain+0x239A0;
    fixture_ticks+=ms;
    for(i=0;i<61;i++) {
        BYTE *d=ds+i*72;uintptr_t target;memcpy(&target,d,8);
        if(memcmp((void*)target,d+9,d[8]))return;
    }
    for(i=0;i<61;i++) {
        BYTE *d=ds+i*72;uintptr_t target;memcpy(&target,d,8);memcpy((void*)target,d+18,d[8]);
    }
    published=61;
}
#define GetModuleHandleA fixture_module
#define GetTickCount64 fixture_time
#define Sleep fixture_sleep
#include "tournament_compat.c"
#undef GetModuleHandleA
#undef GetTickCount64
#undef Sleep
#define CHECK(x) do {if(!(x)){printf("FAIL line %d: %s\n",__LINE__,#x);return 1;}} while(0)
static void original_fixture(void *a,void *b,void *c) {forwarded_args[0]=a;forwarded_args[1]=b;forwarded_args[2]=c;forwarded++;}
int main(int argc,char **argv) {
    BYTE session[0x1350]={0},registry[32*122]={0},career[0x20]={0},row[0x318]={0},saved_row[0x318];
    BYTE *competition,*cw=career,*tw;int index=0,club=130251,league=86,primary=160;
    int stored,l,r,caches[2]={160,160};size_t i;unsigned high=0;
    IMAGE_NT_HEADERS64 *nt;DWORD result;char path[MAX_PATH];FILE *f;
    CHECK(argc==3);
    CHECK(load_roots(argv[1]));CHECK(load_save_mask(argv[2]));CHECK(saved_mask==2047);
    for(i=0;i<root_count;i++) {
        CHECK(resolve_root(roots[i].id,roots[i].league)==roots[i].id);
        {size_t j;unsigned matches=0;int low=roots[i].id&2047;
         for(j=0;j<root_count;j++)if((roots[j].id&2047)==low)matches++;
         CHECK(resolve_root(low,roots[i].league)==(matches==1?roots[i].id:low));}
        if(roots[i].id>2047)high++;
    }
    CHECK(root_count>100 && high>0);
    CHECK(resolve_root(160,86)==2208 && resolve_root(160,351)==2208);
    CHECK(resolve_root(63,74)==63 && resolve_root(63,122)==63);
    CHECK(resolve_root(130,980)==130 && resolve_root(130,123)==130);
    /* Future roots come from compobj, with no compiled ID list. Ambiguous
     * same-league aliases must not select the wrong competition. */
    {Root old[ROOT_CAPACITY];size_t count=root_count;memcpy(old,roots,sizeof(old));
     root_count=1;roots[0]=(Root){70000,2000};CHECK(resolve_root(70000&2047,1)==70000);
     roots[root_count++]=(Root){72048,2001};CHECK(resolve_root(70000&2047,2000)==(70000&2047));
     memcpy(roots,old,sizeof(old));root_count=count;}
    snprintf(path,sizeof(path),"build\\fixture-roots.txt");f=fopen(path,"wb");CHECK(f);
    fputs("70000,3,C2000,0\n70001,3,C2001x,0\n",f);fclose(f);
    CHECK(load_roots(path) && root_count==1 && resolve_root(70000&2047,2000)==70000);
    CHECK(load_roots(argv[1]));
    competition=(BYTE*)VirtualAlloc(NULL,0x9000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);CHECK(competition);
    tw=competition;
    {BYTE *p=registry;memcpy(session+0x1348,&p,8);p=(BYTE*)&cw;
     memcpy(registry+121*32+24,&p,8);p=(BYTE*)&tw;memcpy(registry+20*32+24,&p,8);
     p=row;memcpy(career+0x18,&p,8);memcpy(career+0x14,&index,4);}
    memcpy(row+0x1A4,&club,4);memcpy(row+0x1A8,&league,4);memcpy(row+0x2B8,&primary,4);
    {int type=1;memcpy(row+0x2BC,&type,4);}
    memcpy(saved_row,row,sizeof(row));memcpy(competition+0x8FD0,caches,8);
    CHECK(recover_selection(session,&stored,&l,&r));CHECK(stored==160 && l==86 && r==2208);
    memcpy(caches,competition+0x8FD0,8);CHECK(caches[0]==2208 && caches[1]==2208);
    CHECK(!memcmp(row,saved_row,sizeof(row))); /* User/DB record stays unchanged. */
    /* Reproduce v2 failure: club league 351, tournament root in league 86. */
    league=351;memcpy(row+0x1A8,&league,4);memcpy(saved_row,row,sizeof(row));
    caches[0]=caches[1]=160;memcpy(competition+0x8FD0,caches,8);
    CHECK(recover_selection(session,&stored,&l,&r) && r==2208 && l==351);
    CHECK(!memcmp(row,saved_row,sizeof(row)));
    {int type=0;memcpy(row+0x2BC,&type,4);caches[0]=caches[1]=160;
     memcpy(competition+0x8FD0,caches,8);CHECK(!recover_selection(session,&stored,&l,&r));
     type=1;memcpy(row+0x2BC,&type,4);caches[0]=caches[1]=2208;memcpy(competition+0x8FD0,caches,8);}
    CHECK(!recover_selection(session,&stored,&l,&r));
    caches[0]=100;caches[1]=160;memcpy(competition+0x8FD0,caches,8);
    CHECK(!recover_selection(session,&stored,&l,&r));
    caches[0]=caches[1]=160;memcpy(competition+0x8FD0,caches,8);
    primary=99;memcpy(row+0x2B8,&primary,4);CHECK(!recover_selection(session,&stored,&l,&r));
    primary=160;memcpy(row+0x2B8,&primary,4);
    index=-1;memcpy(career+0x14,&index,4);CHECK(!recover_selection(session,&stored,&l,&r));
    CHECK(!recover_selection(NULL,&stored,&l,&r));index=0;memcpy(career+0x14,&index,4);
    original_load=original_fixture;
    load_with_identity((void*)1,(void*)2,session);CHECK(forwarded==1 && forwarded_args[0]==(void*)1 && forwarded_args[1]==(void*)2 && forwarded_args[2]==session);
    CHECK(!memcmp(row,saved_row,sizeof(row)));
    /* New creation already has a full root: forwarding changes nothing. */
    primary=2208;memcpy(row+0x2B8,&primary,4);memcpy(saved_row,row,sizeof(row));
    load_with_identity((void*)3,(void*)4,session);CHECK(forwarded==2 && forwarded_args[0]==(void*)3 && forwarded_args[1]==(void*)4);
    CHECK(!memcmp(row,saved_row,sizeof(row)));
    fixture_exe=VirtualAlloc(NULL,0x06000000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    fixture_chain=VirtualAlloc(NULL,0x2D000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);CHECK(fixture_exe && fixture_chain);
    ((IMAGE_DOS_HEADER*)fixture_exe)->e_lfanew=0x100;nt=(IMAGE_NT_HEADERS64*)(fixture_exe+0x100);
    nt->FileHeader.Machine=IMAGE_FILE_MACHINE_AMD64;nt->FileHeader.TimeDateStamp=0x577DE45C;nt->OptionalHeader.SizeOfImage=0x06000000;
    ((IMAGE_DOS_HEADER*)fixture_chain)->e_lfanew=0x100;
    ((IMAGE_NT_HEADERS64*)(fixture_chain+0x100))->OptionalHeader.SizeOfImage=0x2D000;
    memcpy(fixture_chain+0x3DF0,"\x41\x57\x41\x56\x41\x55\x41\x54",8);
    for(i=0;i<61;i++) {
        BYTE *d=fixture_chain+0x239A0+i*72;uintptr_t target=(uintptr_t)(fixture_exe+0x1000+i*16);
        DWORD before=100,after=400;memcpy(d,&target,8);d[8]=4;memcpy(d+9,&before,4);memcpy(d+18,&after,4);memcpy((void*)target,&before,4);
    }
    for(i=0;i<2;i++) {
        const CounterSite *s=g_sites+i;BYTE *d=fixture_chain+0x239A0+s->slot*72;
        uintptr_t target=(uintptr_t)(fixture_exe+s->immediate_rva);DWORD actual=s->original_before+0x1000,seed=s->count-actual;
        memcpy(d,&target,8);memcpy(d+9,&s->original_before,4);memcpy(d+18,&s->original_after,4);
        fixture_exe[s->seed_rva]=s->seed_opcode;memcpy(fixture_exe+s->seed_rva+1,&seed,4);
        fixture_exe[s->instruction_rva]=0x8D;fixture_exe[s->instruction_rva+1]=s->lea_opcode;memcpy((void*)target,&actual,4);
    }
    image=fixture_exe;CHECK(!reload_code_ready());CHECK(!install_load_call());
    result=compat_worker(NULL);CHECK(!result && published==61 && count_applied(fixture_chain+0x239A0,fixture_exe,0x06000000)==61);
    published=0;CHECK(!compat_worker(NULL) && !published);
    for(i=0;i<2;i++)CHECK(get_u32(fixture_exe+g_sites[i].seed_rva+1)+get_u32(fixture_exe+g_sites[i].immediate_rva)==g_sites[i].count+300);
    memcpy(image+0x5B7AC4D,"\x89\x99\xD0\x8F\0\0\x89\x99\xD4\x8F\0\0",12);
    memcpy(image+0x5B74A1D,"\x8B\x99\xD4\x8F\0\0",6);
    memcpy(image+0x5AAFFF0,"\x48\x63\x41\x14\x83\xF8\xFF\x75\x03\x31\xC0\xC3\x48\x69\xC0\x18\x03\0\0\x48\x03\x41\x18\xC3",24);
    memcpy(image+LOAD_FUNCTION_RVA,"\x48\x89\x5C\x24\x08\x55\x57\x41\x54\x41\x56\x41",12);
    memcpy(image+0x4456307,"\xC7\x01\x14\0\0\0",6);memcpy(image+0x44575E7,"\xC7\x01\x79\0\0\0",6);
    memcpy(image+LOAD_CALL_RVA,"\xE8\x1A\x9B\xFF\xFF",5);CHECK(reload_code_ready());
    {DWORD mismatch=100;memcpy(image+0x1000,&mismatch,4);CHECK(!capacity_complete() && !install_load_call());
     mismatch=400;memcpy(image+0x1000,&mismatch,4);CHECK(capacity_complete());}
    {BYTE expected[16]={0xCC,0xB9,0x9A,0xFE,0x48,0x89,0xC1,0xE8,
        0x44,0x82,0xE8,0xFF,0xFF,0xC7,0x01,0xC5};
     BYTE after[16],object[0x24]={0};int value=42;int32_t delta;
     typedef int (*Getter)(void *);Getter guard;
     CHECK(!install_creation_guard());memcpy(image+0x5ABC370,expected,16);
     memcpy(image+0x59445C0,"\x8B\x41\x20\xC3",4);CHECK(install_creation_guard());
     memcpy(after,image+0x5ABC370,16);
     CHECK(!memcmp(after,expected,8) && !memcmp(after+12,expected+12,4));
     memcpy(&delta,after+8,4);guard=(Getter)(image+0x5ABC37C+delta);
     CHECK(guard(NULL)==0);memcpy(object+0x20,&value,4);CHECK(guard(object)==42);
     value=-1;memcpy(object+0x20,&value,4);CHECK(guard(object)==-1);
     CHECK(!install_creation_guard());}
    {BYTE before[8],after[8];int32_t delta;LoadFn relay;
     memcpy(before,image+LOAD_CALL_RVA-1,8);CHECK(install_load_call());memcpy(after,image+LOAD_CALL_RVA-1,8);
     CHECK(before[0]==after[0] && after[1]==0xE8 && before[6]==after[6] && before[7]==after[7]);
     memcpy(&delta,image+LOAD_CALL_RVA+1,4);relay=(LoadFn)(image+LOAD_CALL_RVA+5+delta);
     original_load=original_fixture;relay((void*)5,(void*)6,session);CHECK(forwarded==3 && forwarded_args[0]==(void*)5 && forwarded_args[1]==(void*)6 && forwarded_args[2]==session);
     CHECK(!install_load_call());}
    nt->FileHeader.TimeDateStamp=1;CHECK(compat_worker(NULL)==1);
    VirtualFree(competition,0,MEM_RELEASE);VirtualFree(fixture_exe,0,MEM_RELEASE);VirtualFree(fixture_chain,0,MEM_RELEASE);
    puts("PASS: dynamic catalog; cross-league v2 regression; collisions refused; career gate; future IDs; reload forwarding; no user-record writes; 61-site capacity gate; atomic CALL/relay ABI; unsupported build rejected.");
    return 0;
}
