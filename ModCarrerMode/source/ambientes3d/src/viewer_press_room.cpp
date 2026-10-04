#include "viewer_press_room.h"
#include "viewer_room_geometry.h"
#include "viewer_team.h"
#include <cfloat>
#include <cstring>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>

namespace studio {
using namespace fifa_player;
using namespace room_geometry;
namespace {
uint32_t word(const std::vector<uint8_t>&b,size_t i){uint32_t n=0;if(i+4<=b.size())memcpy(&n,b.data()+i,4);return n;}
bool dds(const std::vector<uint8_t>&bytes,Texture&out){
    if(bytes.size()<128||memcmp(bytes.data(),"DDS ",4)||word(bytes,4)!=124)return false;
    auto h=word(bytes,12),w=word(bytes,16),format=word(bytes,84);if(!w||!h||w>4096||h>4096)return false;
    unsigned f=format==0x31545844?0:format==0x33545844?1:format==0x35545844?2:99;
    if(f>2&&word(bytes,88)==32){size_t size=size_t(w)*h*4;if(size>bytes.size()-128)return false;out.width=w;out.height=h;out.format=3;out.bytes.resize(size);uint32_t masks[]={word(bytes,92),word(bytes,96),word(bytes,100),word(bytes,104)};
        for(size_t i=0;i<size;i+=4){uint32_t value=word(bytes,128+i);for(int k=0;k<4;++k){unsigned mask=masks[k],shift=0;if(!mask){out.bytes[i+k]=k==3?255:0;continue;}while(!(mask&1)){mask>>=1;++shift;}out.bytes[i+k]=uint8_t(((value>>shift)&mask)*255/mask);}}return true;
    }
    size_t size=size_t((w+3)/4)*((h+3)/4)*(f?16:8);if(f>2||size>bytes.size()-128)return false;
    out.width=w;out.height=h;out.format=f;out.bytes.assign(bytes.begin()+128,bytes.begin()+128+size);return true;
}
// Decode only the native block-compressed logo textures into a reusable tile.
Texture rgba(const Texture&t){
    if(t.format==3)return t;Texture out;out.width=t.width;out.height=t.height;out.format=3;out.bytes.resize(size_t(t.width)*t.height*4);
    auto rgb=[](unsigned n){return std::array<int,3>{int((n>>11)&31)*255/31,int((n>>5)&63)*255/63,int(n&31)*255/31};};
    for(unsigned y=0;y<t.height;y+=4)for(unsigned x=0;x<t.width;x+=4){size_t block=(size_t(y/4)*((t.width+3)/4)+x/4)*(t.format?16:8);if(block+(t.format?16:8)>t.bytes.size())return {};
        auto p=t.bytes.data()+block;auto color=p+(t.format?8:0);unsigned A=color[0]|color[1]<<8,B=color[2]|color[3]<<8;auto a=rgb(A),b=rgb(B);std::array<std::array<int,3>,4>c={a,b,{},{}};
        for(int k=0;k<3;++k){c[2][k]=(A>B||t.format)?(2*a[k]+b[k])/3:(a[k]+b[k])/2;c[3][k]=(A>B||t.format)?(a[k]+2*b[k])/3:0;}
        uint32_t bits=0;memcpy(&bits,color+4,4);uint64_t alphaBits=0;if(t.format==1)memcpy(&alphaBits,p,8);else if(t.format==2)memcpy(&alphaBits,p+2,6);
        unsigned alpha[8]={p[0],p[1]};if(t.format==2){for(int i=2;i<8;++i)alpha[i]=p[0]>p[1]?((8-i)*p[0]+(i-1)*p[1])/7:i<6?((6-i)*p[0]+(i-1)*p[1])/5:i==6?0:255;}
        for(int j=0;j<16;++j){unsigned X=x+j%4,Y=y+j/4;if(X>=t.width||Y>=t.height)continue;unsigned code=(bits>>(2*j))&3;auto q=&out.bytes[(size_t(Y)*t.width+X)*4];for(int k=0;k<3;++k)q[k]=uint8_t(c[code][k]);q[3]=t.format==1?uint8_t(((alphaBits>>(4*j))&15)*17):t.format==2?uint8_t(alpha[(alphaBits>>(3*j))&7]):A<=B&&code==3?0:255;}
    }return out;
}
Texture sponsor_tile(const std::vector<Texture>&logos){
    Texture tile;tile.width=tile.height=1024;tile.format=3;tile.bytes.assign(1024*1024*4,255);
    // Four by four cards form one square seamless repeating sponsor texture.
    for(int cell=0;cell<16;++cell){int cx=cell%4,cy=cell/4;for(int y=0;y<256;++y)for(int x=0;x<256;++x){auto at=((cy*256+y)*1024+cx*256+x)*4;uint8_t v=250;tile.bytes[at]=tile.bytes[at+1]=tile.bytes[at+2]=v;}
        if(logos.empty())continue;auto source=rgba(logos[size_t(cell+cy)%logos.size()]);if(source.bytes.empty())continue;
        auto background=std::array<int,3>{source.bytes[0],source.bytes[1],source.bytes[2]};int l=int(source.width),r=0,top_source=int(source.height),bottom=0;
        for(unsigned y=0;y<source.height;++y)for(unsigned x=0;x<source.width;++x){auto*p=&source.bytes[(size_t(y)*source.width+x)*4];int difference=abs(p[0]-background[0])+abs(p[1]-background[1])+abs(p[2]-background[2]);if(p[3]>30&&difference>110){l=std::min(l,int(x));r=std::max(r,int(x));top_source=std::min(top_source,int(y));bottom=std::max(bottom,int(y));}}
        if(r<=l||bottom<=top_source){l=0;r=source.width-1;top_source=0;bottom=source.height-1;}
        int source_w=r-l+1,source_h=bottom-top_source+1;
        float scale=std::min(217.f/source_w,148.f/source_h);int w=int(source_w*scale),h=int(source_h*scale),left=cx*256+(256-w)/2,top=cy*256+(256-h)/2;
        for(int y=0;y<h;++y)for(int x=0;x<w;++x){auto src=&source.bytes[(size_t(top_source+unsigned(y/scale))*source.width+l+unsigned(x/scale))*4];auto dst=&tile.bytes[((top+y)*1024+left+x)*4];for(int k=0;k<3;++k)dst[k]=uint8_t((unsigned(src[k])*src[3]+unsigned(dst[k])*(255-src[3]))/255);}
    }return tile;
}
Texture sponsor_logo(const Texture&native,const std::string&name){
    auto src=rgba(native);if(src.bytes.empty())return {};int left=0,right=int(src.width);Vec3 brand={.04f,.04f,.05f};
    if(name=="_Betano"){left=300;right=505;brand={.95f,.23f,.06f};}
    else if(name=="adidas3logos"){left=35;right=155;}
    else if(name=="CocaColaa"){left=2;right=201;brand={.8f,.05f,.13f};}
    else if(name=="Hyundai"){left=33;right=147;brand={.12f,.30f,.55f};}
    else if(name=="_Penalty")brand={.04f,.43f,.26f};
    left=std::clamp(left,0,int(src.width)-1);right=std::clamp(right,left+1,int(src.width));Texture logo;logo.width=right-left;logo.height=src.height;logo.format=3;logo.bytes.assign(size_t(logo.width)*logo.height*4,255);
    // Native white wordmarks are extracted from advertising-strip backgrounds.
    // Their shapes/aspect are unchanged; only the white-wall presentation differs.
    for(unsigned y=0;y<logo.height;++y)for(unsigned x=0;x<logo.width;++x){auto p=&src.bytes[(size_t(y)*src.width+left+x)*4];float coverage=std::clamp((std::min({p[0],p[1],p[2]})-105.f)/135.f,0.f,1.f)*p[3]/255.f;auto q=&logo.bytes[(size_t(y)*logo.width+x)*4];for(int k=0;k<3;k++)q[k]=uint8_t(255*(1-coverage+(&brand.x)[k]*coverage));}
    return logo;
}
void rounded_block(Builder&b,const std::string&name,Vec3 center,Vec3 size,float radius,Vec3 color,bool upright=false,int texture=-1){
    // Rounded padded rectangle; genuine curved edge geometry, not sharp boxes.
    float w=size.x,h=upright?size.y:size.z,thick=upright?size.z:size.y;
    radius=std::min(radius,std::min(w,h)*.45f);std::vector<Vec3>perimeter;
    for(int corner=0;corner<4;++corner){float x=(corner==0||corner==3?1.f:-1.f)*(w/2-radius),y=(corner<2?1.f:-1.f)*(h/2-radius);float start=corner*pi/2;
        for(int i=0;i<=8;++i){float a=start+i*pi/16;perimeter.push_back({x+radius*cosf(a),y+radius*sinf(a),0});}}
    auto point=[&](Vec3 p,float depth){return add(center,upright?Vec3{p.x,p.y,depth}:Vec3{p.x,depth,p.y});};
    for(size_t i=0;i<perimeter.size();++i){auto A=perimeter[i],B=perimeter[(i+1)%perimeter.size()],n=normalized({B.y-A.y,A.x-B.x,0});if(!upright)n={n.x,0,n.y};
        b.face(name,point(A,-thick/2),point(B,-thick/2),point(B,thick/2),point(A,thick/2),n,mul(color,.83f),texture);
        auto normal=upright?Vec3{0,0,1}:Vec3{0,1,0};b.face(name,point({},thick/2),point(A,thick/2),point(B,thick/2),point({},thick/2),normal,color,texture);
        b.face(name,point({},-thick/2),point(B,-thick/2),point(A,-thick/2),point({},-thick/2),mul(normal,-1),color,texture);
    }
}
Texture upholstery(){Texture t;t.width=t.height=128;t.format=3;t.bytes.resize(128*128*4);for(unsigned y=0;y<128;++y)for(unsigned x=0;x<128;++x){unsigned hash=(x*1237+y*1789)^((x+13)*(y+47));float grain=(hash%17)/255.f;for(int k=0;k<3;++k)t.bytes[(y*128+x)*4+k]=uint8_t(27+k*2+grain*255);t.bytes[(y*128+x)*4+3]=255;}return t;}
void water_bottle(Builder&b,const std::string&name,Vec3 p){
    Vec3 glass={.72f,.84f,.87f};b.tube(name,p,add(p,{0,1.3f,0}),3.1f,glass,36);b.frustum(name,add(p,{0,1.3f,0}),3.1f,3.7f,1,glass);b.tube(name,add(p,{0,2.3f,0}),add(p,{0,16.5f,0}),3.7f,glass,36);b.frustum(name,add(p,{0,16.5f,0}),3.7f,1.9f,4,glass);b.tube(name,add(p,{0,20.5f,0}),add(p,{0,23,0}),1.9f,glass,28);b.tube(name,add(p,{0,23,0}),add(p,{0,25,0}),2.05f,{.17f,.33f,.54f},28);
    b.tube(name,add(p,{0,7,0}),add(p,{0,12,0}),3.76f,{.88f,.93f,.95f},36);b.panel(name,add(p,{0,9.5f,3.9f}),5.5f,3,b.texture(text_label(L"ÁGUA",{.88f,.93f,.95f},{.1f,.28f,.42f},64)));
    for(float y:{3.f,4.5f,14.f,15.5f})b.tube(name,add(p,{0,y,0}),add(p,{0,y+.35f,0}),3.78f,{.62f,.77f,.81f},36);
}
void microphone(Builder&b,const std::string&name,Vec3 p){
    rounded_block(b,name,add(p,{0,1.6f,0}),{16,3.2f,12},4,ink);b.box(name,add(p,{3,3.4f,2}),{4,.5f,3},{.42f,.47f,.5f});b.box(name,add(p,{3,3.8f,2}),{2,.4f,1},{.08f,.6f,.28f});
    std::vector<Vec3>stem={{0,3,0},{0,12,-4},{0,21,-10},{2,26,-20},{5,30,-30}};for(size_t i=1;i<stem.size();++i)b.tube(name,add(p,stem[i-1]),add(p,stem[i]),.46f,ink,20);
    b.tube(name,add(p,{5,30,-30}),add(p,{7,31.6f,-35}),1.65f,{.055f,.055f,.06f},32);b.tube(name,add(p,{7,31.6f,-35}),add(p,{7.5f,32,-36.2f}),1.3f,ink,28);
    for(int i=0;i<30;++i){float a=i*pi/15,A=(i+1)*pi/15;b.tube(name,add(p,{12*cosf(a),.22f,10*sinf(a)}),add(p,{12*cosf(A),.22f,10*sinf(A)}),.12f,ink,8);}
}
void gamer_chair(Builder&b,const std::string&name,Vec3 accent,float seat){
    b.rounded_box(name,{0,seat,0},{55,9,51},4.3f,ink);b.rounded_box(name,{0,seat+5,-3},{46,6,38},2.8f,{.13f,.145f,.16f});
    // Bevelled upholstery, lumbar support, shoulder wings and headrest.
    b.rounded_box(name,{0,seat+41,-29},{49,74,10},4.9f,ink);
    b.rounded_box(name,{0,seat+42,-22.8f},{35,51,6},2.9f,{.135f,.15f,.17f});
    b.rounded_box(name,{0,seat+24,-18.8f},{31,13,8},3.8f,{.17f,.18f,.20f});
    for(float side:{-1.f,1.f})b.rounded_box(name,{side*23,seat+46,-23},{11,55,13},4.8f,accent);
    b.rounded_box(name,{0,seat+76,-28},{34,21,12},5.7f,ink);b.rounded_box(name,{0,seat+76,-20.8f},{26,13,3},1.4f,mul(accent,.75f));b.crest(name,{0,seat+76,-18.8f},10);
    for(float x:{-32.f,32.f}){b.tube(name,{x,seat-2,3},{x,seat+20,3},1.8f,metal);b.rounded_box(name,{x,seat+22,3},{9,5,33},2.4f,ink);}
    b.tube(name,{0,20,0},{0,seat-4,0},3.4f,metal);for(int i=0;i<5;++i){float a=i*2*pi/5;Vec3 end={31*cosf(a),5,31*sinf(a)};b.tube(name,{0,11,0},end,2.3f,ink);b.tube(name,add(end,{-3,0,0}),add(end,{3,0,0}),4.5f,ink,20);}
}
void audience_chair(Builder&b,const std::string&name,Vec3 accent,float surface=49,int variant=0){
    Vec3 fabric=variant%3==0?Vec3{.11f,.13f,.16f}:variant%3==1?Vec3{.13f,.15f,.145f}:Vec3{.10f,.10f,.12f};
    rounded_block(b,name,{0,surface-4,0},{51,8,48},7,fabric);rounded_block(b,name,{0,surface+20,-23},{49,45,7},8,mul(fabric,.85f),true);
    rounded_block(b,name,{0,surface+19,-18.8f},{42,35,2},7,fabric,true);for(float x:{-22.f,22.f}){b.tube(name,{x,5,-18},{x,surface-9,-18},1.5f,metal);b.tube(name,{x,surface-9,-18},{x,surface-9,18},1.5f,metal);b.tube(name,{x,surface-9,18},{x,5,24},1.5f,metal);b.tube(name,{x,5,-18},{x,5,24},1.5f,metal);}
    for(float x:{-28.f,28.f}){b.tube(name,{x,surface-18,4},{x,surface+12,4},1.5f,metal);rounded_block(b,name,{x,surface+14,4},{7,4,29},3,ink);}b.box(name,{0,surface+43,-21},{36,1.4f,1},accent);
}
// The SLC equipment is weighted to auxiliary bone 30. It is not a foot and
// must not define the grounding of its owner or remain abandoned below a seat.
void remove_auxiliary_equipment(Model&m){for(auto&p:m.parts){std::vector<uint32_t>indices;for(size_t i=0;i+2<p.indices.size();i+=3){bool equipment=false;for(int k=0;k<3;++k){auto&v=p.vertices[p.indices[i+k]];for(int j=0;j<8;++j)if(v.weights[j]>127&&v.joints[j]>=28)equipment=true;}if(!equipment)indices.insert(indices.end(),p.indices.begin()+i,p.indices.begin()+i+3);}std::vector<Vertex>vertices;std::vector<uint32_t>map(p.vertices.size(),UINT32_MAX);for(auto&i:indices){if(map[i]==UINT32_MAX){map[i]=uint32_t(vertices.size());vertices.push_back(p.vertices[i]);}i=map[i];}p.indices=std::move(indices);p.vertices=std::move(vertices);}}
bool pose_audience(Model&m,int role){
    using namespace DirectX;auto&rig=*m.skeleton;if(rig.names.size()!=31)return false;std::vector<XMFLOAT4X4>rest(31),pose(31),delta(31);
    for(int i=0;i<31;++i){XMFLOAT4X4 inv;memcpy(&inv,rig.inverse_bind[i].data(),64);XMStoreFloat4x4(&rest[i],XMMatrixInverse(nullptr,XMLoadFloat4x4(&inv)));pose[i]=rest[i];}
    auto point=[&](int i){return XMVectorSet(pose[i]._41,pose[i]._42,pose[i]._43,0);};
    auto rotate=[&](int joint,FXMMATRIX rotation){auto p=pose[joint];auto transform=XMMatrixTranslation(-p._41,-p._42,-p._43)*rotation*XMMatrixTranslation(p._41,p._42,p._43);for(int i=joint;i<31;++i){int ancestor=i;while(ancestor!=joint&&rig.parents[ancestor]!=0xffff)ancestor=rig.parents[ancestor];if(ancestor==joint)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*transform);}};
    auto align=[&](int joint,FXMVECTOR from,FXMVECTOR to){float a=XMVectorGetX(XMVector3LengthSq(from)),b=XMVectorGetX(XMVector3LengthSq(to));if(a<.001f||b<.001f)return false;auto F=XMVector3Normalize(from),T=XMVector3Normalize(to);float d=std::clamp(XMVectorGetX(XMVector3Dot(F,T)),-1.f,1.f);if(d<.99999f){auto axis=XMVector3Cross(F,T);if(d<-.9999f)axis=XMVector3Cross(F,XMVectorSet(0,0,1,0));rotate(joint,XMMatrixRotationAxis(axis,acosf(d)));}return true;};
    float shift=(pose[3]._42-pose[4]._42+pose[7]._42-pose[8]._42)*.5f;rotate(3,XMMatrixRotationX(-XM_PIDIV2));rotate(4,XMMatrixRotationX(XM_PIDIV2));rotate(7,XMMatrixRotationX(-XM_PIDIV2));rotate(8,XMMatrixRotationX(XM_PIDIV2));for(auto&p:pose)p._42-=shift;
    for(bool left:{true,false}){int arm=left?17:22,elbow=left?18:23,hand=left?19:24,end=left?20:25;auto S=point(arm);float a=XMVectorGetX(XMVector3Length(point(elbow)-S)),b=XMVectorGetX(XMVector3Length(point(hand)-point(elbow)));if(a<5||b<5)return false;
        auto target=point(2)+XMVectorSet(left?13.f:-13.f,20,34,0);if(role==1||role==3)target=point(2)+XMVectorSet(left?9.f:-9.f,48,33,0);else if(role==2)target=point(2)+XMVectorSet(left?16.f:-13.f,left?7.f:40.f,left?39.f:28.f,0);
        auto axis=XMVector3Normalize(target-S);float dist=std::clamp(XMVectorGetX(XMVector3Length(target-S)),fabsf(a-b)+.05f,a+b-.1f);target=S+axis*dist;float along=(a*a-b*b+dist*dist)/(2*dist),h=sqrtf(std::max(0.f,a*a-along*along));auto pole=XMVectorSet(left?1.f:-1.f,-1,.18f,0);auto plane=XMVector3Normalize(pole-axis*XMVectorGetX(XMVector3Dot(pole,axis)));auto E=S+axis*along+plane*h;
        if(!align(arm,point(elbow)-S,E-S)||!align(elbow,point(hand)-point(elbow),target-point(elbow))||!align(hand,point(end)-point(hand),XMVectorSet(left?-.35f:.35f,-.18f,1,0)))return false;
    }
    for(int i=0;i<31;++i)XMStoreFloat4x4(&delta[i],XMMatrixInverse(nullptr,XMLoadFloat4x4(&rest[i]))*XMLoadFloat4x4(&pose[i]));float floor=FLT_MAX;
    for(auto&p:m.parts){if(!p.skinned)return false;for(auto&v:p.vertices){XMVECTOR position=XMVectorZero(),normal=XMVectorZero();unsigned sum=0;for(int j=0;j<8;++j)if(v.weights[j]){if(v.joints[j]>=31)return false;auto D=XMLoadFloat4x4(&delta[v.joints[j]]);position+=XMVector3TransformCoord(XMVectorSet(v.position.x,v.position.y,v.position.z,1),D)*float(v.weights[j]);normal+=XMVector3TransformNormal(XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),D)*float(v.weights[j]);sum+=v.weights[j];}if(!sum)return false;position/=float(sum);normal=XMVector3Normalize(normal);v.position={XMVectorGetX(position),XMVectorGetY(position),XMVectorGetZ(position)};v.normal={XMVectorGetX(normal),XMVectorGetY(normal),XMVectorGetZ(normal)};floor=std::min(floor,v.position.y);}}
    auto landmark=[&](int bone){return Vec3{pose[bone]._41,pose[bone]._42-floor,pose[bone]._43-pose[2]._43-5};};m.left_hand=landmark(19);m.right_hand=landmark(24);m.left_hip=landmark(7);m.right_hip=landmark(3);float contact=FLT_MAX;
    for(auto&p:m.parts)for(auto&v:p.vertices){v.position.y-=floor;v.position.z-=pose[2]._43+5;unsigned hip=0;for(int j=0;j<8;++j)if(v.joints[j]==2)hip+=v.weights[j];if(hip>90&&v.position.z<12)contact=std::min(contact,v.position.y);}
    if(!std::isfinite(contact)||contact<32||contact>62)return false;m.pose_floor_cm=contact;m.presentation_pose=true;m.presentation_pose_id=600+role;return true;
}
void audience_equipment(Builder&b,const Model&m,const std::string&name){
    int role=int(m.presentation_pose_id)-600;Vec3 hands=mul(add(m.left_hand,m.right_hand),.5f);
    if(role==0){rounded_block(b,name,add(hands,{0,-2,5}),{24,1.5f,19},2,{.17f,.18f,.21f});b.box(name,add(hands,{0,-1,5}),{21,.3f,17},white);b.tube(name,add(m.right_hand,{-2,0,0}),add(m.right_hand,{1,0,11}),.35f,ink,8);}
    else if(role==2){auto hand=m.right_hand;b.tube(name,add(hand,{0,-8,0}),add(hand,{0,9,1}),1.3f,ink,20);b.tube(name,add(hand,{0,9,1}),add(hand,{0,15,1.5f}),3,{.11f,.12f,.14f},24);rounded_block(b,name,add(hand,{0,6,1}),{7,6,6},1.3f,{.23f,.31f,.40f});}
    else{Vec3 p=add(hands,{0,2,7});rounded_block(b,name,p,{role==1?19.f:24.f,13,11},3,ink);b.tube(name,add(p,{0,0,4}),add(p,{0,0,role==1?24.f:16.f}),role==1?4.9f:4.2f,ink,32);for(float z:{9.f,12.f,15.f})b.tube(name,add(p,{0,0,z}),add(p,{0,0,z+.7f}),5.2f,{.23f,.24f,.25f},32);b.tube(name,add(p,{0,0,role==1?24.3f:16.3f}),add(p,{0,0,role==1?24.8f:16.8f}),4.1f,{.11f,.24f,.31f},32);b.box(name,add(p,{0,1,-5.6f}),{10,6,.4f},{.27f,.35f,.4f});if(role==3){b.tube(name,add(p,{-4,8,0}),add(p,{4,8,0}),1.3f,ink,16);b.tube(name,add(p,{5,8,1}),add(p,{5,8,13}),1.4f,ink,16);}}
}
void native_prop(Builder&b,const Model&m,const std::string&name,Vec3 center,float height,float yaw=0){
    if(m.parts.empty())return;Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};for(auto&p:m.parts)for(auto&v:p.vertices)for(int k=0;k<3;++k){(&lo.x)[k]=std::min((&lo.x)[k],(&v.position.x)[k]);(&hi.x)[k]=std::max((&hi.x)[k],(&v.position.x)[k]);}
    float scale=height/std::max(.01f,hi.y-lo.y);Vec3 middle=mul(add(lo,hi),.5f);int offset=int(b.room.textures.size());b.room.textures.insert(b.room.textures.end(),m.textures.begin(),m.textures.end());
    for(auto p:m.parts){p.name=name;p.skinned=false;if(p.texture>=0)p.texture+=offset;for(auto&v:p.vertices){auto q=mul(sub(v.position,{middle.x,lo.y,middle.z}),scale);v.position=b.point(add(center,{q.x*cosf(yaw)+q.z*sinf(yaw),q.y,-q.x*sinf(yaw)+q.z*cosf(yaw)}));auto n=v.normal;v.normal=b.direction({n.x*cosf(yaw)+n.z*sinf(yaw),n.y,-n.x*sinf(yaw)+n.z*cosf(yaw)});}b.room.parts.push_back(std::move(p));}
}
void crowd_person(Builder&b,const Model&m,const std::string&name,std::map<std::string,int>&cache){
    if(m.parts.empty())return;std::vector<int>textures;for(size_t i=0;i<m.textures.size();++i){auto key=m.parts.front().asset+"#"+std::to_string(i);auto at=cache.find(key);if(at==cache.end())at=cache.emplace(key,b.texture(m.textures[i])).first;textures.push_back(at->second);}
    for(auto p:m.parts){p.name=name;p.skinned=false;if(p.texture>=0)p.texture=textures.at(p.texture);if(p.hair_coeff_texture>=0)p.hair_coeff_texture=textures.at(p.hair_coeff_texture);for(auto&v:p.vertices){v.position=b.point(v.position);v.normal=b.direction(v.normal);}b.room.parts.push_back(std::move(p));}
}
void append_participant(Builder&b,const Model&source,bool coach,unsigned pose,float x,float z){
    Model seated=source;bool ready=coach?apply_coach_pose(seated,pose):apply_presentation_pose(seated,false,nullptr,pose==206?302:301);if(!ready)return;
    auto bones=team_bones.find(&seated);if(bones!=team_bones.end())for(auto&bone:bones->second){bone.point.y+=40;bone.frame._42+=40;}
    int offset=int(b.room.textures.size());b.room.textures.insert(b.room.textures.end(),seated.textures.begin(),seated.textures.end());size_t begin=b.room.parts.size();
    for(auto p:seated.parts){p.asset=std::string(coach?"mod/club-room/seated-coach/source/":"mod/club-room/seated-player/source/")+p.asset;p.name=(coach?"Técnico":"Jogador "+std::to_string(source.player_id))+std::string(" / ")+p.name;p.skinned=false;if(p.texture>=0)p.texture+=offset;if(p.hair_coeff_texture>=0)p.hair_coeff_texture+=offset;for(auto&v:p.vertices)v.position=add(v.position,{x,40,z});b.room.parts.push_back(std::move(p));}
    register_team_actor(b.room,seated,begin,x,z);team_bones.erase(&seated);
    ++b.room.player_count;if(coach)b.room.press_coach_present=true;else if(!b.room.press_player_id)b.room.press_player_id=source.player_id;
}
}

