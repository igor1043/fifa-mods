#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace managerface {
// Read the installed font's real Windows family, not its file name. Patches
// often replace EA's font files with another family (for example Barlow).
inline std::wstring valueFontFamily(const std::vector<unsigned char>& data){
 if(data.size()<12||data.size()>4*1024*1024)return {};
 auto word=[&](size_t at){return unsigned(data[at])*256+data[at+1];};
 auto dword=[&](size_t at){return uint32_t(word(at))*65536+word(at+2);};
 unsigned tables=word(4);if(tables>256||12+size_t(tables)*16>data.size())return {};
 size_t name=0,length=0;
 for(unsigned i=0;i<tables;++i){size_t at=12+i*16;
  if(dword(at)==0x6e616d65){name=dword(at+8);length=dword(at+12);break;}}
 if(!name||length<6||name>data.size()||length>data.size()-name)return {};
 unsigned count=word(name+2),strings=word(name+4);
 if(6+size_t(count)*12>length||strings>length)return {};
 std::wstring best;int priority=-1;
 for(unsigned i=0;i<count;++i){size_t at=name+6+i*12;
  unsigned platform=word(at),encoding=word(at+2),language=word(at+4),id=word(at+6),size=word(at+8),offset=word(at+10);
  if(id!=1||!size||size>512||size_t(strings)+offset+size>length)continue;
  std::wstring family;int score=0;size_t text=name+strings+offset;
  if(platform==3&&(encoding==0||encoding==1||encoding==10)){
   if(size%2)continue;for(unsigned j=0;j<size;j+=2)family+=wchar_t(word(text+j));score=language==0x409?3:2;
  }else if(platform==1&&encoding==0){for(unsigned j=0;j<size;++j)if(data[text+j]<128)family+=wchar_t(data[text+j]);else{family.clear();break;}score=1;}
  if(!family.empty()&&family.size()<32&&family.find(wchar_t(0))==std::wstring::npos&&score>priority){best=family;priority=score;}
 }
 return best;
}
}
