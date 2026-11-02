#pragma once
#include <cstdint>
namespace room_medical {
inline int page(std::uint64_t ticks,int count,int bank,bool sequential){
 return count>0?static_cast<int>(((ticks/12000)*(sequential?1:2)+bank)%count):0;
}
}
