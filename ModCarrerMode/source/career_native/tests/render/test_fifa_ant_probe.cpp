/* Offline, read-only game resource investigation. Generated output goes to the
 * study directory, never to the game. This executable is not part of the DLL. */
#define NOMINMAX
#include "../../src/render/assets/fifa_player_assets.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <cctype>
using Bytes=std::vector<uint8_t>;
static uint32_t be32(const uint8_t*p){return uint32_t(p[0])<<24|uint32_t(p[1])<<16|uint32_t(p[2])<<8|p[3];}
static uint32_t le32(const uint8_t*p){return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static bool read_range(const std::string&path,size_t offset,size_t length,Bytes&out) {
    std::ifstream f(path,std::ios::binary);if(!f)return false;
    f.seekg(0,std::ios::end);auto end=f.tellg();
    if(end<0||offset>size_t(end)||length>size_t(end)-offset||length>512u*1024*1024)return false;
    f.seekg(offset);out.resize(length);return bool(f.read((char*)out.data(),length));
}
static bool decode(const Bytes&src,Bytes&out) {
    if(src.size()<32||memcmp(src.data(),"chunkref",8))return fifa_player::decode_container(src,out);
    size_t size=be32(src.data()+12),width=be32(src.data()+16),count=be32(src.data()+20),cursor=32;
    if(be32(src.data()+8)!=2||be32(src.data()+24)!=16||!size||size>512u*1024*1024||!width||width>1024*1024||
        !count||count>32768||count!=(size+width-1)/width)return false;
    out.clear();out.reserve(size);
    for(size_t i=0;i<count;++i) {
        /* The payload begins at a 16-byte boundary; its 8-byte header is
         * immediately before it. Padding is not guaranteed to be zero. */
        cursor=(cursor+7)&~size_t(7);if((cursor&15)!=8)cursor+=8;
        if(cursor+8>src.size())return false;
        size_t stored=be32(src.data()+cursor);uint32_t flag=be32(src.data()+cursor+4);cursor+=8;
        if(!stored||stored>src.size()-cursor||(flag!=2&&flag!=4)){printf("chunk %zu invalid stored=%zu flag=%u cursor=%zu\n",i,stored,flag,cursor);return false;}
        Bytes packed(src.begin()+cursor,src.begin()+cursor+stored),block;
        bool valid=flag==4?(block=std::move(packed),true):
            (packed.size()>=5&&packed[0]==0x10&&packed[1]==0xfb&&fifa_player::decode_container(packed,block));
        if(!valid||block.size()!=std::min(width,size-out.size())){
            printf("chunk %zu decode/range failed bytes=%zu expected=%zu packed=%zu\n",i,block.size(),std::min(width,size-out.size()),packed.size());return false;}
        out.insert(out.end(),block.begin(),block.end());cursor+=stored;
    }
    return out.size()==size;
}
static bool save(const std::string&path,const Bytes&b) {
    std::ofstream f(path,std::ios::binary);return bool(f.write((const char*)b.data(),b.size()));
}
static bool pose_name(const std::string&value) {
    std::string s=value;for(char&c:s)c=(char)std::tolower((unsigned char)c);
    for(const char*p:{"intro","lineup","line_up","photo","anthem","pose","presentation","teamshot","pre_match","prematch"})
        if(s.find(p)!=s.npos)return true;
    return false;
}
static bool inspect(const std::string&name,const Bytes&b,std::ofstream&report) {
    if(b.size()<16||memcmp(b.data(),"GD.STRM",7)||(b[7]!='b'&&b[7]!='l'))return false;
    auto read32=[&](const uint8_t*p,uint8_t endian){return endian=='b'?be32(p):le32(p);};
    if(read32(b.data()+8,b[7])!=b.size())return false;
    printf("%s unpacked=%zu\n",name.c_str(),b.size());report<<"RESOURCE "<<name<<" size="<<b.size()<<"\n";
    size_t blobs=0,hits=0;
    for(size_t i=16;i+12<=b.size();++i)if(!memcmp(b.data()+i,"GD.",3) &&
        (!memcmp(b.data()+i+3,"DATA",4)||!memcmp(b.data()+i+3,"REFL",4)) && (b[i+7]=='b'||b[i+7]=='l')) {
        size_t size=read32(b.data()+i+8,b[i+7]);
        if(size>=16&&size<=b.size()-i){++blobs;report<<"BLOB "<<std::string((char*)b.data()+i,8)<<" offset="<<i<<" size="<<size<<"\n";}
    }
    for(size_t i=0;i<b.size();) {
        size_t start=i;while(i<b.size()&&b[i]>=32&&b[i]<=126)++i;
        if(i-start>=5 && i-start<=256){std::string text((char*)b.data()+start,i-start);
            if(pose_name(text)){++hits;report<<"NAME offset="<<start<<" "<<text<<"\n";}}
        if(i==start)++i;
    }
    printf(" validated blobs=%zu presentation-name candidates=%zu\n",blobs,hits);
    return blobs>0;
}
int main(int argc,char**argv) {
    if(argc!=3)return 2;
    std::string root=argv[1],out=argv[2];std::filesystem::create_directories(out);
    std::ofstream report(out+"/animation_hits.txt");if(!report)return 3;
    for(const char*name:{"ant","common"}) {
        Bytes packed,decoded;std::string path=root+"/data/"+name+".cbac";
        auto size=std::filesystem::file_size(path);
        if(!read_range(path,0,size,packed)||!decode(packed,decoded)){printf("FAIL decoding %s\n",name);return 4;}
        if(!inspect(name,decoded,report)){printf("FAIL stream %s decoded=%zu header=",name,decoded.size());
            for(size_t i=0;i<std::min(size_t(32),decoded.size());++i)printf("%02x",decoded[i]);puts("");return 4;}
        if(!save(out+"/"+name+".unpacked.cba",decoded))return 4;
    }
    int found=0;
    for(const char*archive:{"data_front_end_extra.big","data_front_end.big"}) {
        std::string path=root+"/"+archive;Bytes header,index;
        if(!read_range(path,0,16,header))continue;
        if(memcmp(header.data(),"BIG4",4)&&memcmp(header.data(),"BIGF",4))continue;
        size_t count=be32(header.data()+8),end=be32(header.data()+12),cursor=16;
        if(end>8*1024*1024||count>200000||!read_range(path,0,end,index))return 5;
        for(size_t i=0;i<count && cursor+9<=index.size();++i) {
            size_t offset=be32(index.data()+cursor),length=be32(index.data()+cursor+4);cursor+=8;
            size_t start=cursor;while(cursor<index.size()&&index[cursor]&&cursor-start<2048)++cursor;
            if(cursor==index.size()||cursor-start==2048)return 6;
            std::string name((char*)index.data()+start,cursor-start);++cursor;
            if(name.find("data/ant/pc/niscbac/")!=0||std::filesystem::path(name).extension()!=".cbac")continue;
            Bytes packed,decoded;
            if(!read_range(path,offset,length,packed)||!decode(packed,decoded)||!inspect(name,decoded,report))return 7;
            if(!save(out+"/"+std::filesystem::path(name).filename().string(),decoded))return 8;
            ++found;
        }
    }
    printf("PASS: ant/common chunkref decoded; %d packaged CBAC streams recovered. No game files changed.\n",found);
    return found==25?0:9;
}
