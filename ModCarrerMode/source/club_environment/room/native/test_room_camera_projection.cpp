#include <cassert>
#include <limits>
#include <iostream>
#include <cstring>
#include "room_camera_projection.h"
int main(){
 using room_projection::nearPlane;
 assert(nearPlane(82.92582f,100000.f)==5.f);
 assert(nearPlane(2.f,100000.f)==2.f);
 assert(nearPlane(0.f,100000.f)==0.f);
 assert(nearPlane(80.f,0.f)==80.f);
 assert(nearPlane(80.f,50.f)==80.f);
 assert(nearPlane(80.f,std::numeric_limits<float>::infinity())==80.f);
 assert(std::isnan(nearPlane(std::numeric_limits<float>::quiet_NaN(),100000.f)));
 for(auto range:room_projection::ownedRanges){
  assert(!(range[0]<=0x50&&range[0]+range[1]>0x50));
  assert(!(range[0]<=0x54&&range[0]+range[1]>0x54));
 }
 unsigned char memory[0xd0]{};auto address=(uintptr_t)memory;auto clip=(float*)(memory+0x90),farPlane=(float*)(memory+0x94);*clip=82.92582f;*farPlane=100000;
 unsigned reads=0;auto read=[&](uintptr_t p,void*out,size_t n){++reads;assert(p>=address&&p+n<=address+sizeof memory);memcpy(out,(void*)p,n);return true;};
 auto write=[&](uintptr_t p,const void*in,size_t n){assert(p>=address&&p+n<=address+sizeof memory);memcpy((void*)p,in,n);return true;};
 room_projection::BorrowedNear owner;
 for(int i=0;i<120;++i){assert(owner.apply(address,read,write));assert(*clip==5&&*farPlane==100000);}
 owner.restore(address,read,write);assert(*clip==82.92582f&&*farPlane==100000);
 owner.apply(address,read,write);*clip=11;owner.restore(address,read,write);assert(*clip==11); // native owner wins
 owner.apply(address,read,write);auto before=reads;owner.restore(0,read,write);assert(reads==before&&owner.scene==0); // stale scene never read
 *clip=2;owner.apply(address,read,write);assert(*clip==2);owner.restore(address,read,write);assert(*clip==2);
 *clip=0;assert(!owner.apply(address,read,write));assert(owner.scene==0);
 std::cout<<"PASS room projection: all room views share 5 cm clipping; repeated applies preserve baseline; native ownership/scene change respected; far plane untouched\n";
}
