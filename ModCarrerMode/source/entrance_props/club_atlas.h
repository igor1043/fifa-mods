#pragma once
#include <vector>
#include <algorithm>
#include <string.h>
#include "entrance_catalog.h"
#include "crest_mesh.h"

// Preserve DDS alpha and trim the crest surfaces to their opaque contour.
// Keep the proven static material; untouched BC3 blocks stay byte-identical.
namespace ClubAtlas {
struct Pixel {unsigned char r,g,b,a;};
static unsigned short word(const unsigned char* p){unsigned short x;memcpy(&x,p,2);return x;}
static unsigned dword(const unsigned char* p){unsigned x;memcpy(&x,p,4);return x;}
static void put(unsigned char* p,unsigned value){memcpy(p,&value,4);}
static Pixel colour(unsigned short x){return {(unsigned char)(((x>>11)&31)*255/31),(unsigned char)(((x>>5)&63)*255/63),(unsigned char)((x&31)*255/31),255};}
static unsigned short colour16(Pixel p){return (unsigned short)(((p.r*31+127)/255<<11)|((p.g*63+127)/255<<5)|((p.b*31+127)/255));}
static void decode(const unsigned char* p,Pixel* out,int kind){
    const unsigned char* c=p+(kind==1?0:8);unsigned short c0=word(c),c1=word(c+2);
    Pixel palette[4]={colour(c0),colour(c1),{}, {}};
    for(int channel=0;channel<3;++channel){
        auto a=((unsigned char*)&palette[0])[channel],b=((unsigned char*)&palette[1])[channel];
        if(kind!=1||c0>c1){((unsigned char*)&palette[2])[channel]=(unsigned char)((2*a+b)/3);((unsigned char*)&palette[3])[channel]=(unsigned char)((a+2*b)/3);}
        else {((unsigned char*)&palette[2])[channel]=(unsigned char)((a+b)/2);((unsigned char*)&palette[3])[channel]=0;}
    }
    palette[2].a=255;palette[3].a=(unsigned char)((kind==1&&c0<=c1)?0:255);
    unsigned indices=dword(c+4);unsigned char alpha[8]={};unsigned long long bits=0;
    if(kind==3){
        alpha[0]=p[0];alpha[1]=p[1];
        if(alpha[0]>alpha[1])for(int i=2;i<8;++i)alpha[i]=(unsigned char)(((8-i)*alpha[0]+(i-1)*alpha[1])/7);
        else {for(int i=2;i<6;++i)alpha[i]=(unsigned char)(((6-i)*alpha[0]+(i-1)*alpha[1])/5);alpha[6]=0;alpha[7]=255;}
        for(int i=0;i<6;++i)bits|=(unsigned long long)p[i+2]<<(8*i);
    }else if(kind==2)memcpy(&bits,p,8);
    for(int i=0;i<16;++i){out[i]=palette[(indices>>(2*i))&3];if(kind==3)out[i].a=alpha[(bits>>(3*i))&7];else if(kind==2)out[i].a=(unsigned char)(((bits>>(4*i))&15)*17);}
}
static void encode(const Pixel* in,unsigned char* out){
    unsigned char lowAlpha=255,highAlpha=0;
    for(int i=0;i<16;++i){lowAlpha=std::min(lowAlpha,in[i].a);highAlpha=std::max(highAlpha,in[i].a);}
    out[0]=highAlpha;out[1]=lowAlpha;unsigned char alpha[8]={highAlpha,lowAlpha};
    if(highAlpha>lowAlpha)for(int i=2;i<8;++i)alpha[i]=(unsigned char)(((8-i)*highAlpha+(i-1)*lowAlpha)/7);
    else {for(int i=2;i<6;++i)alpha[i]=lowAlpha;alpha[6]=0;alpha[7]=255;}
    unsigned long long alphaBits=0;
    for(int i=0;i<16;++i){unsigned best=0,dist=256;for(unsigned j=0;j<8;++j){unsigned delta=(unsigned)abs((int)in[i].a-alpha[j]);if(delta<dist){dist=delta;best=j;}}alphaBits|=(unsigned long long)best<<(3*i);}
    for(int i=0;i<6;++i)out[2+i]=(unsigned char)(alphaBits>>(8*i));
    Pixel lo={255,255,255,255},hi={0,0,0,255};
    for(int i=0;i<16;++i)for(int k=0;k<3;++k){auto x=((const unsigned char*)&in[i])[k];((unsigned char*)&lo)[k]=std::min(((unsigned char*)&lo)[k],x);((unsigned char*)&hi)[k]=std::max(((unsigned char*)&hi)[k],x);}
    unsigned short a=colour16(hi),b=colour16(lo);if(a<b)std::swap(a,b);memcpy(out+8,&a,2);memcpy(out+10,&b,2);
    Pixel palette[4]={colour(a),colour(b),{}, {}};
    for(int k=0;k<3;++k){unsigned x=((unsigned char*)&palette[0])[k],y=((unsigned char*)&palette[1])[k];((unsigned char*)&palette[2])[k]=(unsigned char)((2*x+y)/3);((unsigned char*)&palette[3])[k]=(unsigned char)((x+2*y)/3);}
    unsigned packed=0;
    for(int i=0;i<16;++i){unsigned best=0,dist=~0u;for(unsigned j=0;j<4;++j){unsigned distance=0;for(int k=0;k<3;++k){int delta=((const unsigned char*)&in[i])[k]-((unsigned char*)&palette[j])[k];distance+=(unsigned)(delta*delta);}if(distance<dist){dist=distance;best=j;}}packed|=best<<(2*i);}
    put(out+12,packed);
}
static bool file(const char* path,std::vector<unsigned char>& out){
    FILE* f=nullptr;if(fopen_s(&f,path,"rb")||!f)return false;
    if(fseek(f,0,SEEK_END)){fclose(f);return false;}long n=ftell(f);rewind(f);
    if(n<16||n>32*1024*1024){fclose(f);return false;}out.resize((size_t)n);
    bool ok=fread(out.data(),1,out.size(),f)==out.size();fclose(f);return ok;
}
static unsigned checksum(const std::vector<unsigned char>& data){unsigned hash=2166136261u;for(auto b:data){hash^=b;hash*=16777619u;}return hash;}
static unsigned char component(unsigned value,unsigned mask,unsigned char missing){
    if(!mask)return missing;unsigned shift=0;while(!(mask&1)){mask>>=1;++shift;}
    return (unsigned char)((((uint64_t)(value>>shift)&mask)*255+mask/2)/mask);
}
static bool crest(const std::vector<unsigned char>& raw,std::vector<Pixel>& pixels,unsigned& width,unsigned& height){
    if(raw.size()<128||memcmp(raw.data(),"DDS ",4)||dword(raw.data()+4)!=124)return false;
    height=dword(raw.data()+12);width=dword(raw.data()+16);unsigned code=dword(raw.data()+84);
    if(width<4||height<4||width>2048||height>2048)return false;
    if(!code&&(dword(raw.data()+80)&0x40)&&dword(raw.data()+88)==32){
        unsigned pitch=width*4;if(dword(raw.data()+8)&8)pitch=dword(raw.data()+20);
        if(pitch<width*4||pitch>width*16||128+(size_t)pitch*height>raw.size())return false;
        const unsigned r=dword(raw.data()+92),g=dword(raw.data()+96),b=dword(raw.data()+100),alpha=dword(raw.data()+104);
        if(!r||!g||!b||(r&g)||(r&b)||(g&b)||(alpha&(r|g|b)))return false;
        pixels.resize((size_t)width*height);
        for(unsigned y=0;y<height;++y)for(unsigned x=0;x<width;++x){
            unsigned value=dword(raw.data()+128+(size_t)y*pitch+x*4);
            pixels[(size_t)y*width+x]={component(value,r,0),component(value,g,0),component(value,b,0),component(value,alpha,255)};
        }return true;
    }
    int kind=code==0x31545844?1:code==0x33545844?2:code==0x35545844?3:0;if(!kind)return false;
    unsigned blocksX=(width+3)/4,blocksY=(height+3)/4,bytes=kind==1?8u:16u;
    if(128+(size_t)blocksX*blocksY*bytes>raw.size())return false;pixels.resize((size_t)width*height);
    for(unsigned y=0;y<blocksY;++y)for(unsigned x=0;x<blocksX;++x){Pixel block[16];decode(raw.data()+128+((size_t)y*blocksX+x)*bytes,block,kind);for(unsigned j=0;j<4;++j)for(unsigned i=0;i<4;++i)if(x*4+i<width&&y*4+j<height)pixels[(size_t)(y*4+j)*width+x*4+i]=block[j*4+i];}
    return true;
}
static void pad_rgb(std::vector<Pixel>& pixels,unsigned w,unsigned h){
    // Avoid dark filtering fringes without changing any pixel's transparency.
    if(!w||!h)return;std::vector<unsigned char> filled(pixels.size());
    for(size_t i=0;i<pixels.size();++i)filled[i]=(unsigned char)(pixels[i].a>=128);
    for(unsigned pass=0;pass<3;++pass){auto next=filled;auto colour=pixels;
        for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x){size_t i=(size_t)y*w+x;if(filled[i])continue;
            unsigned sums[3]={},count=0;const int offsets[4][2]={{-1,0},{1,0},{0,-1},{0,1}};
            for(const auto& offset:offsets){int xx=(int)x+offset[0],yy=(int)y+offset[1];if(xx<0||yy<0||xx>=(int)w||yy>=(int)h)continue;
                size_t j=(size_t)yy*w+xx;if(!filled[j])continue;++count;for(unsigned k=0;k<3;++k)sums[k]+=((const unsigned char*)&pixels[j])[k];}
            if(count){next[i]=1;for(unsigned k=0;k<3;++k)((unsigned char*)&colour[i])[k]=(unsigned char)(sums[k]/count);}
        }pixels.swap(colour);filled.swap(next);
    }
}
static bool prepare(const char* game,const EntranceCatalog::Asset& asset,unsigned home,unsigned away,char (&relative)[MAX_PATH]){
    if(!asset.slots)return false;
    if(!home||!away||home>1000000||away>1000000)return false;
    char p[MAX_PATH];std::vector<unsigned char> h,a;
    _snprintf_s(p,MAX_PATH,_TRUNCATE,"%s\\data\\ui\\imgAssets\\crest\\light\\l%u.dds",game,home);file(p,h);
    _snprintf_s(p,MAX_PATH,_TRUNCATE,"%s\\data\\ui\\imgAssets\\crest\\light\\l%u.dds",game,away);file(p,a);
    unsigned hw=0,hh=0,aw=0,ah=0;std::vector<Pixel> hp,ap;
    if(!crest(h,hp,hw,hh)){hp.clear();hw=hh=0;}if(!crest(a,ap,aw,ah)){ap.clear();aw=ah=0;}
    if(_snprintf_s(relative,MAX_PATH,_TRUNCATE,"data/sceneassets/entrance_props/competitions/%s/fixtures/alpha18_%u_%u_%08x_%08x_%016llx/",asset.slug,home,away,checksum(h),checksum(a),asset.stamp)<0)return false;
    char directory[MAX_PATH],dest[MAX_PATH],modelDest[MAX_PATH];
    if(_snprintf_s(directory,MAX_PATH,_TRUNCATE,"%s/%s",game,relative)<0||_snprintf_s(dest,MAX_PATH,_TRUNCATE,"%s/textures.rx3",directory)<0||_snprintf_s(modelDest,MAX_PATH,_TRUNCATE,"%s/model.rx3",directory)<0)return false;
    std::vector<unsigned char> rx;_snprintf_s(p,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\template.rx3",game,asset.slug);if(!file(p,rx))return false;
    if(!EntranceCatalog::texture(rx))return false;
    unsigned sections=dword(rx.data()+12);if(sections>32||16+sections*16>rx.size())return false;
    unsigned off=0,len=0;
    for(unsigned i=0;i<sections;++i){auto row=rx.data()+16+i*16;if(dword(row)==0x7a0b60da){off=dword(row+4);len=dword(row+8);break;}}
    if(!off||len<16||(size_t)off+len>rx.size())return false;
    auto tex=rx.data()+off;unsigned w=word(tex+8),height=word(tex+10),mips=word(tex+14);if(w!=4096||height!=4096||tex[5]!=2||mips!=13)return false;
    WIN32_FILE_ATTRIBUTE_DATA existing{};
    if(GetFileAttributesExA(dest,GetFileExInfoStandard,&existing)&&existing.nFileSizeHigh==0&&existing.nFileSizeLow==rx.size()){
        std::vector<unsigned char> cached,cachedModel;EntranceCatalog::Asset check{};
        if(file(dest,cached)&&file(modelDest,cachedModel)&&EntranceCatalog::model(cachedModel,check)&&EntranceCatalog::texture(cached)&&!memcmp(cached.data(),rx.data(),off+16)&&
           !memcmp(cached.data()+off+len,rx.data()+off+len,rx.size()-off-len))return true;
    }
    pad_rgb(hp,hw,hh);pad_rgb(ap,aw,ah);
    size_t at=16;
    for(unsigned mip=0;mip<mips;++mip){
        if(at+16>len)return false;unsigned pitch=dword(tex+at),rows=dword(tex+at+4),size=dword(tex+at+8);at+=16;
        unsigned bx=std::max(1u,(w+3)/4),by=std::max(1u,(height+3)/4);if(pitch!=bx*16||rows!=by||size!=pitch*rows||at+size>len)return false;
        {
            for(unsigned slot=0;slot<asset.slots;++slot){
                const auto& spec=asset.token[slot];
                const unsigned slotX=spec.x*w/4096,slotY=spec.y*height/4096,span=spec.size*w/4096;
                if(!span)continue;
                const bool isHome=spec.side==0;unsigned cw=isHome?hw:aw,ch=isHome?hh:ah;const auto& source=isHome?hp:ap;
                for(unsigned y=slotY/4;y<std::min(by,(slotY+span+3)/4);++y)for(unsigned x=slotX/4;x<std::min(bx,(slotX+span+3)/4);++x){
                    auto encoded=tex+at+(size_t)y*pitch+x*16;Pixel block[16];decode(encoded,block,3);
                    for(unsigned j=0;j<4;++j)for(unsigned i=0;i<4;++i){
                        unsigned px=x*4+i,py=y*4+j;if(px<slotX||py<slotY||px>=slotX+span||py>=slotY+span||px>=w||py>=height)continue;
                        Pixel crestPixel={0,0,0,0};
                        if(cw&&ch){unsigned sx=std::min(cw-1,(px-slotX)*cw/span),sy=std::min(ch-1,(py-slotY)*ch/span);crestPixel=source[(size_t)sy*cw+sx];}
                        block[j*4+i]=crestPixel;
                    }encode(block,encoded);
                }
            }
        }
        at+=size;w=std::max(1u,w/2);height=std::max(1u,height/2);
    }
    std::vector<unsigned char> originalModel,model;
    _snprintf_s(p,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\model.rx3",game,asset.slug);
    if(!file(p,originalModel)||!CrestMesh::build(originalModel,asset,CrestMesh::rectangles(hp,hw,hh),CrestMesh::rectangles(ap,aw,ah),model)||!EntranceCatalog::texture(rx))return false;
    _snprintf_s(p,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\fixtures",game,asset.slug);if(!CreateDirectoryA(p,nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return false;
    if(!CreateDirectoryA(directory,nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return false;
    const char* names[2]={modelDest,dest};const std::vector<unsigned char>* data[2]={&model,&rx};
    for(unsigned i=0;i<2;++i){char temporary[MAX_PATH];if(_snprintf_s(temporary,MAX_PATH,_TRUNCATE,"%s.tmp",names[i])<0)return false;FILE* f=nullptr;if(fopen_s(&f,temporary,"wb")||!f)return false;
        bool ok=fwrite(data[i]->data(),1,data[i]->size(),f)==data[i]->size();if(fclose(f))ok=false;if(!ok||!MoveFileExA(temporary,names[i],MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))return false;}
    return true;
}
}