PressResources load_press_resources(Assets&assets,const fs::path&game,int club,int competition){
    PressResources out;out.competition=assets.league(club,out.league_name);if(competition>0){out.competition=competition;out.league_name="Competição "+std::to_string(competition);}out.prints=load_dressing_prints(assets,game,club,out.competition);
    if(out.competition>0){assets.competition_icon(out.competition,out.competition_icon);out.trophy=assets.trophy(out.competition);}
    // One initial sponsor set for every club. Real installed logos, not invented
    // contractual associations. Architecture supports a per-club set later.
    for(auto name:{"_Betano","adidas3logos","CocaColaa","Hyundai","_Penalty"}){auto path=game/L"data"/L"ui"/L"imgAssets"/L"adsponsors512x64"/wide(std::string("adsponsors512x64")+name+".dds");std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)continue;auto size=file.tellg();if(size<128||size>16*1024*1024)continue;std::vector<uint8_t>raw(size_t(size),0);file.seekg(0);file.read(reinterpret_cast<char*>(raw.data()),size);Texture tex;if(file&&dds(raw,tex))out.sponsors.push_back(sponsor_logo(tex,name));}
    std::vector<std::string>people;for(int type=1;type<=8;++type)people.push_back("data/sceneassets/crowd/crowd_"+std::to_string(type)+"_0_1_0");people.push_back("data/sceneassets/slc/specificphotographer_0_7_0");people.push_back("data/sceneassets/slc/specificphotographer_0_30_0");
    for(auto&base:people){std::vector<uint8_t>mesh,raw;Model source;Skeleton rig;
        if(!assets.read(base+".rx3",mesh)||!read_mesh(mesh,source.parts)||!read_coach_skeleton(mesh,rig))continue;
        std::vector<std::string>textures={base+"_textures.rx3"};if(base.find("/crowd/")!=std::string::npos)textures.push_back(base.substr(0,base.size()-4)+"_0_0_textures.rx3");else if(base.find("specific")==std::string::npos){auto prefix=base.substr(0,base.find('_'));textures.push_back(prefix+"_0_0_0_0_textures.rx3");}
        Texture tex;bool found=false;for(auto&path:textures){if(!assets.read(path,raw))continue;for(auto&n:texture_names(raw))if(n.find("_cm")!=std::string::npos&&read_texture(raw,n,tex)){found=true;break;}if(found)break;}if(!found)continue;
        // Crowd diffuse alpha stores customization masks, not cut-out opacity.
        // Treating it as transparency removes faces, limbs and parts of shirts.
        if(base.find("/crowd/")!=std::string::npos){tex=rgba(tex);for(size_t i=3;i<tex.bytes.size();i+=4)tex.bytes[i]=255;}
        source.skeleton=std::make_shared<Skeleton>(std::move(rig));source.textures.push_back(std::move(tex));remove_auxiliary_equipment(source);for(auto&p:source.parts){p.asset=base+".rx3";p.texture=0;}
        for(int role=0;role<4;++role){auto m=source;if(!pose_audience(m,role))continue;auto size=bounds(m);if(size.high.x-size.low.x>90||size.high.y>175)continue;out.crowd.push_back(std::move(m));}
    }
    std::ostringstream status;status<<"Bola: "<<out.prints.ball_asset<<". Troféu: "<<out.trophy.diagnostic<<". Logos: "<<out.sponsors.size()<<". Plateia nativa variada: "<<out.crowd.size()<<" combinações de modelo/pose (anotações, fotografia, microfone e vídeo; poses estáticas).";out.diagnostic=status.str();return out;
}

