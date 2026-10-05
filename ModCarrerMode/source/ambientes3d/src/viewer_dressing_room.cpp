#define WIN32_LEAN_AND_MEAN
#include "viewer_dressing_room.h"
#include "viewer_room_geometry.h"
#include <windows.h>
#include <DirectXMath.h>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <map>
#include <sstream>
#include <regex>
#include <stdexcept>
#include <tuple>
#include <cstring>
#include <cwctype>

namespace studio {
using namespace fifa_player;
namespace {
constexpr float pi=3.14159265358979f;
const Vec3 white={.96f,.965f,.97f},metal={.55f,.59f,.62f},ink={.065f,.08f,.095f};
Vec3 add(Vec3 a,Vec3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
Vec3 sub(Vec3 a,Vec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
Vec3 mul(Vec3 a,float s){return {a.x*s,a.y*s,a.z*s};}
Vec3 normalized(Vec3 a){float n=sqrtf(a.x*a.x+a.y*a.y+a.z*a.z);return n>.00001f?mul(a,1/n):Vec3{0,1,0};}
Vec3 cross(Vec3 a,Vec3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
unsigned byte(float c){return unsigned(std::clamp(c,0.f,1.f)*255+.5f);}

using room_geometry::Builder;

Texture material(bool wood){
    Texture t;t.width=t.height=128;t.format=3;t.bytes.resize(128*128*4);
    for(unsigned y=0;y<128;++y)for(unsigned x=0;x<128;++x){unsigned h=(x*1973+y*9277+89173);h=(h^(h>>13))*1274126177;float noise=float(h&255)/255-.5f;
        float grain=.016f*sinf(x*.49f+3*sinf(y*.021f))+.009f*sinf(x*1.8f+y*.012f);
        Vec3 c=wood?Vec3{.76f+grain,.65f+grain,.50f+grain}:Vec3{.49f,.51f,.53f};
        if(!wood&&(x==0||y==0))c={.39f,.41f,.43f};
        float fleck=!wood&&(h&63)<4?.09f:0;
        for(int k=0;k<3;++k)t.bytes[(y*128+x)*4+k]=uint8_t(byte((&c.x)[k]+noise*(wood?.013f:.085f)+fleck));t.bytes[(y*128+x)*4+3]=255;
    }return t;
}
Texture table_material(){
    Texture t;t.width=1024;t.height=512;t.format=3;t.bytes.resize(size_t(t.width)*t.height*4);
    for(unsigned y=0;y<t.height;++y)for(unsigned x=0;x<t.width;++x){float X=x/1024.f,Y=y/512.f;unsigned h=(x*1973+y*9277+89173);h=(h^(h>>13))*1274126177;
        float warp=Y+.018f*sinf(X*13)+.009f*sinf(X*31+Y*4),grain=.035f*sinf(warp*190)+.016f*sinf(warp*440+3*sinf(X*4))+.006f*sinf(warp*980),pore=(h&255)/255.f-.5f;
        for(auto knot:std::array<Vec3,3>{{{.19f,.28f,0},{.74f,.66f,0},{.54f,.13f,0}}}){float dx=(X-knot.x)*2.3f,dy=(Y-knot.y)*6,r=sqrtf(dx*dx+dy*dy);grain+=.018f*sinf(r*150)*expf(-r*8)-.06f*expf(-r*40);}
        Vec3 c={.68f+grain+pore*.012f,.50f+grain*.80f+pore*.009f,.32f+grain*.55f+pore*.007f};for(int k=0;k<3;++k)t.bytes[(size_t(y)*t.width+x)*4+k]=uint8_t(byte((&c.x)[k]));t.bytes[(size_t(y)*t.width+x)*4+3]=255;
    }return t;
}
Texture label(const std::wstring&text,Vec3 background,Vec3 foreground,int height=64){
    Texture t;t.width=512;t.height=unsigned(height);t.format=3;
    BITMAPINFO info={};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=int(t.width);info.bmiHeader.biHeight=-int(t.height);info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    HDC dc=CreateCompatibleDC(nullptr);if(!dc)throw std::runtime_error("Não foi possível criar as placas do vestiário");void*data=nullptr;HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&data,nullptr,0);
    if(!bitmap){DeleteDC(dc);throw std::runtime_error("Não foi possível desenhar as placas do vestiário");}
    auto old=SelectObject(dc,bitmap);RECT rect={0,0,int(t.width),int(t.height)};HBRUSH brush=CreateSolidBrush(RGB(byte(background.x),byte(background.y),byte(background.z)));FillRect(dc,&rect,brush);DeleteObject(brush);
    HFONT font=CreateFontW(-int(height*.56f),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"Segoe UI");auto old_font=SelectObject(dc,font);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(byte(foreground.x),byte(foreground.y),byte(foreground.z)));
    DrawTextW(dc,text.c_str(),int(text.size()),&rect,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS|DT_NOPREFIX);GdiFlush();
    auto*p=static_cast<unsigned char*>(data);t.bytes.resize(t.width*t.height*4);for(size_t i=0;i<t.bytes.size();i+=4){t.bytes[i]=p[i+2];t.bytes[i+1]=p[i+1];t.bytes[i+2]=p[i];t.bytes[i+3]=255;}
    SelectObject(dc,old_font);DeleteObject(font);SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);return t;
}
std::wstring font_family(const std::vector<uint8_t>&data){
    auto u16=[&](size_t p)->unsigned{return p+2<=data.size()?unsigned(data[p])*256+data[p+1]:0;};auto u32=[&](size_t p)->size_t{return p+4<=data.size()?(size_t(data[p])<<24)|(size_t(data[p+1])<<16)|(size_t(data[p+2])<<8)|data[p+3]:0;};
    for(size_t i=0;i<std::min(size_t(u16(4)),size_t(512));++i){size_t p=12+i*16;if(p+16>data.size())break;if(memcmp(data.data()+p,"name",4))continue;size_t start=u32(p+8),length=u32(p+12);if(start>data.size()||length>data.size()-start||length<6)break;size_t strings=start+u16(start+4);
        for(unsigned j=0;j<std::min(u16(start+2),2000u);++j){size_t r=start+6+j*12;if(r+12>start+length)break;if(u16(r)!=3||u16(r+6)!=1)continue;size_t len=u16(r+8),offset=strings+u16(r+10);if(len%2||len>256||offset>data.size()||len>data.size()-offset)continue;std::wstring family;for(size_t k=0;k<len;k+=2)family+=wchar_t(u16(offset+k));if(!family.empty())return family;}
    }return L"Segoe UI";
}
Texture shirt_name(const std::string&name,const std::vector<uint8_t>&font_bytes,Vec3 color){
    Texture t;t.width=512;t.height=96;t.format=3;std::wstring text=wide(name);for(auto&c:text)c=towupper(c);
    DWORD fonts=0;HANDLE resource=font_bytes.empty()?nullptr:AddFontMemResourceEx(const_cast<uint8_t*>(font_bytes.data()),DWORD(font_bytes.size()),nullptr,&fonts);std::wstring family=resource?font_family(font_bytes):L"Segoe UI";
    BITMAPINFO info={};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=512;info.bmiHeader.biHeight=-96;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;void*data=nullptr;HDC dc=CreateCompatibleDC(nullptr);HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&data,nullptr,0);
    if(!dc||!bitmap){if(bitmap)DeleteObject(bitmap);if(dc)DeleteDC(dc);if(resource)RemoveFontMemResourceEx(resource);throw std::runtime_error("Não foi possível desenhar o nome na camisa");}
    auto old=SelectObject(dc,bitmap);RECT rect={0,0,512,96};FillRect(dc,&rect,static_cast<HBRUSH>(GetStockObject(BLACK_BRUSH)));SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(255,255,255));HFONT font=nullptr;HGDIOBJ old_font=nullptr;
    for(int height=70;height>=14;height-=2){if(font){SelectObject(dc,old_font);DeleteObject(font);}font=CreateFontW(-height,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,family.c_str());old_font=SelectObject(dc,font);SIZE extent={};GetTextExtentPoint32W(dc,text.c_str(),int(text.size()),&extent);if(extent.cx<=484)break;}
    DrawTextW(dc,text.c_str(),int(text.size()),&rect,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);GdiFlush();auto*p=static_cast<uint8_t*>(data);t.bytes.resize(512*96*4);
    for(size_t i=0;i<t.bytes.size();i+=4){t.bytes[i]=uint8_t(byte(color.x));t.bytes[i+1]=uint8_t(byte(color.y));t.bytes[i+2]=uint8_t(byte(color.z));t.bytes[i+3]=std::max({p[i],p[i+1],p[i+2]});}
    SelectObject(dc,old_font);DeleteObject(font);SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);if(resource)RemoveFontMemResourceEx(resource);return t;
}
int native_texture(Builder&b,const Model&m,int texture,std::map<int,int>&copied){
    if(texture<0||size_t(texture)>=m.textures.size())return -1;auto it=copied.find(texture);if(it!=copied.end())return it->second;int out=b.texture(m.textures[texture]);copied[texture]=out;return out;
}
bool place_native(Builder&b,const Model&m,const Part&source,const std::string&name,Vec3 center,float height,float max_width,bool hang,std::map<int,int>&textures){
    if(source.vertices.empty())return false;Vec3 low={FLT_MAX,FLT_MAX,FLT_MAX},high={-FLT_MAX,-FLT_MAX,-FLT_MAX};
    for(auto&v:source.vertices)for(int k=0;k<3;++k){(&low.x)[k]=std::min((&low.x)[k],(&v.position.x)[k]);(&high.x)[k]=std::max((&high.x)[k],(&v.position.x)[k]);}
    auto size=sub(high,low);float scale=std::min(height/std::max(.1f,size.y),max_width/std::max(.1f,size.x));Vec3 middle=mul(add(low,high),.5f);
    Part p=source;p.name=name;p.asset="studio/dressing/native/"+source.asset;p.skinned=false;p.texture=native_texture(b,m,source.texture,textures);p.hair_coeff_texture=-1;
    for(auto&v:p.vertices){auto q=mul(sub(v.position,middle),scale);q.y=hang?center.y+(v.position.y-high.y)*scale:center.y+(v.position.y-low.y)*scale;if(hang){q.x=-q.x;q.z=-q.z;v.normal.x=-v.normal.x;v.normal.z=-v.normal.z;}q.x+=center.x;q.z+=center.z;v.position=b.point(q);v.normal=b.direction(v.normal);}
    b.room.parts.push_back(std::move(p));return true;
}
void towel(Builder&b,const std::string&name,Vec3 p,Vec3 accent,bool rolled){
    Vec3 linen={.94f,.935f,.91f};
    if(rolled){b.tube(name,add(p,{-13,0,0}),add(p,{13,0,0}),5,linen,24);for(float x:{-13.2f,13.2f}){b.tube(name,add(p,{x,0,0}),add(p,{x+.2f,0,0}),3.7f,{.76f,.77f,.74f},24);b.tube(name,add(p,{x+.25f,0,0}),add(p,{x+.4f,0,0}),2.4f,linen,24);}}
    else{b.box(name,p,{28,2.5f,22},linen);b.box(name,add(p,{0,1.4f,6}),{28,.25f,2},accent);b.box(name,add(p,{0,0,11.1f}),{27,.45f,.3f},{.77f,.78f,.76f});}
}
void bottle(Builder&b,const std::string&name,Vec3 p,Vec3 accent,int variation=0){
    // Closed sports bottle: rounded foot/shoulder, ribbed grip and push nozzle.
    float h=22+float(variation%3)*1.5f;Vec3 body={.82f,.88f,.90f};
    b.tube(name,p,add(p,{0,.7f,0}),2.9f,body,32);b.frustum(name,add(p,{0,.6f,0}),2.9f,3.65f,1.8f,body);
    b.tube(name,add(p,{0,2.4f,0}),add(p,{0,h-6,0}),3.65f,body,32);
    for(float y:{3.2f,5.f,14.f,15.7f})b.tube(name,add(p,{0,y,0}),add(p,{0,y+.35f,0}),3.78f,{.66f,.75f,.79f},32);
    b.tube(name,add(p,{0,7,0}),add(p,{0,12,0}),3.73f,accent,32);
    b.frustum(name,add(p,{0,h-6,0}),3.65f,2.1f,3.4f,body);b.tube(name,add(p,{0,h-2.6f,0}),add(p,{0,h,0}),2.15f,ink,28);
    b.tube(name,add(p,{0,h,0}),add(p,{0,h+1.3f,0}),1.05f,{.7f,.76f,.8f},20);b.tube(name,add(p,{0,h+1.3f,0}),add(p,{0,h+1.65f,0}),1.3f,ink,20);
    b.crest(name,add(p,{0,9.5f,3.85f}),4);
}
void native_ball(Builder&b,const Model&source,const std::string&name,Vec3 center,float yaw,std::map<int,int>&textures){
    if(source.parts.empty())return;Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};
    for(auto&p:source.parts)for(auto&v:p.vertices)for(int k=0;k<3;++k){(&lo.x)[k]=std::min((&lo.x)[k],(&v.position.x)[k]);(&hi.x)[k]=std::max((&hi.x)[k],(&v.position.x)[k]);}
    auto dimensions=sub(hi,lo),middle=mul(add(lo,hi),.5f);float scale=22/std::max({dimensions.x,dimensions.y,dimensions.z,.01f});
    for(auto p:source.parts){p.name=name;p.skinned=false;p.texture=native_texture(b,source,p.texture,textures);p.hair_coeff_texture=-1;
        for(auto&v:p.vertices){auto q=mul(sub(v.position,middle),scale);q={q.x*cosf(yaw)+q.z*sinf(yaw),q.y,-q.x*sinf(yaw)+q.z*cosf(yaw)};v.position=b.point(add(center,q));auto n=v.normal;v.normal=b.direction({n.x*cosf(yaw)+n.z*sinf(yaw),n.y,-n.x*sinf(yaw)+n.z*cosf(yaw)});}
        b.room.parts.push_back(std::move(p));
    }
}
void bag(Builder&b,const std::string&name,Vec3 p,Vec3 accent){
    b.box(name,add(p,{0,10,0}),{42,20,23},ink);b.box(name,add(p,{0,10,11.8f}),{34,12,1},accent);b.box(name,add(p,{0,20.2f,0}),{34,.7f,.6f},metal);b.crest(name,add(p,{0,10,12.5f}),9);
    for(float x:{-9.f,9.f})b.tube(name,add(p,{x,18,-2}),add(p,{x,27,-2}),.8f,ink);b.tube(name,add(p,{-9,27,-2}),add(p,{9,27,-2}),1,ink);
    for(float x:{-16.f,16.f})b.box(name,add(p,{x,10,12.1f}),{1.2f,19,.4f},{.7f,.72f,.74f});
}
void notebook(Builder&b,Vec3 accent){
    const std::string name="Mesa do técnico / computador";b.frame({14,0,62},-.10f);Vec3 aluminum={.40f,.44f,.47f};
    b.rounded_box(name,{0,80,0},{38,1.8f,27},.75f,aluminum);b.rounded_box(name,{0,81.05f,-2},{35,.3f,20},.1f,{.31f,.35f,.38f});
    b.tube(name,{-15,81,-11},{15,81,-11},.8f,ink,24);
    for(int x=0;x<13;++x)for(int z=0;z<4;++z)b.rounded_box(name,{-14.4f+x*2.4f,81.4f,-8.5f+z*2.9f},{2.05f,.4f,2.1f},.17f,ink);
    b.rounded_box(name,{0,81.5f,3.8f},{13,.3f,1.5f},.13f,ink);b.rounded_box(name,{0,81.4f,8.8f},{10,.2f,5.2f},.08f,{.23f,.27f,.30f});
    b.box(name,{17.9f,81.5f,-8},{1.5f,.2f,.7f},accent);
    for(float z:{-5.f,1.f,6.f})b.box(name,{-19.05f,80,z},{.14f,.65f,2.5f},ink);
    for(int i=0;i<8;++i)b.box(name,{19.05f,80,-6.f+i*1.2f},{.14f,.55f,.55f},ink);
    size_t first=b.room.parts.size();b.rounded_box(name,{0,93,-11.5f},{38,25,1.6f},.7f,ink);
    b.box(name,{0,93,-10.6f},{34,20.5f,.12f},{.065f,.115f,.15f});
    b.panel(name,{0,101,-10.4f},29,2.6f,b.texture(label(L"ANÁLISE DO ELENCO",{.065f,.115f,.15f},{.85f,.91f,.94f},64)));
    auto line=[&](float x,float y,float X,float Y){b.tube(name,{x,y,-10.35f},{X,Y,-10.35f},.07f,{.46f,.70f,.72f},8);};
    line(-14,85,1,85);line(1,85,1,96);line(1,96,-14,96);line(-14,96,-14,85);line(-6.5f,85,-6.5f,96);
    for(int i=0;i<24;++i){float a=i*2*pi/24,A=(i+1)*2*pi/24;line(-6.5f+2*cosf(a),90.5f+2*sinf(a),-6.5f+2*cosf(A),90.5f+2*sinf(A));}
    for(int i=0;i<11;++i)b.tube(name,{-12.f+(i%4)*3,87.f+(i/4)*3,-10.35f},{-12.f+(i%4)*3,87.f+(i/4)*3,-10.15f},.3f,white,12);
    for(int i=0;i<5;++i){float height=4.f+(i*7)%6;b.box(name,{5.f+i*2.1f,85+height/2,-10.35f},{1.2f,height,.1f},i%2?Vec3{.28f,.66f,.64f}:Vec3{.57f,.73f,.8f});}
    b.tube(name,{0,104.1f,-10.5f},{0,104.1f,-10.3f},.35f,{.31f,.39f,.45f},16);
    // Tilt the whole lid around the real hinge, including the screen contents.
    for(size_t i=first;i<b.room.parts.size();++i)for(auto&v:b.room.parts[i].vertices){auto q=b.local(v.position);q.y-=81;q.z+=11.5f;float y=q.y*cosf(-.24f)-q.z*sinf(-.24f),z=q.y*sinf(-.24f)+q.z*cosf(-.24f);v.position=b.point({q.x,y+81,z-11.5f});auto n=v.normal;n={n.x,n.y*cosf(-.24f)-n.z*sinf(-.24f),n.y*sinf(-.24f)+n.z*cosf(-.24f)};v.normal=n;}
    b.frame();
}
void coach_table(Builder&b,Vec3 accent,int wood){
    const std::string name="Mesa do técnico";
    b.rounded_box(name+" / tampo",{0,76,95},{220,6,104},2.7f,{1,1,1},b.texture(table_material()));
    // Planar UVs follow the actual tabletop, not the rounded mesh's uneven grid.
    for(auto&v:b.room.parts.back().vertices){auto q=b.local(v.position);if(fabsf(v.normal.y)>.5f){v.u=(q.x+110)/220;v.v=(q.z-43)/104;}else{v.u=(q.x+110)/220;v.v=(q.y-73)/6;}}
    b.rounded_box(name+" / borda",{0,72.5f,95},{209,1.5f,95},.65f,{.28f,.23f,.17f});
    b.rounded_box(name+" / apoio do notebook",{14,79.1f,62},{49,.2f,38},.09f,{.11f,.14f,.16f});
    b.rounded_box(name,{0,22,95},{205,3,88},1.3f,{.87f,.9f,.91f});
    for(float x:{-94.f,94.f}){for(float z:{54.f,136.f}){b.rounded_box(name,{x,38,z},{5,73,5},1.3f,metal);b.rounded_box(name,{x,2,z},{6,3,6},1,ink);}b.tube(name,{x,14,54},{x,14,136},2.1f,metal);}
    b.tube(name,{-94,69,95},{94,69,95},2,metal);
    // Tactical clipboard on the tabletop, with a small 3D pitch and magnets.
    b.box(name+" / prancheta",{-47,80,98},{45,1.6f,32},ink);b.box(name+" / prancheta",{-47,81,98},{41,.2f,28},white);
    auto line=[&](float x,float z,float X,float Z){b.tube(name+" / prancheta",{x,81.3f,z},{X,81.3f,Z},.14f,{.17f,.26f,.27f},8);};
    line(-65,86,-29,86);line(-29,86,-29,110);line(-29,110,-65,110);line(-65,110,-65,86);line(-47,86,-47,110);
    for(int i=0;i<24;++i){float a=i*2*pi/24,A=(i+1)*2*pi/24;line(-47+3.5f*cosf(a),98+3.5f*sinf(a),-47+3.5f*cosf(A),98+3.5f*sinf(A));}
    for(int i=0;i<11;++i)b.tube(name+" / prancheta",{-62.f+(i%4)*8,81.4f,90.f+(i/4)*7},{-62.f+(i%4)*8,82,90.f+(i/4)*7},.75f,accent,16);
    b.box(name+" / prancheta",{-47,82.1f,84},{11,1.4f,3},metal);
    // Laptop, session notebook, marker set, whistle and spare club kit bag.
    notebook(b,accent);
    b.box(name+" / plano de treino",{63,81,117},{30,3,23},accent);b.box(name+" / plano de treino",{63,82.7f,117},{25,.15f,18},white);
    for(int i=0;i<7;++i)b.box(name+" / plano de treino",{63,82.9f,111.f+i*1.6f},{19,.12f,.12f},{.3f,.36f,.42f});
    for(int i=0;i<4;++i){Vec3 c=i==0?accent:i==1?Vec3{.16f,.39f,.7f}:i==2?Vec3{.86f,.15f,.13f}:ink;b.tube(name+" / marcadores",{-87.f+i*3,80,122},{-87.f+i*3,80,134},.65f,c,12);b.tube(name+" / marcadores",{-87.f+i*3,80,133},{-87.f+i*3,80,135},.72f,ink,12);}
    b.box(name+" / apito",{8,81,122},{5,3,2.5f},metal);b.tube(name+" / apito",{10,81,122},{14,81,122},1.25f,metal,16);
    for(int i=0;i<32;++i){float a=i*2*pi/32,A=(i+1)*2*pi/32;b.tube(name+" / apito",{2+10*cosf(a),79.5f,122+7*sinf(a)},{2+10*cosf(A),79.5f,122+7*sinf(A)},.17f,ink,8);}
    for(int i=0;i<5;++i)bottle(b,name+" / garrafas",{-91.f+i*12,79,62},accent,i);
    towel(b,name+" / toalhas",{77,80.25f,69},accent,false);towel(b,name+" / toalhas",{77,83,69},accent,false);
    bag(b,name+" / bolsa reserva",{18,24,102},accent);
}
void caster(Builder&b,const std::string&name,Vec3 p,float radius=6){
    b.tube(name,add(p,{-2.3f,0,0}),add(p,{2.3f,0,0}),radius,ink,32);
    for(float x:{-2.55f,2.55f}){b.tube(name,add(p,{x,0,0}),add(p,{x+.15f,0,0}),radius*.58f,metal,24);b.tube(name,add(p,{x+.2f,0,0}),add(p,{x+.3f,0,0}),1.1f,ink,16);b.tube(name,add(p,{x,0,0}),add(p,{x,radius+4,2}),.65f,metal,12);}
    b.tube(name,add(p,{-2.5f,radius+4,2}),add(p,{2.5f,radius+4,2}),1.1f,metal,16);b.tube(name,add(p,{0,radius+4,2}),add(p,{0,radius+9,2}),1.4f,metal,20);
}
void ball_cart(Builder&b){
    const std::string name="Equipamentos / carrinho de bolas";Vec3 c={-280,0,335};
    b.rounded_box(name,add(c,{0,23,0}),{106,4,78},1.8f,{.84f,.88f,.9f});
    for(float x:{-46.f,46.f})for(float z:{-33.f,33.f}){caster(b,name,add(c,{x,6,z}));b.tube(name,add(c,{x,21,z}),add(c,{x,78,z}),1.4f,metal,24);}
    for(float y:{38.f,57.f,78.f})b.rim(name,add(c,{0,y,0}),100,72,5,1.1f,metal);
    for(float x=-38;x<=38;x+=12)for(float z:{-35.f,35.f})b.tube(name,add(c,{x,25,z}),add(c,{x,77,z}),.45f,{.44f,.49f,.53f},10);
    for(float z=-24;z<=24;z+=12)for(float x:{-49.f,49.f})b.tube(name,add(c,{x,25,z}),add(c,{x,77,z}),.45f,{.44f,.49f,.53f},10);
    for(float x:{-42.f,42.f}){b.tube(name,add(c,{x,75,35}),add(c,{x,94,47}),1.4f,metal,20);b.tube(name,add(c,{x,94,47}),add(c,{x,97,44}),1.4f,metal,20);}
    b.tube(name,add(c,{-42,97,44}),add(c,{42,97,44}),1.8f,ink,24);
}
void water_station(Builder&b,Vec3 accent,int wood){
    const std::string name="Hidratação";
    b.rounded_box(name,{0,53,24},{124,101,47},3,white);b.rounded_box(name,{0,107,24},{128,5,49},2,{1,1,1},wood);
    b.rounded_box(name,{0,51,48},{112,78,2},.8f,accent);b.crest(name,{0,54,49.4f},24);
    b.box(name+" / armário",{0,53,49.2f},{.35f,73,.3f},ink);for(float x:{-5.f,5.f})b.tube(name+" / armário",{x,76,50},{x,66,50},.6f,metal,16);
    for(float x:{-51.f,51.f})for(float z:{9.f,39.f})b.rounded_box(name,{x,2,z},{5,4,5},1.5f,ink);
    b.rounded_box(name+" / bandeja",{-28,110,25},{55,1,30},.45f,metal);b.rim(name+" / bandeja",{-28,111,25},52,27,3,.5f,metal);
    for(int i=0;i<4;++i)bottle(b,name+" / garrafas",{-46.f+12*i,110.5f,24},accent,i);
    // Drinking-water dispenser and sealed refill tank, standing beside counter.
    size_t dispenser_begin=b.room.parts.size();
    b.rounded_box(name+" / bebedouro",{79,53,24},{43,104,39},5,white);b.rounded_box(name+" / bebedouro",{79,6,24},{41,8,36},3,ink);
    b.rounded_box(name+" / bebedouro",{79,77,42},{34,34,4},1.8f,{.17f,.22f,.26f});
    b.rounded_box(name+" / bebedouro",{79,61,48},{35,3,13},1.3f,metal);b.rounded_box(name+" / bebedouro",{79,62.5f,48},{30,.6f,10},.2f,ink);
    for(int i=0;i<10;++i)b.box(name+" / bebedouro",{66.f+i*2.8f,62.95f,48},{.5f,.1f,8},metal);
    for(int i=0;i<7;++i)b.rounded_box(name+" / bebedouro",{79,18.f+i*3,43.2f},{28,.75f,.2f},.09f,{.4f,.44f,.46f});
    b.rounded_box(name+" / bebedouro",{79,101,24},{38,3,34},1.3f,{.61f,.66f,.69f});
    for(int i=0;i<2;++i){float x=71.f+i*15;Vec3 c=i?Vec3{.86f,.19f,.17f}:Vec3{.14f,.37f,.76f};b.tube(name+" / bebedouro",{x,82,43},{x,82,50},1.4f,metal);b.tube(name+" / bebedouro",{x,82,50},{x,78,50},1.3f,metal);b.box(name+" / bebedouro",{x,85,47},{4,2,7},c);}
    b.tube(name+" / bebedouro",{79,103,24},{79,110,24},8.2f,{.69f,.74f,.77f},32);
    Vec3 tank={.53f,.74f,.87f};b.tube(name+" / bebedouro",{79,109,24},{79,114,24},7,tank,32);b.frustum(name+" / bebedouro",{79,114,24},7,16,5,tank);b.tube(name+" / bebedouro",{79,119,24},{79,145,24},16,tank,40);b.frustum(name+" / bebedouro",{79,145,24},16,12,4,tank);
    for(float y:{122.f,128.f,141.f})b.tube(name+" / bebedouro",{79,y,24},{79,y+1.2f,24},16.4f,{.47f,.68f,.82f},40);
    // Wider counter leaves a proper gap beside the dispenser, without intersection.
    auto offset=b.direction({31,0,0});for(size_t i=dispenser_begin;i<b.room.parts.size();++i)for(auto&v:b.room.parts[i].vertices)v.position=add(v.position,offset);
    b.tube(name+" / copos",{19,110,29},{19,125,29},3.7f,white,24);for(float y=111;y<125;y+=2)b.tube(name+" / copos",{19,y,29},{19,y+.4f,29},3.9f,{.73f,.77f,.79f},24);
    b.rounded_box(name+" / toalhas",{39,110,24},{29,1,28},.4f,white);towel(b,name+" / toalhas",{38,112,24},accent,false);towel(b,name+" / toalhas",{38,114.6f,24},accent,false);
    b.rounded_box(name+" / refrigerador",{-102,48,25},{49,94,49},3.5f,white);b.rounded_box(name+" / refrigerador",{-102,48,51},{43,85,3},2,{.22f,.29f,.33f});b.rounded_box(name+" / refrigerador",{-102,99,25},{52,4,52},1.7f,white);
    b.tube(name+" / refrigerador",{-86,70,54},{-86,48,54},.9f,metal);for(int i=0;i<5;++i)b.box(name+" / refrigerador",{-102,13.f+i*2.2f,53},{30,.65f,.35f},ink);
    b.panel(name+" / refrigerador",{-102,83,53},36,5,b.texture(label(L"BEBIDAS",{.22f,.29f,.33f},white,64)));
    b.box(name+" / identificação",{0,153,2},{126,19,2},accent);b.panel(name+" / identificação",{0,153,3.7f},118,13,b.texture(label(L"ÁGUA E HIDRATAÇÃO",accent,{1,1,1},80)));
}
void medical_area(Builder&b,Vec3 accent){
    const std::string name="Área médica";Vec3 upholstery={.76f,.82f,.83f},red={.83f,.1f,.13f};
    // Full treatment couch, facing the room, with pillow and examination roll.
    b.rounded_box(name+" / maca",{295,73,176},{72,6,183},2.7f,ink);b.rounded_box(name+" / maca",{295,80,191},{70,10,151},4.5f,upholstery);b.rounded_box(name+" / maca",{295,87,101},{70,12,29},5,upholstery);
    b.rim(name+" / maca",{295,81.5f,191},66,147,6,.2f,{.57f,.64f,.65f});
    for(float x:{267.f,323.f})for(float z:{105.f,251.f}){b.tube(name+" / maca",{x,18,z},{x,71,z},1.7f,metal,24);caster(b,name+" / maca",{x,6,z});}
    for(float x:{267.f,323.f})b.tube(name+" / maca",{x,24,105},{x,24,251},1.5f,metal);b.rounded_box(name+" / maca",{295,96,103},{36,7,21},3.2f,white);
    b.rounded_box(name+" / maca",{295,85.25f,220},{60,.6f,70},.27f,{.95f,.95f,.92f});b.tube(name+" / maca",{269,63,266},{321,63,266},5,white,32);
    // Mobile cart with dressings, bandage rolls, antiseptic, glove box and icebox.
    for(float x:{347.f,393.f})for(float z:{303.f,342.f}){b.tube(name+" / carrinho",{x,18,z},{x,89,z},1.3f,metal,24);caster(b,name+" / carrinho",{x,6,z});}
    b.rounded_box(name+" / carrinho",{370,85,322},{54,3,46},1.3f,white);b.rounded_box(name+" / carrinho",{370,39,322},{54,3,46},1.3f,white);
    b.rim(name+" / carrinho",{370,89,322},52,43,4,1,metal);b.rim(name+" / carrinho",{370,43,322},52,43,4,1,metal);
    b.tube(name+" / carrinho",{347,87,342},{347,101,350},1.2f,metal,20);b.tube(name+" / carrinho",{393,87,342},{393,101,350},1.2f,metal,20);b.tube(name+" / carrinho",{347,101,350},{393,101,350},1.5f,ink,24);
    b.box(name+" / luvas",{381,92,324},{22,10,16},{.24f,.52f,.68f});b.box(name+" / luvas",{381,97.3f,324},{10,.4f,4},white);
    for(int i=0;i<3;++i){float z=308.f+12*i;b.tube(name+" / ataduras",{353,90,z},{361,90,z},3.5f,white,24);b.tube(name+" / ataduras",{361.1f,90,z},{361.4f,90,z},1.6f,{.78f,.78f,.73f},16);}
    b.tube(name+" / antisséptico",{379,86.5f,306},{379,102,306},3.3f,{.67f,.8f,.82f},28);b.tube(name+" / antisséptico",{379,102,306},{379,106,306},1.8f,white,20);b.box(name+" / antisséptico",{381,106,306},{7,2,2},white);
    b.box(name+" / gelo",{370,55,322},{33,27,30},accent);b.box(name+" / gelo",{370,70,322},{36,4,32},white);
    towel(b,name+" / toalhas",{287,41.75f,171},accent,false);towel(b,name+" / toalhas",{287,44.5f,171},accent,false);b.box(name+" / maca",{295,38,176},{61,5,155},white);
    // Adjustable exam lamp, with no exterior/sun source.
    b.disc(name+" / luminária",{221,3,96},19,metal);b.tube(name+" / luminária",{221,4,96},{221,154,96},2,metal);b.tube(name+" / luminária",{221,154,96},{261,179,96},1.8f,metal);b.tube(name+" / luminária",{261,179,96},{277,162,96},1.8f,metal);
    b.tube(name+" / luminária",{277,161,96},{277,165,96},9,white,32);b.tube(name+" / luminária",{277,160.6f,96},{277,161,96},7.8f,{1.16f,1.15f,1.1f},32);
    // Wall supplies/cross and towel rail near the examination corner.
    b.frame({432,0,552+dressing_entrance_shift},pi);b.box(name+" / primeiros socorros",{0,175,2},{70,64,16},white);b.box(name+" / primeiros socorros",{0,175,10.5f},{63,57,1},white);b.box(name+" / primeiros socorros",{0,175,11.6f},{9,29,.4f},red);b.box(name+" / primeiros socorros",{0,175,12},{29,9,.4f},red);
    b.box(name+" / identificação",{0,223,3},{93,17,2},accent);b.panel(name+" / identificação",{0,223,4.8f},85,12,b.texture(label(L"APOIO MÉDICO",accent,{1,1,1},80)));
    b.tube(name+" / toalheiro",{-36,124,20},{36,124,20},1.3f,metal);for(float x:{-23.f,0.f,23.f}){b.box(name+" / toalheiro",{x,101,23},{18,46,1.8f},white);b.box(name+" / toalheiro",{x,81,24},{18,2,.4f},accent);}b.frame();
}
void chalkboard(Builder&b,int wood){
    const std::string name="Quadro negro / análises";Vec3 board_color={.055f,.083f,.071f},chalk={.76f,.8f,.74f};
    b.frame({210,0,552+dressing_entrance_shift},pi);b.rounded_box(name,{0,189,2},{198,122,4},1.8f,{1,1,1},wood);b.rounded_box(name,{0,189,4.3f},{188,111,.7f},.3f,board_color);
    b.panel(name,{0,235,5.2f},167,9,b.texture(label(L"ANÁLISE TÁTICA",board_color,chalk,64)));
    b.panel(name,{-46,218,5.2f},76,7,b.texture(label(L"POSSE  /  PRESSÃO",board_color,chalk,64)));
    auto line=[&](float x,float y,float X,float Y,Vec3 c){b.tube(name,{x,y,5.15f},{X,Y,5.15f},.16f,c,8);};
    line(-85,152,-12,152,chalk);line(-85,152,-85,207,chalk);
    float heights[]={9,21,17,34,41,37};for(int i=0;i<6;++i){float x=-80.f+i*12;line(x,152,x,152+heights[i],{.42f,.61f,.69f});if(i<5)line(x,159+heights[i],x+12,159+heights[i+1],chalk);}
    for(int i=0;i<3;++i)line(-85,165.f+i*14,-12,165.f+i*14,{.13f,.18f,.15f});
    b.panel(name,{-46,142,5.2f},78,7,b.texture(label(L"1    2    3    4    5    6",board_color,chalk,64)));
    line(6,147,85,147,chalk);line(85,147,85,213,chalk);line(85,213,6,213,chalk);line(6,213,6,147,chalk);line(45.5f,147,45.5f,213,chalk);
    for(int i=0;i<40;++i){float a=i*2*pi/40,A=(i+1)*2*pi/40;line(45.5f+9*cosf(a),180+9*sinf(a),45.5f+9*cosf(A),180+9*sinf(A),chalk);}
    for(int i=0;i<11;++i){float x=13.f+(i%4)*20,y=158.f+(i/4)*20;for(int k=0;k<16;++k){float a=k*2*pi/16,A=(k+1)*2*pi/16;line(x+1.8f*cosf(a),y+1.8f*sinf(a),x+1.8f*cosf(A),y+1.8f*sinf(A),chalk);}}
    for(float y:{161.f,197.f}){line(33,y,50,y+3,{.55f,.66f,.76f});line(50,y+3,45,y+6,{.55f,.66f,.76f});line(50,y+3,45,y,{.55f,.66f,.76f});}
    for(int i=0;i<16;++i){float x=-88.f+(i*13)%169,y=154.f+(i*19)%55;line(x,y,x+4,y+.5f,{.10f,.13f,.11f});}
    b.rounded_box(name,{0,127,7},{198,3,10},1.3f,metal);b.rounded_box(name,{-63,130,8},{12,3,5},1,{.32f,.34f,.29f});
    for(int i=0;i<3;++i)b.tube(name,{56.f+i*8,129.3f,8},{62.f+i*8,129.3f,8},.55f,i==2?Vec3{.61f,.74f,.85f}:chalk,12);
    b.frame();
}
void board(Builder&b,Vec3 accent,Vec3 secondary){
    const std::string name="Quadro tático";float z=-205;
    b.box(name,{0,169,z-3},{161,111,4},metal);b.box(name,{0,169,z},{155,105,2},white);
    // Landscape pitch, in real 3D, including boxes, centre circle and magnets.
    auto line=[&](float x,float y,float X,float Y){b.tube(name,{x,y,z+1.3f},{X,Y,z+1.3f},.35f,{.19f,.25f,.27f},8);};
    float l=-68,r=68,bottom=125,top=213;line(l,bottom,r,bottom);line(r,bottom,r,top);line(r,top,l,top);line(l,top,l,bottom);line(0,bottom,0,top);
    for(int i=0;i<64;++i){float a=2*pi*i/64,A=2*pi*(i+1)/64;line(13*cosf(a),169+13*sinf(a),13*cosf(A),169+13*sinf(A));}
    for(float side:{-1.f,1.f}){float x=side*68,X=side*45;line(x,146,X,146);line(X,146,X,192);line(X,192,x,192);line(x,158,side*59,158);line(side*59,158,side*59,180);line(side*59,180,x,180);b.tube(name,{side*51,169,z+1.6f},{side*51,169,z+2.2f},.8f,ink,12);}
    Vec3 home=accent;if(home.x+home.y+home.z>2.2f)home={.08f,.3f,.68f};Vec3 opponent={.86f,.16f,.13f};if(home.x>.6f&&home.y<.35f)opponent={.12f,.35f,.78f};
    float positions[][2]={{-61,169},{-42,140},{-42,158},{-42,180},{-42,198},{-17,148},{-17,169},{-17,191},{15,142},{25,169},{15,196}};
    for(auto&p:positions){b.tube(name,{p[0],p[1],z+2},{p[0],p[1],z+3.7f},2.1f,home,20);b.tube(name,{p[0],p[1],z+3.8f},{p[0],p[1],z+4},.5f,white,12);}
    for(int i=0;i<7;++i)b.tube(name,{float(34+(i%2)*18),float(139+(i/2)*20),z+2},{float(34+(i%2)*18),float(139+(i/2)*20),z+3.7f},2.1f,opponent,20);
    for(float y:{148.f,191.f}){b.tube(name,{-14,y,z+2},{8,y,z+2},.6f,{.14f,.36f,.69f},10);b.tube(name,{8,y,z+2},{4,y+3,z+2},.6f,{.14f,.36f,.69f},10);b.tube(name,{8,y,z+2},{4,y-3,z+2},.6f,{.14f,.36f,.69f},10);}
    b.box(name,{0,114,z+3},{161,3,9},metal);b.box(name,{-45,117,z+4},{12,3,4},ink);for(int i=0;i<3;++i)b.tube(name,{25.f+i*7,117,z+4},{25.f+i*7,119,z+4},.8f,i==0?home:i==1?opponent:ink,12);
    for(float x:{-70.f,70.f}){b.tube(name,{x,16,z-5},{x,117,z-5},2.2f,metal);b.tube(name,{x,15,z-27},{x,15,z+24},2.2f,metal);for(float Z:{z-25,z+22})b.tube(name,{x-2,9,Z},{x+2,9,Z},5,ink,20);}
    b.crest(name,{64,217,z+2},9);b.box("Painel do clube",{0,266,-304},{190,29,3},accent);b.crest("Painel do clube",{0,266,-301},25);
}

