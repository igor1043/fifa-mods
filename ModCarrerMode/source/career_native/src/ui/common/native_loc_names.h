#pragma once
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>
/* Read-only counterpart of localization/loc_db.py. Never rewrite LOC, never
 * reinterpret Huffman bytes as ANSI, and never retain a game DB pointer. */
namespace native_loc {
inline uint32_t u32(const std::vector<uint8_t>&b,size_t p){return uint32_t(b[p])|uint32_t(b[p+1])<<8|uint32_t(b[p+2])<<16|uint32_t(b[p+3])<<24;}
inline uint32_t crc(const std::vector<uint8_t>&b,size_t p,size_t end){
    uint32_t value=0xffffffff;for(;p<end;++p){value^=uint32_t(b[p])<<24;for(int bit=0;bit<8;++bit)value=(value<<1)^((value&0x80000000)?0x04c11db7:0);}return value;
}
class Names {
    std::unordered_map<int,std::string>names,leagues,nations;
    static bool decode(const std::vector<uint8_t>&b,size_t block,size_t length,size_t tree,uint32_t pointer,bool long_string,std::string&out){
        out.clear();if(pointer==0xffffffff)return true;size_t prefix=long_string?2:1;
        if(pointer<tree||pointer+prefix>length)return false;
        size_t count=b[block+pointer];if(long_string)count=count*256+b[block+pointer+1];if(count>32000)return false;
        size_t bit=(pointer+prefix)*8;out.reserve(count);
        for(size_t i=0;i<count;++i){size_t node=0;bool leaf=false;
            for(int depth=0;depth<32;++depth){if(bit>=length*8||node*4+3>=tree)return false;
                unsigned side=(b[block+bit/8]>>(7-bit%8))&1;++bit;
                unsigned child=b[block+node*4+side*2],symbol=b[block+node*4+side*2+1];
                if(child){if(symbol)return false;node=child;}else{if(!symbol)return false;out.push_back((char)symbol);leaf=true;break;}}
            if(!leaf)return false;
        }
        return out.empty()||MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,out.data(),(int)out.size(),nullptr,0)>0;
    }
    bool load(const std::string&path){
        FILE*f=nullptr;if(fopen_s(&f,path.c_str(),"rb")||!f)return false;fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);
        if(size<124||size>32*1024*1024){fclose(f);return false;}std::vector<uint8_t>b(size);size_t got=fread(b.data(),1,b.size(),f);fclose(f);if(got!=b.size())return false;
        static const uint8_t signature[8]={'D','B',0,8,0,0,0,0};
        if(memcmp(b.data(),signature,8)||u32(b,8)!=b.size()||u32(b,16)!=1||memcmp(b.data()+24,"GJCv",4)||u32(b,28)!=0)return false;
        size_t table=36,records=120;unsigned allocated=b[52]|unsigned(b[53])<<8,count=b[54]|unsigned(b[55])<<8;
        if(u32(b,40)!=16||b[60]!=3||!count||count>allocated)return false;
        /* Exact source/key field types and bit offsets, no guessed schema. */
        if(u32(b,72)!=14||u32(b,76)!=0||memcmp(b.data()+80,"bYbZ",4)||u32(b,88)!=3||u32(b,92)!=32||memcmp(b.data()+96,"jKhj",4)||u32(b,104)!=13||u32(b,108)!=64||memcmp(b.data()+112,"VhAs",4))return false;
        size_t block=records+allocated*16,length=u32(b,48),end=block+((length+7)&~size_t(7));
        if(length<4||end+4!=b.size())return false;
        for(auto r:{std::pair<size_t,size_t>{0,20},{24,32},{36,68},{72,end}})if(crc(b,r.first,r.second)!=u32(b,r.second))return false;
        size_t tree=length;for(unsigned i=0;i<count;++i)for(size_t field:{size_t(0),size_t(8)}){auto p=u32(b,records+i*16+field);if(p!=0xffffffff)tree=std::min(tree,size_t(p));}
        if(!tree||tree%4||tree>1020)return false;
        std::unordered_map<int,std::string>decoded,divisions,countries;
        for(unsigned i=0;i<count;++i){std::string key,value;if(!decode(b,block,length,tree,u32(b,records+i*16+8),false,key))continue;
            bool league=key.compare(0,11,"LeagueName_")==0;
            bool nation=key.compare(0,11,"NationName_")==0;
            const char*prefix=league?"LeagueName_":nation?"NationName_":"TrophyName_";if(key.compare(0,strlen(prefix),prefix))continue;
            std::string id=key.substr(strlen(prefix));if(id.empty()||id.find_first_not_of("0123456789")!=id.npos)continue;
            if(decode(b,block,length,tree,u32(b,records+i*16),true,value)&&!value.empty())(league?divisions:nation?countries:decoded)[atoi(id.c_str())]=std::move(value);
        }if(decoded.empty())return false;names=std::move(decoded);leagues=std::move(divisions);nations=std::move(countries);return true;
    }
public:
    explicit Names(const std::string&root){if(!load(root+"/data/loc/por_br.db"))load(root+"/data/loc/eng_us.db");
        /* Installed custom competition labels are a fallback, not a navigation
         * dependency. The original UTF-8 LOC name always wins for its key. */
        FILE*f=nullptr;if(fopen_s(&f,(root+"/FSW/settings.ini").c_str(),"rb")||!f)return;
        char line[2048];bool section=false;while(fgets(line,sizeof(line),f)){
            if(line[0]=='['){section=_strnicmp(line,"[movies]",8)==0;continue;}if(!section)continue;
            char*equal=strchr(line,'=');if(!equal)continue;*equal=0;int id=atoi(line);if(id<=0||id>65535||names.count(id))continue;
            std::string value=equal+1;while(!value.empty()&&(value.back()=='\r'||value.back()=='\n'||value.back()==' '))value.pop_back();
            if(value.empty())continue;if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),(int)value.size(),nullptr,0)){
                int count=MultiByteToWideChar(1252,0,value.c_str(),-1,nullptr,0);std::vector<wchar_t>w(count);
                if(!count)continue;MultiByteToWideChar(1252,0,value.c_str(),-1,w.data(),count);
                int n=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);std::string converted(n,'\0');
                WideCharToMultiByte(CP_UTF8,0,w.data(),-1,&converted[0],n,nullptr,nullptr);converted.pop_back();value=std::move(converted);}
            names[id]=std::move(value);
        }fclose(f);
    }
    std::string competition(int id)const{auto it=names.find(id);return it==names.end()?std::string{}:it->second;}
    std::string league(int id)const{auto it=leagues.find(id);return it==leagues.end()?std::string{}:it->second;}
    std::string nation(int id)const{auto it=nations.find(id);return it==nations.end()?std::string{}:it->second;}
};
}
