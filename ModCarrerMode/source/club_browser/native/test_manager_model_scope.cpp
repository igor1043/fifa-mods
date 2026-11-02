#include "manager_model_scope.h"
#include <cassert>
#include <iostream>
using namespace managerModels;
int main(){
 const std::string text="S16MGR1\nschema=1\npid=5\ncreated=11\ncontext=1234\nepoch=2\nclub=1043\ndate=20261123\noperation=read\naccess_tick_ms=30\npath=\\\\?\\C:\\saves\\slot\\DATA\nbranch=b\ndigest=d\nrevision=r\nrow=1629|0\nrow=383|14\n";
 const std::string io="schema=3\npid=5\nprocess_created_100ns=11\ncomplete_file=1\nsave_type=SaveType_Career\noperation=read\naccess_tick_ms=30\npath=c:/saves/slot/data\n";
 Mapping m;Fields e;Scope s{5,11,1234,2,1043,20261123};assert(parse(text,m)&&fields(io,e)&&matches(m,s,e));assert(m.clubs.at(1629)==0&&m.clubs.at(383)==14);
 for(auto change:{"pid","created","context","epoch","club","date","access_tick_ms"}){auto stale=m;stale.owner[change]="999";assert(!matches(stale,s,e));}
 auto other=e;other["path"]="C:/saves/other/DATA";assert(!matches(m,s,other));other=e;other["operation"]="write";assert(!matches(m,s,other));other=e;other["access_tick_ms"]="31";assert(!matches(m,s,other));other=e;other["process_created_100ns"]="12";assert(!event(other,s));
 for(auto suffix:{"row=1629|14\n","pid=5\n","row=0|1\n","row=99|200001\n","row=99|-1\n","row=99|1|2\n"}){Mapping invalid;assert(!parse(text+suffix,invalid));}
 uint64_t n=0;assert(!number("18446744073709551616",n));assert(!number("-1",n));assert(!number("1x",n));std::cout<<"career model ownership, stale saves, duplicate/bounded rows: PASS\n";
}
