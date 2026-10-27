#include <windows.h>
#include <cassert>
#include <iostream>
#include <cstring>
#include "native_animation.h"
int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);assert(argc==3);auto path=std::filesystem::path(argv[1]);std::ifstream header(path,std::ios::binary);header.seekg(16);unsigned player=0;header.read((char*)&player,4);assert(header);auto clip=clubanim::load(path,player);assert(clip);unsigned verified=0;
 for(auto&t:clip->tracks){auto file=std::filesystem::path(argv[2])/(L"sample_"+std::to_wstring(verified)+L".bin");std::ifstream in(file,std::ios::binary);assert(in);std::vector<unsigned char>bytes((std::istreambuf_iterator<char>(in)),{});assert(bytes.size()==size_t(t.vertices)*28);assert(t.expandedInitial==bytes);assert(clubanim::range(t,bytes.data(),bytes.size(),28)==0);++verified;}
 assert(verified>=8);std::cout<<"PASS live FIFA GPU layout: "<<verified<<" complete meshes match exactly; half positions, expanded normals/tangents, truncation and UVs\n";
}
