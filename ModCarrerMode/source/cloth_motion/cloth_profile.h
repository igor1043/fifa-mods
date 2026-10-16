#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace cloth_motion {
enum class Garment : unsigned { Other,Jersey,Shorts };
// FIFA 16 x64's original parameter block is forwarded without modification.
struct Parameters {
    unsigned char bytes[0x78]{};
    float number(size_t at)const{float v;std::memcpy(&v,bytes+at,4);return v;}
    void number(size_t at,float v){std::memcpy(bytes+at,&v,4);}
};
static_assert(sizeof(Parameters)==0x78,"native parameter size");
constexpr size_t Damping=0x30,Fold=0x2c,AnchorFactor=0x40;
inline bool contains(const char* value,const char* search) {
    if(!value)return false;
    for(size_t i=0;value[i];++i) {
        size_t j=0;
        for(;search[j]&&value[i+j];++j) {
            char c=value[i+j];if(c>='A'&&c<='Z')c=char(c-'A'+'a');
            if(c!=search[j])break;
        }
        if(!search[j])return true;
    }
    return false;
}
inline Garment garment(const char* name) {
    if(contains(name,"hair"))return Garment::Other;
    if(contains(name,"jersey"))return Garment::Jersey;
    if(contains(name,"shorts"))return Garment::Shorts;
    return Garment::Other;
}
}