bool back_surface(const std::vector<Vec3>&vertices,const Part&shirt,float x,float y,float&z){
    z=-FLT_MAX;bool found=false;for(size_t i=0;i<shirt.indices.size();i+=3){auto a=vertices[shirt.indices[i]],B=vertices[shirt.indices[i+1]],c=vertices[shirt.indices[i+2]];if(x<std::min({a.x,B.x,c.x})||x>std::max({a.x,B.x,c.x})||y<std::min({a.y,B.y,c.y})||y>std::max({a.y,B.y,c.y}))continue;float denominator=(B.y-c.y)*(a.x-c.x)+(c.x-B.x)*(a.y-c.y);if(fabsf(denominator)<.00001f)continue;float A=((B.y-c.y)*(x-c.x)+(c.x-B.x)*(y-c.y))/denominator,bb=((c.y-a.y)*(x-c.x)+(a.x-c.x)*(y-c.y))/denominator,cc=1-A-bb;if(A<-.0001f||bb<-.0001f||cc<-.0001f)continue;float depth=A*a.z+bb*B.z+cc*c.z;z=std::max(z,depth);found=true;}return found;
}
void fitted_hanger(Builder&b,const Part&shirt,const std::string&name){
    std::vector<Vec3>vertices;for(auto&v:shirt.vertices)vertices.push_back(b.local(v.position));
    auto top=[&](float x){float height=-FLT_MAX;for(size_t i=0;i<shirt.indices.size();i+=3)for(int k=0;k<3;++k){auto a=vertices[shirt.indices[i+k]],c=vertices[shirt.indices[i+(k+1)%3]];if(fabsf(a.x-c.x)<.0001f||x<std::min(a.x,c.x)||x>std::max(a.x,c.x))continue;float t=(x-a.x)/(c.x-a.x);height=std::max(height,a.y+(c.y-a.y)*t);}return height==-FLT_MAX?195.f:height;};
    float apex=top(0)-1.2f,left=top(-19)-1.2f,right=top(19)-1.2f,depth=42;
    float surface;if(back_surface(vertices,shirt,0,apex-2,surface))depth=surface-1.7f;
    // Shoulder bars sit inside the actual cloth; only the throat/hook emerges.
    b.tube(name,{-19,left,depth},{0,apex,depth},.65f,ink,20);b.tube(name,{0,apex,depth},{19,right,depth},.65f,ink,20);
    b.tube(name,{-19,left,depth},{19,right,depth},.65f,ink,20);
    b.tube(name,{0,apex,depth},{0,206,depth},.55f,metal,20);b.tube(name,{0,206,depth},{0,211.05f,32},.55f,metal,20);
    constexpr float hook_y=213.45f,hook_radius=2.4f;for(int i=0;i<28;++i){float a=-pi/2+i*(pi*1.58f)/28,A=-pi/2+(i+1)*(pi*1.58f)/28;b.tube(name,{0,hook_y+hook_radius*sinf(a),32+hook_radius*cosf(a)},{0,hook_y+hook_radius*sinf(A),32+hook_radius*cosf(A)},.65f,metal,12);}
}
void print_digit(Builder&b,const Part&shirt,const std::string&name,int texture,float center,float top,float width,float height){
    // Tessellated print follows the actual native jersey back, not a floating card.
    Part p;p.name=name;p.asset="studio/dressing/kit-number/native-digit";p.texture=texture;p.blend=true;p.native_normals=true;
    std::vector<Vec3>local;local.reserve(shirt.vertices.size());for(auto&v:shirt.vertices)local.push_back(b.local(v.position));
    constexpr int nx=8,ny=16;
    for(int y=0;y<ny;++y)for(int x=0;x<nx;++x){float u=float(x)/nx,U=float(x+1)/nx,v=float(y)/ny,V=float(y+1)/ny;float X=center-width*.5f+u*width,XX=center-width*.5f+U*width,Y=top-v*height,YY=top-V*height;Vec3 points[]={{X,Y,0},{XX,Y,0},{XX,YY,0},{X,YY,0}};bool valid=true;for(auto&q:points){float depth;if(!back_surface(local,shirt,q.x,q.y,depth)){valid=false;break;}q.z=depth+.9f;}if(!valid)continue;
        uint32_t offset=uint32_t(p.vertices.size());float uv[][2]={{u,v},{U,v},{U,V},{u,V}};auto normal=normalized(cross(sub(points[3],points[0]),sub(points[1],points[0])));if(normal.z<0)normal=mul(normal,-1);
        for(int k=0;k<4;++k){Vertex q={};q.position=b.point(points[k]);q.normal=b.direction(normal);q.u=uv[k][0];q.v=uv[k][1];p.vertices.push_back(q);}for(auto i:{0,1,2,0,2,3})p.indices.push_back(offset+unsigned(i));
    }if(!p.indices.empty())b.room.parts.push_back(std::move(p));
}
void locker(Builder&b,const Model&source,const ClubPlayerRow*row,size_t index,Vec3 accent,Vec3 secondary,int wood,const KitNumberSet*number_set,std::map<std::pair<const KitNumberSet*,int>,int>&digit_textures,const DressingPrints&prints){
    std::string prefix="Armário "+std::to_string(index+1);if(row)prefix+=" — "+std::string(row->name);
    std::string kit=prefix+" / uniforme",shoes=prefix+" / chuteiras",equipment=prefix+" / acessórios";
    b.box(prefix,{0,131,1},{84,246,6},white);b.box(prefix,{0,158,5},{77,154,2},{1,1,1},wood);
    for(float x:{-42.f,42.f})b.box(prefix,{x,130,30},{4,250,64},white);
    b.box(prefix,{0,225,31},{82,4,63},white);b.box(prefix,{0,250,31},{84,4,64},white);
    b.box(prefix,{0,72,28},{82,4,58},white);b.box(prefix,{0,9,29},{82,4,58},white);
    b.box(prefix,{0,258,69},{83,23,2},accent);
    std::wstring text=row?wide(row->name):L"VESTIÁRIO";
    Vec3 fg=accent.x*.2126f+accent.y*.7152f+accent.z*.0722f>.55f?ink:Vec3{1,1,1};
    int plate=b.texture(label(text,accent,fg,112));b.panel(prefix,{0,258,71},78,18,plate);
    b.rounded_box(prefix,{0,48,64},{82,7,57},2,{.90f,.85f,.76f});b.rounded_box(prefix,{0,54,65},{77,9,51},4,accent);b.rounded_box(prefix,{0,86,8},{76,52,9},4,accent);
    b.rim(prefix+" / costura do assento",{0,55.4f,65},73,47,4.5f,.16f,mul(accent,.65f));
    for(float x:{-30.f,30.f})b.box(prefix,{x,27,65},{4,40,42},white);
    b.box(prefix,{0,16,65},{77,3,51},white);b.box(prefix,{0,59,89},{77,.8f,1},secondary);
    b.tube(prefix,{-36,214,32},{36,214,32},1.2f,metal);
    // Hanger is fitted after placing the native jersey, not at a guessed height.
    Model dressed=source;apply_presentation_pose(dressed,false,nullptr,101);std::map<int,int>textures;
    for(auto&p:dressed.parts)if(p.asset.find("/jersey_")!=std::string::npos){if(place_native(b,dressed,p,kit,{0,199,42},79,62,true,textures)&&row){Part shirt=b.room.parts.back();fitted_hanger(b,shirt,kit+" / cabide");int type=source.goalkeeper?2:0;auto font=prints.name_fonts.find(type);auto info=prints.metadata.find(type);Vec3 color=info==prints.metadata.end()?Vec3{1,1,1}:info->second.name_color;if(color.x+color.y+color.z<.05f)color={1,1,1};int name_texture=b.texture(shirt_name(row->name,font==prints.name_fonts.end()?std::vector<uint8_t>{}:font->second,color));print_digit(b,shirt,kit+" / nome "+std::string(row->name),name_texture,0,185,44,7);
        if(number_set){std::string number=std::to_string(row->number);float width=number.size()>1?13.f:16.f;for(size_t d=0;d<number.size();++d){int digit=number[d]-'0';if(digit<0||digit>9||!number_set->available[digit])continue;auto key=std::make_pair(number_set,digit);auto at=digit_textures.find(key);int texture;if(at==digit_textures.end()){texture=b.texture(number_set->digits[digit]);digit_textures[key]=texture;}else texture=at->second;float x=(float(d)-float(number.size()-1)*.5f)*(width+1);print_digit(b,shirt,kit+" / número "+number,texture,x,180,width,33);}}}break;}
    for(auto&p:source.parts)if(p.asset.find("/shoe/")!=std::string::npos){place_native(b,source,p,shoes,{0,19,77},14,52,false,textures);break;}
    // Folded towels, a rolled towel, bottles, kit bag and an occasional hanging towel.
    towel(b,equipment,{-16,228.25f,35},accent,false);towel(b,equipment,{-16,230.9f,35},accent,false);towel(b,equipment,{22,232,33},accent,true);
    b.box(equipment,{-21,27,31},{26,17,29},ink);b.box(equipment,{-21,36,31},{27,2,30},secondary);
    bottle(b,equipment,{29,76,20},accent,int(index));
    if(index%3==0)bag(b,equipment,{11,58,67},accent);
    if(index%3==1){b.box(equipment,{26,159,28},{19,38,2},white);b.box(equipment,{26,179,28},{19,2,8},white);b.box(equipment,{26,143,29.2f},{19,2,.3f},secondary);}
    b.box(prefix,{0,222,38},{68,1,26},{1.16f,1.12f,.99f});
}
}

