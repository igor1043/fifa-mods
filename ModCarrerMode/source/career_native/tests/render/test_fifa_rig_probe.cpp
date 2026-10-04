/* Read-only resource inventory, never calls a FIFA actor/animation function. */
#define NOMINMAX
#include "../../src/render/assets/fifa_player_assets.h"
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <algorithm>
#include <cmath>
static uint32_t le(const uint8_t*p){return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static bool validate_skeleton(const std::vector<uint8_t>&b) {
    if(b.size()<16||memcmp(b.data(),"RX3l",4))return false;
    size_t count=le(b.data()+12),matrices=0,parents=0,names=0,bones=0;
    if(count>2048||16+count*16>b.size())return false;
    for(size_t i=0;i<count;++i) {
        const uint8_t*p=b.data()+16+i*16;size_t off=le(p+4),size=le(p+8);
        if(off>b.size()||size>b.size()-off||size<16)return false;
        size_t n=le(b.data()+off+4);if(!n||n>2048)return false;
        if(bones&&bones!=n)return false;bones=n;
        switch(le(p)) {
        case 0xdf9aec1e:
            if(size!=16+n*64)return false;matrices=off;
            for(size_t j=0;j<n*16;++j){float f;memcpy(&f,b.data()+off+16+j*4,4);if(!std::isfinite(f))return false;}
            break;
        case 0x70278fee:
            if(size<16+n*2)return false;parents=off;
            for(size_t j=0;j<n;++j){const auto*q=b.data()+off+16+j*2;unsigned parent=q[0]|unsigned(q[1])<<8;
                if(parent!=0xffff&&parent>=j)return false;}
            break;
        case 0x4c9b9eb2:
            names=off;{
                size_t cursor=off+16,end=off+size;
                for(size_t j=0;j<n;++j){if(cursor>end||end-cursor<8)return false;
                    size_t length=le(b.data()+cursor+4);cursor+=8;
                    if(!length||length>1024||length>end-cursor||b[cursor+length-1])return false;
                    cursor+=length;}
            }break;
        default:return false;
        }
    }
    printf(" VALIDATED skeleton bones=%zu finite matrices; parent hierarchy and names bounded\n",bones);
    return matrices&&parents&&names&&(bones==400||bones==82);
}
int main(int argc,char**argv) {
    if(argc!=3)return 2;fifa_player::Assets assets(argv[1]);std::filesystem::create_directories(argv[2]);int found=0;
    for(const auto &path:{"data/sceneassets/rig/skeleton_player.rx3","data/sceneassets/rig/skeleton_ant.rx3",
        "data/sceneassets/rigamate/player_rigamate_body_lod0_male.rbo",
        "data/sceneassets/rigamate/player_rigamate_face_male.rbo",
        "data/sceneassets/presentation/presentation_1.rx3"}) {
        std::vector<uint8_t>b;
        if(!assets.read(path,b)){printf("MISSING %s\n",path);continue;}
        if(strstr(path,"/rig/skeleton_")&&!validate_skeleton(b))return 5;
        printf("RESOURCE %s decoded=%zu header=",path,b.size());
        for(size_t i=0;i<std::min(size_t(32),b.size());++i)printf("%02x",b[i]);puts("");
        std::string target=std::string(argv[2])+"/"+std::filesystem::path(path).filename().string();FILE*f=nullptr;
        if(fopen_s(&f,target.c_str(),"wb")||!f)return 3;fwrite(b.data(),1,b.size(),f);fclose(f);++found;
        if(b.size()>=16 && !memcmp(b.data(),"RX3l",4)) {
            size_t count=le(b.data()+12);if(count>2048||16+16*count>b.size())return 4;
            for(size_t i=0;i<count;++i){auto p=b.data()+16+i*16;size_t off=le(p+4),len=le(p+8);
                printf(" section %08x offset=%zu size=%zu",le(p),off,len);
                if(off<=b.size()&&len<=b.size()-off){printf(" prefix=");for(size_t j=0;j<std::min(size_t(32),len);++j)printf("%02x",b[off+j]);}puts("");}
        }
        printf(" ASCII labels:");size_t words=0;
        for(size_t i=0;i<b.size()&&words<60;) {
            size_t start=i;while(i<b.size() && ((b[i]>='A'&&b[i]<='Z')||(b[i]>='a'&&b[i]<='z')||b[i]=='_'||b[i]==' '))++i;
            if(i-start>=5&&i-start<90){printf(" [%.*s]",(int)(i-start),(const char*)b.data()+start);++words;}if(i==start)++i;
        }puts("");
    }
    printf("Recovered %d resources. Skeleton/resource presence is NOT native animation playback.\n",found);
    return found>=4?0:1;
}
