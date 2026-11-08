#include "native_animation.h"
#include <cassert>
#include <iostream>
int main(){
 auto folder=std::filesystem::temp_directory_path()/(L"mascot-ranges-"+std::to_wstring(GetCurrentProcessId()));std::filesystem::create_directories(folder);
 auto path=folder/L"animation.bin";
 {std::ofstream out(path,std::ios::binary);unsigned parts=1,count=32,player=0,slot=0,vertices=3;float seconds=8.4f;
 out.write("FFPVTX01",8);for(auto n:{parts,count,player})out.write((char*)&n,4);out.write((char*)&seconds,4);out.write((char*)&slot,4);out.write((char*)&vertices,4);std::vector<char>frames(32*3*20);out.write(frames.data(),frames.size());}
 {std::ofstream out(folder/L"variants.tsv");out<<"S16MASCOTCLIPS 1 2\n0 15 4.2\n16 31 4.2\n";}
 auto clip=clubanim::load(path,0);assert(clip&&clip->ranges.size()==2&&!clip->constant);
 clubanim::chooseCelebration(clip,1234);auto previous=clip->selectedRange;assert(previous<2);
 for(unsigned n=0;n<100;++n){clubanim::chooseCelebration(clip,1234+n);assert(clip->selectedRange<2&&clip->selectedRange!=previous);previous=clip->selectedRange;}
 clubanim::setPlaying(clip,true);assert(!clip->paused&&!clip->begun);clubanim::setPlaying(clip,false);assert(clip->paused&&!clip->begun);
 {std::ofstream out(folder/L"variants.tsv");out<<"S16MASCOTCLIPS 1 1\n0 99 4.2\n";}
 clip=clubanim::load(path,0);assert(clip&&clip->ranges.empty());assert(!clubanim::load(path,123));
 // Delete only the three exact files created above, never a recursive path.
 std::filesystem::remove(path);std::filesystem::remove(folder/L"variants.tsv");std::filesystem::remove(folder);
 std::cout<<"PASS bounded mascot ranges, random non-repeating choice, stop, malformed-metadata fallback\n";
}
