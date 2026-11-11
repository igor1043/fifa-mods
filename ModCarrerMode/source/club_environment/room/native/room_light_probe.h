#pragma once
#include <array>
#include <cmath>
#include <algorithm>

namespace room_light_probe {
struct Probe {std::array<float,4> local{0,0,0,1};bool valid=false;};
inline bool transform(const Probe& probe,const float* matrix,float* sphere){
 if(!probe.valid||!matrix||!sphere)return false;
 for(unsigned i=0;i<16;++i)if(!std::isfinite(matrix[i]))return false;
 for(unsigned axis=0;axis<3;++axis)
  sphere[axis]=matrix[12+axis]+probe.local[0]*matrix[axis]+probe.local[1]*matrix[4+axis]+probe.local[2]*matrix[8+axis];
 float scale=0;
 for(unsigned row=0;row<3;++row){float length=0;for(unsigned c=0;c<3;++c)length+=matrix[row*4+c]*matrix[row*4+c];scale=std::max(scale,std::sqrt(length));}
 sphere[3]=probe.local[3]*scale;
 return std::isfinite(sphere[0])&&std::isfinite(sphere[1])&&std::isfinite(sphere[2])&&std::isfinite(sphere[3]);
}
// FIFA's environment query expects the original instance float4, including W.
// Geometry bounds belong only to our local spotlight calculation.
inline std::array<float,4> sample(const float* nativeSphere,const Probe* probe=nullptr,const float* matrix=nullptr){
 std::array<float,4> result{};std::copy_n(nativeSphere,4,result.begin());
 if(probe&&matrix){std::array<float,4> transformed{};if(transform(*probe,matrix,transformed.data()))result=transformed;}
 return result;
}
}
