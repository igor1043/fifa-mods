/* Inspect the self-describing layout of recovered FIFA GenericData banks.
 * This offline tool has no connection to the running game. */
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>
using Bytes=std::vector<uint8_t>;
static uint32_t u32(const uint8_t*p){return uint32_t(p[0])<<24|uint32_t(p[1])<<16|uint32_t(p[2])<<8|p[3];}
static uint64_t u64(const uint8_t*p){return uint64_t(u32(p))<<32|u32(p+4);}
static bool span(size_t p,size_t n,size_t end){return p<=end&&n<=end-p;}
static std::string str(const Bytes&b,size_t pos,size_t end) {
    if(pos>=end)return {};size_t i=pos;while(i<end&&b[i]&&i-pos<512)++i;
    if(i==end||i-pos==512)return {};return {(const char*)b.data()+pos,i-pos};
}
struct Field {uint32_t type,size,offset;uint16_t count,flags;std::string name;};
struct Layout {uint32_t hash,size;std::string name;std::vector<Field>fields;};
static bool layouts(const Bytes&b,std::unordered_map<uint32_t,Layout>&out,std::ofstream&report) {
    size_t base=32;if(b.size()<base+8||memcmp(b.data()+16,"GD.REFLb",8))return false;
    size_t end=16+u32(b.data()+24);if(end>b.size())return false;
    size_t count=(size_t)u64(b.data()+base);if(count>10000||!span(base+8,count*8,end))return false;
    for(size_t i=0;i<count;++i) {
        size_t pos=base+(size_t)u64(b.data()+base+8+i*8);if(!span(pos,32,end))return false;
        int32_t min=(int32_t)u32(b.data()+pos),max=(int32_t)u32(b.data()+pos+4);
        size_t n=max>=min?size_t(max)-min+1:0;
        size_t strings=pos+u32(b.data()+pos+16),length=u32(b.data()+pos+20);
        if(n>10000||!span(pos+32,n*32,end)||!span(strings,length,end))return false;
        Layout l;l.hash=u32(b.data()+pos+28);l.size=u32(b.data()+pos+8);l.name=str(b,strings+1,strings+length);
        if(l.name.empty())return false;
        for(size_t j=0;j<n;++j){const uint8_t*p=b.data()+pos+32+j*32;
            Field f={u32(p),u32(p+4),u32(p+8),uint16_t(p[16]*256+p[17]),uint16_t(p[18]*256+p[19]),
                str(b,strings+u32(p+12),strings+length)};
            if(f.name.empty()||f.offset>l.size)return false;l.fields.push_back(f);}
        report<<"LAYOUT "<<l.name<<" hash="<<l.hash<<" size="<<l.size<<"\n";
        for(const auto&f:l.fields)report<<" FIELD "<<f.name<<" offset="<<f.offset<<" type="<<f.type<<" element="<<f.size<<" count="<<f.count<<" flags="<<f.flags<<"\n";
        out.emplace(l.hash,std::move(l));
    }
    return true;
}
static bool read(const std::filesystem::path&path,Bytes&b) {
    auto size=std::filesystem::file_size(path);if(size>512u*1024*1024)return false;
    std::ifstream f(path,std::ios::binary);b.resize(size);return bool(f.read((char*)b.data(),b.size()));
}
int main(int argc,char**argv) {
    if(argc!=2)return 2;std::filesystem::path dir(argv[1]);std::ofstream report(dir/"layout_objects.txt");
    for(const auto&entry:std::filesystem::directory_iterator(dir)) {
        if(entry.path().extension()!=".cba"&&entry.path().extension()!=".cbac")continue;
        Bytes b;if(!read(entry.path(),b))return 3;
        std::unordered_map<uint32_t,Layout>map;report<<"RESOURCE "<<entry.path().filename().string()<<"\n";
        if(!layouts(b,map,report)){printf("FAIL reflection %s\n",entry.path().filename().string().c_str());return 4;}
        size_t pos=16+u32(b.data()+24),objects=0,named=0;
        while(span(pos,16,b.size())) {
            if(memcmp(b.data()+pos,"GD.DATAb",8))return 5;
            size_t size=u32(b.data()+pos+8),end=pos+size;
            if(size<48||!span(pos,size,b.size()))return 6;
            size_t generic=pos+16;uint32_t hash=(uint32_t)u64(b.data()+generic+16);
            auto type=map.find(hash);
            if(type!=map.end()) {
                ++objects;const auto&l=type->second;std::string name;
                for(const auto&f:l.fields)if(f.name=="__name"&&f.type==17) {
                    for(size_t fieldBase:{generic,generic+32}) {
                        size_t at=fieldBase+f.offset;if(!span(at,16,end))continue;
                        size_t count=u32(b.data()+at+4),off=(size_t)u64(b.data()+at+8);
                        if(!count||count>512)continue;
                        for(size_t offsetBase:{generic,fieldBase,pos})if(span(offsetBase+off,count,end)) {
                            auto value=str(b,offsetBase+off,offsetBase+off+count);
                            if(value.size()+1==count){name=value;break;}
                        }
                        if(!name.empty())break;
                    }
                }
                if(!name.empty()) {
                    ++named;report<<"OBJECT offset="<<pos<<" type="<<l.name<<" name="<<name<<"\n";
                    if(l.name=="AnimationAsset"||l.name=="DctAnimationAsset"||l.name=="ClipControllerAsset"||l.name=="ChannelToDofAsset"){
                        for(const auto&f:l.fields) {
                            size_t at=generic+f.offset;
                            report<<" VALUE "<<f.name<<" at="<<at<<" bytes=";
                            for(size_t j=0;j<std::min(size_t(16),size_t(f.size));++j)if(span(at+j,1,end)) {
                                char hex[3];sprintf_s(hex,"%02x",b[at+j]);report<<hex;}
                            report<<"\n";
                        }
                    }
                }
            }
            pos=end;
        }
        printf("%s layouts=%zu objects=%zu named=%zu\n",entry.path().filename().string().c_str(),map.size(),objects,named);
    }
    return 0;
}