Model build_press_room(const std::vector<std::shared_ptr<const Model>>&players,const CoachAsset&coach,const PressResources&resources,const Settings&s){
    Builder b;auto&room=b.room;if(players.empty())return room;const auto&club=*players.front();room.room=RoomPressPair;room.team_id=club.team_id;room.player_count=0;room.presentation_pose_id=s.pose;room.club_colors_valid=club.club_colors_valid;std::copy(std::begin(club.club_colors),std::end(club.club_colors),room.club_colors);
    if(club.crest_texture>=0&&size_t(club.crest_texture)<club.textures.size()){room.crest_texture=0;room.textures.push_back(club.textures[club.crest_texture]);}
    Vec3 accent=club.club_colors_valid?club.club_colors[0]:Vec3{.12f,.3f,.55f},secondary=club.club_colors_valid?club.club_colors[1]:ink;
    int wood=b.texture(surface_material(true)),rubber=b.texture(surface_material(false));
    b.box("Imprensa / parede de fundo",{0,160,-457},{1112,320,14},{.91f,.90f,.87f});
    b.box("Imprensa / paredes laterais",{555,160,296},{12,320,1500},{.94f,.93f,.9f});
    // Actual opening in the left wall, with a participant-only lateral exit.
    b.box("Imprensa / paredes laterais",{-555,160,386},{12,320,1320},{.94f,.93f,.9f});b.box("Imprensa / paredes laterais",{-555,285,-330},{12,70,110},{.94f,.93f,.9f});b.box("Imprensa / paredes laterais",{-555,140,-422},{12,280,71},white);
    for(float x:{-548.f,548.f}){b.box("Imprensa / faixa lateral",{x,152,480},{1.5f,12,1100},accent);b.box("Imprensa / rodapé",{x,8,296},{2,16,1490},ink);}
    b.box("Imprensa / piso",{0,-3,296},{1112,6,1500},{.55f,.49f,.42f});b.face("Imprensa / piso",{-548,.08f,-448},{548,.08f,-448},{548,.08f,1043},{-548,.08f,1043},{0,1,0},{.92f,.88f,.80f},wood,false,22,2);
    b.box("Imprensa / corredor central",{0,.5f,422},{140,.8f,1130},{.18f,.20f,.22f});
    b.box("Imprensa / palco",{0,20,-323},{1080,40,258},{.2f,.22f,.24f});b.box("Imprensa / palco",{0,40.4f,-323},{1080,.8f,258},{.31f,.32f,.33f});
    b.box("Imprensa / degraus",{0,14,-177},{990,28,37},{.29f,.30f,.31f});b.box("Imprensa / degraus",{0,7,-140},{990,14,37},{.33f,.34f,.35f});for(float z:{-195.f,-158.f,-121.f})b.box("Imprensa / borda dos degraus",{0,z==-195?40.9f:z==-158?28.7f:14.7f,z},{990,.9f,2.5f},metal);
    b.frame({-545,40,-330},pi/2);for(float x:{-55.f,55.f})b.box("Imprensa / saída lateral",{x,108,0},{5,218,9},metal);b.box("Imprensa / saída lateral",{0,216,0},{116,5,9},metal);b.box("Imprensa / saída lateral",{0,103,-3},{106,208,4},{.19f,.22f,.25f});b.box("Imprensa / saída lateral",{0,104,.5f},{96,198,2},{.32f,.29f,.25f},wood);b.tube("Imprensa / saída lateral",{35,85,3},{35,107,3},1.3f,metal);b.crest("Imprensa / saída lateral",{0,158,3},28);b.panel("Imprensa / saída lateral",{0,229,3},110,13,b.texture(text_label(L"ACESSO DOS PARTICIPANTES",ink,{1,1,1},72)));b.frame();
    b.box("Imprensa / teto",{0,325,296},{1112,10,1500},white);for(float z=-400;z<1044;z+=100)b.box("Imprensa / teto modular",{0,319,z},{1100,.4f,.5f},{.8f,.81f,.81f});for(float x=-500;x<=500;x+=100)b.box("Imprensa / teto modular",{x,319,296},{.5f,.4f,1500},{.8f,.81f,.81f});
    for(float x:{-300.f,0.f,300.f})for(float z:{-350.f,35.f,420.f,820.f}){b.box("Imprensa / luminárias",{x,315,z},{92,5,48},metal);b.box("Imprensa / luminárias",{x,312,z},{87,.6f,44},{1.3f,1.29f,1.26f});}
    for(float x:{-250.f,0.f,250.f}){b.box("Imprensa / luz frontal",{x,294,-150},{118,6,27},metal);b.box("Imprensa / luz frontal",{x,290.7f,-150},{113,.6f,22},{1.3f,1.3f,1.27f});}
    // Full rear sponsor wall: a square repeated texture, shared for now.
    auto logos=resources.sponsors;if(room.crest_texture>=0)logos.push_back(room.textures[room.crest_texture]);int tile=b.texture(sponsor_tile(logos));b.box("Imprensa / painel de patrocinadores",{0,204,-442},{795,183,5},white);
    // Square physical texels: width/height, not a fixed 2:1 UV stretching.
    b.face("Imprensa / painel de patrocinadores",{-394,294,-437},{394,294,-437},{394,114,-437},{-394,114,-437},{0,0,1},{1,1,1},tile,false,788.f/180.f,1);
    b.box("Imprensa / painel superior",{0,306,-438},{807,7,3},ink);for(float x:{-407.f,407.f})b.box("Imprensa / moldura do painel",{x,204,-438},{7,200,3},ink);
    // Five equally spaced removable participants, while the five chairs remain.
    std::array<const Model*,5>assigned={};std::set<int>used;bool coach_used=false;
    for(int slot=0;slot<5;++slot){int id=s.press_slots[slot];if(id==-1&&!coach_used&&coach.model&&coach.model->team_id==s.club){assigned[slot]=coach.model.get();coach_used=true;}else if(id){if(id==-2)id=s.player;for(auto&p:players)if(p->player_id==id&&used.insert(id).second){assigned[slot]=p.get();break;}}
        float x=(slot-2)*132.f,seat=64;bool is_coach=assigned[slot]&&assigned[slot]==coach.model.get();
        if(assigned[slot]&&!is_coach){Model pose=*assigned[slot];if(apply_presentation_pose(pose,false,nullptr,s.pose==206?302:301))seat=std::clamp((pose.left_hip.y+pose.right_hip.y)*.5f-5.f,35.f,65.f)+16;team_bones.erase(&pose);}
        b.frame({x,16,-344});gamer_chair(b,"Mesa / cadeira "+std::to_string(slot+1),accent,seat-16);b.frame();
        std::string mic="Mesa / microfone "+std::to_string(slot+1);microphone(b,mic,{x-10,105,-250});water_bottle(b,"Mesa / água "+std::to_string(slot+1),{x+37,105,-271});
        b.tube("Mesa / copos",{x+24,105,-263},{x+24,113,-263},2.8f,{.8f,.88f,.9f},32);b.tube("Mesa / copos",{x+24,112.7f,-263},{x+24,113.2f,-263},3,{.64f,.77f,.8f},32);
        b.box("Mesa / gravadores",{x+3,106,-241},{7,2,11},{.12f,.14f,.17f});b.box("Mesa / gravadores",{x+3,107.1f,-243},{4,.3f,3},{.35f,.51f,.53f});b.box("Mesa / gravadores",{x+3,107.3f,-239},{.8f,.2f,.8f},{.76f,.14f,.12f});
        b.box("Mesa / anotações",{x+21,106,-301},{18,1,22},white);b.tube("Mesa / anotações",{x+31,107,-297},{x+31,107,-310},.35f,ink,12);
    }
    rounded_block(b,"Mesa / tampo",{0,101,-278},{752,8,115},18,{.12f,.13f,.145f});rounded_block(b,"Mesa / painel frontal",{0,58,-219},{726,82,9},12,{.16f,.18f,.20f},true);
    b.box("Mesa / faixa do clube",{0,83,-213},{706,5,1.5f},accent);b.box("Mesa / acabamento inferior",{0,18,-214},{721,3,4},metal);
    for(float x:{-340.f,340.f})b.box("Mesa / suporte",{x,56,-276},{8,86,92},ink);
    b.crest("Mesa / escudo",{0,55,-212},46);for(float side:{-1.f,1.f})for(int slat=0;slat<15;++slat)b.box("Mesa / ripado",{side*(100.f+slat*16),52,-213},{3,48,2},{.46f,.41f,.35f});
    // Media accessories: tablet, tissue box and a small floral arrangement.
    rounded_block(b,"Mesa / tablet",{50,107,-286},{22,1.5f,16},2,ink);b.box("Mesa / tablet",{50,108,-286},{18,.2f,12},{.08f,.18f,.24f});
    rounded_block(b,"Mesa / lenços",{-48,110,-272},{21,10,12},2,{.85f,.84f,.8f});b.box("Mesa / lenços",{-48,115.5f,-272},{10,.5f,2},ink);b.box("Mesa / lenços",{-46,118,-272},{6,6,.3f},white);
    b.tube("Mesa / flores",{0,105,-266},{0,120,-266},4,{.71f,.73f,.74f},32);for(int f=0;f<7;++f){float a=f*2*pi/7;b.tube("Mesa / flores",{0,114,-266},{7*cosf(a),127,-266+5*sinf(a)},.3f,{.23f,.38f,.23f},8);rounded_block(b,"Mesa / flores",{7*cosf(a),127,-266+5*sinf(a)},{5,4,5},1.9f,{.87f,.84f,.70f});}
    // Ball podium and reserved competition trophy position, only populated in final mode.
    b.box("Competição / pedestal da bola",{-398,68,-287},{53,105,51},white);b.box("Competição / pedestal da bola",{-398,122,-287},{59,5,56},ink);
    std::map<int,int>ball_textures;game_ball(b,resources.prints.ball,"Competição / bola",{-398,136,-287},.7f,ball_textures);
    b.box("Competição / suporte do troféu",{398,69,-287},{57,108,53},white);b.box("Competição / suporte do troféu",{398,126,-287},{62,5,58},ink);
    if(s.press_final)native_prop(b,resources.trophy,"Competição / troféu",{398,128.5f,-287},75);
    if(!resources.competition_icon.bytes.empty()){int t=b.texture(resources.competition_icon);b.face("Competição / logo",{-424,107,-259},{-372,107,-259},{-372,49,-259},{-424,49,-259},{0,0,1},{1,1,1},t,true);b.face("Competição / logo",{372,107,-259},{424,107,-259},{424,49,-259},{372,49,-259},{0,0,1},{1,1,1},t,true);}
    // 48 rounded seats, centre aisle and lateral circulation.
    std::map<std::string,int>crowd_textures;for(int row=0;row<6;++row)for(int seat=0;seat<8;++seat){float x=seat<4?-420+seat*92.f:144+(seat-4)*92.f,z=65+row*137.f;int number=row*8+seat+1;const Model*person=s.press_audience&&!resources.crowd.empty()&&(row+seat)%3!=1?&resources.crowd[size_t(row*13+seat*7)%resources.crowd.size()]:nullptr;b.frame({x,0,z},pi);audience_chair(b,"Plateia / cadeira "+std::to_string(number),mul(accent,.7f),person?person->pose_floor_cm:49,number);if(person){crowd_person(b,*person,"Plateia / jornalista "+std::to_string(number),crowd_textures);audience_equipment(b,*person,"Plateia / equipamento "+std::to_string(number));}b.frame();}
    // Camera/media equipment beside the seating, plus a proper glazed entrance.
    for(float x:{-390.f,390.f}){std::string n="Imprensa / câmera";b.box(n,{x,167,930},{19,18,34},ink);b.tube(n,{x,167,911},{x,167,895},6,ink,24);b.tube(n,{x,158,930},{x,98,930},2,metal);for(float side:{-1.f,1.f})b.tube(n,{x,99,930},{x+side*25,3,945},1.5f,metal);b.tube(n,{x,99,930},{x,3,903},1.5f,metal);}
    b.box("Imprensa / entrada",{-264,160,752},{385,320,12},white);b.box("Imprensa / entrada",{264,160,752},{385,320,12},white);b.box("Imprensa / entrada",{0,286,752},{150,68,12},white);
    for(float x:{-71.f,0.f,71.f})b.box("Imprensa / porta",{x,123,745},{5,244,10},metal);b.box("Imprensa / porta",{0,245,745},{147,5,10},metal);for(float x:{-36.f,36.f}){b.box("Imprensa / porta",{x,124,748},{65,230,3},{.24f,.33f,.38f});b.box("Imprensa / porta",{x,144,744},{62,151,1},{.43f,.54f,.6f});b.box("Imprensa / porta",{x,38,741},{63,64,2},accent);b.tube("Imprensa / porta",{x<0?-10.f:10.f,93,739},{x<0?-10.f:10.f,117,739},1.2f,metal);}
    b.frame({0,0,752},pi);b.panel("Imprensa / saída",{0,269,11},109,16,b.texture(text_label(L"SAÍDA",{.07f,.42f,.21f},{1,1,1},80)));b.frame();
    // Raise the furniture/accessories together to the 40 cm stage level.
    for(auto&p:room.parts)if(p.name.rfind("Mesa /",0)==0||p.name.rfind("Competição /",0)==0)for(auto&v:p.vertices)v.position.y+=24;
    // Stretch the rear entrance segment to the enlarged auditorium only.
    for(auto&p:room.parts)if(p.name=="Imprensa / entrada"||p.name=="Imprensa / porta"||p.name=="Imprensa / saída")for(auto&v:p.vertices)v.position.z+=290;
    b.box("Imprensa / fechamento posterior",{-500,160,1042},{100,320,12},white);b.box("Imprensa / fechamento posterior",{500,160,1042},{100,320,12},white);
    b.batch();
    for(int slot=0;slot<5;++slot)if(assigned[slot])append_participant(b,*assigned[slot],assigned[slot]==coach.model.get(),s.pose,(slot-2)*132.f,-344);
    room.diagnostic="Sala de imprensa: cinco lugares configuráveis; 48 cadeiras na plateia; palco de 40 cm e degraus; saída lateral; patrocinadores comuns; iluminação interna. "+resources.diagnostic;if(s.press_final&&resources.trophy.parts.empty())room.diagnostic+=" Troféu exato indisponível: suporte vazio, sem substituição por outra competição.";return room;
}
void press_camera_view(Camera&c,int view){
    c.orbit=true;c.speed=170;c.position={0,176,985};c.target={0,166,-329};c.fov=64;
    if(view==1){c.position={0,193,95};c.target={0,167,-347};c.fov=72;}
    else if(view==2){c.position={340,185,257};c.target={-60,142,-300};c.fov=65;}
    else if(view==3){c.position={0,1035,1830};c.target={0,99,290};c.fov=55;}
    else if(view==4){c.position={0,161,-178};c.target={0,100,500};c.fov=72;}
    auto d=sub(c.target,c.position);c.distance=sqrtf(d.x*d.x+d.y*d.y+d.z*d.z);c.pitch=asinf(d.y/c.distance);c.yaw=atan2f(d.x,-d.z);c.synchronize_orbit();
}
void open_press_room(Model&m){
    for(auto&p:m.parts)if(p.name=="Imprensa / teto"||p.name=="Imprensa / teto modular"||p.name=="Imprensa / luminárias"||p.name=="Imprensa / luz frontal"||p.name=="Imprensa / paredes laterais"||p.name=="Imprensa / faixa lateral"||p.name=="Imprensa / entrada"||p.name=="Imprensa / porta"||p.name=="Imprensa / saída"){p.vertices.clear();p.indices.clear();}
}
}
