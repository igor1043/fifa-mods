#pragma once
#include <filesystem>
#include <fstream>
#include <map>
#include <vector>
#include <string>
#include <cstring>
#include <cstdint>
#include "third_party/miniz/miniz_tinfl.h"

// Read the installed art in place. No extracted files or persistent image cache.
namespace clubassets {
using Bytes=std::vector<unsigned char>;
inline uint32_t be(const unsigned char* p){return uint32_t(p[0])<<24|uint32_t(p[1])<<16|uint32_t(p[2])<<8|p[3];}
inline uint32_t le(const unsigned char* p){return uint32_t(p[3])<<24|uint32_t(p[2])<<16|uint32_t(p[1])<<8|p[0];}
inline std::string normalized(std::string s){for(auto& c:s){if(c=='\\')c='/';if(c>='A'&&c<='Z')c+='a'-'A';}return s;}
inline Bytes refpack(const Bytes& in){
 if(in.size()<5||in[1]!=0xfb||(in[0]!=0x10&&in[0]!=0x90))return {};
 size_t n=(in[0]&0x80)?4:3,p=2+n,size=0;for(size_t i=2;i<p;++i)size=size*256+in[i];if(!size||size>32*1024*1024)return {};
 Bytes out;out.reserve(size);
 while(p<in.size()){
  unsigned a=in[p++],lit=0,copy=0,back=0;
  if(a<0x80){if(p>=in.size())return {};lit=a&3;copy=((a>>2)&7)+3;back=((a&0x60)<<3)+in[p++]+1;}
  else if(a<0xc0){if(p+2>in.size())return {};unsigned b=in[p++],c=in[p++];lit=b>>6;copy=(a&63)+4;back=((b&63)<<8)+c+1;}
  else if(a<0xe0){if(p+3>in.size())return {};unsigned b=in[p++],c=in[p++],d=in[p++];lit=a&3;copy=((a&12)<<6)+d+5;back=((a&16)<<12)+(b<<8)+c+1;}
  else if(a<0xfc)lit=((a&31)<<2)+4;else lit=a&3;
  if(p+lit>in.size()||out.size()+lit+copy>size)return {};out.insert(out.end(),in.begin()+p,in.begin()+p+lit);p+=lit;
  if(copy){if(!back||back>out.size())return {};for(unsigned i=0;i<copy;++i)out.push_back(out[out.size()-back]);}
  if(a>=0xfc)break;
 }
 return out.size()==size?out:Bytes{};
}
inline Bytes unpack(const Bytes& in){
 if(in.size()>=2&&in[1]==0xfb&&(in[0]==0x10||in[0]==0x90))return refpack(in);
 if(in.size()<40||(memcmp(in.data(),"chunkzip",8)&&memcmp(in.data(),"chunkref",8)))return in;
 const auto size=be(in.data()+12),width=be(in.data()+16),count=be(in.data()+20);bool ref=!memcmp(in.data(),"chunkref",8);
 if(be(in.data()+8)!=2||!size||size>32*1024*1024||!width||count!=(size+uint64_t(width)-1)/width)return {};
 Bytes out;out.reserve(size);size_t p=32;
 for(unsigned i=0;i<count;++i){
  if(ref){p=(p+7)&~size_t(7);if((p&15)!=8)p+=8;}else{p=(p+3)&~size_t(3);while(p+4<=in.size()&&!be(in.data()+p))p+=4;}
  if(p+8>in.size())return {};auto stored=be(in.data()+p),flag=be(in.data()+p+4);p+=8;if(!stored||p+stored>in.size())return {};
  size_t expected=(std::min)(size_t(width),size-out.size());Bytes decoded(expected);
  if(flag==1){if(tinfl_decompress_mem_to_mem(decoded.data(),decoded.size(),in.data()+p,stored,0)!=expected)return {};}
  else if(flag==2)decoded=refpack(Bytes(in.begin()+p,in.begin()+p+stored));
  else if(flag==4)decoded.assign(in.begin()+p,in.begin()+p+stored);else return {};
  if(decoded.size()!=expected)return {};out.insert(out.end(),decoded.begin(),decoded.end());p+=stored;
 }
 return out.size()==size?out:Bytes{};
}
struct Entry{std::filesystem::path file;uint64_t offset=0;uint32_t length=0;};
inline Bytes read(const Entry& e){if(!e.length||e.length>32*1024*1024)return {};std::ifstream f(e.file,std::ios::binary);if(!f)return {};f.seekg(0,std::ios::end);auto size=f.tellg();if(size<0||e.offset+e.length>uint64_t(size))return {};Bytes bytes(e.length);f.seekg(e.offset);return f.read(reinterpret_cast<char*>(bytes.data()),bytes.size())?unpack(bytes):Bytes{};}
struct Reader{
 std::filesystem::path game;std::map<std::string,Entry> index;
 void initialize(const std::filesystem::path& folder){game=folder;index.clear();
  for(const auto* archive:{L"data_patch.big",L"data_front_end.big",L"data_graphic1_extra.big",L"data_graphic2_extra.big",L"data_graphic3_extra.big",L"data_graphic1.big",L"data_graphic2.big",L"data_graphic3.big",L"data_front_end_extra.big",L"data_default.big"}){
   auto path=game/archive;std::ifstream f(path,std::ios::binary);unsigned char header[16]{};if(!f.read((char*)header,16)||(memcmp(header,"BIGF",4)&&memcmp(header,"BIG4",4)))continue;
   uint32_t count=be(header+8),size=be(header+12);if(count>200000||size<16||size>32*1024*1024)continue;Bytes table(size);f.seekg(0);if(!f.read((char*)table.data(),size))continue;size_t p=16;
   for(unsigned i=0;i<count&&p+9<=table.size();++i){auto offset=be(table.data()+p),length=be(table.data()+p+4);p+=8;auto end=p;while(end<table.size()&&table[end])++end;if(end==table.size())break;auto name=normalized(std::string((char*)table.data()+p,end-p));p=end+1;
    if(name.find("data/ui/")==0&&(name.find("/crest/")!=std::string::npos||name.find("/league/")!=std::string::npos||name.find("/flags512x512/")!=std::string::npos||name.find("/countryflags/")!=std::string::npos||name.find("/careercompetitionicons/")!=std::string::npos))index.emplace(name,Entry{path,offset,length});
   }
  }
 }
 Bytes asset(const std::string& name)const{auto relative=normalized(name);if(relative.find("..")!=std::string::npos||relative.find(':')!=std::string::npos||relative.empty()||relative[0]=='/')return {};auto path=game/std::filesystem::path(relative);std::error_code ec;auto size=std::filesystem::file_size(path,ec);if(!ec&&size<=32*1024*1024)return read({path,0,uint32_t(size)});auto it=index.find(relative);return it==index.end()?Bytes{}:read(it->second);}
};
inline Bytes texture(Bytes bytes){
 if(bytes.size()<16||(memcmp(bytes.data(),"BIGF",4)&&memcmp(bytes.data(),"BIG4",4)))return bytes;
 auto count=be(bytes.data()+8),header=be(bytes.data()+12);if(count>10000||header>bytes.size())return {};size_t p=16;
 for(unsigned i=0;i<count&&p+9<=header;++i){auto offset=be(bytes.data()+p),length=be(bytes.data()+p+4);p+=8;while(p<header&&bytes[p])++p;++p;if(uint64_t(offset)+length>bytes.size())return {};auto data=unpack(Bytes(bytes.begin()+offset,bytes.begin()+offset+length));if(data.size()>128&&!memcmp(data.data(),"DDS ",4))return data;}
 return {};
}
}
