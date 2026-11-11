#include "room_light_probe.h"
#include <cassert>
#include <limits>
#include <iostream>
int main(){
 using namespace room_light_probe;
 Probe probe{{30,120,780,40},true};float matrix[16]{},sphere[4]{};for(unsigned i=0;i<4;++i)matrix[i*5]=1;
 matrix[12]=100000;matrix[13]=1000;
 assert(transform(probe,matrix,sphere));assert(sphere[0]==100030&&sphere[1]==1120&&sphere[2]==780&&sphere[3]==40);
 // A rotated/scaled instance needs its own world-space center and radius.
 matrix[0]=matrix[10]=0;matrix[2]=2;matrix[8]=-2;matrix[5]=2;
 assert(transform(probe,matrix,sphere));assert(sphere[0]==98440&&sphere[1]==1240&&sphere[2]==60&&sphere[3]==80);
 probe.valid=false;assert(!transform(probe,matrix,sphere));probe.valid=true;
 matrix[0]=std::numeric_limits<float>::quiet_NaN();assert(!transform(probe,matrix,sphere));
 const float nativeSphere[4]={100000,1000,530,1};
 const auto original=sample(nativeSphere);assert(original[3]==1);
 for(unsigned i=0;i<16;++i)matrix[i]=i%5==0?1.f:0.f;
 matrix[12]=100000;matrix[13]=1000;
 const auto local=sample(nativeSphere,&probe,matrix);
 assert(local[0]==100030&&local[1]==1120&&local[2]==780&&local[3]==40);
 assert(nativeSphere[0]==100000&&nativeSphere[1]==1000&&nativeSphere[2]==530&&nativeSphere[3]==1);
 matrix[0]=std::numeric_limits<float>::quiet_NaN();assert(sample(nativeSphere,&probe,matrix)==original);
 assert(sample(nativeSphere)==original); // Absent/invalid bounds never change the native query.
 std::cout<<"PASS per-submesh room light probe: baked center, world offset, rotation, scale and invalid input\n";
}
