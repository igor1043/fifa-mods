#include "var_cabin.cpp"
#include <assert.h>

struct TestString{unsigned char header[16]{};size_t length=0;char text[64]{};};
struct TestTable{
    alignas(8) unsigned char data[64]{};
    TestTable(LuaNode* nodes,unsigned char power,LuaValue* array=nullptr,int size=0){
        data[8]=5;data[11]=power;
        uintptr_t p=(uintptr_t)nodes;memcpy(data+32,&p,8);
        p=(uintptr_t)array;memcpy(data+24,&p,8);memcpy(data+56,&size,4);
    }
};
static LuaValue tableValue(TestTable& table){return {(uint64_t)(uintptr_t)table.data,5,0};}
static LuaValue numberValue(double value){LuaValue out{};out.tag=3;memcpy(&out.bits,&value,8);return out;}
static void stringKey(LuaNode& node,TestString& key,const char* text){
    key.length=strlen(text);strcpy_s(key.text,text);node.key={(uint64_t)(uintptr_t)&key,4,0};
}
int main(){
    // Exercise the native reader against the exact x64 Lua array/hash layout.
    LuaNode rowNodes[2]{},sleNodes[1]{},dbNodes[1]{},globalNodes[1]{};
    TestString idKey,ownedKey,sleKey,dbKey;
    stringKey(rowNodes[0],idKey,"varCabinCompetitionId");
    stringKey(rowNodes[1],ownedKey,"isVarCabin");rowNodes[1].value=numberValue(1);
    TestTable row(rowNodes,1);LuaValue array[64]{};array[40]=tableValue(row);
    TestTable sles(sleNodes,0,array,64),db(dbNodes,0),globals(globalNodes,0);
    stringKey(dbNodes[0],sleKey,"sle");dbNodes[0].value=tableValue(sles);
    stringKey(globalNodes[0],dbKey,"db");globalNodes[0].value=tableValue(db);
    alignas(8) unsigned char lua[0x90]{};uintptr_t globalPtr=(uintptr_t)globals.data;
    memcpy(lua+0x78,&globalPtr,8);int tag=5;memcpy(lua+0x80,&tag,4);
    void* fake=VirtualAlloc(nullptr,0x3615000,MEM_RESERVE,PAGE_NOACCESS);assert(fake);
    image=(uintptr_t)fake;
    assert(VirtualAlloc((void*)(image+0x3613000),4096,MEM_COMMIT,PAGE_READWRITE));
    uintptr_t luaPtr=(uintptr_t)lua;memcpy((void*)(image+0x3613fd0),&luaPtr,8);

    for(int id=-1;id<=2500;++id){
        rowNodes[0].value=numberValue(id);
        assert(readCompetition(41)==id);
        assert(competitionAllowed(readCompetition(41))==(id==7||id==83));
    }
    // Allowed -> disallowed -> other allowed must not retain the old state.
    const int transitions[]={7,-1,83,350,7,351,83,101,31,29,0};
    for(int id:transitions){
        rowNodes[0].value=numberValue(id);assert(readCompetition(41)==id);
    }
    rowNodes[0].value=numberValue(7.5);assert(readCompetition(41)==-1);
    rowNodes[0].value=numberValue(1e100);assert(readCompetition(41)==-1);
    rowNodes[0].value=numberValue(7);rowNodes[0].value.tag=4;assert(readCompetition(41)==-1);
    rowNodes[0].value=numberValue(7);rowNodes[1].value=numberValue(0);assert(readCompetition(41)==-1);
    rowNodes[1].value=numberValue(1);assert(readCompetition(40)==-1&&readCompetition(176)==-1);
    // RNA index zero lives in the numeric hash portion of a Lua table.
    sleNodes[0].key=numberValue(0);sleNodes[0].value=tableValue(row);
    assert(readCompetition(0)==7);
    sles.data[11]=17;assert(readCompetition(0)==-1);sles.data[11]=0;
    globalNodes[0].value.tag=0;assert(readCompetition(41)==-1);globalNodes[0].value=tableValue(db);
    globals.data[8]=0;assert(readCompetition(41)==-1);globals.data[8]=5;
    assert(VirtualFree(fake,0,MEM_RELEASE));image=0;
    puts("PASS native competition reader: only 7/83, context transitions, malformed/missing data, array/hash rows");
    return 0;
}
