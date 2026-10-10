#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static size_t queryCalls;
static SIZE_T WINAPI counted_query(LPCVOID address, PMEMORY_BASIC_INFORMATION info, SIZE_T length)
{
    ++queryCalls;
    return ::VirtualQuery(address, info, length);
}
#define VirtualQuery counted_query
#include "../mascot_goal_line.cpp"
#undef VirtualQuery

static unsigned int checks;
static void check(bool ok, const char* name)
{
    ++checks;
    if (!ok) { fprintf(stderr, "FAIL: %s\n", name); ExitProcess(1); }
}

// Original lookup, retained here to compare the real revised implementation.
static uintptr_t baseline_field(uintptr_t table, const char* key)
{
    unsigned char type, power; uintptr_t nodes;
    if (!get(table+8,type) || type!=5 || !get(table+11,power) || power>16 || !get(table+32,nodes)) return 0;
    const size_t length=strlen(key), count=(size_t)1<<power;
    for (size_t i=0;i<count;++i) {
        const uintptr_t node=nodes+i*40;
        int tag; uintptr_t value; size_t textLength;
        if (!get(node+24,tag)) return 0;
        if (tag!=4 || !get(node+16,value) || !get(value+16,textLength) ||
            textLength!=length || !readable(value+24,length)) continue;
        if (!memcmp((void*)(value+24),key,length)) return node;
    }
    return 0;
}

static unsigned int crowdPasses;
static void __fastcall original_crowd_mock(void*) { ++crowdPasses; }

