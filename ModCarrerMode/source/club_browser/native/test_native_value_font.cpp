#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "native_value_font.h"
#include <fstream>
#include <filesystem>
#include <cassert>
#include <iostream>
int wmain(int argc,wchar_t**argv){
 assert(argc==2);std::ifstream in(std::filesystem::path(argv[1]),std::ios::binary);
 std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),{});
 auto family=managerface::valueFontFamily(bytes);assert(!family.empty());
 assert(managerface::valueFontFamily({}).empty());
 auto shortFont=bytes;shortFont.resize(11);assert(managerface::valueFontFamily(shortFont).empty());
 auto bad=bytes;bad[4]=255;bad[5]=255;assert(managerface::valueFontFamily(bad).empty());
 assert(AddFontResourceExW(argv[1],FR_PRIVATE,nullptr)>0);
 auto dc=CreateCompatibleDC(nullptr);auto font=CreateFontW(-25,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,family.c_str());
 auto previous=SelectObject(dc,font);wchar_t actual[64]{};assert(GetTextFaceW(dc,64,actual)>0);
 assert(_wcsicmp(actual,family.c_str())==0);
 SelectObject(dc,previous);DeleteObject(font);DeleteDC(dc);RemoveFontResourceExW(argv[1],FR_PRIVATE,nullptr);
 std::wcout<<L"PASS installed native value font family: "<<family<<L"\n";
}
