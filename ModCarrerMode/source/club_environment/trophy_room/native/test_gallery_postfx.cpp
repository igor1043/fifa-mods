#include "gallery_postfx.h"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
 assert(gallery_postfx::testMode("S16GALLERYTEST 1 42 1",42)==1);
 for(auto text:{"S16GALLERYTEST 1 41 1","S16GALLERYTEST 2 42 1","S16GALLERYTEST 1 42 5","S16GALLERYTEST 1 42 1 extra",""})assert(!gallery_postfx::testMode(text,42));
 assert(!gallery_postfx::bridge(1)&&!gallery_postfx::bridge(3)&&gallery_postfx::bridge(0));
 assert(!gallery_postfx::optics(2)&&!gallery_postfx::optics(3)&&gallery_postfx::optics(0));
 gallery_postfx::Lease lease;unsigned count=0;std::ofstream out;
 if(argc>1)out.open(argv[1]);
 auto execute=[&](const char*s){++count;if(out)out<<s<<"\n-- NEXT\n";return true;};
 lease.update(true,1000,execute);lease.update(true,1499,execute);assert(count==1);
 lease.update(true,1500,execute);assert(count==2);
 lease.update(false,1501,execute);lease.update(false,3000,execute);assert(count==3);
 std::cout<<"PASS camera post-effects lease: bounded refresh, process isolation, scoped comparison and restoration\n";
}