int main()
{
    SYSTEM_INFO system{}; GetSystemInfo(&system);
    const size_t page=system.dwPageSize;
    unsigned char* protectedMemory=(unsigned char*)VirtualAlloc(nullptr,page*2,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    check(protectedMemory!=nullptr,"allocate safety fixture");
    MascotScopedMemoryReader reader;
    int value=0;
    check(reader.get((uintptr_t)protectedMemory,value),"read committed memory");
    check(!reader.readable(0,4) && !reader.readable(UINTPTR_MAX-1,4),"reject null and overflow");
    DWORD old;
    check(VirtualProtect(protectedMemory+page,page,PAGE_NOACCESS,&old)!=0,"protect fixture");
    // The prior range is deliberately stale: SEH must reject it and clear it.
    check(!reader.get((uintptr_t)(protectedMemory+page),value) && reader.rangeCount==0,"stale range cannot bypass guarded read");
    check(!reader.readable((uintptr_t)(protectedMemory+page-2),4),"reject cross-region read");
    MascotScopedMemoryReader nextReader;
    check(!nextReader.get((uintptr_t)(protectedMemory+page),value),"new scope retains no old ranges");
    VirtualFree(protectedMemory,0,MEM_RELEASE);

    unsigned char* table=(unsigned char*)VirtualAlloc(nullptr,131072,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    check(table!=nullptr,"allocate Lua fixture");
    table[8]=5; table[11]=10;
    const uintptr_t nodes=(uintptr_t)(table+128);
    memcpy(table+32,&nodes,8);
    for (size_t i=0;i<1024;++i) {
        const uintptr_t text=(uintptr_t)(table+50000+i*48);
        const size_t length=6;
        *(int*)(nodes+i*40+24)=4;
        memcpy((void*)(nodes+i*40+16),&text,8);
        memcpy((void*)(text+16),&length,8);
        memcpy((void*)(text+24),i==1023?"teamid":"unused",6);
    }
    const uintptr_t expected=nodes+1023*40;
    check(lua_table_field((uintptr_t)table,"teamid")==expected && baseline_field((uintptr_t)table,"teamid")==expected,"lookup result unchanged");
    check(!lua_table_field((uintptr_t)table,"absent"),"missing field returns zero");
    table[11]=17; check(!lua_table_field((uintptr_t)table,"teamid"),"reject malformed table size"); table[11]=10;
    check(!lua_table_field(0,"teamid"),"reject missing table");
    LARGE_INTEGER frequency,start,end; QueryPerformanceFrequency(&frequency);
    constexpr size_t iterations=500;
    queryCalls=0; QueryPerformanceCounter(&start);
    for(size_t i=0;i<iterations;++i) check(baseline_field((uintptr_t)table,"teamid")==expected,"baseline repeated lookup");
    QueryPerformanceCounter(&end);
    const double baselineUs=(double)(end.QuadPart-start.QuadPart)*1000000.0/frequency.QuadPart/iterations;
    const size_t baselineQueries=queryCalls/iterations;
    queryCalls=0; QueryPerformanceCounter(&start);
    for(size_t i=0;i<iterations;++i) check(lua_table_field((uintptr_t)table,"teamid")==expected,"revised repeated lookup");
    QueryPerformanceCounter(&end);
    const double revisedUs=(double)(end.QuadPart-start.QuadPart)*1000000.0/frequency.QuadPart/iterations;
    const size_t revisedQueries=queryCalls/iterations;
    check(revisedQueries<baselineQueries/100,"reduce Windows memory queries");
    VirtualFree(table,0,MEM_RELEASE);

    unsigned char records[40*0x50]{};
    for(size_t i=0;i<40;++i) records[i*0x50+0x42]=(unsigned char)(i%3);
    mascot_assign_one(records,40,7);
    size_t mascots=0;
    for(size_t i=0;i<40;++i) mascots+=records[i*0x50+0x42]==2;
    check(mascots==1 && records[7*0x50+0x42]==2,"one mascot only");
    check(mascot_assign_one(records,40,7)==0,"stable assignment has no writes");
    mascot_assign_none(records,40);
    mascots=0; for(size_t i=0;i<40;++i) mascots+=records[i*0x50+0x42]>=2;
    check(mascots==0,"missing mascot leaves ordinary photographers");
    const float origin[3]={1,2,3}; float target[3]; mascot_position_by_goal_line(origin,target);
    check(target[0]==-5850 && target[1]==2 && target[2]==3150,"approved position retained");

    MascotFrameContext frame{}; frame.home=999; queryCalls=0;
    mascot_animate_instance(frame);
    check(queryCalls==0 && !mascotAnimationEnabled,"unsupported club does no animation lookup");
    mascotOriginalCrowdAssignments=(uintptr_t)&original_crowd_mock;
    mascotLastAppliedBehavior=-1; mascotRequestedBehavior=-1; queryCalls=0;
    mascot_crowd_assignment_hook(nullptr);
    check(crowdPasses==1 && queryCalls==0,"inactive crowd hook directly passes through");
    frame.renderer=0x10000; frame.records=0x20000; frame.count=40;
    frame.home=1043; frame.packages=4; frame.generation=1; frame.mascotActive=true; frame.packageAnimated=true;
    wcscpy_s(gameDirectory,L"Z:\\__mascot_regression_missing_package__");
    mascot_animate_instance(frame);
    check(!mascotAnimationInitialized && !mascotAnimationEnabled,"missing model safely falls back");
    mascotInitAttemptTick=GetTickCount()-5;
    const DWORD attempted=mascotInitAttemptTick;
    mascot_animate_instance(frame);
    check(mascotInitAttemptTick==attempted,"retry does not repeat every frame");
    check(!mascotAnimationEnabled,"pending failed retry does not activate score watcher");
    ++frame.generation; mascot_animate_instance(frame);
    check(mascotInitAttemptGeneration==frame.generation,"resource generation allows immediate retry");
    check(!mascot_rx3_file_valid(L"Z:\\__mascot_regression_missing_package__\\model.rx3",false),"missing package guard");

    printf("{\"checks\":%u,\"fixture_hash_nodes\":1024,\"iterations\":%zu,\"baseline_queries_per_lookup\":%zu,\"revised_queries_per_lookup\":%zu,\"baseline_us_per_lookup\":%.3f,\"revised_us_per_lookup\":%.3f,\"in_game_fps_measured\":false}\n",
        checks,iterations,baselineQueries,revisedQueries,baselineUs,revisedUs);
    return 0;
}
