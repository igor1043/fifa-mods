// Build against unmodified official Lua 5.1 x64 sources, outside the game.
#include <windows.h>
#include <cassert>
#include <cstddef>
#include <iostream>
#include <string>
#include "lua_numeric_bridge.h"
extern "C" {
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "lstate.h"
}
bool read(uintptr_t at,void* out,size_t n){if(at<0x10000)return false;__try{memcpy(out,(void*)at,n);return true;}__except(1){return false;}}
bool write(uintptr_t at,const void* in,size_t n){__try{memcpy((void*)at,in,n);return true;}__except(1){return false;}}
int selected=0;
int callback(lua_State* L){int club=managerLua::argument(uintptr_t(L),read);return managerLua::result(uintptr_t(L),club?selected:0,read,write);}
int main(){
 static_assert(offsetof(lua_State,top)==0x10&&offsetof(lua_State,base)==0x18&&offsetof(lua_State,stack_last)==0x38&&offsetof(lua_State,l_gt)==0x78,"FIFA Lua ABI");
 static_assert(offsetof(CClosure,f)==32&&offsetof(CClosure,upvalue)==40&&sizeof(TValue)==16,"FIFA closure ABI");
 auto L=luaL_newstate();luaL_openlibs(L);assert(!luaL_dostring(L,"FIFA16_Career_Manager_Asset=string.gmatch('', '')"));lua_getglobal(L,"FIFA16_Career_Manager_Asset");auto closure=uintptr_t(lua_topointer(L,-1));auto original=managerLua::ownedFunction(closure,read);assert(original&&original==uintptr_t(clvalue(L->top-1)->c.f));
 assert(InterlockedCompareExchangePointer((void*volatile*)(closure+32),(void*)&callback,(void*)original)==(void*)original);lua_settop(L,0);
 for(int code:{-1,0,1,14,20}){selected=code;auto script="assert(FIFA16_Career_Manager_Asset(1629)=="+std::to_string(code)+")";assert(!luaL_dostring(L,script.c_str()));}
 assert(!luaL_dostring(L,"assert(FIFA16_Career_Manager_Asset()==0);assert(FIFA16_Career_Manager_Asset('1629')==0);assert(FIFA16_Career_Manager_Asset(0/0)==0);assert(FIFA16_Career_Manager_Asset(2.5)==0);assert(FIFA16_Career_Manager_Asset(200001)==0);local f=string.gmatch('abc','.') assert(f()=='a' and f()=='b' and f()=='c');collectgarbage('collect');assert(FIFA16_Career_Manager_Asset(1)==20)"));
 // Guard rejects borrowed/non-C closures and invalid stack states.
 assert(!luaL_dostring(L,"other=function()end"));lua_getglobal(L,"other");assert(!managerLua::ownedFunction(uintptr_t(lua_topointer(L,-1)),read));lua_pop(L,1);
 lua_close(L);std::cout<<"Real Lua 5.1 ABI, owned closure, numeric callbacks, GC and library isolation: PASS\n";
}
