#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "fifa_player_assets.h"
#include "../../platform/mod_paths.h"
#include "../../screens/player/club_player_profile.h"
#include "../../ui/common/native_loc_names.h"
#include "../../ui/common/profile_reputation.h"
#include "../../../third_party/miniz/miniz_tinfl.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <limits>
#include <cfloat>
#include <cstdlib>
#include <cctype>
#include <mutex>
#include <DirectXMath.h>

namespace {
std::mutex player_identity_guard;
std::unordered_map<int,int> player_nationalities;
struct Birthday {int raw,date;};
std::unordered_map<int,Birthday> player_birthdays;
std::unordered_map<int,int> player_feet;
struct League {int id;std::string name;};
std::unordered_map<int,League> club_leagues;
struct LeagueStrength {int league;float value;};
std::unordered_map<int,LeagueStrength> live_strengths;
int player_career_date=0;
struct CompetitionSnapshot {std::vector<PlayerCompetitionInput>rows;bool available=false;int club=0,date=0;unsigned long generation=0;};
std::shared_ptr<const CompetitionSnapshot>competition_snapshot;
std::unordered_map<uint64_t,player_competitions::Stats>competition_cache;
}
extern "C" void player_profile_publish_competitions(const PlayerCompetitionInput*rows,size_t count,int club,int date,unsigned long generation){
    std::lock_guard<std::mutex>guard(player_identity_guard);
    if(competition_snapshot&&competition_snapshot->club==club&&competition_snapshot->date==date&&competition_snapshot->generation==generation)return;
    auto snapshot=std::make_shared<CompetitionSnapshot>();snapshot->club=club;snapshot->date=date;snapshot->generation=generation;
    snapshot->available=club>0&&club_profile::valid_date(date)&&count<=196608&&(!count||rows);
    if(snapshot->available&&count)snapshot->rows.assign(rows,rows+count);
    competition_snapshot=snapshot;competition_cache.clear();
}
extern "C" void player_profile_publish_nationality(int id,int nation) {
    if(id<=0||id>524287)return;
    std::lock_guard<std::mutex>guard(player_identity_guard);
    if(player_nationalities.size()>=4096&&!player_nationalities.count(id))player_nationalities.erase(player_nationalities.begin());
    player_nationalities[id]=nation>0&&nation<=3000?nation:0;
}
extern "C" void player_profile_publish_career_date(int date){
    std::lock_guard<std::mutex>guard(player_identity_guard);player_career_date=club_profile::valid_date(date)?date:0;
}
extern "C" void player_profile_publish_birthdate(int id,int raw,int date){
    if(id<=0||id>524287)return;std::lock_guard<std::mutex>guard(player_identity_guard);
    if(player_birthdays.size()>=4096&&!player_birthdays.count(id))player_birthdays.erase(player_birthdays.begin());
    player_birthdays[id]={raw>=0&&raw<=1048575?raw:-1,club_profile::valid_date(date)?date:0};
}
extern "C" void player_profile_publish_foot(int id,int foot){
    if(id<=0||id>524287)return;std::lock_guard<std::mutex>guard(player_identity_guard);
    if(player_feet.size()>=4096&&!player_feet.count(id))player_feet.erase(player_feet.begin());player_feet[id]=foot==1||foot==2?foot:0;
}
extern "C" void player_profile_publish_league(int club,int id,const char*name){
    if(club<=0||club>200000)return;std::lock_guard<std::mutex>guard(player_identity_guard);
    if(club_leagues.size()>=512&&!club_leagues.count(club))club_leagues.erase(club_leagues.begin());
    club_leagues[club]={id>0&&id<=4096?id:0,name?std::string(name,strnlen(name,127)):std::string{}};
}
extern "C" void player_profile_publish_league_strength(int club,int league,float strength){
    if(club<=0||club>200000)return;std::lock_guard<std::mutex>guard(player_identity_guard);
    if(live_strengths.size()>=512&&!live_strengths.count(club))live_strengths.erase(live_strengths.begin());
    live_strengths[club]={league,std::isfinite(strength)&&strength>=0&&strength<=100?strength:-1};
}
namespace fifa_player {
player_competitions::Stats profile_competitions(int player,int club){
    uint64_t key=(uint64_t)(unsigned)club<<32|(unsigned)player;std::shared_ptr<const CompetitionSnapshot>snapshot;
    {std::lock_guard<std::mutex>guard(player_identity_guard);auto cached=competition_cache.find(key);if(cached!=competition_cache.end())return cached->second;snapshot=competition_snapshot;}
    if(!snapshot||!snapshot->available)return {};
    auto out=player_competitions::aggregate(snapshot->rows,player,club);
    {std::lock_guard<std::mutex>guard(player_identity_guard);if(snapshot==competition_snapshot){if(competition_cache.size()>=512)competition_cache.clear();competition_cache.emplace(key,out);}}
    return out;
}
std::vector<CompetitionIdentity>Assets::profile_competition_names(int player,int club){
    auto stats=profile_competitions(player,club);std::vector<CompetitionIdentity>out;
    for(auto&r:stats.rows){int key=r.asset>0?r.asset:r.root;auto at=competition_names_.find(key);
        if(at==competition_names_.end()){native_loc::Names names(root_);at=competition_names_.emplace(key,names.competition(key)).first;}
        out.push_back({r.root,r.asset,at->second.empty()?"Competição "+std::to_string(r.root):at->second});}
    return out;
}
static const size_t limit=64*1024*1024;
static uint32_t u32(const uint8_t *p, bool be=false) {
    if(be) return (uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|p[3];
    return p[0]|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
}
static uint16_t u16(const uint8_t *p, bool be=false) {
    return be ? uint16_t(p[0]*256+p[1]):uint16_t(p[0]+p[1]*256);
}
static float f32(const uint8_t *p, bool be) { uint32_t v=u32(p,be);float f;memcpy(&f,&v,4);return f; }
static float half(uint16_t h) {
    const int exp=(h>>10)&31; const float sign=(h&0x8000)?-1.f:1.f;
    if(exp==31) return std::numeric_limits<float>::quiet_NaN();
    return sign*std::ldexp(exp ? 1.f+float(h&1023)/1024.f:float(h&1023)/1024.f, exp?exp-15:-14);
}
static bool span(size_t p,size_t n,size_t size) {return p<=size && n<=size-p;}
bool read_kit_collars(const std::vector<uint8_t>&b,std::unordered_map<unsigned,int>&out) {
    /* Verified FIFA 16 teamkits fields have range-low zero. Packed values
     * are decoded in a private byte buffer; neither database nor save is touched. */
    if(b.size()<28||memcmp(b.data(),"DB\0\x08",4))return false;
    size_t tables=u32(b.data()+16),base=28+tables*8;
    if(!tables||tables>2048||!span(24,tables*8+4,b.size()))return false;
    for(size_t t=0;t<tables;++t) {
        const uint8_t*entry=b.data()+24+t*8;if(memcmp(entry,"GdtI",4))continue;
        size_t off=base+u32(entry+4);if(!span(off,36,b.size()))return false;
        size_t stride=u32(b.data()+off+4),count=u16(b.data()+off+18),fields=b[off+24];
        if(!stride||stride>4096||!fields||fields>128||count>u16(b.data()+off+16))return false;
        size_t descriptors=off+36,records=descriptors+fields*16;
        if(!span(descriptors,fields*16,b.size())||!span(records,count*stride,b.size()))return false;
        struct Field {size_t bit=0,depth=0;bool found=false;}team,kit,collar;
        for(size_t f=0;f<fields;++f) {
            const uint8_t*d=b.data()+descriptors+f*16;
            Field*target=!memcmp(d+8,"qljg",4)?&team:!memcmp(d+8,"MlXB",4)?&kit:!memcmp(d+8,"MQyn",4)?&collar:nullptr;
            if(!target)continue;size_t bit=u32(d+4),depth=u32(d+12);
            if(target->found||u32(d)!=3||!depth||depth>32||bit>stride*8||depth>stride*8-bit)return false;
            *target={bit,depth,true};
        }
        if(!team.found||!kit.found||!collar.found)return false;
        auto value=[](const uint8_t*r,const Field&f){unsigned n=0;
            for(size_t bit=0;bit<f.depth;++bit)n|=unsigned((r[(f.bit+bit)/8]>>((f.bit+bit)%8))&1)<<bit;return n;};
        std::unordered_map<unsigned,int>parsed;
        for(size_t i=0;i<count;++i){const uint8_t*r=b.data()+records+i*stride;
            unsigned id=value(r,team),type=value(r,kit),c=value(r,collar);
            if(id>0&&id<=200000&&type<=22&&c<=255)parsed[id*32+type]=(int)c;}
        out=std::move(parsed);return true;
    }return false;
}
bool read_kit_collar_override(const std::string&text,int team,int kit,int&out) {
    /* Only unconditional literal assignments. Never execute arbitrary Lua or
     * evaluate tournament/random/year expressions without their live context. */
    if(text.size()>1024*1024)return false;
    std::string clean;bool quote=false;char q=0;
    for(size_t i=0;i<text.size();) {
        if(quote){char c=text[i++];clean+=c;if(c=='\\'&&i<text.size())clean+=text[i++];else if(c==q)quote=false;continue;}
        if(text[i]=='\''||text[i]=='"'){quote=true;q=text[i];clean+=text[i++];continue;}
        if(i+1<text.size()&&text[i]=='-'&&text[i+1]=='-') {
            size_t p=i+2,level=0;if(p<text.size()&&text[p]=='['){++p;while(p<text.size()&&text[p]=='='){++level;++p;}
                if(p<text.size()&&text[p]=='['){auto end=text.find("]"+std::string(level,'=')+"]",p+1);
                    i=end==text.npos?text.size():end+level+2;clean+='\n';continue;}}
            i=text.find('\n',i);if(i==text.npos)break;continue;
        }
        clean+=text[i++];
    }
    std::istringstream lines(clean);std::string line;bool found=false;int chosen=-1;
    while(std::getline(lines,line)) {
        size_t p=line.find_first_not_of(" \t\r");if(p==line.npos)continue;
        /* Conditional files stay on the database fallback rather than guessing
         * whether an assignment inside a function/branch actually runs. */
        for(const char*word:{"if ","if(","function ","for ","while ","repeat"})if(line.compare(p,strlen(word),word)==0)return false;
        const std::string call="assignKitDetails";
        if(line.compare(p,call.size(),call))continue;p+=call.size();
        while(p<line.size()&&isspace((unsigned char)line[p]))++p;if(p>=line.size()||line[p++]!='(')continue;
        std::vector<std::string>args;size_t start=p;char quoted=0;bool closed=false;
        for(;p<line.size();++p){char c=line[p];
            if(quoted){if(c=='\\')++p;else if(c==quoted)quoted=0;continue;}
            if(c=='\''||c=='"'){quoted=c;continue;}
            if(c==','||c==')'){args.push_back(line.substr(start,p-start));start=p+1;if(c==')'){closed=true;break;}}
        }
        if(!closed||args.size()!=10)continue;
        auto integer=[](const std::string&s,int&v){char*end=nullptr;long n=strtol(s.c_str(),&end,10);
            if(end==s.c_str())return false;while(*end&&isspace((unsigned char)*end))++end;
            if(*end||n< -1||n>200000)return false;v=(int)n;return true;};
        int id,type,c;if(integer(args[0],id)&&integer(args[1],type)&&integer(args[9],c)&&id==team&&type==kit&&c>=-1&&c<=255){chosen=c;found=c>=0;}
    }if(found)out=chosen;return found;
}
static std::string normalized(std::string s) {
    for(char &c:s) {if(c=='\\')c='/';if(c>='A'&&c<='Z')c+=32;}return s;
}
static bool file_range(const std::string &path, uint64_t offset, size_t count,
    std::vector<uint8_t> &out) {
    FILE *f=nullptr; if(fopen_s(&f,path.c_str(),"rb")||!f)return false;
    _fseeki64(f,0,SEEK_END); const auto size=_ftelli64(f);
    if(!count && !offset && size>0) count=(size_t)size;
    bool ok=size>=0 && count>0 && count<=limit && offset<=uint64_t(size) && count<=uint64_t(size)-offset;
    if(ok) {out.resize(count);ok=_fseeki64(f,offset,SEEK_SET)==0 && fread(out.data(),1,count,f)==count;}
    fclose(f);if(!ok)out.clear();return ok;
}
bool decode_container(const std::vector<uint8_t> &src,std::vector<uint8_t> &out,size_t byte_limit) {
    const size_t limit=std::min(byte_limit,size_t(512)*1024*1024);
    out.clear(); if(src.size()<4||src.size()>limit)return false;
    if(src.size()>=32 && !memcmp(src.data(),"chunkzip",8)) {
        if(u32(src.data()+8,true)!=2)return false;
        size_t size=u32(src.data()+12,true), chunks=u32(src.data()+20,true), cursor=32;
        if(!size||size>limit||!chunks||chunks>1024)return false;
        out.reserve(size);
        for(size_t c=0;c<chunks;++c) {
            cursor=(cursor+3)&~size_t(3);size_t skipped=0;
            while(span(cursor,4,src.size()) && !u32(src.data()+cursor,true) && skipped++<16)cursor+=4;
            if(!span(cursor,8,src.size()))return false;
            size_t stored=u32(src.data()+cursor,true);uint32_t flag=u32(src.data()+cursor+4,true);cursor+=8;
            if(flag!=1||!stored||!span(cursor,stored,src.size())||out.size()>=size)return false;
            std::vector<uint8_t> block(size-out.size());
            size_t decoded=tinfl_decompress_mem_to_mem(block.data(),block.size(),src.data()+cursor,stored,0);
            if(decoded==TINFL_DECOMPRESS_MEM_TO_MEM_FAILED||!decoded||decoded>block.size())return false;
            out.insert(out.end(),block.begin(),block.begin()+decoded);cursor+=stored;
        }
        return out.size()==size;
    }
    if(src.size()>=5 && src[0]==0x10 && src[1]==0xfb) {
        size_t size=(size_t(src[2])<<16)|(size_t(src[3])<<8)|src[4],p=5;
        if(!size||size>limit)return false;out.reserve(size);bool ended=false;
        while(p<src.size()&&!ended) {
            unsigned a=src[p++];size_t lit=0,copy=0,back=0;
            if(a<0x80) {if(!span(p,1,src.size()))return false;lit=a&3;copy=((a>>2)&7)+3;back=((a&0x60)<<3)+src[p++]+1;}
            else if(a<0xc0) {if(!span(p,2,src.size()))return false;unsigned b=src[p++];lit=b>>6;copy=(a&63)+4;back=((b&63)<<8)+src[p++]+1;}
            else if(a<0xe0) {if(!span(p,3,src.size()))return false;unsigned b=src[p++],c=src[p++],d=src[p++];lit=a&3;copy=((a&12)<<6)+d+5;back=((a&16)<<12)+(b<<8)+c+1;}
            else if(a<0xfc)lit=((a&31)<<2)+4;
            else {lit=a&3;ended=true;}
            if(!span(p,lit,src.size())||lit+copy>size-out.size())return false;
            out.insert(out.end(),src.begin()+p,src.begin()+p+lit);p+=lit;
            if(copy && (!back||back>out.size()))return false;
            while(copy--)out.push_back(out[out.size()-back]);
        }
        return ended && out.size()==size;
    }
    out=src;return true;
}
struct Section {uint32_t type;size_t offset,size;};
static bool sections(const std::vector<uint8_t> &b,std::vector<Section> &s,bool &be,size_t max_sections=2048) {
    if(b.size()<16 || memcmp(b.data(),"RX3",3)|| (b[3]!='l'&&b[3]!='b'))return false;
    be=b[3]=='b';size_t n=u32(b.data()+12,be);
    if(!n||n>max_sections||!span(16,n*16,b.size()))return false;
    for(size_t i=0;i<n;++i) {
        const uint8_t *p=b.data()+16+16*i;
        Section e={u32(p,be),u32(p+4,be),u32(p+8,be)};
        if(e.size<4||!span(e.offset,e.size,b.size()))return false;s.push_back(e);
    }
    return true;
}
static std::vector<std::string> part_names(const std::vector<uint8_t>&b,const std::vector<Section>&s,bool be,size_t max_length=1024) {
    std::vector<std::string> out;
    for(auto e:s)if(e.type==0x4c9b9eb2 && e.size>=16) {
        size_t p=e.offset+16,end=e.offset+e.size,n=u32(b.data()+e.offset+4,be);
        if(n>2048)continue;
        for(size_t i=0;i<n&&span(p,8,end);++i) {
            size_t length=u32(b.data()+p+4,be);p+=8;
            if(!length||length>max_length||!span(p,length,end))break;
            std::string name((const char*)b.data()+p,length);auto z=name.find('\0');if(z!=name.npos)name.resize(z);
            out.push_back(name);p+=length;
        }
    }
    return out;
}
static bool decode_mesh(const std::vector<uint8_t>&b,std::vector<Part>&parts,bool stadium) {
    std::vector<Section> s,desc,vert,idx;bool be=false;
    if(!sections(b,s,be,stadium?8192:2048))return false;
    for(auto e:s) {
        if(e.type==0xc28193f0)desc.push_back(e);
        else if(e.type==0x00587aa1)vert.push_back(e);
        else if(e.type==0x005878f4)idx.push_back(e);
    }
    if(vert.empty()||vert.size()!=desc.size()||vert.size()!=idx.size()||vert.size()>(stadium?1024:64))return false;
    size_t total_vertices=0,total_indices=0;
    auto names=part_names(b,s,be);std::vector<Part> decoded;
    for(size_t m=0;m<vert.size();++m) {
        auto d=desc[m],v=vert[m],in=idx[m];
        if(d.size<16||v.size<16||in.size<16)return false;
        size_t n=u32(b.data()+v.offset+4,be),stride=u32(b.data()+v.offset+8,be);
        size_t count=u32(b.data()+in.offset+4,be),width=u32(b.data()+in.offset+8,be);
        size_t len=u32(b.data()+d.offset+4,be);
        total_vertices+=n;total_indices+=count;
        if(stadium&&(total_vertices>3000000||total_indices>12000000))return false;
        if(!n||n>200000||!stride||stride>512||!count||count>1000000||count%3||
           (width!=2&&width!=4)||!span(16,n*stride,v.size)||!span(16,count*width,in.size)||!span(16,len,d.size))return false;
        std::string text((const char*)b.data()+d.offset+16,len);std::istringstream tokens(text);
        size_t position_offset=SIZE_MAX,uv_offset=SIZE_MAX,normal_offset=SIZE_MAX;bool phalf=false,uhalf=false,normal_packed=false;
        size_t joint_offsets[2]={SIZE_MAX,SIZE_MAX},weight_offsets[2]={SIZE_MAX,SIZE_MAX};
        bool joint_words[2]={false,false};
        std::string token;
        while(tokens>>token) {
            char semantic[32]={0},format[32]={0};unsigned offset=0,stream=0,usage=0;
            if(sscanf_s(token.c_str(),"%31[^:]:%x:%x:%x:%31s",semantic,32,&offset,&stream,&usage,format,32)!=5)continue;
            if(!strcmp(semantic,"p0") && (!strncmp(format,"3f32",5)||!strncmp(format,"4f16",5))) {
                phalf=!strncmp(format,"4f16",5);if(!span(offset,phalf?8:12,stride))return false;position_offset=offset;
            }
            if(!strcmp(semantic,"t0")&&(!strncmp(format,"2f32",5)||!strncmp(format,"2f16",5))) {
                uhalf=!strncmp(format,"2f16",5);if(!span(offset,uhalf?4:8,stride))return false;uv_offset=offset;
            }
            if(!strcmp(semantic,"n0")&&(!strncmp(format,"3s10n",6)||!strncmp(format,"3f32",5))) {
                normal_packed=!strncmp(format,"3s10n",6);if(!span(offset,normal_packed?4:12,stride))return false;normal_offset=offset;
            }
            if((!strcmp(semantic,"i0")||!strcmp(semantic,"i1"))&&(!strcmp(format,"4u16")||!strcmp(format,"4u8"))) {
                int slot=semantic[1]-'0';joint_words[slot]=!strcmp(format,"4u16");
                if(!span(offset,joint_words[slot]?8:4,stride))return false;joint_offsets[slot]=offset;
            }
            if((!strcmp(semantic,"w0")||!strcmp(semantic,"w1"))&&(!strcmp(format,"4u8n")||!strcmp(format,"4u8"))) {
                if(!span(offset,4,stride))return false;weight_offsets[semantic[1]-'0']=offset;
            }
        }
        if(position_offset==SIZE_MAX)return false;
        Part p;p.name=m<names.size()?names[m]:"part";p.name=p.name.substr(0,p.name.find('.'));
        p.skinned=joint_offsets[0]!=SIZE_MAX&&weight_offsets[0]!=SIZE_MAX;
        p.native_normals=normal_offset!=SIZE_MAX;
        for(int slot=0;slot<2;++slot)if((joint_offsets[slot]==SIZE_MAX)!=(weight_offsets[slot]==SIZE_MAX))return false;
        p.vertices.reserve(n);p.indices.reserve(count);
        for(size_t j=0;j<n;++j) {
            const uint8_t *base=b.data()+v.offset+16+j*stride,*pos=base+position_offset;
            Vertex a={};
            a.position={phalf?half(u16(pos,be)):f32(pos,be),phalf?half(u16(pos+2,be)):f32(pos+4,be),phalf?half(u16(pos+4,be)):f32(pos+8,be)};
            if(uv_offset!=SIZE_MAX) {const uint8_t *t=base+uv_offset;a.u=uhalf?half(u16(t,be)):f32(t,be);a.v=uhalf?half(u16(t+2,be)):f32(t+4,be);}
            if(p.native_normals) {
                const uint8_t*normal=base+normal_offset;
                if(normal_packed) {
                    uint32_t packed=u32(normal,be);
                    auto component=[&](int shift){int value=(packed>>shift)&1023;if(value&512)value-=1024;return std::max(-1.f,value/511.f);};
                    a.normal={component(0),component(10),component(20)};
                } else a.normal={f32(normal,be),f32(normal+4,be),f32(normal+8,be)};
                float length=sqrtf(a.normal.x*a.normal.x+a.normal.y*a.normal.y+a.normal.z*a.normal.z);
                if(!std::isfinite(length)||length<.01f||length>2){if(!stadium)return false;p.native_normals=false;a.normal={};}
                else {a.normal.x/=length;a.normal.y/=length;a.normal.z/=length;}
            }
            unsigned weight_sum=0;
            for(int slot=0;slot<2;++slot)if(joint_offsets[slot]!=SIZE_MAX)for(int k=0;k<4;++k) {
                const uint8_t*j=base+joint_offsets[slot];int at=slot*4+k;
                a.joints[at]=joint_words[slot]?u16(j+k*2,be):j[k];a.weights[at]=base[weight_offsets[slot]+k];
                weight_sum+=a.weights[at];if(a.weights[at]&&a.joints[at]>=1024)return false;
            }
            if(p.skinned&&!weight_sum)return false;
            if(!std::isfinite(a.position.x)||!std::isfinite(a.position.y)||!std::isfinite(a.position.z)||
                fabs(a.position.x)>(stadium?100000:10000)||fabs(a.position.y)>(stadium?100000:10000)||fabs(a.position.z)>(stadium?100000:10000)||!std::isfinite(a.u)||!std::isfinite(a.v))return false;
            p.vertices.push_back(a);
        }
        for(size_t j=0;j<count;++j) {const uint8_t *a=b.data()+in.offset+16+j*width;uint32_t val=width==2?u16(a,be):u32(a,be);if(val>=n)return false;p.indices.push_back(val);}
        decoded.push_back(std::move(p));
    }
    parts=std::move(decoded);return true;
}
bool read_mesh(const std::vector<uint8_t>&b,std::vector<Part>&parts){return decode_mesh(b,parts,false);}
bool read_stadium(const std::vector<uint8_t>&b,const std::vector<uint8_t>&tex,Model&out){
    auto reject=[](int line){
#ifdef STADIUM_DECODER_DIAGNOSTICS
        fprintf(stderr,"Stadium decoder rejected line %d\n",line);
#endif
        return false;
    };
    std::vector<Section>s;bool be=false;if(!sections(b,s,be,8192))return reject(__LINE__);
    Model model;model.room=RoomStadium;model.player_count=0;
    if(!decode_mesh(b,model.parts,true))return reject(__LINE__);
    std::vector<int>materials;std::vector<std::string>shaders;size_t nodes=0;
    for(auto&e:s){
        if(e.type==0x28da5ce2)++nodes;
        if(e.type!=0x075bd958)continue;
        size_t p=e.offset+16,end=e.offset+e.size;int diffuse=-1;
        auto string=[&](std::string&v){size_t at=p;while(p<end&&b[p]&&p-at<1024)++p;if(p>=end||p-at>=1024)return reject(__LINE__);v.assign((const char*)b.data()+at,p-at);++p;return true;};
        std::string shader,key;if(!string(shader))return reject(__LINE__);
        size_t count=u32(b.data()+e.offset+4,be);if(count>32)return reject(__LINE__);
        for(size_t i=0;i<count;++i){if(!string(key)||!span(p,4,end))return reject(__LINE__);unsigned index=u32(b.data()+p,be);p+=4;if(key=="diffuseTexture"&&index<1024)diffuse=(int)index;}
        materials.push_back(diffuse);shaders.push_back(shader);
    }
    auto names=part_names(b,s,be,32768);
    const size_t texture_names_offset=nodes+model.parts.size();
#ifdef STADIUM_DECODER_DIAGNOSTICS
    fprintf(stderr,"mesh names=%zu nodes=%zu meshes=%zu resource_offset=%zu\n",names.size(),nodes,model.parts.size(),texture_names_offset);
    for(auto&e:s)if(e.type==0x4c9b9eb2){size_t p=e.offset+16;std::unordered_map<unsigned,unsigned>counts;for(size_t i=0;i<names.size()&&span(p,8,e.offset+e.size);++i){unsigned tag=u32(b.data()+p,be),len=u32(b.data()+p+4,be);p+=8;if(!span(p,len,e.offset+e.size))break;if(counts[tag]++<2)fprintf(stderr,"name tag %08x %.*s\n",tag,(int)len,b.data()+p);p+=len;}for(auto&c:counts)fprintf(stderr,"tag %08x count %u\n",c.first,c.second);}
#endif
    for(size_t i=0;i<model.parts.size();++i)if(nodes+i<names.size())model.parts[i].name=names[nodes+i];
    std::vector<std::string>groups;
    for(auto&e:s)if(e.type==0x0dc3ffd4){size_t p=e.offset+16,end=e.offset+e.size;while(p<end&&b[p])++p;if(p>=end)return reject(__LINE__);groups.emplace_back((const char*)b.data()+e.offset+16,p-e.offset-16);}
    std::vector<bool>assigned(model.parts.size()),visible(model.parts.size()),core(model.parts.size());size_t group=0;
    for(auto&e:s)if(e.type==0x7e2480ec){
        if(group>=groups.size())return reject(__LINE__);bool display=groups[group]!="Sky"&&groups[group]!="CollisionGeometry";
        bool focus=groups[group].find("MainStadium")==0||groups[group]=="Roof"||groups[group]=="Pitch";++group;
        if(e.size<120)return reject(__LINE__);size_t count=u32(b.data()+e.offset+112,be);
        if(count>1024||!span(120,count*40,e.size))return reject(__LINE__);
        // Native group transform must be identity in this first supported layout.
        // Reject rather than silently render translated geometry in the wrong place.
        for(int i=0;i<16;++i){float v=f32(b.data()+e.offset+16+i*4,be);if(!std::isfinite(v)||fabsf(v-(i%5==0?1.f:0.f))>.001f)return reject(__LINE__);}
        for(size_t i=0;i<count;++i){size_t p=e.offset+152+i*40;unsigned mesh=u32(b.data()+p,be),mat=u32(b.data()+p+4,be);
            if(mesh>=model.parts.size()||mat>=materials.size())return reject(__LINE__);
            model.parts[mesh].texture=materials[mat];assigned[mesh]=true;visible[mesh]=visible[mesh]||display;
            core[mesh]=core[mesh]||(display&&focus);
        }
    }
    if(std::find(assigned.begin(),assigned.end(),false)!=assigned.end())return reject(__LINE__);
    Vec3 core_lo={FLT_MAX,FLT_MAX,FLT_MAX},core_hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};bool has_core=false;
    for(size_t i=0;i<model.parts.size();++i)if(core[i])for(auto&v:model.parts[i].vertices){has_core=true;auto&p=v.position;core_lo.x=std::min(core_lo.x,p.x);core_lo.y=std::min(core_lo.y,p.y);core_lo.z=std::min(core_lo.z,p.z);core_hi.x=std::max(core_hi.x,p.x);core_hi.y=std::max(core_hi.y,p.y);core_hi.z=std::max(core_hi.z,p.z);}
    size_t part_index=0;model.parts.erase(std::remove_if(model.parts.begin(),model.parts.end(),[&](const Part&){return !visible[part_index++];}),model.parts.end());
    if(model.parts.empty())return reject(__LINE__);
    auto texture_list=texture_names(tex);if(texture_list.empty()||texture_list.size()>1024)return reject(__LINE__);
    model.textures.resize(texture_list.size());size_t texture_bytes=0,unbaked=0;
    for(auto&p:model.parts){
        if(p.texture<0){p.color={.65f,.70f,.72f};++unbaked;continue;} // Runtime-only surfaces have no baked diffuse in the RX3.
        if(texture_names_offset+size_t(p.texture)>=names.size())return reject(__LINE__);
        auto found=std::find(texture_list.begin(),texture_list.end(),names[texture_names_offset+p.texture]);
        if(found==texture_list.end()){
            std::string alias=names[texture_names_offset+p.texture];size_t dot=alias.rfind('.');
            if(dot!=alias.npos&&alias.size()-dot==4&&std::all_of(alias.begin()+dot+1,alias.end(),[](unsigned char c){return c>='0'&&c<='9';})){
                alias.resize(dot);if(std::count(texture_list.begin(),texture_list.end(),alias)==1)found=std::find(texture_list.begin(),texture_list.end(),alias);
            }
        }
#ifdef STADIUM_DECODER_DIAGNOSTICS
        if(found==texture_list.end()){fprintf(stderr,"missing stadium texture %s for mesh %s, names=%zu offset=%zu textures=%zu\n",names[texture_names_offset+p.texture].c_str(),p.name.c_str(),names.size(),texture_names_offset,texture_list.size());for(size_t i=0;i<std::min<size_t>(15,texture_list.size());++i)fprintf(stderr,"texture entry %zu %s\n",i,texture_list[i].c_str());}
#endif
        // No ambiguous image borrowing: runtime-only/missing diffuse surfaces
        // retain their geometry with a neutral material in this preview.
        if(found==texture_list.end()){p.texture=-1;p.color={.65f,.70f,.72f};++unbaked;continue;}p.texture=(int)(found-texture_list.begin());
        auto&t=model.textures[p.texture];if(t.bytes.empty()){if(!read_texture(tex,texture_list[p.texture],t))return reject(__LINE__);texture_bytes+=t.bytes.size();if(texture_bytes>256*1024*1024)return reject(__LINE__);}}
    // Center and normalize the entire structure. Camera scale is independent
    // of whether the source uses centimetres or metres; original bytes stay untouched.
    Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};
    for(auto&p:model.parts)for(auto&v:p.vertices){lo.x=std::min(lo.x,v.position.x);lo.y=std::min(lo.y,v.position.y);lo.z=std::min(lo.z,v.position.z);hi.x=std::max(hi.x,v.position.x);hi.y=std::max(hi.y,v.position.y);hi.z=std::max(hi.z,v.position.z);}
    float span=std::max({hi.x-lo.x,hi.y-lo.y,hi.z-lo.z});if(!std::isfinite(span)||span<1)return reject(__LINE__);
    if(!has_core){core_lo=lo;core_hi=hi;}
    Vec3 center={(core_hi.x+core_lo.x)*.5f,(core_hi.y+core_lo.y)*.5f,(core_hi.z+core_lo.z)*.5f};
    float rx=(core_hi.x-core_lo.x)*.5f,ry=(core_hi.y-core_lo.y)*.5f,rz=(core_hi.z-core_lo.z)*.5f;
    model.stadium_focus_radius=sqrtf(rx*rx+ry*ry+rz*rz)*1000/span;
    for(auto&p:model.parts)for(auto&v:p.vertices){v.position={(v.position.x-center.x)*1000/span,(v.position.y-center.y)*1000/span,(v.position.z-center.z)*1000/span};}
    model.diagnostic="Native RX3 stadium: "+std::to_string(model.parts.size())+" meshes; own diffuse materials; neutral runtime surfaces="+std::to_string(unbaked);out=std::move(model);return true;
}
bool read_skeleton(const std::vector<uint8_t>&b,Skeleton&out) {
    std::vector<Section>s;bool be=false;if(!sections(b,s,be))return false;
    Skeleton rig;rig.names=part_names(b,s,be);
    for(const auto&e:s) {
        if(e.size<16)return false;size_t count=u32(b.data()+e.offset+4,be);
        if(e.type==0xdf9aec1e) {
            if(!count||count>1024||e.size!=16+count*64||!rig.inverse_bind.empty())return false;
            rig.inverse_bind.resize(count);
            for(size_t i=0;i<count;++i)for(size_t j=0;j<16;++j){float f=f32(b.data()+e.offset+16+i*64+j*4,be);
                if(!std::isfinite(f))return false;rig.inverse_bind[i][j]=f;}
        } else if(e.type==0x70278fee) {
            if(!count||count>1024||!span(16,count*2,e.size)||!rig.parents.empty())return false;
            for(size_t i=0;i<count;++i){uint16_t p=u16(b.data()+e.offset+16+i*2,be);
                if(p!=0xffff&&p>=i)return false;rig.parents.push_back(p);}
        }
    }
    if(rig.names.empty()||rig.names.size()!=rig.parents.size()||rig.names.size()!=rig.inverse_bind.size())return false;
    out=std::move(rig);return true;
}
bool read_coach_skeleton(const std::vector<uint8_t>&b,Skeleton&out) {
    /* Verified compact SLC layout, NOT ANT/player vertex indices. Matrices
     * are stored as affine 4x3 in padded 4x4 slots (M44 is zero padding).
     * Accept only this 31-bone layout and anatomical bounds; other assets
     * retain their original static geometry instead of a guessed rig. */
    std::vector<Section>s;bool be=false;if(!sections(b,s,be))return false;
    static const char*names[]={"Reference","Root","Hips","RightUpLeg","RightLeg","RightFoot","RightToeBase",
        "LeftUpLeg","LeftLeg","LeftFoot","LeftToeBase","Spine","Spine2","Neck","Head","HeadEnd",
        "LeftShoulder","LeftArm","LeftForeArm","LeftHand","LeftHandEnd","RightShoulder","RightArm","RightForeArm","RightHand","RightHandEnd",
        "LeftAnkleAux","RightAnkleAux","Aux","Trajectory","End"};
    static const uint16_t parents[]={0xffff,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,12,16,17,18,19,12,21,22,23,24,9,5,0,0,0};
    Skeleton rig;std::vector<Vec3>world;
    for(const auto&e:s)if(e.type==0xdf9aec1e) {
        if(!rig.inverse_bind.empty()||e.size!=16+31*64||u32(b.data()+e.offset+4,be)!=31)return false;
        for(size_t i=0;i<31;++i) {
            std::array<float,16>m;for(int k=0;k<16;++k){m[k]=f32(b.data()+e.offset+16+i*64+k*4,be);if(!std::isfinite(m[k]))return false;}
            if(fabsf(m[3])+fabsf(m[7])+fabsf(m[11])>.001f||(fabsf(m[15])>.001f&&fabsf(m[15]-1)>.001f))return false;m[15]=1;
            DirectX::XMFLOAT4X4 matrix,rest;memcpy(&matrix,m.data(),64);DirectX::XMVECTOR det;
            auto inverse=DirectX::XMMatrixInverse(&det,DirectX::XMLoadFloat4x4(&matrix));
            if(!std::isfinite(DirectX::XMVectorGetX(det))||fabsf(DirectX::XMVectorGetX(det))<.0001f)return false;
            DirectX::XMStoreFloat4x4(&rest,inverse);world.push_back({rest._41,rest._42,rest._43});
            rig.inverse_bind.push_back(m);rig.names.push_back(names[i]);rig.parents.push_back(parents[i]);
        }
    }
    if(world.size()!=31)return false;
    if(world[2].y<70||world[2].y>140||world[14].y<world[13].y||world[17].x<5||world[22].x> -5||
        world[18].x<=world[17].x||world[23].x>=world[22].x||world[19].x<=world[18].x||world[24].x>=world[23].x||
        world[4].y>=world[3].y||world[8].y>=world[7].y||world[5].y>=world[4].y||world[9].y>=world[8].y)return false;
    out=std::move(rig);return true;
}
std::vector<std::string> texture_names(const std::vector<uint8_t>&b) {
    std::vector<Section>s;bool be=false;if(!sections(b,s,be))return {};
    return part_names(b,s,be);
}
bool read_texture(const std::vector<uint8_t>&b,const std::string &wanted,Texture &out) {
    std::vector<Section>s;bool be=false;if(!sections(b,s,be))return false;
    auto names=part_names(b,s,be);size_t index=0;
    for(auto e:s)if(e.type==2047566042) {
        size_t current=index++;if(e.size<32)continue;
        if(!wanted.empty() && (current>=names.size() ||
            (wanted.back()=='_'?names[current].find(wanted)!=0:names[current]!=wanted)))continue;
        const uint8_t*p=b.data()+e.offset;uint32_t format=p[5];size_t width=u16(p+8,be),height=u16(p+10,be),stored=u32(p+24,be);
        if(format>2||!width||!height||width>4096||height>4096)continue;
        size_t required=((width+3)/4)*((height+3)/4)*(format==0?8:16);
        if(stored<required||!span(32,stored,e.size))continue;
        out.width=(uint32_t)width;out.height=(uint32_t)height;out.format=format;
        out.bytes.assign(p+32,p+32+required);return true;
    }
    return false;
}
bool read_crest_dds(const std::vector<uint8_t>&b,Texture&out) {
    if(b.size()<128||memcmp(b.data(),"DDS ",4)||u32(b.data()+4,false)!=124||u32(b.data()+76,false)!=32)return false;
    uint32_t width=u32(b.data()+16,false),height=u32(b.data()+12,false),flags=u32(b.data()+80,false),four=u32(b.data()+84,false);
    if(!width||!height||width>2048||height>2048||!(flags&4))return false;
    uint32_t format=four==0x31545844?0:four==0x33545844?1:four==0x35545844?2:3;
    if(format>2)return false;size_t bytes=((width+3)/4)*size_t((height+3)/4)*(format?16:8);
    if(!span(128,bytes,b.size()))return false;
    Texture t;t.width=width;t.height=height;t.format=format;t.bytes.assign(b.begin()+128,b.begin()+128+bytes);out=std::move(t);return true;
}
float hair_alpha_scale(const Texture&t) {
    /* Some installed custom hair diffuse maps store only 0..1 or 0..3 in
     * their DXT5 alpha. Treat that low range as a mask; leaving it divided by
     * 255 erases the entire silhouette. Full-range maps are left unchanged.
     * Inspect USED texel values, not unused compression palette endpoints. */
    if(t.format!=2||t.bytes.empty()||t.bytes.size()%16)return 1;
    unsigned maximum=0;
    for(size_t block=0;block<t.bytes.size();block+=16) {
        const uint8_t*p=t.bytes.data()+block;unsigned values[8]={p[0],p[1]};uint64_t indices=0;
        if(p[0]>p[1])for(unsigned k=1;k<=6;++k)values[k+1]=((7-k)*p[0]+k*p[1])/7;
        else {for(unsigned k=1;k<=4;++k)values[k+1]=((5-k)*p[0]+k*p[1])/5;values[6]=0;values[7]=255;}
        for(int k=0;k<6;++k)indices|=uint64_t(p[k+2])<<(k*8);
        for(int pixel=0;pixel<16;++pixel)maximum=std::max(maximum,values[(indices>>(pixel*3))&7]);
        if(maximum>15)return 1;
    }
    return maximum?255.f/maximum:1.f;
}
void Assets::index_archives() {
    if(indexed_)return;indexed_=true;
    const char* files[]={"data_patch.big","data_front_end.big","data_graphic1_extra.big","data_graphic2_extra.big","data_graphic3_extra.big",
        "data_graphic1.big","data_graphic2.big","data_graphic3.big","data_front_end_extra.big","data_front_end.big","data_default.big",
        "data/ui/imgAssets/heads/2dheads0_extra.big","data/ui/imgAssets/heads/2dheads0.big"};
    for(const char*file:files) {
        std::string path=root_+"/"+file;std::vector<uint8_t>b;
        if(!file_range(path,0,16,b)|| (memcmp(b.data(),"BIG4",4)&&memcmp(b.data(),"BIGF",4)))continue;
        size_t n=u32(b.data()+8,true),end=u32(b.data()+12,true),p=16;
        if(n>2000000||end<16||end>8*1024*1024||!file_range(path,0,end,b))continue;
        for(size_t i=0;i<n && span(p,9,b.size());++i) {
            uint32_t offset=u32(b.data()+p,true),length=u32(b.data()+p+4,true);p+=8;size_t start=p;
            while(p<b.size()&&b[p]&&p-start<2048)++p;
            if(p>=b.size()||p-start>=2048)break;
            std::string name=normalized(std::string((const char*)b.data()+start,p-start));++p;
            if((name.find("data/sceneassets/")==0||name.find("data/ui/imgassets/crest/")==0||name.find("data/ui/imgassets/heads/")==0||name.find("data/ui/imgassets/league/")==0||name.find("data/ui/imgassets/trophy/")==0||name.find("data/ui/imgassets/flags512x512/")==0||name.find("data/ui/pow/imgassets/logos/")==0) && name.find("..") == name.npos && length<=limit && !entries_.count(name))
                entries_.emplace(name,Entry{path,offset,length});
        }
    }
}
static bool read_icon_dds(const std::vector<uint8_t>&stored,Texture&out) {
    if(stored.size()>=4&&!memcmp(stored.data(),"DDS ",4))return read_crest_dds(stored,out);
    std::vector<uint8_t>decoded;
    return decode_container(stored,decoded)&&read_crest_dds(decoded,out);
}
bool Assets::crest(int id,Texture&out) {
    if(id<=0)return false;
    if(checked_crests_.count(id)){auto found=crests_.find(id);if(found==crests_.end())return false;out=found->second;return true;}
    checked_crests_[id]=true;
    for(const char*theme:{"light","dark"}) {
        std::string path="data/ui/imgAssets/crest/"+std::string(theme)+"/l"+std::to_string(id)+".dds";std::vector<uint8_t>b;Texture t;
        if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,t)){crests_[id]=t;out=std::move(t);return true;}
        index_archives();auto found=entries_.find(normalized(path));
        if(found!=entries_.end()&&file_range(found->second.archive,found->second.offset,found->second.length,b)&&read_icon_dds(b,t)){crests_[id]=t;out=std::move(t);return true;}
    }
    return false;
}
bool Assets::competition_icon(int id,Texture&out) {
    if(id<=0||id>65535)return false;
    for(const char*theme:{"light","dark"}) {
        std::string path="data/ui/imgAssets/league/"+std::string(theme)+"/l"+std::to_string(id)+".dds";std::vector<uint8_t>b;
        if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,out))return true;
        index_archives();auto found=entries_.find(normalized(path));
        if(found!=entries_.end()&&file_range(found->second.archive,found->second.offset,found->second.length,b)&&read_icon_dds(b,out))return true;
    }return false;
}
bool Assets::competition_movement_icon(bool up,Texture&out) {
    const std::string path=up?"data/ui/pow/imgassets/logos/green_arrowup.dds":"data/ui/pow/imgassets/logos/red_arrowdown.dds";
    std::vector<uint8_t>b;Texture t;
    if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,t)){out=std::move(t);return true;}
    index_archives();auto found=entries_.find(normalized(path));
    if(found==entries_.end()||!file_range(found->second.archive,found->second.offset,found->second.length,b)||!read_icon_dds(b,t))return false;
    out=std::move(t);return true;
}
bool Assets::trophy_icon(int id,Texture&out) {
    if(id<=0||id>65535)return false;
    std::string path="data/ui/imgAssets/trophy/t"+std::to_string(id)+".dds";std::vector<uint8_t>b;
    if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,out))return true;
    index_archives();auto found=entries_.find(normalized(path));
    return found!=entries_.end()&&file_range(found->second.archive,found->second.offset,found->second.length,b)&&read_icon_dds(b,out);
}
bool Assets::portrait(int id,Texture&out) {
    if(id<=0||id>300000)return false;
    if(checked_portraits_.count(id)){auto found=portraits_.find(id);if(found==portraits_.end())return false;out=found->second;return true;}
    checked_portraits_[id]=true;
    const std::string path="data/ui/imgAssets/heads/p"+std::to_string(id)+".dds";std::vector<uint8_t>b;Texture t;
    if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,t)){portraits_[id]=t;out=std::move(t);return true;}
    index_archives();auto found=entries_.find(normalized(path));
    if(found!=entries_.end()&&file_range(found->second.archive,found->second.offset,found->second.length,b)&&read_icon_dds(b,t)) {
        portraits_[id]=t;out=std::move(t);return true;
    }
    return false; /* Never reuse another player's portrait. UI owns neutral placeholder. */
}
void Assets::load_player_identities() {
    if(!nationalities_checked_) {
        nationalities_checked_=true;std::vector<uint8_t>b;
        if(file_range(root_+"/data/db/fifa_ng_db.db",0,0,b)&&b.size()>=28&&!memcmp(b.data(),"DB\0\x08",4)) {
            size_t tables=u32(b.data()+16),base=28+tables*8;
            if(tables>0&&tables<=2048&&span(24,tables*8+4,b.size()))for(size_t t=0;t<tables;++t) {
                const uint8_t*entry=b.data()+24+t*8;if(memcmp(entry,"CZUM",4))continue;
                size_t off=base+u32(entry+4);if(!span(off,36,b.size()))break;
                size_t stride=u32(b.data()+off+4),count=u16(b.data()+off+18),fields=b[off+24];
                if(!stride||stride>4096||!fields||fields>128||count>u16(b.data()+off+16))break;
                size_t descriptors=off+36,records=descriptors+fields*16;
                if(!span(descriptors,fields*16,b.size())||!span(records,count*stride,b.size()))break;
                size_t bits[4]={},depths[4]={};bool valid=true;
                for(size_t f=0;f<fields;++f){const uint8_t*d=b.data()+descriptors+f*16;
                    int k=!memcmp(d+8,"ykFq",4)?0:!memcmp(d+8,"enmm",4)?1:!memcmp(d+8,"WVIU",4)?2:!memcmp(d+8,"MDvm",4)?3:-1;if(k<0)continue;
                    size_t bit=u32(d+4),depth=u32(d+12);
                    if(depths[k]||u32(d)!=3||!depth||depth>32||bit>stride*8||depth>stride*8-bit){valid=false;break;}
                    bits[k]=bit;depths[k]=depth;}
                if(valid&&depths[0]&&depths[1]&&depths[2]&&depths[3]==1)for(size_t i=0;i<count;++i){const uint8_t*r=b.data()+records+i*stride;unsigned values[4]={};
                    for(int k=0;k<4;++k)for(size_t bit=0;bit<depths[k];++bit)values[k]|=unsigned((r[(bits[k]+bit)/8]>>((bits[k]+bit)%8))&1)<<bit;
                    if(values[0]>0&&values[0]<=524287){if(values[1]>0&&values[1]<=3000)nationalities_[values[0]]=(int)values[1];if(values[2]<=1048575)birthdates_[values[0]]=(int)values[2];preferred_feet_[values[0]]=(int)values[3]+1;}}
                break;
            }
            if(tables>0&&tables<=2048&&span(24,tables*8+4,b.size()))for(size_t t=0;t<tables;++t){
                const uint8_t*entry=b.data()+24+t*8;if(memcmp(entry,"qdZF",4))continue;size_t off=base+u32(entry+4);if(!span(off,36,b.size()))break;
                size_t stride=u32(b.data()+off+4),count=u16(b.data()+off+18),fields=b[off+24],descriptors=off+36,records=descriptors+fields*16;
                if(!stride||stride>4096||!fields||fields>128||count>u16(b.data()+off+16)||!span(descriptors,fields*16,b.size())||!span(records,count*stride,b.size()))break;
                size_t bits[3]={},depths[3]={};bool valid=true;
                for(size_t f=0;f<fields;++f){const uint8_t*d=b.data()+descriptors+f*16;int k=!memcmp(d+8,"mCXg",4)?0:!memcmp(d+8,"aQrQ",4)?1:!memcmp(d+8,"tROM",4)?2:-1;if(k<0)continue;
                    size_t bit=u32(d+4),depth=u32(d+12);if(depths[k]||u32(d)!=3||!depth||depth>32||bit>stride*8||depth>stride*8-bit){valid=false;break;}bits[k]=bit;depths[k]=depth;}
                if(valid&&depths[0]&&depths[1]&&depths[2])for(size_t i=0;i<count;++i){const uint8_t*r=b.data()+records+i*stride;unsigned v[3]={};
                    for(int k=0;k<3;++k)for(size_t bit=0;bit<depths[k];++bit)v[k]|=unsigned((r[(bits[k]+bit)/8]>>((bits[k]+bit)%8))&1)<<bit;
                    unsigned club=v[0]+1,league=v[1]+1;if(v[2]||club>200000||league>4096)continue;
                    auto at=club_leagues_.find(club);if(at==club_leagues_.end())club_leagues_[club]=(int)league;else if(at->second!=(int)league)at->second=0;}
                break;
            }
        }
    }
}
int Assets::nationality(int id) {
    if(id<=0||id>524287)return 0;
    {std::lock_guard<std::mutex>guard(player_identity_guard);
        auto live=player_nationalities.find(id);if(live!=player_nationalities.end())return live->second;}
    load_player_identities();
    auto at=nationalities_.find(id);return at==nationalities_.end()?0:at->second;
}
int Assets::player_age(int id) {
    if(id<=0||id>524287)return -1;int date=0;
    {std::lock_guard<std::mutex>guard(player_identity_guard);date=player_career_date;
        auto live=player_birthdays.find(id);if(live!=player_birthdays.end())return club_profile::age_at(live->second.raw,live->second.date?live->second.date:date);}
    load_player_identities();auto at=birthdates_.find(id);
    return at==birthdates_.end()?-1:club_profile::age_at(at->second,date);
}
int Assets::preferred_foot(int id){
    if(id<=0||id>524287)return 0;{std::lock_guard<std::mutex>guard(player_identity_guard);auto at=player_feet.find(id);if(at!=player_feet.end())return at->second;}
    load_player_identities();auto at=preferred_feet_.find(id);return at==preferred_feet_.end()?0:at->second;
}
int Assets::league(int club,std::string&name){
    name.clear();if(club<=0||club>200000)return 0;int id=0;bool live=false;
    {std::lock_guard<std::mutex>guard(player_identity_guard);auto at=club_leagues.find(club);if(at!=club_leagues.end()){live=true;id=at->second.id;name=at->second.name;}}
    if(!live){load_player_identities();auto at=club_leagues_.find(club);if(at!=club_leagues_.end())id=at->second;}
    if(id>0&&name.empty()){auto at=league_names_.find(id);if(at==league_names_.end()){native_loc::Names names(root_);at=league_names_.emplace(id,names.league(id)).first;}name=at->second;}
    return id;
}
float Assets::league_strength(int club){
    std::string name;int id=league(club,name);if(id<=0)return -1;
    {std::lock_guard<std::mutex>lock(player_identity_guard);auto live=live_strengths.find(club);
        if(live!=live_strengths.end())return live->second.league==id?live->second.value:-1;}
    if(!league_strength_checked_){league_strength_checked_=true;std::vector<uint8_t>b;
        if(file_range(root_+"/data/db/fifa_ng_db.db",0,0,b)&&b.size()>=28&&!memcmp(b.data(),"DB\0\x08",4)){
            std::unordered_map<int,int>levels,prestige;std::unordered_map<int,std::unordered_map<int,bool>>members;
            size_t tables=u32(b.data()+16),base=28+tables*8;
            if(tables>0&&tables<=2048&&span(24,tables*8+4,b.size()))for(size_t t=0;t<tables;++t){
                const uint8_t*e=b.data()+24+t*8;int kind=!memcmp(e,"onMQ",4)?0:!memcmp(e,"lyxL",4)?1:!memcmp(e,"qdZF",4)?2:-1;if(kind<0)continue;
                size_t off=base+u32(e+4);if(!span(off,36,b.size()))continue;
                size_t stride=u32(b.data()+off+4),count=u16(b.data()+off+18),fields=b[off+24],desc=off+36,records=desc+fields*16;
                if(!stride||stride>4096||!fields||fields>128||count>u16(b.data()+off+16)||!span(desc,fields*16,b.size())||!span(records,count*stride,b.size()))continue;
                const char*names[3]={kind==0?"aQrQ":"mCXg",kind==0?"paPI":kind==1?"edvw":"aQrQ","tROM"};
                size_t bits[3]={},depths[3]={};bool valid=true;int needed=kind==2?3:2;
                for(size_t f=0;f<fields;++f){const uint8_t*d=b.data()+desc+f*16;int k=-1;for(int j=0;j<needed;++j)if(!memcmp(d+8,names[j],4))k=j;if(k<0)continue;
                    size_t bit=u32(d+4),depth=u32(d+12);if(depths[k]||u32(d)!=3||!depth||depth>32||bit>stride*8||depth>stride*8-bit){valid=false;break;}bits[k]=bit;depths[k]=depth;}
                for(int j=0;j<needed;++j)if(!depths[j])valid=false;if(!valid)continue;
                for(size_t i=0;i<count;++i){const uint8_t*r=b.data()+records+i*stride;unsigned v[3]={};
                    for(int j=0;j<needed;++j)for(size_t bit=0;bit<depths[j];++bit)v[j]|=unsigned((r[(bits[j]+bit)/8]>>((bits[j]+bit)%8))&1)<<bit;
                    unsigned key=v[0]+1;if(kind==0){if(key<=4096&&v[1]<7)levels[key]=v[1]+1;}
                    else if(kind==1){if(key<=200000&&v[1]<=20)prestige[key]=v[1];}
                    else if(!v[2]&&key<=200000&&v[1]<4096)members[v[1]+1][key]=true;}
            }
            for(const auto&m:members){auto level=levels.find(m.first);if(level==levels.end()||m.second.empty())continue;
                double sum=0;bool complete=true;for(const auto&team:m.second){auto p=prestige.find(team.first);if(p==prestige.end()){complete=false;break;}sum+=p->second;}
                if(complete)league_strengths_[m.first]=(float)profile_reputation::league(level->second,sum/m.second.size());}
        }
    }
    auto at=league_strengths_.find(id);return at==league_strengths_.end()?-1:at->second;
}
bool Assets::nationality_flag(int nation,Texture&out) {
    if(nation<=0||nation>3000)return false;
    const std::string path="data/ui/imgAssets/flags512x512/f_"+std::to_string(nation)+".dds";std::vector<uint8_t>b;
    if(file_range(root_+"/"+path,0,0,b)&&read_icon_dds(b,out))return true;
    index_archives();auto at=entries_.find(normalized(path));
    return at!=entries_.end()&&file_range(at->second.archive,at->second.offset,at->second.length,b)&&read_icon_dds(b,out);
}
bool Assets::read(const std::string &input,std::vector<uint8_t>&decoded) {
    std::string name=normalized(input);if(name.find("data/sceneassets/")!=0||name.find("..")!=name.npos)return false;
    std::vector<uint8_t>b;
    if(file_range(root_+"/"+name,0,0,b))return decode_container(b,decoded);
    index_archives();auto it=entries_.find(name);if(it==entries_.end())return false;
    return file_range(it->second.archive,it->second.offset,it->second.length,b) && decode_container(b,decoded);
}
bool Assets::read_packaged(const std::string&input,std::vector<uint8_t>&decoded){
    std::string name=normalized(input);if(name.find("data/sceneassets/")!=0||name.find("..")!=name.npos)return false;
    index_archives();auto it=entries_.find(name);if(it==entries_.end())return false;std::vector<uint8_t>b;
    return file_range(it->second.archive,it->second.offset,it->second.length,b)&&decode_container(b,decoded);
}
bool Assets::exists(const std::string &name) {
    if(GetFileAttributesA((root_+"/"+name).c_str())!=INVALID_FILE_ATTRIBUTES)return true;
    index_archives();return entries_.count(normalized(name))!=0;
}
std::string Assets::first(const std::string &prefix,const std::string &suffix) {
    WIN32_FIND_DATAA data;HANDLE h=FindFirstFileA((root_+"/"+prefix+"*"+suffix).c_str(),&data);
    if(h!=INVALID_HANDLE_VALUE) {FindClose(h);auto slash=prefix.rfind('/');return prefix.substr(0,slash+1)+data.cFileName;}
    index_archives();std::string found;
    for(const auto &i:entries_)if(i.first.find(prefix)==0 && i.first.size()>=suffix.size()&&
        i.first.compare(i.first.size()-suffix.size(),suffix.size(),suffix)==0&&(found.empty()||i.first<found))found=i.first;
    return found;
}
Model Assets::load(const ClubPlayerRow&r) {
    Model model;std::ostringstream diag;int missing=0;
    if(!rig_checked_) {
        rig_checked_=true;std::vector<uint8_t>b;Skeleton rig;
        if(read("data/sceneassets/rig/skeleton_player.rx3",b)&&read_skeleton(b,rig))rig_=std::make_shared<Skeleton>(std::move(rig));
    }
    model.skeleton=rig_;
    model.player_id=r.player_id;model.height_cm=r.height>=130&&r.height<=230?r.height:180;
    model.team_id=r.team_id;model.club_colors_valid=r.club_colors_valid!=0;
    if(model.club_colors_valid)for(int i=0;i<3;++i){uint32_t rgb=r.club_colors[i];model.club_colors[i]={((rgb>>16)&255)/255.f,((rgb>>8)&255)/255.f,(rgb&255)/255.f};}
    Texture crest_tex;if(crest(r.team_id,crest_tex)){model.crest_texture=(int)model.textures.size();model.textures.push_back(std::move(crest_tex));}
    diag<<"backdrop club="<<r.team_id<<" colors="<<model.club_colors_valid<<" crest="<<(model.crest_texture>=0)<<"\n";
    model.goalkeeper=r.position==0;
    auto texture=[&](const std::vector<std::string>&candidates,const char*name) {
        for(const auto &path:candidates) {std::vector<uint8_t>b;Texture t;
            if(!path.empty()&&read(path,b)&&read_texture(b,name,t)){model.textures.push_back(std::move(t));
                diag<<"material "<<name<<": "<<path<<"\n";return int(model.textures.size()-1);}}
        diag<<"missing material "<<name<<"\n";return -1;
    };
    auto mesh=[&](const std::vector<std::string>&paths,int t,Vec3 color,bool head=false) {
        for(const auto &path:paths) {std::vector<uint8_t>b;std::vector<Part>parts;
            if(!read(path,b)||!read_mesh(b,parts))continue;
            for(auto &p:parts) {p.texture=t;p.color=color;p.asset=path;model.parts.push_back(std::move(p));}
            diag<<path<<"\n";if(path!=paths.front())diag<<"fallback mesh requested="<<paths.front()<<" chosen="<<path<<"\n";
            if(head && (path.find("head_"+std::to_string(r.player_id)+"_")!=path.npos ||
                path.find("specifichead_0_"+std::to_string(r.team_id)+".")!=path.npos))model.specific_head=true;return;}
        ++missing;diag<<"missing: "<<paths.front()<<"\n";
    };
    auto s=[](int v){return std::to_string(v);};const std::string base="data/sceneassets/",body=base+"body/";
    int gender=r.gender==1?1:0,skin=std::max(1,std::min(11,r.skin_tone));
    Vec3 skin_color={.72f,.47f,.32f};if(skin<4)skin_color={.91f,.70f,.55f};else if(skin>=7)skin_color={.43f,.26f,.18f};
    int proxy=r.head_class>0?1:0;
    int face_tex=texture({base+"faces/specificface_"+s(r.player_id)+"_0_textures.rx3",
        base+"faces/specificface_0_"+s(r.team_id)+"_textures.rx3",
        base+"faces/face_"+s(r.player_id)+"_0_0_0_0_0_0_0_0_textures.rx3",
        base+"faces/face_"+s(r.head_type)+"_"+s(proxy)+"_0_"+s(r.eyebrow)+"_"+s(r.sideburns)+"_"+
            s(r.facial_hair_color)+"_"+s(r.facial_hair_type)+"_"+s(r.skin_type)+"_"+s(skin)+"_textures.rx3",
        first(base+"faces/face_"+s(r.head_type)+"_","_textures.rx3")},"head_cm");
    int hair_tex=-1,hair_coeff=-1;
    /* Diffuse and coverage MUST come from the same selected hair package.
     * Native player.lua binds hair_coeff separately; custom diffuse alpha
     * can contain tiny values which are not the strand silhouette. */
    for(const auto&path:std::vector<std::string>{base+"hair/specifichair_"+s(r.player_id)+"_0_textures.rx3",
        base+"hair/specifichair_0_"+s(r.team_id)+"_textures.rx3",base+"hair/hair_"+s(r.player_id)+"_0_textures.rx3",
        base+"hair/hair_"+s(r.hair_type)+"_"+s(proxy)+"_textures.rx3"}) {
        std::vector<uint8_t>raw;Texture diffuse,coeff;
        if(!read(path,raw)||!read_texture(raw,"hair_cm",diffuse))continue;
        hair_tex=(int)model.textures.size();model.textures.push_back(std::move(diffuse));
        diag<<"material hair_cm: "<<path<<"\n";
        if(read_texture(raw,"hair_coeff",coeff)) {
            hair_coeff=(int)model.textures.size();model.textures.push_back(std::move(coeff));
            diag<<"material hair_coeff: "<<path<<"; coverage=red\n";
        } else diag<<"missing hair_coeff; coverage falls back to diffuse alpha\n";
        break;
    }
    int eyes=texture({base+"heads/specificeyes_"+s(r.player_id)+"_0_textures.rx3",
        base+"heads/specificeyes_0_"+s(r.team_id)+"_textures.rx3",base+"heads/eyes_"+s(r.player_id)+"_0_textures.rx3",
        base+"heads/eyes_"+s(r.eye_color)+"_1_textures.rx3",base+"heads/eyes_1_1_textures.rx3"},"eyes_cm");
    /* The native player binding uses kitType=2 for the goalkeeper. Never
     * silently substitute an outfield kit if the goalkeeper texture is absent. */
    bool keeper=r.position==0;
    std::string kit=base+"kit/kit_"+s(r.team_id)+(keeper?"_2_0.rx3":"_0_0.rx3");
    diag<<"player="<<r.player_id<<" goalkeeper="<<keeper<<" kitType="<<(keeper?2:0)<<"\n";
    int jersey=texture({kit},"jersey_cm"),shorts=texture({kit},"shorts_cm");
    /* FIFA maps both shorts and socks from the shorts atlas (shortstex2). */
    int socks=shorts;
    auto shoe_paths=[&](const char*suffix) {
        const std::string dir=base+"shoe/";std::vector<std::string>paths;
        /* Career preview uses the current club's home kit. Reproduce the
         * concrete ID/club overrides in GetRMBoot without invoking arbitrary
         * Lua or inventing tournament/year/random assignments. */
        if(r.shoe_type!=0) {
            paths.push_back(dir+"playershoe_"+s(r.player_id)+"_"+s(r.team_id)+(keeper?"_2_0":"_0_0")+suffix);
            if(keeper)paths.push_back(dir+"playershoe_"+s(r.player_id)+"_"+s(r.team_id)+"_0_0"+suffix);
            paths.push_back(dir+"playershoe_0_"+s(r.team_id)+"_0_0"+suffix);
            paths.push_back(dir+"playershoe_"+s(r.player_id)+"_0_0_0"+suffix);
        }
        paths.push_back(dir+"shoe_"+s(r.shoe_type)+(strstr(suffix,"textures")?"_"+s(r.shoe_design):std::string())+suffix);
        paths.push_back(dir+"shoe_15"+(strstr(suffix,"textures")?std::string("_0"):std::string())+suffix);
        return paths;
    };
    diag<<"shoes player="<<r.player_id<<" type="<<r.shoe_type<<" design="<<r.shoe_design<<"\n";
    int shoes=texture(shoe_paths("_textures.rx3"),"shoe_cm");
    int skin_tex=texture({body+"playerskin_"+s(r.player_id)+"_"+s(r.team_id)+"_0_0_textures.rx3",
        body+"playerskin_"+s(r.player_id)+"_textures.rx3",body+"playerskin_0_"+s(r.team_id)+"_0_0_textures.rx3",
        base+"tattoo/tattoo_"+s(r.player_id)+"_0.rx3",body+"skin_"+s(skin)+"_"+s(gender)+"_textures.rx3"},"body_");
    size_t head_begin=model.parts.size();
    mesh({base+"heads/specifichead_"+s(r.player_id)+"_0.rx3",base+"heads/specifichead_0_"+s(r.team_id)+".rx3",
        base+"heads/head_"+s(r.player_id)+"_0.rx3",base+"heads/head_"+s(r.head_type)+"_"+s(r.head_class)+".rx3",
        base+"heads/head_0_0.rx3"},face_tex,skin_color,true);
    for(size_t i=head_begin;i<model.parts.size();++i)if(model.parts[i].name=="eyes") {
        model.parts[i].texture=eyes;model.parts[i].color={.65f,.62f,.58f};
    }
    size_t hair_begin=model.parts.size();
    mesh({base+"hair/specifichair_"+s(r.player_id)+"_0.rx3",base+"hair/specifichair_0_"+s(r.team_id)+".rx3",
        base+"hair/hair_"+s(r.player_id)+"_0_0.rx3",base+"hair/hair_"+s(r.hair_type)+"_"+s(proxy)+"_0.rx3"},hair_tex,{.25f,.19f,.13f});
    static const uint32_t hair_colors[]={0xedac57,0x0e0e0d,0xa07741,0x1f160e,0xffd286,0x6e4d2b,0x3b2816,
        0x782c08,0xc8c9cf,0x525355,0x345a34,0x263f67,0xf62f0a};
    const float hair_alpha=hair_coeff<0&&hair_tex>=0?hair_alpha_scale(model.textures[hair_tex]):1.f;
    for(size_t i=hair_begin;i<model.parts.size();++i) {
        Part &p=model.parts[i];
        p.alpha_scale=hair_alpha;
        p.hair_coeff_texture=hair_coeff;
        /* Some custom RX3s rename alphaA/alphaB. Preserve both meshes: the
         * first remains the opaque cap; subsequent unnamed parts are strands. */
        p.blend=p.name=="alphaB" || (p.name!="alphaA" && i>hair_begin);
        if(p.asset==base+"hair/hair_"+s(r.hair_type)+"_"+s(proxy)+"_0.rx3" && proxy>0 &&
            r.hair_color>=0 && r.hair_color<int(sizeof(hair_colors)/sizeof(hair_colors[0]))) {
            uint32_t rgb=hair_colors[r.hair_color];p.tint={((rgb>>16)&255)/127.5f,((rgb>>8)&255)/127.5f,(rgb&255)/127.5f};
        }
        diag<<"hair submesh="<<p.name<<" vertices="<<p.vertices.size()<<" triangles="<<p.indices.size()/3<<" strands="<<p.blend<<" nativeNormals="<<p.native_normals<<" alphaScale="<<p.alpha_scale<<" coeff="<<(hair_coeff>=0)<<"\n";
    }
    /* players stores seasonal sleeve codes, not the mesh's binary sleeve
     * length. Use the mapping in PlayerUpdate: 1/2 long, 3/4 underarms. */
    int sleeve=r.sleeve_length==1||r.sleeve_length==2?1:0;
    int tuck=std::max(0,std::min(1,r.jersey_style));
    int fit=gender==1?0:std::max(0,std::min(2,r.jersey_fit));
    int sock=std::max(0,std::min(2,r.sock_length)),short_style=r.short_style==1?1:0;
    int armband=r.captain==1?1:0;
    int collar=kit_collar(r.team_id,keeper?2:0);
    diag<<"appearance sleeveCode="<<r.sleeve_length<<" meshSleeve="<<sleeve<<" collar="<<collar<<" tucked="<<tuck<<" fit="<<fit<<" sock="<<sock<<" shorts="<<short_style<<" captain="<<armband<<"\n";
    const std::string jersey_prefix=body+"jersey_0_"+s(collar)+"_"+s(sleeve)+"_"+s(armband)+"_"+s(tuck)+"_";
    const std::string plain_prefix=body+"jersey_0_"+s(collar)+"_"+s(sleeve)+"_0_"+s(tuck)+"_";
    mesh({jersey_prefix+s(fit)+"_"+s(gender)+".rx3",jersey_prefix+"0_"+s(gender)+".rx3",
        plain_prefix+s(fit)+"_"+s(gender)+".rx3",plain_prefix+"0_"+s(gender)+".rx3",
        body+"jersey_0_0_0_0_0_0_"+s(gender)+".rx3",body+"jersey_0_0_0_0_0_1_"+s(gender)+".rx3"},jersey,{.88f,.88f,.88f});
    int arm_length=r.sleeve_length>=1&&r.sleeve_length<=4?1:0;
    mesh({body+"arms_0_"+s(arm_length)+"_"+s(gender)+".rx3",body+"arms_0_0_"+s(gender)+".rx3"},skin_tex,skin_color);
    if(r.sleeve_length==3||r.sleeve_length==4)mesh({body+"underarms_0_0_"+s(gender)+".rx3"},jersey,{.88f,.88f,.88f});
    if(r.sleeve_length==2||r.sleeve_length==4)mesh({body+"underneck_0_0_"+s(gender)+".rx3"},jersey,{.88f,.88f,.88f});
    mesh({body+"shorts_0_"+s(short_style)+"_"+s(gender)+".rx3",body+"shorts_0_0_"+s(gender)+".rx3"},shorts,{.18f,.2f,.23f});
    if(!short_style) {
        mesh({body+"legs_0_"+s(sock)+"_"+s(gender)+".rx3",body+"legs_0_0_"+s(gender)+".rx3"},skin_tex,skin_color);
        mesh({body+"sock_0_"+s(sock)+"_"+s(gender)+".rx3",body+"sock_0_0_"+s(gender)+".rx3"},socks,{.86f,.87f,.89f});
    } else mesh({body+"legs_0_-1_"+s(gender)+".rx3"},skin_tex,skin_color);
    mesh(shoe_paths(".rx3"),shoes,{.09f,.09f,.1f});
    if(keeper) {
        const std::string gloves=base+"gkglove/";
        auto glove_paths=[&](const char *suffix) {
            return std::vector<std::string>{
                gloves+"playergkglove_"+s(r.player_id)+"_"+s(r.team_id)+"_2_0"+suffix,
                gloves+"playergkglove_"+s(r.player_id)+"_"+s(r.team_id)+"_0_0"+suffix,
                gloves+"playergkglove_"+s(r.player_id)+"_0_0_0"+suffix,
                gloves+"playergkglove_0_"+s(r.team_id)+"_2_0"+suffix,
                gloves+"gkglove_"+s(std::max(0,r.glove_type))+suffix,
                gloves+"gkglove_0"+suffix};
        };
        int glove_tex=texture(glove_paths("_textures.rx3"),"gkglove_cm");
        mesh(glove_paths(".rx3"),glove_tex,{.86f,.88f,.91f});
    }
    /* Bind model has no native body morph evaluator yet. Preserve the
     * seams by scaling the entire assembled model, not individual pieces. */
    if(r.height>=130 && r.height<=230 && !model.parts.empty()) {
        float head_top=0,feet=10000;
        for(const auto&p:model.parts)for(const auto&v:p.vertices) {
            feet=std::min(feet,v.position.y);
            if(p.asset.find("/heads/")!=p.asset.npos && p.name!="eyes")head_top=std::max(head_top,v.position.y);
        }
        /* Height is measured at the head, never at the tip of an afro/ponytail.
         * The renderer still includes ALL hair vertices in its camera bounds. */
        if(head_top-feet>100 && head_top-feet<250){float scale=r.height/(head_top-feet);
            model.bind_scale=scale;model.bind_feet=feet;
            for(auto&p:model.parts)for(auto&v:p.vertices){v.position.x*=scale;v.position.y=(v.position.y-feet)*scale;v.position.z*=scale;}}
    }
    diag<<"parts="<<model.parts.size()<<" textures="<<model.textures.size()<<" missing="<<missing<<" specific_head="<<model.specific_head;
    model.diagnostic=diag.str();return model;
}
static std::vector<int> assigned_goalkeeper_kits(const std::string&root,int team){
    std::vector<int>out;std::vector<uint8_t>bytes;
    if(team<=0||team>200000||!file_range(root+"/data/fifarna/lua/assignments/teams/team_"+std::to_string(team)+".lua",0,0,bytes))return out;
    std::istringstream lines(std::string(bytes.begin(),bytes.end()));std::string line;
    while(std::getline(lines,line)){
        const char*p=line.c_str();while(*p==' '||*p=='\t')++p;
        if(strncmp(p,"assignGKKit",11))continue;p+=11;while(*p==' '||*p=='\t')++p;if(*p++!='(')continue;
        while(*p==' '||*p=='\t')++p;char*end=nullptr;long club=strtol(p,&end,10);if(end==p)continue;p=end;
        while(*p==' '||*p=='\t')++p;if(*p++!=',')continue;
        while(*p==' '||*p=='\t')++p;strtol(p,&end,10);if(end==p)continue;p=end;
        while(*p==' '||*p=='\t')++p;if(*p++!=',')continue;
        while(*p&&*p!='{')++p;if(*p!='{'||club!=team)continue;++p;
        for(int n=0;n<24&&*p;++n){while(*p==' '||*p=='\t')++p;if(*p=='}')break;
            long type=strtol(p,&end,10);if(end==p||type<0||type>22)break;
            out.push_back((int)type);p=end;while(*p==' '||*p=='\t')++p;if(*p==','){++p;continue;}if(*p=='}')break;break;}
    }
    std::sort(out.begin(),out.end());out.erase(std::unique(out.begin(),out.end()),out.end());return out;
}
std::vector<KitThumbnail> Assets::kit_thumbnails(int team){
    std::vector<KitThumbnail>out;if(team<=0||team>200000)return out;
    std::vector<int>keepers=assigned_goalkeeper_kits(root_,team);if(std::find(keepers.begin(),keepers.end(),2)==keepers.end())keepers.push_back(2);
    std::string directory=root_+"/data/ui/imgAssets/kits/",pattern=directory+"j*_"+std::to_string(team)+"_*.dds";
    WIN32_FIND_DATAA data={};HANDLE search=FindFirstFileA(pattern.c_str(),&data);
    if(search==INVALID_HANDLE_VALUE)return out;
    do{
        std::string filename=data.cFileName;const char*p=filename.c_str();if(*p++!='j')continue;
        char*end=nullptr;long type=strtol(p,&end,10);if(end==p||*end++!='_'||type<0||type>22)continue;p=end;
        long file_team=strtol(p,&end,10);if(end==p||*end++!='_'||file_team!=team)continue;p=end;
        long variant=strtol(p,&end,10);if(end==p||variant<0||variant>1000000||_stricmp(end,".dds"))continue;
        std::vector<uint8_t>bytes;Texture image;
        if(!file_range(directory+filename,0,0,bytes)||bytes.size()>8*1024*1024||!read_icon_dds(bytes,image))continue;
        KitThumbnail kit;kit.type=(int)type;kit.variant=(int)variant;
        kit.goalkeeper=kit.type==2||std::find(keepers.begin(),keepers.end(),kit.type)!=keepers.end();kit.image=std::move(image);out.push_back(std::move(kit));
    }while(FindNextFileA(search,&data));
    FindClose(search);
    std::sort(out.begin(),out.end(),[](const KitThumbnail&a,const KitThumbnail&b){return a.type!=b.type?a.type<b.type:a.variant<b.variant;});
    out.erase(std::unique(out.begin(),out.end(),[](const KitThumbnail&a,const KitThumbnail&b){return a.type==b.type&&a.variant==b.variant;}),out.end());
    return out;
}
int Assets::kit_collar(int team,int kit) {
    if(team<=0||team>200000||kit<0||kit>22)return 0;unsigned key=team*32+kit;
    auto found=resolved_collars_.find(key);if(found!=resolved_collars_.end())return found->second;
    if(!kits_checked_){kits_checked_=true;std::vector<uint8_t>b;
        if(file_range(root_+"/data/db/fifa_ng_db.db",0,0,b))read_kit_collars(b,kit_collars_);}
    int c=0;auto db=kit_collars_.find(key);if(db!=kit_collars_.end())c=db->second;
    std::vector<uint8_t>lua;
    if(file_range(root_+"/data/fifarna/lua/assignments/teams/team_"+std::to_string(team)+".lua",0,0,lua)) {
        int assigned;if(read_kit_collar_override(std::string(lua.begin(),lua.end()),team,kit,assigned))c=assigned;
    }
    resolved_collars_[key]=c;return c;
}
CoachAsset Assets::coach(const ClubPlayerRow&club) {
    CoachAsset out;if(club.team_id<=0||club.team_id>200000)return out;
    std::vector<uint8_t>names;
    if(!file_range(career_paths::read(root_+"/ModCarrerMode","data\\catalogs","club_manager_fallback.tsv"),0,0,names))return out;
    std::istringstream lines(std::string(names.begin(),names.end()));std::string line;
    while(std::getline(lines,line)){char*end=nullptr;long id=strtol(line.c_str(),&end,10);
        if(id!=club.team_id||end==line.c_str()||*end!='|')continue;
        std::string name=end+1;size_t last=name.find_last_not_of(" \t\r"),first=name.find_first_not_of(" \t\r");
        if(first==name.npos||last-first>=128||name.find('\0')!=name.npos)return out;
        out.name=name.substr(first,last-first+1);break;}
    if(out.name.empty())return out;
    /* Same club-specific baseline in GetRMSle, but deliberately NO global or
     * another-club fallback. The SLC has its own skin/bone palette, not the
     * player's 400 bones. Use its verified compact embedded rig; unsupported
     * SLC layouts keep their original static mesh without re-rigging. */
    std::string base="data/sceneassets/slc/specificmanager_"+std::to_string(club.team_id)+"_0_0";
    std::vector<uint8_t>raw;std::vector<Part>parts;Texture diffuse;Skeleton coach_rig;
    if(!read(base+".rx3",raw)||!read_mesh(raw,parts))return out;
    bool rig_ok=read_coach_skeleton(raw,coach_rig);
    if(!read(base+"_textures.rx3",raw))return out;
    bool material=false;for(const auto&name:texture_names(raw))if(name.size()>=3&&name.compare(name.size()-3,3,"_cm")==0&&read_texture(raw,name,diffuse)){material=true;break;}
    if(!material&&read_texture(raw,"cm",diffuse))material=true;if(!material)return out;
    auto model=std::make_shared<Model>();model->team_id=club.team_id;model->specific_head=true;
    if(rig_ok)model->skeleton=std::make_shared<Skeleton>(std::move(coach_rig));
    model->club_colors_valid=club.club_colors_valid!=0;
    if(model->club_colors_valid)for(int i=0;i<3;++i){auto rgb=club.club_colors[i];model->club_colors[i]={((rgb>>16)&255)/255.f,((rgb>>8)&255)/255.f,(rgb&255)/255.f};}
    model->textures.push_back(std::move(diffuse));Texture crest_tex;
    if(crest(club.team_id,crest_tex)){model->crest_texture=(int)model->textures.size();model->textures.push_back(std::move(crest_tex));}
    float floor=10000,top=-10000;for(const auto&p:parts)for(const auto&v:p.vertices){floor=std::min(floor,v.position.y);top=std::max(top,v.position.y);}
    if(top-floor<50||top-floor>250)return out;
    for(auto&p:parts){p.texture=0;p.asset=base+".rx3";for(auto&v:p.vertices)v.position.y-=floor;model->parts.push_back(std::move(p));}
    model->height_cm=(int)lroundf(top-floor);
    model->bind_feet=floor;
    model->diagnostic="coach club="+std::to_string(club.team_id)+" name="+out.name+" asset="+base+".rx3; compact SLC rig="+std::to_string(rig_ok)+"; no player rig or save writes";
    out.asset=base+".rx3";out.model=std::move(model);return out;
}
Model Assets::trophy(int id) {
    Model model;model.player_count=0;
    if(id<=0||id>65535){model.diagnostic="invalid trophy asset ID";return model;}
    std::string base="data/sceneassets/trophy/trophy_"+std::to_string(id);
    std::vector<uint8_t>raw;std::vector<Part>parts;Texture texture;
    if(!read(base+".rx3",raw)||!read_mesh(raw,parts)) {model.diagnostic="missing native trophy mesh: "+base;return model;}
    if(!read(base+"_textures.rx3",raw)){model.diagnostic="missing native trophy texture: "+base;return model;}
    bool found=false;
    for(const auto&name:texture_names(raw))if(name.size()>=3&&name.compare(name.size()-3,3,"_cm")==0&&read_texture(raw,name,texture)){found=true;break;}
    if(!found&&read_texture(raw,"_cm",texture))found=true;
    if(!found){model.diagnostic="native trophy diffuse _cm unavailable: "+base;return model;}
    model.textures.push_back(std::move(texture));
    for(auto&p:parts){p.asset=base+".rx3";p.texture=0;p.skinned=false;p.color={1,1,1};
        /* Never replace a missing cup with the game's unrelated default cup. */
        p.blend=p.name.find("glass")!=p.name.npos;model.parts.push_back(std::move(p));}
    model.diagnostic="native_trophy="+std::to_string(id)+" exact RX3 mesh+diffuse; no generic fallback";return model;
}
Model assemble_starting_eleven(const std::vector<std::shared_ptr<const Model>>&players,unsigned pose_id) {
    auto unavailable=[](const std::string&reason){Model out;out.player_count=0;out.diagnostic="starting XI photo unavailable: "+reason;return out;};
    if(players.size()!=11)return unavailable("expected exactly eleven current starters");
    int club=0;std::vector<int>ids;
    for(const auto&p:players) {
        if(!p||p->parts.empty())return unavailable("missing player model; partial team photo suppressed");
        if(p->player_id<=0||p->player_id>524287)return unavailable("invalid player identity");
        if(!club)club=p->team_id;
        if(club<=0||p->team_id!=club)return unavailable("players belong to different clubs");
        if(std::find(ids.begin(),ids.end(),p->player_id)!=ids.end())return unavailable("duplicate player identity");
        ids.push_back(p->player_id);
    }
    Model out=assemble_team(players,pose_id);
    if(out.player_count!=11||out.formation.size()!=11||!out.presentation_pose)
        return unavailable("complete native pose unavailable; partial/bind-pose photo suppressed");
    return out;
}
Model assemble_team(const std::vector<std::shared_ptr<const Model>>&players,unsigned pose_id) {
    Model out;out.player_count=0;out.specific_head=true;
    const auto*style=presentation_pose_find(pose_id);if(!style||!(style->modes&PoseGroup)){out.diagnostic="unknown/group-incompatible presentation pose; no formation published";return out;}
    std::vector<std::shared_ptr<const Model>>pool;
    for(const auto&p:players)if(p&&!p->parts.empty()&&pool.size()<11)pool.push_back(p);
    std::stable_sort(pool.begin(),pool.end(),[](const auto&a,const auto&b){return a->height_cm>b->height_cm;});
    size_t count=pool.size(),back=count==11?style->back_count:(count+1)/2;
    if(back>count||back==0)return out;
    std::vector<std::shared_ptr<const Model>>keepers,order;
    for(auto i=pool.begin();i!=pool.end()&&keepers.size()<std::min(size_t(2),back);)
        if((*i)->goalkeeper){keepers.push_back(*i);i=pool.erase(i);}else ++i;
    if(!keepers.empty())order.push_back(keepers.front());
    size_t standing=back-keepers.size();
    for(size_t i=0;i<standing;++i)order.push_back(pool[i]);
    if(keepers.size()>1)order.push_back(keepers[1]);
    for(size_t i=standing;i<pool.size();++i)order.push_back(pool[i]);
    std::vector<std::shared_ptr<Model>>base_poses;
    std::vector<bool>valid;
    std::vector<Vec3>positions;
    for(size_t i=0;i<count;++i) {
        auto m=std::make_shared<Model>(*order[i]);valid.push_back(apply_presentation_pose(*m,i>=back,nullptr,pose_id));base_poses.push_back(m);
        size_t col=i<back?i:i-back,row_size=i<back?back:count-back;
        positions.push_back({(float(col)-float(row_size-1)*.5f)*style->column_spacing,0,count>1?(i<back?style->back_z:style->front_z):0.f});
    }
    std::ostringstream diag;
    for(size_t i=0;i<count;++i) {
        const auto&source=order[i];
        size_t row_begin=i<back?0:back,row_end=i<back?back:count,col=i-row_begin;
        PoseContacts contacts;contacts.floor_cm=base_poses[i]->pose_floor_cm;
        auto neighbour=[&](bool left,size_t n) {
            if(!valid[i]||!valid[n])return;
            const auto&q=*base_poses[n];
            Vec3 target=left?q.right_shoulder:q.left_shoulder;
            /* All neighbour supports now land on the upper back, below and
             * behind the shoulder. No wrist over the shoulder or neck. Use
             * the neighbour's posed landmarks, not a fixed scene height. */
            target.x+=(left?5.f:-5.f)*q.bind_scale;target.y-=10*q.bind_scale;target.z-=15*q.bind_scale;
            target.x+=positions[n].x-positions[i].x;
            target.z+=positions[n].z-positions[i].z;
            if(left){contacts.left=true;contacts.left_target=target;}
            else{contacts.right=true;contacts.right_target=target;}
        };
        if(!source->goalkeeper&&style->contact_pattern!=1) {
            if(i>=back&&(col%2==1||style->contact_pattern==2)) {if(i+1<row_end)neighbour(true,i+1);if(i>row_begin)neighbour(false,i-1);}
            else if(i<back&&style->contact_pattern==0&&col%2==1) {if(i+1<row_end)neighbour(true,i+1);else if(i>row_begin)neighbour(false,i-1);}
        }
        auto posed=base_poses[i];bool posed_ok=valid[i];
        auto error=[](Vec3 a,Vec3 b){return sqrtf((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z));};
        if(contacts.left||contacts.right) {
            auto linked=std::make_shared<Model>(*source);
            if(apply_presentation_pose(*linked,i>=back,&contacts,pose_id)) {
                bool too_far=(contacts.left&&error(linked->left_hand,contacts.left_target)>3)||
                    (contacts.right&&error(linked->right_hand,contacts.right_target)>3);
                if(too_far) {
                    if(contacts.left&&error(linked->left_hand,contacts.left_target)>3)contacts.left=false;
                    if(contacts.right&&error(linked->right_hand,contacts.right_target)>3)contacts.right=false;
                    diag<<"neighbour beyond natural arm reach slot="<<i+1<<"; uncoupled arm uses base stance\n";
                    if(contacts.left||contacts.right) {
                        linked=std::make_shared<Model>(*source);
                        if(apply_presentation_pose(*linked,i>=back,&contacts,pose_id))posed=linked;
                        else contacts.left=contacts.right=false;
                    }
                } else posed=linked;
            }
            else {contacts.left=contacts.right=false;diag<<"neighbour contact unavailable slot="<<i+1<<"; base pose retained\n";}
        }
        const auto&m=posed;
        std::vector<int>materials;
        for(const auto&t:m->textures) {
            size_t j=0;for(;j<out.textures.size();++j){const auto&existing=out.textures[j];
                if(existing.width==t.width&&existing.height==t.height&&existing.format==t.format&&existing.bytes==t.bytes)break;}
            if(j==out.textures.size())out.textures.push_back(t);materials.push_back((int)j);
        }
        if(i==0) {
            out.team_id=m->team_id;out.club_colors_valid=m->club_colors_valid;
            std::copy(std::begin(m->club_colors),std::end(m->club_colors),out.club_colors);
            if(m->crest_texture>=0&&size_t(m->crest_texture)<materials.size())out.crest_texture=materials[m->crest_texture];
        }
        float x=positions[i].x,z=positions[i].z;
        out.formation.push_back({source->player_id,source->height_cm,source->goalkeeper,i>=back,x,z,
            contacts.left,contacts.right,contacts.left?error(m->left_hand,contacts.left_target):0,contacts.right?error(m->right_hand,contacts.right_target):0,
            contacts.left,contacts.right});
        for(auto p:m->parts) {
            for(auto&v:p.vertices){v.position.x+=x;v.position.z+=z;}
            if(p.texture>=0)p.texture=materials[p.texture];
            if(p.hair_coeff_texture>=0)p.hair_coeff_texture=materials[p.hair_coeff_texture];
            out.parts.push_back(std::move(p));
        }
        ++out.player_count;out.specific_head=out.specific_head&&m->specific_head;
        if(i==0)out.presentation_pose=true;out.presentation_pose=out.presentation_pose&&posed_ok;
        out.presentation_pose_id=out.presentation_pose?pose_id:0;
        diag<<"player slot="<<(i+1)<<" pose="<<(i<back?"standing":"crouching")<<" applied="<<posed_ok<<"\n"<<m->diagnostic<<"\n";
    }
    out.diagnostic="collective players="+std::to_string(out.player_count)+"\n"+diag.str();return out;
}
}
