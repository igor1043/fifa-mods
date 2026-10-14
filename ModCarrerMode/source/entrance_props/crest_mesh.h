#pragma once
#include <array>
#include <vector>
#include <algorithm>
#include <math.h>

// Keep the proven static material. Empty crest pixels have no triangles;
// geometry and crests still occupy one native actor and one visibility rule.
namespace CrestMesh {
struct Rect {float left,top,right,bottom;};
using Vertex=std::array<float,11>; // position, normal, tangent, atlas UV
static unsigned half_bits(float value){
    unsigned bits;memcpy(&bits,&value,4);unsigned sign=(bits>>16)&0x8000;
    int exponent=(int)((bits>>23)&255)-127+15;unsigned fraction=bits&0x7fffff;
    if(exponent>=31)return sign|0x7c00;
    if(exponent<=0){
        if(exponent<-10)return sign;
        fraction|=0x800000;unsigned shift=(unsigned)(14-exponent),base=fraction>>shift;
        unsigned remainder=fraction&((1u<<shift)-1),mid=1u<<(shift-1);
        return sign|(base+(remainder>mid||(remainder==mid&&(base&1))));
    }
    unsigned base=fraction>>13,remainder=fraction&8191;
    if(remainder>4096||(remainder==4096&&(base&1))){if(++base==1024){base=0;++exponent;}}
    return sign|((unsigned)exponent<<10)|base;
}
static unsigned packed(const float* vector){
    float length=sqrtf(vector[0]*vector[0]+vector[1]*vector[1]+vector[2]*vector[2]);unsigned result=0;
    for(unsigned k=0;k<3;++k){float v=length>1e-10f?vector[k]/length:0;int n=(int)lroundf(std::max(-1.f,std::min(1.f,v))*511);result|=(unsigned)(n&1023)<<(k*10);}
    return result;
}
static Vertex decode(const unsigned char* data){
    Vertex vertex{};
    for(unsigned k=0;k<3;++k)vertex[k]=EntranceCatalog::half(EntranceCatalog::word16(data+k*2));
    for(unsigned attribute=0;attribute<2;++attribute){unsigned code=EntranceCatalog::word32(data+8+attribute*4);
        for(unsigned k=0;k<3;++k){int v=(code>>(k*10))&1023;if(v>=512)v-=1024;vertex[3+attribute*3+k]=v/511.f;}}
    vertex[9]=EntranceCatalog::half(EntranceCatalog::word16(data+16));vertex[10]=EntranceCatalog::half(EntranceCatalog::word16(data+18));return vertex;
}
static void encode(const Vertex& vertex,std::vector<unsigned char>& data){
    unsigned char output[20]={};unsigned short value=0;
    for(unsigned k=0;k<3;++k){value=(unsigned short)half_bits(vertex[k]);memcpy(output+k*2,&value,2);}
    value=0x3c00;memcpy(output+6,&value,2);
    unsigned word=packed(vertex.data()+3);memcpy(output+8,&word,4);word=packed(vertex.data()+6);memcpy(output+12,&word,4);
    value=(unsigned short)half_bits(vertex[9]);memcpy(output+16,&value,2);value=(unsigned short)half_bits(vertex[10]);memcpy(output+18,&value,2);
    data.insert(data.end(),output,output+20);
}
template<class Pixel>static std::vector<Rect> rectangles(const std::vector<Pixel>& pixels,unsigned width,unsigned height){
    unsigned w=std::min(width,128u),h=std::min(height,128u);std::vector<Rect> all;
    struct Run{unsigned left,right,rectangle;};std::vector<Run> previous;
    if(!w||!h||pixels.size()!=(size_t)width*height)return all;
    for(unsigned y=0;y<h;++y){std::vector<Run> row;
        for(unsigned x=0;x<w;){
            auto opaque=[&](unsigned column){unsigned sx=std::min(width-1,(2*column+1)*width/(2*w)),sy=std::min(height-1,(2*y+1)*height/(2*h));return pixels[(size_t)sy*width+sx].a>=128;};
            if(!opaque(x)){++x;continue;}unsigned left=x;while(x<w&&opaque(x))++x;unsigned right=x,index=(unsigned)all.size();
            auto old=std::find_if(previous.begin(),previous.end(),[&](const Run& r){return r.left==left&&r.right==right;});
            if(old!=previous.end()){index=old->rectangle;all[index].bottom=(y+1)/(float)h;}
            else all.push_back({left/(float)w,y/(float)h,right/(float)w,(y+1)/(float)h});
            row.push_back({left,right,index});
        }previous.swap(row);
    }return all;
}
static void clip(std::vector<Vertex>& polygon,unsigned axis,float limit,bool lower){
    if(polygon.empty())return;std::vector<Vertex> output;output.reserve(8);
    for(size_t i=0;i<polygon.size();++i){const auto& a=polygon[i];const auto& b=polygon[(i+1)%polygon.size()];
        bool insideA=lower?a[axis]>=limit:a[axis]<=limit,insideB=lower?b[axis]>=limit:b[axis]<=limit;
        if(insideA)output.push_back(a);
        if(insideA!=insideB){float t=(limit-a[axis])/(b[axis]-a[axis]);Vertex point{};for(unsigned k=0;k<11;++k)point[k]=a[k]+(b[k]-a[k])*t;output.push_back(point);}
    }polygon.swap(output);
}
static bool in_slot(const Vertex& v,const EntranceCatalog::Slot& slot){
    // Half-float UV storage can move a boundary by about half an atlas texel.
    const float pad=.0003f;
    return v[9]>=slot.x/4096.f-pad&&v[9]<=(slot.x+slot.size)/4096.f+pad&&
           v[10]>=slot.y/4096.f-pad&&v[10]<=(slot.y+slot.size)/4096.f+pad;
}
static void put32(std::vector<unsigned char>& data,size_t at,unsigned value){memcpy(data.data()+at,&value,4);}
static size_t aligned(size_t size){return (size+15)&~(size_t)15;}
static bool build(const std::vector<unsigned char>& raw,const EntranceCatalog::Asset& asset,
                  const std::vector<Rect>& home,const std::vector<Rect>& away,std::vector<unsigned char>& output,bool bodyOnly=false){
    EntranceCatalog::Asset check{};if(!EntranceCatalog::model(raw,check))return false;
    EntranceCatalog::Section vb{},ib{};if(!EntranceCatalog::sections(raw,0x587aa1,vb)||!EntranceCatalog::sections(raw,0x5878f4,ib))return false;
    unsigned vertices=EntranceCatalog::word32(vb.data+4),count=EntranceCatalog::word32(ib.data+4),width=EntranceCatalog::word32(ib.data+8);
    std::vector<unsigned char> vertexData(vb.data+16,vb.data+16+(size_t)vertices*20);
    std::vector<unsigned> indices;indices.reserve(count+4096);
    for(unsigned face=0;face<count;face+=3){Vertex triangle[3];unsigned original[3];int selected=-1;
        for(unsigned k=0;k<3;++k){const auto p=ib.data+16+(size_t)(face+k)*width;original[k]=width==2?EntranceCatalog::word16(p):EntranceCatalog::word32(p);triangle[k]=decode(vb.data+16+(size_t)original[k]*20);}
        for(unsigned s=0;s<asset.slots;++s){const auto& slot=asset.token[s];
            float u=(triangle[0][9]+triangle[1][9]+triangle[2][9])/3,v=(triangle[0][10]+triangle[1][10]+triangle[2][10])/3;
            if(u>slot.x/4096.f&&u<(slot.x+slot.size)/4096.f&&v>slot.y/4096.f&&v<(slot.y+slot.size)/4096.f&&
               in_slot(triangle[0],slot)&&in_slot(triangle[1],slot)&&in_slot(triangle[2],slot)){selected=(int)s;break;}
        }
        if(selected<0){indices.insert(indices.end(),original,original+3);continue;}
        if(bodyOnly)continue;
        const auto& slot=asset.token[selected];const auto& rectangles=slot.side?away:home;
        float minU=std::min({triangle[0][9],triangle[1][9],triangle[2][9]}),maxU=std::max({triangle[0][9],triangle[1][9],triangle[2][9]});
        float minV=std::min({triangle[0][10],triangle[1][10],triangle[2][10]}),maxV=std::max({triangle[0][10],triangle[1][10],triangle[2][10]});
        for(const auto& rectangle:rectangles){
            float left=(slot.x+rectangle.left*slot.size)/4096.f,right=(slot.x+rectangle.right*slot.size)/4096.f;
            float top=(slot.y+rectangle.top*slot.size)/4096.f,bottom=(slot.y+rectangle.bottom*slot.size)/4096.f;
            if(maxU<=left||minU>=right||maxV<=top||minV>=bottom)continue;
            std::vector<Vertex> polygon(triangle,triangle+3);
            clip(polygon,9,left,true);clip(polygon,9,right,false);clip(polygon,10,top,true);clip(polygon,10,bottom,false);
            if(polygon.size()<3)continue;
            for(size_t t=1;t+1<polygon.size();++t){
                const auto& a=polygon[0];const auto& b=polygon[t];const auto& c=polygon[t+1];
                if(fabsf((b[9]-a[9])*(c[10]-a[10])-(b[10]-a[10])*(c[9]-a[9]))<1e-12f)continue;
                unsigned first=(unsigned)(vertexData.size()/20);encode(a,vertexData);encode(b,vertexData);encode(c,vertexData);
                indices.insert(indices.end(),{first,first+1,first+2});
            }
            if(vertexData.size()/20>750000||indices.size()>3000000)return build(raw,asset,home,away,output,true);
        }
    }
    if(indices.empty()||vertexData.size()/20>1000000)return false;
    unsigned vertexCount=(unsigned)(vertexData.size()/20),indexWidth=vertexCount<=65535?2:4;
    std::vector<unsigned char> newVertex(aligned(16+vertexData.size()));put32(newVertex,0,(unsigned)newVertex.size());put32(newVertex,4,vertexCount);put32(newVertex,8,20);put32(newVertex,12,1);memcpy(newVertex.data()+16,vertexData.data(),vertexData.size());
    std::vector<unsigned char> newIndex(aligned(16+(size_t)indices.size()*indexWidth));put32(newIndex,0,(unsigned)newIndex.size());put32(newIndex,4,(unsigned)indices.size());put32(newIndex,8,indexWidth);
    for(size_t i=0;i<indices.size();++i){if(indexWidth==2){unsigned short v=(unsigned short)indices[i];memcpy(newIndex.data()+16+i*2,&v,2);}else put32(newIndex,16+i*4,indices[i]);}
    unsigned sections=EntranceCatalog::word32(raw.data()+12);output.assign(raw.begin(),raw.begin()+16+sections*16);output.resize(aligned(output.size()));
    for(unsigned s=0;s<sections;++s){auto row=raw.data()+16+s*16;unsigned kind=EntranceCatalog::word32(row),offset=EntranceCatalog::word32(row+4),length=EntranceCatalog::word32(row+8);
        std::vector<unsigned char> bytes(raw.begin()+offset,raw.begin()+offset+length);
        if(kind==0x587aa1)bytes=newVertex;else if(kind==0x5878f4)bytes=newIndex;
        else if(kind==0x22b2be36){if(bytes.size()<28)return false;put32(bytes,16,(unsigned)newIndex.size());put32(bytes,20,(unsigned)indices.size());put32(bytes,24,indexWidth);}
        put32(output,16+s*16+4,(unsigned)output.size());put32(output,16+s*16+8,(unsigned)bytes.size());
        output.insert(output.end(),bytes.begin(),bytes.end());output.resize(aligned(output.size()));
    }
    if(output.size()>32*1024*1024)return false;put32(output,8,(unsigned)output.size());return EntranceCatalog::model(output,check);
}
}
