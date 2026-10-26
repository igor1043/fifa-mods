#include "room_scene_command.h"
#include <cassert>
#include <string>
#include <iostream>
int main(){
 using namespace room_command;Request request;Receipt receipt;
 auto wire=[](unsigned sequence,int code){return "S16ROOM2|1629|0123456789abcdef|"+std::to_string(sequence)+"|"+std::to_string(code)+"|ENDROOM";};
 for(int code=-3;code<128;++code){assert(parse(wire(7,code).c_str(),request));assert(request.club==1629&&request.sequence==7&&request.code==code);}
 for(const char*bad:{"","S16ROOM2|0|0123456789abcdef|1|0|ENDROOM","S16ROOM2|1629|wrong|1|0|ENDROOM",
 "S16ROOM2|1629|0123456789abcdef|0|0|ENDROOM","S16ROOM2|1629|0123456789abcdef|1|-4|ENDROOM",
 "S16ROOM2|1629|0123456789abcdef|1|128|ENDROOM","S16ROOM2|1629|0123456789abcdef|1|0|ENDROOM\n",
 "S16ROOM2|1629|0123456789abcdef|1|0|ENDROOMextra","S16ROOM2|99999999999999999999|0123456789abcdef|1|0|ENDROOM"})assert(!parse(bad,request));
 // Re-entering does not start another heap inventory or impose a time gate.
 for(unsigned entry=0;entry<6;++entry){
  assert(parse(wire(entry+1,2).c_str(),request));assert(receipt.accepts(request));receipt.commit(request);
  assert(!receipt.accepts(request));Request older=request;older.sequence=1;assert(!receipt.accepts(older));
 }
 Request different=request;different.club=1043;different.sequence=1;assert(receipt.accepts(different));
 different=request;different.nonce[0]='f';different.sequence=1;assert(receipt.accepts(different));
 std::cout<<"PASS direct scene commands: bounded parsing, scope, deduplication and six immediate re-entries\n";
}
