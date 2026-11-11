#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <cassert>
#include "graphics.h"
#include "manager_face_model.h"
int wmain(int argc,wchar_t** argv){
 if(argc!=3)return 2;
 assert(SUCCEEDED(CoInitializeEx(nullptr,COINIT_MULTITHREADED)));
 ID3D11Device* device=nullptr;ID3D11DeviceContext* context=nullptr;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context)));
 std::ifstream source(argv[2],std::ios::binary);std::vector<managerface::Choice> rows;assert(managerface::load(source,rows));
 const std::filesystem::path game=argv[1];clubassets::Reader art;art.initialize(game);int photos=0,crests=0;
 for(const auto& row:rows){
  if(!row.asset)continue;clubgfx::Texture image;
  const auto path=game/L"ModCarrerMode/data/manager_market"/std::filesystem::u8path(row.image);
  assert(clubgfx::image(device,image,path.wstring())&&image.view&&image.w&&image.h);++photos;image.clear();
  if(row.club){auto id=std::to_string(row.club);assert(clubgfx::gameImage(device,image,art,{"data/ui/imgAssets/crest/light/l"+id+".dds","data/ui/imgAssets/crest/dark/l"+id+".dds"}));++crests;image.clear();}
 }
 clubgfx::release(context);clubgfx::release(device);CoUninitialize();std::cout<<"PASS: "<<photos<<" real coach portraits and "<<crests<<" club crests decoded and uploaded\n";
}
