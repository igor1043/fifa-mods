#define NOMINMAX
#include "../../src/render/assets/fifa_player_assets.h"
#include <DirectXMath.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
using namespace DirectX;
static uint32_t u32(const uint8_t*p){return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
int main(int argc,char**argv) {
    if(argc!=3)return 2;fifa_player::Assets assets(argv[1]);std::ofstream report(argv[2]);if(!report)return 3;
    for(const char*path:{"data/sceneassets/rig/skeleton_player.rx3","data/sceneassets/rig/skeleton_ant.rx3",
        "data/sceneassets/heads/head_0_0.rx3","data/sceneassets/heads/head_158023_0.rx3",
        "data/sceneassets/hair/hair_158023_0_0.rx3","data/sceneassets/body/jersey_0_0_0_0_0_0_0.rx3",
        "data/sceneassets/body/arms_0_0_0.rx3","data/sceneassets/body/legs_0_0_0.rx3",
        "data/sceneassets/shoe/shoe_15.rx3","data/sceneassets/gkglove/gkglove_0.rx3",
        "data/sceneassets/gkglove/playergkglove_167495_0_0_0.rx3"}) {
        std::vector<uint8_t>b;if(!assets.read(path,b)||b.size()<16||memcmp(b.data(),"RX3l",4))return 4;
        auto names=fifa_player::texture_names(b);size_t n=u32(b.data()+12);if(n>2048||16+n*16>b.size())return 5;
        report<<"RESOURCE "<<path<<" bytes="<<b.size()<<"\n";size_t vertex=0;
        for(size_t i=0;i<n;++i) {
            const uint8_t*e=b.data()+16+i*16;uint32_t type=u32(e);size_t off=u32(e+4),len=u32(e+8);
            if(off>b.size()||len>b.size()-off||len<16)return 6;
            report<<"section "<<std::hex<<type<<std::dec<<" offset="<<off<<" size="<<len<<" count="<<u32(b.data()+off+4)<<"\n";
            if(type==0xc28193f0) {size_t text=u32(b.data()+off+4);if(text>len-16)return 7;
                report<<" descriptor "<<std::string((char*)b.data()+off+16,text)<<"\n";}
            if(type==0x587aa1) {
                size_t count=u32(b.data()+off+4),stride=u32(b.data()+off+8);
                if(stride>512||16+count*stride>len)return 8;
                for(size_t j=0;j<std::min(count,size_t(3));++j) {
                    report<<" vertex "<<vertex<<"."<<j<<" bytes=";
                    for(size_t k=0;k<stride;++k)report<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(b[off+16+j*stride+k]);
                    report<<std::dec<<"\n";
                }++vertex;
            }
            if(type==0xdf9aec1e) {
                size_t count=u32(b.data()+off+4);if(16+count*64>len)return 9;
                for(size_t j=0;j<count;++j)if(j<names.size() &&
                    (names[j]=="Hips"||names[j]=="Head"||names[j]=="LeftArm"||names[j]=="RightArm"||
                    names[j]=="LeftUpLeg"||names[j]=="RightUpLeg"||names[j]=="LeftLeg"||names[j]=="LeftHand")) {
                    XMFLOAT4X4 f;memcpy(&f,b.data()+off+16+j*64,64);XMMATRIX m=XMLoadFloat4x4(&f);XMFLOAT4X4 inv;
                    XMStoreFloat4x4(&inv,XMMatrixInverse(nullptr,m));
                    report<<" bone "<<j<<" "<<names[j]<<" rawTranslation="<<f._41<<","<<f._42<<","<<f._43
                        <<" inverseWorld="<<inv._41<<","<<inv._42<<","<<inv._43<<"\n";
                }
            }
        }
    }
    puts("PASS: raw mesh layouts and native skeleton matrices inspected without game writes");return 0;
}