namespace room_geometry {
Texture text_label(const std::wstring&t,Vec3 bg,Vec3 fg,int h){return label(t,bg,fg,h);}
Texture surface_material(bool wood){return material(wood);}
void sports_bottle(Builder&b,const std::string&n,Vec3 p,Vec3 a,int v){bottle(b,n,p,a,v);}
void game_ball(Builder&b,const Model&m,const std::string&n,Vec3 p,float y,std::map<int,int>&t){native_ball(b,m,n,p,y,t);}
}
DressingPrints load_dressing_prints(Assets&assets,const fs::path&game,int club,int competition){
    DressingPrints result;result.metadata=club_kit_prints(game,club);const std::string dir="data/sceneassets/kitnumbers/";
    result.ball_league_id=assets.league(club,result.ball_league);
    if(competition>0){result.ball_league_id=competition;result.ball_league="Competição "+std::to_string(competition);}
    int assigned=0;std::vector<uint8_t>lua;
    // Read the concrete club assignment as a fallback, never execute game Lua.
    if(assets.read("data/fifarna/lua/assignments/teams/team_"+std::to_string(club)+".lua",lua)&&lua.size()<1024*1024){std::string text(lua.begin(),lua.end());std::smatch match;std::regex assignment("(^|\n)\\s*assignTeamTournament\\(\\s*"+std::to_string(club)+"\\s*,\\s*([0-9]{1,6})\\s*\\)");if(std::regex_search(text,match,assignment))assigned=std::stoi(match[2].str());}
    const std::string ball_dir="data/sceneassets/ball/";std::vector<std::string>balls;
    auto add_ball=[&](int team,int league){balls.push_back(ball_dir+"specificball_"+std::to_string(team)+"_"+std::to_string(league)+"_0");};
    if(result.ball_league_id>0){add_ball(club,result.ball_league_id);add_ball(0,result.ball_league_id);}add_ball(club,0);if(assigned>0)add_ball(0,assigned);add_ball(0,0);balls.push_back(ball_dir+"ball_23");
    for(auto&path:balls){std::vector<uint8_t>mesh,raw;std::vector<Part>parts;Texture texture;
        if(!assets.read(path+".rx3",mesh)||!assets.read(path+"_textures.rx3",raw)||!read_mesh(mesh,parts))continue;
        bool decoded=read_texture(raw,"ball_cm",texture);if(!decoded)for(auto&name:texture_names(raw))if(name.find("_cm")!=std::string::npos&&read_texture(raw,name,texture)){decoded=true;break;}if(!decoded)continue;
        result.ball.parts=std::move(parts);result.ball.textures.push_back(std::move(texture));for(auto&p:result.ball.parts){p.asset=path+".rx3";p.texture=0;p.color=p.tint={1,1,1};p.skinned=false;}
        result.ball_asset=path+".rx3";break;
    }
    for(int type:{0,2}){auto info=result.metadata.count(type)?result.metadata.at(type):KitPrintInfo{};std::vector<std::string>paths={dir+"specifickitnumbers_"+std::to_string(club)+"_1_0_"+std::to_string(type)+".rx3",dir+"specifickitnumbers_"+std::to_string(club)+"_0_0_"+std::to_string(info.color)+".rx3",dir+"kitnumbers_"+std::to_string(info.font)+"_"+std::to_string(info.color)+".rx3",dir+"kitnumbers_0_0.rx3"};
        for(auto&path:std::vector<std::string>{"data/sceneassets/jerseyfonts/specificfont_"+std::to_string(club)+"_1_0_"+std::to_string(type)+".ttf","data/sceneassets/jerseyfonts/specificfont_"+std::to_string(club)+"_0_0_0.ttf","data/sceneassets/jerseyfonts/font_"+std::to_string(info.name_font)+".ttf"}){std::vector<uint8_t>font;if(assets.read(path,font)&&!font.empty()&&font.size()<4*1024*1024){result.name_fonts[type]=std::move(font);break;}}
        for(auto&path:paths){std::vector<uint8_t>raw;if(!assets.read(path,raw))continue;KitNumberSet set;set.asset=path;auto names=texture_names(raw);std::regex digit_suffix("_([0-9])(?:\\..*)?$");for(auto&name:names){std::smatch match;if(!std::regex_search(name,match,digit_suffix))continue;int digit=match[1].str()[0]-'0';Texture t;if(read_texture(raw,name,t)){set.digits[digit]=std::move(t);set.available[digit]=true;}}
            if(std::all_of(set.available.begin(),set.available.end(),[](bool value){return value;})){result.kits[type]=std::move(set);break;}
        }
    }return result;
}
Model build_dressing_room(const std::vector<std::shared_ptr<const Model>>&players,const std::vector<ClubPlayerRow>&roster,const DressingPrints&prints){
    Builder b;auto&room=b.room;if(players.empty()||!players.front())return room;const auto&club=*players.front();
    for(auto&p:players)if(p&&p->team_id!=club.team_id)throw std::runtime_error("O vestiário não pode misturar clubes");
    room.room=RoomDressing;room.team_id=club.team_id;room.club_colors_valid=club.club_colors_valid;std::copy(std::begin(club.club_colors),std::end(club.club_colors),room.club_colors);
    if(club.crest_texture>=0&&size_t(club.crest_texture)<club.textures.size()){room.crest_texture=0;room.textures.push_back(club.textures[club.crest_texture]);}
    Vec3 accent=club.club_colors_valid?club.club_colors[0]:Vec3{.12f,.3f,.55f},secondary=club.club_colors_valid?club.club_colors[1]:Vec3{.3f,.4f,.5f};
    int wood=b.texture(material(true)),rubber=b.texture(material(false));
    b.box("Sala / parede de fundo",{0,160,-489},{1090,320,12},white);
    b.box("Sala / parede esquerda",{-540,160,115},{12,320,1210},white);b.box("Sala / parede direita",{540,160,115},{12,320,1210},white);
    b.box("Sala / piso",{0,-5,115},{1090,6,1210},{.46f,.48f,.50f});
    b.face("Sala / piso",{-540,.02f,-485},{540,.02f,-485},{540,.02f,715},{-540,.02f,715},{0,1,0},{1,1,1},rubber,false,18,21);
    // Tile joints are part of the rubber material, avoiding coplanar flicker at long distance.
    // Inlaid club roundel and non-slip circulation strips; nothing floats above the floor.
    for(float x:{-397.f,397.f})b.box("Sala / faixa do piso",{x,.12f,15},{5,.12f,910},accent);
    b.floor_crest("Sala / escudo no piso",{0,.8f,312},190);
    b.box("Sala / tapete de entrada",{0,.4f,669},{147,.6f,69},{.18f,.2f,.22f});
    for(float z=639;z<=698;z+=3.5f)b.box("Sala / tapete de entrada",{0,.8f,z},{140,.16f,.5f},{.25f,.27f,.29f});
    b.box("Sala / teto",{0,323,115},{1090,6,1210},white);
    for(float x=-500;x<=500;x+=100)b.box("Sala / teto modular",{x,319,115},{.45f,.2f,1200},{.8f,.81f,.81f});
    for(float z=-450;z<715;z+=100)b.box("Sala / teto modular",{0,319,z},{1070,.2f,.45f},{.8f,.81f,.81f});
    for(float x:{-320.f,0.f,320.f})for(float z:{-350.f,115.f,580.f}){b.box("Sala / luminárias",{x,315,z},{80,4,50},metal);b.box("Sala / luminárias",{x,312.7f,z},{76,.5f,46},{1.3f,1.28f,1.21f});}
    b.box("Sala / faixa do clube",{0,283,-482},{1070,9,1},accent);b.box("Sala / faixa secundária",{0,275,-482},{1070,2,1},secondary);
    for(float x:{-533.f,533.f}){b.box("Sala / faixa do clube",{x,283,115},{1,9,1200},accent);b.box("Sala / rodapé",{x,7,115},{2,14,1200},metal);}
    b.box("Sala / rodapé",{0,7,-482},{1070,14,2},metal);
    // Enclosed entrance, behind the default camera. No fake photographic walls.
    b.box("Sala / entrada",{-293,160,722},{475,320,10},white);b.box("Sala / entrada",{293,160,722},{475,320,10},white);b.box("Sala / entrada",{0,279,722},{112,86,10},white);
    b.box("Porta",{0,117,719},{106,230,4},ink);for(float x:{-55.f,55.f})b.box("Porta",{x,119,715},{4,238,6},metal);b.box("Porta",{0,237,715},{112,4,6},metal);b.tube("Porta",{37,98,714},{37,114,714},1.3f,metal);
    size_t count=24;size_t uniform_count=0,shoe_count=0;Model reserve;
    std::map<std::pair<const KitNumberSet*,int>,int>digit_textures;
    for(size_t i=0;i<count;++i){const Model&person=i<players.size()&&players[i]?*players[i]:reserve;const ClubPlayerRow*row=nullptr;for(auto&r:roster)if(r.player_id==person.player_id){row=&r;break;}
        if(i<8){float x=i<4?-420.f+float(i)*90:150.f+float(i-4)*90;b.frame({x,0,-477});}
        else if(i<16)b.frame({-522,0,-343+float(i-8)*108},pi/2);
        else b.frame({522,0,-343+float(i-16)*108},-pi/2);
        auto numbers=prints.kits.find(person.goalkeeper?2:0);locker(b,person,row,i,accent,secondary,wood,numbers==prints.kits.end()?nullptr:&numbers->second,digit_textures,prints);
        for(auto&p:person.parts){if(p.asset.find("/jersey_")!=std::string::npos){++uniform_count;break;}}
        for(auto&p:person.parts){if(p.asset.find("/shoe/")!=std::string::npos){++shoe_count;break;}}
    }
    b.frame({0,0,-170});board(b,accent,secondary);b.frame();
    coach_table(b,accent,wood);medical_area(b,accent);chalkboard(b,wood);
    // Clear standing space in front of the analysis board; the reserve bench is removed.
    b.frame({-346,0,711},pi);water_station(b,accent,wood);
    b.frame();b.box("Cesto de roupa",{435,33,663},{44,60,43},{.83f,.85f,.86f});b.box("Cesto de roupa",{435,62,663},{48,4,47},ink);towel(b,"Cesto / toalhas",{432,65,663},accent,true);towel(b,"Cesto / toalhas",{441,69,664},accent,false);
    ball_cart(b);
    std::map<int,int>ball_textures;int ball_count=0;
    for(int layer=0;layer<2;++layer)for(int x=0;x<3;++x)for(int z=0;z<2;++z){native_ball(b,prints.ball,"Equipamentos / bola "+std::to_string(++ball_count),{-306.f+x*26,35.f+layer*23,321.f+z*28},float(ball_count)*.63f,ball_textures);}
    native_ball(b,prints.ball,"Equipamentos / bola 13",{-244,11,263},1.8f,ball_textures);native_ball(b,prints.ball,"Equipamentos / bola 14",{-317,11,263},-.6f,ball_textures);
    b.batch();std::ostringstream info;info<<"Vestiário: "<<count<<" armários, uniformes com nomes/números, mesa do técnico, bebedouro, área médica e piso personalizado. Bola: "<<(prints.ball_asset.empty()?"recurso nativo indisponível":prints.ball_asset)<<"; liga "<<prints.ball_league_id<<". Arquivos FIFA somente leitura.";room.diagnostic=info.str();return room;
}
void dressing_camera_view(Camera&c,int view){
    c.orbit=true;c.speed=160;c.fov=74;c.position={0,212,665};c.target={0,115,-175};
    if(view==1){c.position={-315,180,-190};c.target={-315,145,-455};c.fov=66;}
    else if(view==2){c.position={30,177,-100};c.target={0,165,-375};c.fov=50;}
    else if(view==3){c.position={370,190,390};c.target={-155,145,-250};c.fov=75;}
    else if(view==4){c.position={0,800,1640};c.target={0,120,80};c.fov=50;}
    else if(view==5){c.position={-160,185,430};c.target={-403,105,684};c.fov=58;}
    else if(view==6){c.position={110,180,350};c.target={300,91,185};c.fov=61;}
    else if(view==7){c.position={0,315,495};c.target={0,12,305};c.fov=70;}
    else if(view==8){c.position={-60,166,263};c.target={0,81,85};c.fov=56;}
    else if(view==9){c.position={75,186,500};c.target={255,186,709};c.fov=62;}
    auto d=sub(c.target,c.position);c.distance=sqrtf(d.x*d.x+d.y*d.y+d.z*d.z);c.pitch=asinf(d.y/c.distance);c.yaw=atan2f(d.x,-d.z);c.synchronize_orbit();
}
void edit_dressing_objects(Model&m,const std::vector<ObjectEdit>&edits){
    using namespace DirectX;
    for(auto&e:edits){Vec3 low={FLT_MAX,FLT_MAX,FLT_MAX},high={-FLT_MAX,-FLT_MAX,-FLT_MAX};bool found=false;auto matches=[&](const std::string&name){return name==e.name||name.rfind(e.name+" / ",0)==0;};
        for(auto&p:m.parts)if(matches(p.name))for(auto&v:p.vertices){found=true;for(int k=0;k<3;++k){(&low.x)[k]=std::min((&low.x)[k],(&v.position.x)[k]);(&high.x)[k]=std::max((&high.x)[k],(&v.position.x)[k]);}}
        if(!found)continue;auto center=mul(add(low,high),.5f);auto rotation=XMMatrixRotationRollPitchYaw(XMConvertToRadians(e.rotation.x),XMConvertToRadians(e.rotation.y),XMConvertToRadians(e.rotation.z));
        auto transform=XMMatrixTranslation(-center.x,-center.y,-center.z)*XMMatrixScaling(e.scale,e.scale,e.scale)*rotation*XMMatrixTranslation(center.x+e.translation.x,center.y+e.translation.y,center.z+e.translation.z);
        for(auto&p:m.parts)if(matches(p.name)){if(!e.visible){p.vertices.clear();p.indices.clear();continue;}for(auto&v:p.vertices){auto q=XMVector3TransformCoord(XMVectorSet(v.position.x,v.position.y,v.position.z,1),transform),n=XMVector3TransformNormal(XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),rotation);v.position={XMVectorGetX(q),XMVectorGetY(q),XMVectorGetZ(q)};v.normal={XMVectorGetX(n),XMVectorGetY(n),XMVectorGetZ(n)};}}
    }
}
void open_dressing_room(Model&m){
    const char*hidden[]={"Sala / teto","Sala / teto modular","Sala / luminárias","Sala / entrada","Porta","Sala / parede esquerda","Sala / parede direita","Sala / faixa do clube","Sala / faixa secundária","Sala / rodapé"};
    for(auto&p:m.parts)for(auto*name:hidden)if(p.name==name){p.vertices.clear();p.indices.clear();break;}
}
}
