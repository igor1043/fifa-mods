
#pragma once
#include <float.h>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")

// All file parsing is complete before invoking any FIFA/RNA resource loader.
namespace EntranceCatalog {
struct Slot {unsigned x,y,size,side;};
struct Asset {
    char slug[81]={};
    unsigned competition=0,round=0;
    uint64_t stamp=0;
    float minimum[4]={},maximum[4]={};
    unsigned slots=0;
    Slot token[64]={};
};
static bool slug(const char* value){
    size_t length=strlen(value);if(!length||length>80)return false;
    for(size_t i=0;i<length;++i)if(!((value[i]>='a'&&value[i]<='z')||(value[i]>='0'&&value[i]<='9')||(i&&(value[i]=='-'||value[i]=='_'))))return false;
    return true;
}
static unsigned word32(const unsigned char* p){unsigned x;memcpy(&x,p,4);return x;}
static unsigned short word16(const unsigned char* p){unsigned short x;memcpy(&x,p,2);return x;}
static float half(unsigned short value){
    const unsigned sign=value>>15,exponent=(value>>10)&31,fraction=value&1023;
    float result=exponent==0?ldexpf((float)fraction,-24):exponent==31?(fraction?NAN:INFINITY):ldexpf((float)(1024+fraction),(int)exponent-25);
    return sign?-result:result;
}
static bool read(const char* path,std::vector<unsigned char>& out){
    FILE* file=nullptr;if(fopen_s(&file,path,"rb")||!file)return false;
    if(fseek(file,0,SEEK_END)){fclose(file);return false;}
    long bytes=ftell(file);rewind(file);
    if(bytes<32||bytes>32*1024*1024){fclose(file);return false;}
    out.resize((size_t)bytes);bool ok=fread(out.data(),1,out.size(),file)==out.size();fclose(file);return ok;
}
struct Section {const unsigned char* data;unsigned length;};
static bool sections(const std::vector<unsigned char>& raw,unsigned kind,Section& section){
    if(raw.size()<32||memcmp(raw.data(),"RX3l",4)||word32(raw.data()+8)!=raw.size())return false;
    unsigned count=word32(raw.data()+12);if(!count||count>32||16+(size_t)count*16>raw.size())return false;
    bool found=false;
    for(unsigned i=0;i<count;++i){
        const auto row=raw.data()+16+i*16;unsigned offset=word32(row+4),length=word32(row+8);
        if(offset<16+count*16||length<4||(size_t)offset+length>raw.size())return false;
        if(word32(row)==kind){if(found)return false;section={raw.data()+offset,length};found=true;}
    }return found;
}
static bool model(const std::vector<unsigned char>& raw,Asset& out){
    Section vertex{},index{};
    if(!sections(raw,0x587aa1,vertex)||!sections(raw,0x5878f4,index))return false;
    if(vertex.length<16||index.length<16)return false;
    unsigned vertices=word32(vertex.data+4),stride=word32(vertex.data+8),indices=word32(index.data+4),width=word32(index.data+8);
    if(!vertices||vertices>1000000||stride!=20||!indices||indices>6000000||indices%3||(width!=2&&width!=4)||
       word32(vertex.data)!=vertex.length||word32(index.data)!=index.length||
       16+(size_t)vertices*stride>vertex.length||16+(size_t)indices*width>index.length)return false;
    for(unsigned k=0;k<3;++k){out.minimum[k]=FLT_MAX;out.maximum[k]=-FLT_MAX;}
    for(unsigned i=0;i<vertices;++i){
        auto p=vertex.data+16+(size_t)i*stride;
        for(unsigned k=0;k<3;++k){
            float value=half(word16(p+k*2));if(!isfinite(value)||fabsf(value)>50000)return false;
            out.minimum[k]=std::min(out.minimum[k],value);out.maximum[k]=std::max(out.maximum[k],value);
        }
        for(unsigned k=16;k<20;k+=2)if(!isfinite(half(word16(p+k))))return false;
    }
    for(unsigned i=0;i<indices;++i){auto p=index.data+16+(size_t)i*width;unsigned value=width==2?word16(p):word32(p);if(value>=vertices)return false;}
    for(unsigned k=0;k<3;++k){out.minimum[k]-=10;out.maximum[k]+=10;}
    return out.maximum[1]>out.minimum[1]&&out.maximum[0]>out.minimum[0]&&out.maximum[2]>out.minimum[2];
}
static bool texture(const std::vector<unsigned char>& raw){
    if(raw.size()<32||memcmp(raw.data(),"RX3l",4)||word32(raw.data()+8)!=raw.size())return false;
    unsigned count=word32(raw.data()+12);if(!count||count>32||16+(size_t)count*16>raw.size())return false;
    unsigned colours=0;
    for(unsigned i=0;i<count;++i){
        auto row=raw.data()+16+i*16;unsigned offset=word32(row+4),length=word32(row+8);
        if(offset<16+count*16||length<4||(size_t)offset+length>raw.size())return false;
        if(word32(row)!=0x7a0b60da)continue;
        ++colours;auto t=raw.data()+offset;
        if(length<16||word32(t)!=length||t[5]!=2)return false;
        unsigned w=word16(t+8),h=word16(t+10),mips=word16(t+14);
        if(!w||!h||w>4096||h>4096||(w&(w-1))||(h&(h-1))||!mips||mips>13)return false;
        size_t at=16;
        for(unsigned level=0;level<mips;++level){
            if(at+16>length)return false;
            unsigned pitch=word32(t+at),rows=word32(t+at+4),bytes=word32(t+at+8);at+=16;
            if(pitch!=std::max(1u,(w+3)/4)*16||rows!=std::max(1u,(h+3)/4)||bytes!=pitch*rows||at+bytes>length)return false;
            at+=bytes;w=std::max(1u,w/2);h=std::max(1u,h/2);
        }if(at!=length)return false;
    }return colours==3;
}
static uint64_t digest(const std::vector<unsigned char>& raw){uint64_t x=14695981039346656037ull;for(auto byte:raw){x^=byte;x*=1099511628211ull;}return x;}
static bool approved(const std::vector<unsigned char>& raw,const char* key,const char* ini){
    char expected[66]={};GetPrivateProfileStringA("asset",key,"",expected,sizeof(expected),ini);
    if(strlen(expected)!=64)return false;
    BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char bytes[32]={};
    bool ok=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
    if(ok)ok=BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0;
    if(ok)ok=BCryptHashData(hash,const_cast<PUCHAR>(raw.data()),(ULONG)raw.size(),0)>=0;
    if(ok)ok=BCryptFinishHash(hash,bytes,sizeof(bytes),0)>=0;
    if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);
    if(!ok)return false;
    const char digits[]="0123456789abcdef";char actual[65]={};
    for(unsigned i=0;i<32;++i){actual[2*i]=digits[bytes[i]>>4];actual[2*i+1]=digits[bytes[i]&15];}
    return !_stricmp(expected,actual);
}
static bool load(const char* game,const char* name,unsigned competition,unsigned round,Asset& out){
    if(!slug(name))return false;
    char directory[MAX_PATH],path[MAX_PATH],metadata[MAX_PATH];
    if(_snprintf_s(directory,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s",game,name)<0)return false;
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\asset.ini",directory);
    strcpy_s(metadata,path);
    if(GetPrivateProfileIntA("asset","schema",0,path)!=1)return false;
    unsigned expectedModel=GetPrivateProfileIntA("asset","model_bytes",0,path),expectedTexture=GetPrivateProfileIntA("asset","texture_bytes",0,path);
    out.slots=GetPrivateProfileIntA("asset","slots",65,path);if(out.slots>64)return false;
    for(unsigned i=0;i<out.slots;++i){
        char section[24];_snprintf_s(section,sizeof(section),_TRUNCATE,"slot%u",i);Slot& s=out.token[i];
        s.x=GetPrivateProfileIntA(section,"x",4096,path);s.y=GetPrivateProfileIntA(section,"y",4096,path);
        s.size=GetPrivateProfileIntA(section,"size",0,path);s.side=GetPrivateProfileIntA(section,"side",2,path);
        if(s.side>1||s.size<4||s.size>2048||(s.size&(s.size-1))||s.x%4||s.y%4||s.x+s.size>4096||s.y+s.size>4096)return false;
        for(unsigned j=0;j<i;++j){const Slot& p=out.token[j];if(s.x<p.x+p.size&&p.x<s.x+s.size&&s.y<p.y+p.size&&p.y<s.y+s.size)return false;}
    }
    std::vector<unsigned char> raw;
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\model.rx3",directory);
    if(!read(path,raw)||raw.size()!=expectedModel||!model(raw,out)||!approved(raw,"model_sha256",metadata))return false;
    uint64_t stamp=digest(raw);
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\template.rx3",directory);
    if(!read(path,raw)||raw.size()!=expectedTexture||!texture(raw)||!approved(raw,"texture_sha256",metadata))return false;
    out.stamp=stamp^digest(raw)^((uint64_t)competition<<32)^round;
    for(unsigned i=0;i<out.slots;++i){const auto s=out.token[i];out.stamp=out.stamp*1099511628211ull^s.x^((uint64_t)s.y<<12)^((uint64_t)s.size<<24)^((uint64_t)s.side<<48);}
    strcpy_s(out.slug,name);out.competition=competition;out.round=round;return true;
}
}
