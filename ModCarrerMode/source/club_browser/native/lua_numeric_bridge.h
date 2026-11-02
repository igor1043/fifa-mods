#pragma once
// Lua 5.1 x64 ABI: an owned C closure and one numeric return. Nothing is
// allocated by the plugin; Lua retains ownership of closure, stack and GC.
// Layouts verified against the 5.1 sources and an independently built VM.
#include <cstdint>
#include <cstring>
#include <cmath>
namespace managerLua {
struct Value{double number;int tag,pad;};
static_assert(sizeof(Value)==16,"Lua 5.1 x64 TValue");
template<class Read> int argument(uintptr_t L,Read read){
 uintptr_t first=0,top=0;Value v{};
 if(!read(L+0x18,&first,8)||!read(L+0x10,&top,8)||!first||top<first+16||top-first>65536||!read(first,&v,16)||v.tag!=3||!std::isfinite(v.number)||v.number<1||v.number>200000||std::floor(v.number)!=v.number)return 0;
 return int(v.number);
}
template<class Read,class Write> int result(uintptr_t L,int code,Read read,Write write){
 uintptr_t top=0,last=0,first=0;Value value{double(code),3,0};
 if(!read(L+0x10,&top,8)||!read(L+0x18,&first,8)||!read(L+0x38,&last,8)||!first||top<first||top>last||last-top<16||top-first>65536||((top-first)%16))return 0;
 auto next=top+16;if(!write(top,&value,sizeof value)||!write(L+0x10,&next,8))return 0;return 1;
}
template<class Read> uintptr_t ownedFunction(uintptr_t closure,Read read){
 unsigned char header[40]{};if(!read(closure,header,sizeof header)||header[8]!=6||header[10]!=1||header[11]!=3)return 0;
 // string.gmatch('', '') has three upvalues: the two empty strings and zero.
 Value values[3]{};if(!read(closure+40,values,sizeof values)||values[0].tag!=4||values[1].tag!=4||values[2].tag!=3||values[2].number!=0)return 0;
 for(int i=0;i<2;++i){uintptr_t string=0;std::memcpy(&string,&values[i],8);size_t length=1;if(!read(string+16,&length,8)||length)return 0;}
 uintptr_t fn=0;std::memcpy(&fn,header+32,8);return fn;
}
}
