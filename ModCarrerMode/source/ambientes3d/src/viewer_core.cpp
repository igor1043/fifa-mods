#include "viewer_core.h"
#include "viewer_cinematics.h"
#include <xmllite.h>
#include <shlwapi.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <DirectXMath.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <set>
#include <stdexcept>
using Microsoft::WRL::ComPtr;
using namespace DirectX;
namespace studio {
std::string utf8(const std::wstring&s){if(s.empty())return {};int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0,nullptr,nullptr);if(!n)throw std::runtime_error("Texto Unicode invalido");std::string out(n,0);WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),out.data(),n,nullptr,nullptr);return out;}
std::wstring wide(const std::string&s){if(s.empty())return {};int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0);if(!n)throw std::runtime_error("Texto UTF-8 invalido");std::wstring out(n,0);MultiByteToWideChar(CP_UTF8,0,s.data(),int(s.size()),out.data(),n);return out;}
bool path_inside(const fs::path&file,const fs::path&folder){auto p=fs::weakly_canonical(fs::absolute(file)).wstring();auto root=fs::weakly_canonical(fs::absolute(folder)).wstring();while(!root.empty()&&(root.back()==L'\\'||root.back()==L'/'))root.pop_back();if(p.size()<=root.size())return _wcsicmp(p.c_str(),root.c_str())==0;return !_wcsnicmp(p.c_str(),root.c_str(),root.size())&&(p[root.size()]==L'\\'||p[root.size()]==L'/');}
std::vector<Element> read_xml(const fs::path&path){
    std::error_code ec;auto size=fs::file_size(path,ec);if(ec||size>8*1024*1024)throw std::runtime_error("XML ausente ou grande demais: "+utf8(path.wstring()));
    ComPtr<IStream>stream;ComPtr<IXmlReader>reader;
    if(FAILED(SHCreateStreamOnFileEx(path.c_str(),STGM_READ|STGM_SHARE_DENY_WRITE,FILE_ATTRIBUTE_NORMAL,FALSE,nullptr,&stream))||FAILED(CreateXmlReader(__uuidof(IXmlReader),reinterpret_cast<void**>(reader.GetAddressOf()),nullptr)))throw std::runtime_error("Nao foi possivel abrir XML");
    reader->SetProperty(XmlReaderProperty_DtdProcessing,DtdProcessing_Prohibit);reader->SetProperty(XmlReaderProperty_MaxElementDepth,32);reader->SetInput(stream.Get());
    std::vector<Element>out;XmlNodeType type;HRESULT hr;
    while((hr=reader->Read(&type))==S_OK){if(type!=XmlNodeType_Element&&type!=XmlNodeType_EndElement)continue;
        const wchar_t*name=nullptr;UINT len=0;reader->GetLocalName(&name,&len);Element e;e.name=utf8(std::wstring(name,len));e.end=type==XmlNodeType_EndElement;
        if(!e.end&&reader->MoveToFirstAttribute()==S_OK){do{const wchar_t*v=nullptr;UINT vl=0;reader->GetLocalName(&name,&len);reader->GetValue(&v,&vl);e.values[utf8(std::wstring(name,len))]=utf8(std::wstring(v,vl));}while(reader->MoveToNextAttribute()==S_OK);reader->MoveToElement();}
        bool empty=!e.end&&reader->IsEmptyElement();auto empty_name=e.name;out.push_back(std::move(e));if(empty)out.push_back({empty_name,{},true});if(out.size()>200000)throw std::runtime_error("XML excede o limite de elementos");}
    if(FAILED(hr))throw std::runtime_error("XML malformado ou inseguro");return out;
}
static std::string value(const Element&e,const char*key,const std::string&fallback={}){auto it=e.values.find(key);return it==e.values.end()?fallback:it->second;}
static float number(const Element&e,const char*key,float fallback,float lo,float hi){auto text=value(e,key);if(text.empty())return fallback;size_t used=0;float n=std::stof(text,&used);if(used!=text.size()||!std::isfinite(n)||n<lo||n>hi)throw std::runtime_error(std::string("Valor invalido: ")+key);return n;}
static Vec3 vector(const Element&e,const char*x,const char*y,const char*z,Vec3 fallback,float limit){return {number(e,x,fallback.x,-limit,limit),number(e,y,fallback.y,-limit,limit),number(e,z,fallback.z,-limit,limit)};}
Settings load_settings(const fs::path&p){Settings s;auto xml=read_xml(p);if(xml.empty()||xml[0].name!="visualizador"||(value(xml[0],"versao")!="1"&&value(xml[0],"versao")!="2"&&value(xml[0],"versao")!="3"))throw std::runtime_error("Formato de preset incompatível");
    Keyframe*key=nullptr;ActorEdit*actor=nullptr;CameraScene*film=nullptr;
    for(auto&e:xml){if(e.end){if(e.name=="quadro")key=nullptr;if(e.name=="jogador"||e.name=="tecnico")actor=nullptr;if(e.name=="filmagem")film=nullptr;continue;}
        if(e.name=="origem")s.game=value(e,"jogo",s.game);
        if(e.name=="alvo")s.coach_target=value(e,"tipo","tecnico")=="tecnico";
        if(e.name=="coletiva"){s.press_competition=int(number(e,"competicao",0,0,65535));s.press_final=value(e,"final","nao")=="sim";s.press_audience=value(e,"plateia","sim")=="sim";}
        if(e.name=="lugar"){int slot=int(number(e,"numero",1,1,5))-1;s.press_slots[slot]=int(number(e,"pessoa",0,-2,524287));}
        if(e.name=="cena"){s.club=int(number(e,"clube",1043,1,200000));s.player=int(number(e,"jogador",0,0,524287));s.scene=int(number(e,"tipo",0,0,7));s.pose=unsigned(number(e,"pose",205,1,1000));s.coach_target=value(e,"alvo","tecnico")=="tecnico";s.room_cutaway=value(e,"vistaAberta","nao")=="sim";}
        if(e.name=="camera"){s.camera.position=vector(e,"x","y","z",s.camera.position,100000);s.camera.target=vector(e,"alvoX","alvoY","alvoZ",s.camera.target,100000);s.camera.yaw=number(e,"yaw",0,-10000,10000);s.camera.pitch=number(e,"pitch",0,-1.5f,1.5f);s.camera.fov=number(e,"fov",45,15,100);s.camera.speed=number(e,"velocidade",160,1,2000);s.camera.distance=number(e,"distancia",650,1,100000);s.camera.orbit=value(e,"modo","orbita")=="orbita";}
        if(e.name=="filmagem"){if(film||s.camera_scenes.size()>=100)throw std::runtime_error("Biblioteca cinematográfica inválida ou grande demais");CameraScene scene;scene.id=value(e,"id");scene.name=value(e,"nome");scene.environment=int(number(e,"ambiente",1,0,7));if(std::any_of(s.camera_scenes.begin(),s.camera_scenes.end(),[&](auto&old){return old.id==scene.id;}))throw std::runtime_error("Cena cinematográfica duplicada");s.camera_scenes.push_back(std::move(scene));film=&s.camera_scenes.back();}
        if(e.name=="enquadramento"){if(!film||film->keys.size()>=256)throw std::runtime_error("Enquadramento fora de uma filmagem ou em excesso");CameraKey shot;shot.time=number(e,"tempo",0,0,600);shot.position=vector(e,"x","y","z",{},100000);shot.target=vector(e,"alvoX","alvoY","alvoZ",{},100000);shot.fov=number(e,"fov",60,20,90);shot.transition=int(number(e,"transicao",0,0,2));film->keys.push_back(shot);}
        if(e.name=="quadro"){if(s.keys.size()>=4096)throw std::runtime_error("Muitos quadros no XML");s.keys.push_back({number(e,"tempo",0,0,600),{}});key=&s.keys.back();}
        if(e.name=="fbx"){s.fbx_file=value(e,"arquivo");s.fbx_take=int(number(e,"take",0,0,1000));s.fbx_time=number(e,"tempo",0,0,600);s.root_motion=value(e,"deslocamento","nao")=="sim";}
        if(e.name=="mapa"){if(s.mapping.size()>=1024)throw std::runtime_error("Muitos ossos no mapa");s.mapping.push_back({value(e,"fifa"),value(e,"origem")});}
        if(e.name=="jogador"||e.name=="tecnico"){
            if(actor||s.actors.size()>=100)throw std::runtime_error("Jogadores demais ou estrutura aninhada no XML");
            ActorEdit a;a.player=int(number(e,"id",0,1,524287));a.translation=vector(e,"x","y","z",{},10000);a.rotation=vector(e,"rx","ry","rz",{},180);a.scale=number(e,"escala",1,.25f,3);a.pose=unsigned(number(e,"pose",0,0,1000));
            if(a.player<=0)throw std::runtime_error("Jogador sem identificação no XML");
            if(e.name=="tecnico")a.player=-a.player;
            if(std::any_of(s.actors.begin(),s.actors.end(),[&](const auto&old){return old.player==a.player;}))throw std::runtime_error("Jogador duplicado no XML");
            if(a.pose){auto*p=fifa_player::presentation_pose_find(a.pose);if(!p||!(p->modes&(a.player<0?fifa_player::PoseCoachAny:fifa_player::PoseIndividual)))throw std::runtime_error("Pose individual inválida");}
            s.actors.push_back(std::move(a));actor=&s.actors.back();
        }
        if(e.name=="articulacao"){auto&joints=actor?actor->joints:key?key->joints:s.joints;if(joints.size()>=1024)throw std::runtime_error("Muitas articulacoes no XML");joints.push_back({value(e,"nome"),vector(e,"rx","ry","rz",{},180),vector(e,"x","y","z",{},100),number(e,"escala",1,.25f,3)});}
        if(e.name=="objeto"){if(s.objects.size()>=10000)throw std::runtime_error("Muitos objetos no XML");ObjectEdit o;o.name=value(e,"nome");o.translation=vector(e,"x","y","z",{},10000);o.rotation=vector(e,"rx","ry","rz",{},180);o.scale=number(e,"escala",1,.05f,10);o.visible=value(e,"visivel","sim")!="nao";s.objects.push_back(o);}
    }
    for(auto&film:s.camera_scenes)validate_camera_scene(film);
    if(s.scene==2)throw std::runtime_error("Chegada à coletiva foi removida. Selecione Academia ou outro ambiente da biblioteca.");
    if(s.scene==3||s.scene==5||s.scene>=6)s.coach_target=false;
    if(s.scene==4)s.coach_target=true;
    if(s.scene!=1&&s.scene<6){unsigned mode=s.scene==0?fifa_player::PoseSeatedCoach:s.scene==3?fifa_player::PoseIndividual:s.scene==4?fifa_player::PoseCoachAny:fifa_player::PoseGroup;auto*pose=fifa_player::presentation_pose_find(s.pose);if(!pose||!(pose->modes&mode))throw std::runtime_error("A pose do XML não pertence a esta cena");}
    std::sort(s.keys.begin(),s.keys.end(),[](const auto&a,const auto&b){return a.time<b.time;});
    if(s.camera.orbit)s.camera.synchronize_orbit();return s;
}
static std::string escape(std::string s){std::string out;for(char c:s){switch(c){case '&':out+="&amp;";break;case '<':out+="&lt;";break;case '>':out+="&gt;";break;case '"':out+="&quot;";break;default:out+=c;}}return out;}
void save_settings(const fs::path&p,const Settings&s){
    if(path_inside(p,wide(s.game)))throw std::runtime_error("Não é permitido salvar presets dentro da pasta do jogo");
    if(_wcsicmp(p.extension().c_str(),L".xml"))throw std::runtime_error("O preset precisa ter extensão .xml");
    if(s.camera_scenes.size()>100)throw std::runtime_error("Biblioteca cinematográfica grande demais");std::set<std::string>film_ids;for(auto&film:s.camera_scenes){validate_camera_scene(film);if(!film_ids.insert(film.id).second)throw std::runtime_error("Cena cinematográfica duplicada");}
    fs::create_directories(p.parent_path());auto temporary=p;temporary+=L".tmp";
    std::ofstream out(temporary,std::ios::binary);out.imbue(std::locale::classic());out<<std::setprecision(8)<<"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<visualizador versao=\""<<(!s.camera_scenes.empty()?3:s.actors.empty()?1:2)<<"\">\n  <origem jogo=\""<<escape(s.game)<<"\"/>\n  <cena tipo=\""<<s.scene<<"\" clube=\""<<s.club<<"\" jogador=\""<<s.player<<"\" pose=\""<<s.pose<<"\" vistaAberta=\""<<(s.room_cutaway?"sim":"nao")<<"\"/>\n";
    auto&c=s.camera;out<<"  <camera modo=\""<<(c.orbit?"orbita":"livre")<<"\" x=\""<<c.position.x<<"\" y=\""<<c.position.y<<"\" z=\""<<c.position.z<<"\" alvoX=\""<<c.target.x<<"\" alvoY=\""<<c.target.y<<"\" alvoZ=\""<<c.target.z<<"\" yaw=\""<<c.yaw<<"\" pitch=\""<<c.pitch<<"\" fov=\""<<c.fov<<"\" distancia=\""<<c.distance<<"\" velocidade=\""<<c.speed<<"\"/>\n";
    out<<"  <alvo tipo=\""<<(s.coach_target?"tecnico":"jogador")<<"\"/>\n";
    out<<"  <coletiva competicao=\""<<s.press_competition<<"\" final=\""<<(s.press_final?"sim":"nao")<<"\" plateia=\""<<(s.press_audience?"sim":"nao")<<"\">\n";
    for(int i=0;i<5;++i)out<<"    <lugar numero=\""<<i+1<<"\" pessoa=\""<<s.press_slots[i]<<"\"/>\n";
    out<<"  </coletiva>\n";
    auto write_joint=[&](const JointEdit&j,const char*indent){out<<indent<<"<articulacao nome=\""<<escape(j.name)<<"\" rx=\""<<j.rotation.x<<"\" ry=\""<<j.rotation.y<<"\" rz=\""<<j.rotation.z<<"\" x=\""<<j.translation.x<<"\" y=\""<<j.translation.y<<"\" z=\""<<j.translation.z<<"\" escala=\""<<j.scale<<"\"/>\n";};
    for(auto&j:s.joints)write_joint(j,"  ");
    for(auto&a:s.actors){auto tag=a.player<0?"tecnico":"jogador";out<<"  <"<<tag<<" id=\""<<abs(a.player)<<"\" x=\""<<a.translation.x<<"\" y=\""<<a.translation.y<<"\" z=\""<<a.translation.z<<"\" rx=\""<<a.rotation.x<<"\" ry=\""<<a.rotation.y<<"\" rz=\""<<a.rotation.z<<"\" escala=\""<<a.scale<<"\" pose=\""<<a.pose<<"\">\n";for(auto&j:a.joints)write_joint(j,"    ");out<<"  </"<<tag<<">\n";}
    for(auto&key:s.keys){out<<"  <quadro tempo=\""<<key.time<<"\">\n";for(auto&j:key.joints)write_joint(j,"    ");out<<"  </quadro>\n";}
    if(!s.fbx_file.empty())out<<"  <fbx arquivo=\""<<escape(s.fbx_file)<<"\" take=\""<<s.fbx_take<<"\" tempo=\""<<s.fbx_time<<"\" deslocamento=\""<<(s.root_motion?"sim":"nao")<<"\"/>\n";
    for(auto&m:s.mapping)out<<"  <mapa fifa=\""<<escape(m.target)<<"\" origem=\""<<escape(m.source)<<"\"/>\n";
    for(auto&o:s.objects)out<<"  <objeto nome=\""<<escape(o.name)<<"\" x=\""<<o.translation.x<<"\" y=\""<<o.translation.y<<"\" z=\""<<o.translation.z<<"\" rx=\""<<o.rotation.x<<"\" ry=\""<<o.rotation.y<<"\" rz=\""<<o.rotation.z<<"\" escala=\""<<o.scale<<"\" visivel=\""<<(o.visible?"sim":"nao")<<"\"/>\n";
    for(auto&film:s.camera_scenes){out<<"  <filmagem id=\""<<escape(film.id)<<"\" nome=\""<<escape(film.name)<<"\" ambiente=\""<<film.environment<<"\">\n";for(auto&k:film.keys)out<<"    <enquadramento tempo=\""<<k.time<<"\" x=\""<<k.position.x<<"\" y=\""<<k.position.y<<"\" z=\""<<k.position.z<<"\" alvoX=\""<<k.target.x<<"\" alvoY=\""<<k.target.y<<"\" alvoZ=\""<<k.target.z<<"\" fov=\""<<k.fov<<"\" transicao=\""<<k.transition<<"\"/>\n";out<<"  </filmagem>\n";}
    out<<"</visualizador>\n";out.close();if(!out)throw std::runtime_error("Nao foi possivel salvar preset");
    if(fs::exists(p)){auto backup=p;backup+=L".bak";fs::copy_file(p,backup,fs::copy_options::overwrite_existing);}
    if(!MoveFileExW(temporary.c_str(),p.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))throw std::runtime_error("Nao foi possivel concluir preset; o arquivo anterior foi preservado");
}
Vec3 Camera::forward()const{return {sinf(yaw)*cosf(pitch),sinf(pitch),-cosf(yaw)*cosf(pitch)};}
void Camera::synchronize_orbit(){auto f=forward();position={target.x-f.x*distance,target.y-f.y*distance,target.z-f.z*distance};}
void Camera::move(float r,float u,float f,float dt){auto dir=forward();Vec3 delta={(cosf(yaw)*r+dir.x*f)*speed*dt,(u+dir.y*f)*speed*dt,(sinf(yaw)*r+dir.z*f)*speed*dt};position={position.x+delta.x,position.y+delta.y,position.z+delta.z};target={target.x+delta.x,target.y+delta.y,target.z+delta.z};}
void Camera::look(float h,float v){yaw+=h;pitch=std::clamp(pitch+v,-1.5f,1.5f);if(orbit)synchronize_orbit();}
struct Field {size_t bit=0,depth=0;uint32_t type=0;int low=0;};
struct Table {size_t start=0,stride=0,count=0,allocated=0,block=0,length=0,tree=0;std::map<std::string,Field>fields;};
struct Database {
    std::vector<uint8_t>b;std::map<std::string,Table>tables;
    bool span(size_t p,size_t n)const{return p<=b.size()&&n<=b.size()-p;}
    uint32_t u32(size_t p)const{if(!span(p,4))throw std::runtime_error("Banco truncado");return b[p]|uint32_t(b[p+1])<<8|uint32_t(b[p+2])<<16|uint32_t(b[p+3])<<24;}
    uint16_t u16(size_t p)const{if(!span(p,2))throw std::runtime_error("Banco truncado");return b[p]|uint16_t(b[p+1])<<8;}
    explicit Database(const fs::path&game){
        auto file=game/L"data/db/fifa_ng_db.db";std::ifstream in(file,std::ios::binary|std::ios::ate);if(!in)throw std::runtime_error("Banco de jogadores nao encontrado no jogo");auto size=in.tellg();if(size<28||size>128*1024*1024)throw std::runtime_error("Tamanho de banco invalido");b.resize(size_t(size));in.seekg(0);in.read(reinterpret_cast<char*>(b.data()),b.size());if(!in||memcmp(b.data(),"DB\0\x08",4))throw std::runtime_error("Banco FIFA incompatível");
        std::map<std::string,std::string>shorts;std::map<std::string,std::map<std::string,std::pair<std::string,int>>>meta;std::string current;
        for(auto&e:read_xml(game/L"data/db/fifa_ng_db-meta.xml")){if(e.name=="table"){if(e.end)current.clear();else{current=value(e,"shortname");shorts[current]=value(e,"name");}}if(e.name=="field"&&!e.end&&!current.empty())meta[current][value(e,"shortname")]={value(e,"name"),int(number(e,"rangelow",0,-2147483648.f,2147483648.f))};}
        size_t count=u32(16);if(!count||count>2048||!span(24,count*8+4))throw std::runtime_error("Diretorio de tabelas invalido");size_t base=28+count*8;
        for(size_t i=0;i<count;++i){size_t d=24+i*8;std::string key(reinterpret_cast<char*>(b.data()+d),4);if(!shorts.count(key))continue;auto long_name=shorts[key];if(long_name!="teams"&&long_name!="players"&&long_name!="teamplayerlinks"&&long_name!="playernames"&&long_name!="teamkits")continue;size_t offset=base+u32(d+4);if(!span(offset,36))throw std::runtime_error("Tabela incompleta");
            Table t;t.stride=u32(offset+4);t.count=u16(offset+18);t.allocated=u16(offset+16);size_t fields=b[offset+24];t.start=offset+36+fields*16;
            if(!t.stride||t.stride>4096||fields>128||t.count>t.allocated||!span(offset+36,fields*16)||!span(t.start,t.allocated*t.stride))throw std::runtime_error("Limites de tabela invalidos");
            t.block=t.start+t.allocated*t.stride;t.length=u32(offset+12);t.tree=t.length;
            for(size_t f=0;f<fields;++f){size_t p=offset+36+f*16;std::string name(reinterpret_cast<char*>(b.data()+p+8),4);auto m=meta[key].find(name);if(m==meta[key].end())continue;Field field{u32(p+4),u32(p+12),u32(p),m->second.second};
                size_t bits=(field.type==13||field.type==14)?32:field.depth;if(field.bit>t.stride*8||bits>t.stride*8-field.bit)throw std::runtime_error("Campo fora do registro");t.fields[m->second.first]=field;
                if(field.type==13||field.type==14)for(size_t r=0;r<t.count;++r){auto pointer=u32(t.start+r*t.stride+field.bit/8);if(pointer!=0xffffffff)t.tree=std::min(t.tree,size_t(pointer));}}
            tables[shorts[key]]=std::move(t);
        }
    }
    int integer(const Table&t,size_t row,const char*name,int fallback=0)const{auto at=t.fields.find(name);if(at==t.fields.end())return fallback;auto f=at->second;if((f.type!=3&&f.type!=4)||!f.depth||f.depth>32)return fallback;uint32_t n=0;size_t p=t.start+row*t.stride;for(size_t k=0;k<f.depth;++k)n|=uint32_t((b[p+(f.bit+k)/8]>>((f.bit+k)%8))&1)<<k;return int(int64_t(n)+f.low);}
    std::string text(const Table&t,size_t row,const char*name)const{auto at=t.fields.find(name);if(at==t.fields.end())return {};auto f=at->second;size_t p=t.start+row*t.stride+f.bit/8;
        if(f.type==0){size_t bytes=f.depth/8;auto end=std::find(b.begin()+p,b.begin()+p+bytes,0);return std::string(b.begin()+p,end);}
        if(f.type!=13&&f.type!=14)return {};size_t pointer=u32(p);if(pointer==0xffffffff)return {};size_t prefix=f.type==14?2:1;
        if(!span(t.block,t.length)||pointer<t.tree||pointer+prefix>t.length||!t.tree||t.tree>1020||t.tree%4)return {};size_t n=b[t.block+pointer];if(prefix==2)n=n*256+b[t.block+pointer+1];if(n>32000)return {};size_t bit=(pointer+prefix)*8;std::string out;
        for(size_t i=0;i<n;++i){size_t node=0;bool found=false;for(int depth=0;depth<32;++depth){if(bit>=t.length*8||node*4+3>=t.tree)return {};unsigned side=(b[t.block+bit/8]>>(7-bit%8))&1;++bit;auto child=b[t.block+node*4+side*2],symbol=b[t.block+node*4+side*2+1];if(child){if(symbol)return {};node=child;}else{if(!symbol)return {};out+=char(symbol);found=true;break;}}if(!found)return {};}
        if(!out.empty()&&!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,out.data(),int(out.size()),nullptr,0))return {};return out;
    }
};
std::map<int,KitPrintInfo> club_kit_prints(const fs::path&game,int club){Database db(game);std::map<int,KitPrintInfo>result;auto at=db.tables.find("teamkits");if(at==db.tables.end())return result;auto&t=at->second;std::map<int,int>years;
    for(size_t i=0;i<t.count;++i){if(db.integer(t,i,"teamtechid")!=club)continue;int type=db.integer(t,i,"teamkittypetechid"),year=db.integer(t,i,"year");if(type!=0&&type!=2)continue;if(years.count(type)&&year<years[type])continue;years[type]=year;KitPrintInfo p;p.font=db.integer(t,i,"numberfonttype");p.color=db.integer(t,i,"numbercolor");p.name_font=db.integer(t,i,"jerseynamefonttype");p.name_color={db.integer(t,i,"jerseynamecolorr",255)/255.f,db.integer(t,i,"jerseynamecolorg",255)/255.f,db.integer(t,i,"jerseynamecolorb",255)/255.f};result[type]=p;}return result;
}
void Catalog::load(const fs::path&game){Database db(game);clubs.clear();rosters.clear();auto&teams=db.tables.at("teams");auto&players=db.tables.at("players");auto&links=db.tables.at("teamplayerlinks");std::map<int,std::string>names;
    if(db.tables.count("playernames")){auto&t=db.tables.at("playernames");for(size_t i=0;i<t.count;++i)names[db.integer(t,i,"nameid")]=db.text(t,i,"name");}
    std::map<int,Club>by_club;for(size_t i=0;i<teams.count;++i){Club c;c.id=db.integer(teams,i,"teamid");c.name=db.text(teams,i,"teamname");if(c.id<=0||c.name.empty())continue;for(int k=0;k<3;++k){auto prefix="teamcolor"+std::to_string(k+1);c.colors[k]=(db.integer(teams,i,(prefix+"r").c_str())<<16)|(db.integer(teams,i,(prefix+"g").c_str())<<8)|db.integer(teams,i,(prefix+"b").c_str());}by_club[c.id]=c;}
    std::map<int,ClubPlayerRow>by_player;
    for(size_t i=0;i<players.count;++i){ClubPlayerRow r={};auto get=[&](const char*n,int fallback=0){return db.integer(players,i,n,fallback);};r.player_id=get("playerid");r.position=get("preferredposition1");r.overall=get("overallrating");r.squad_position=-1;r.height=get("height",180);r.weight=get("weight",75);r.head_type=get("headtypecode");r.head_class=get("headclasscode");r.hair_type=get("hairtypecode");r.hair_color=get("haircolorcode");r.skin_tone=get("skintonecode",1);r.skin_type=get("skintypecode");r.facial_hair_type=get("facialhairtypecode");r.facial_hair_color=get("facialhaircolorcode");r.shoe_type=get("shoetypecode");r.shoe_design=get("shoedesigncode");r.gender=get("gender");r.body_type=get("bodytypecode",1);r.eye_color=get("eyecolorcode",1);r.eyebrow=get("eyebrowcode");r.sideburns=get("sideburnscode");r.sleeve_length=get("jerseysleevelengthcode");r.jersey_fit=get("jerseyfit");r.jersey_style=get("jerseystylecode");r.sock_length=get("socklengthcode");r.short_style=get("shortstyle");r.glove_type=get("gkglovetypecode");std::string name=names[get("commonnameid")];if(name.empty()){name=names[get("firstnameid")];auto last=names[get("lastnameid")];if(!last.empty()){if(!name.empty())name+=' ';name+=last;}}if(name.empty())name="Jogador "+std::to_string(r.player_id);strncpy_s(r.name,name.c_str(),_TRUNCATE);by_player[r.player_id]=r;}
    for(size_t i=0;i<links.count;++i){int club=db.integer(links,i,"teamid"),player=db.integer(links,i,"playerid");if(!by_club.count(club)||!by_player.count(player))continue;auto r=by_player[player];r.team_id=club;r.number=db.integer(links,i,"jerseynumber");r.squad_position=db.integer(links,i,"position",29);r.club_colors_valid=1;std::copy(std::begin(by_club[club].colors),std::end(by_club[club].colors),std::begin(r.club_colors));rosters[club].push_back(r);}
    for(auto&kv:rosters){auto&rows=kv.second;std::stable_sort(rows.begin(),rows.end(),[](const auto&a,const auto&b){return a.squad_position!=b.squad_position?a.squad_position<b.squad_position:a.overall>b.overall;});clubs.push_back(by_club[kv.first]);}std::sort(clubs.begin(),clubs.end(),[](const Club&a,const Club&b){return a.name<b.name;});if(clubs.empty())throw std::runtime_error("Nenhum clube com jogadores encontrado");
}
Bounds bounds(const fifa_player::Model&m){Bounds b;b.low={FLT_MAX,FLT_MAX,FLT_MAX};b.high={-FLT_MAX,-FLT_MAX,-FLT_MAX};for(auto&p:m.parts)for(auto&v:p.vertices){auto a=v.position;b.low={std::min(b.low.x,a.x),std::min(b.low.y,a.y),std::min(b.low.z,a.z)};b.high={std::max(b.high.x,a.x),std::max(b.high.y,a.y),std::max(b.high.z,a.z)};}if(b.low.x==FLT_MAX)return {};b.center={(b.low.x+b.high.x)*.5f,(b.low.y+b.high.y)*.5f,(b.low.z+b.high.z)*.5f};b.radius=std::max({b.high.x-b.low.x,b.high.y-b.low.y,b.high.z-b.low.z})*.5f;return b;}
void edit_objects(fifa_player::Model&m,const std::vector<ObjectEdit>&edits){for(auto&e:edits)for(auto&p:m.parts)if(p.name==e.name){if(!e.visible){p.vertices.clear();p.indices.clear();continue;}if(p.vertices.empty())continue;fifa_player::Model single;single.parts.push_back(p);auto center=bounds(single).center;auto rot=XMMatrixRotationRollPitchYaw(XMConvertToRadians(e.rotation.x),XMConvertToRadians(e.rotation.y),XMConvertToRadians(e.rotation.z));auto matrix=XMMatrixTranslation(-center.x,-center.y,-center.z)*XMMatrixScaling(e.scale,e.scale,e.scale)*rot*XMMatrixTranslation(center.x+e.translation.x,center.y+e.translation.y,center.z+e.translation.z);for(auto&v:p.vertices){auto a=XMVector3TransformCoord(XMVectorSet(v.position.x,v.position.y,v.position.z,1),matrix);auto n=XMVector3TransformNormal(XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),rot);v.position={XMVectorGetX(a),XMVectorGetY(a),XMVectorGetZ(a)};v.normal={XMVectorGetX(n),XMVectorGetY(n),XMVectorGetZ(n)};}}}
bool save_png(ID3D11Device*d,ID3D11DeviceContext*c,ID3D11ShaderResourceView*srv,const fs::path&path){if(!d||!c||!srv)return false;ComPtr<ID3D11Resource>resource;srv->GetResource(&resource);ComPtr<ID3D11Texture2D>texture;if(FAILED(resource.As(&texture)))return false;D3D11_TEXTURE2D_DESC desc;texture->GetDesc(&desc);desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;desc.MiscFlags=0;ComPtr<ID3D11Texture2D>staging;if(FAILED(d->CreateTexture2D(&desc,nullptr,&staging)))return false;c->CopyResource(staging.Get(),texture.Get());D3D11_MAPPED_SUBRESOURCE mapped={};if(FAILED(c->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped)))return false;std::vector<uint8_t>pixels(size_t(desc.Width)*desc.Height*4);for(UINT y=0;y<desc.Height;++y){auto*src=static_cast<const uint8_t*>(mapped.pData)+y*mapped.RowPitch;auto*dst=pixels.data()+size_t(y)*desc.Width*4;for(UINT x=0;x<desc.Width;++x){auto a=src[x*4+3];dst[x*4]=uint8_t((src[x*4+2]*a+245*(255-a))/255);dst[x*4+1]=uint8_t((src[x*4+1]*a+248*(255-a))/255);dst[x*4+2]=uint8_t((src[x*4]*a+252*(255-a))/255);dst[x*4+3]=255;}}c->Unmap(staging.Get(),0);fs::create_directories(path.parent_path());ComPtr<IWICImagingFactory>factory;ComPtr<IWICStream>stream;ComPtr<IWICBitmapEncoder>encoder;ComPtr<IWICBitmapFrameEncode>frame;HRESULT hr=CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory));if(SUCCEEDED(hr))hr=factory->CreateStream(&stream);if(SUCCEEDED(hr))hr=stream->InitializeFromFilename(path.c_str(),GENERIC_WRITE);if(SUCCEEDED(hr))hr=factory->CreateEncoder(GUID_ContainerFormatPng,nullptr,&encoder);if(SUCCEEDED(hr))hr=encoder->Initialize(stream.Get(),WICBitmapEncoderNoCache);if(SUCCEEDED(hr))hr=encoder->CreateNewFrame(&frame,nullptr);if(SUCCEEDED(hr))hr=frame->Initialize(nullptr);if(SUCCEEDED(hr))hr=frame->SetSize(desc.Width,desc.Height);WICPixelFormatGUID format=GUID_WICPixelFormat32bppBGRA;if(SUCCEEDED(hr))hr=frame->SetPixelFormat(&format);if(SUCCEEDED(hr))hr=frame->WritePixels(desc.Height,desc.Width*4,UINT(pixels.size()),pixels.data());if(SUCCEEDED(hr))hr=frame->Commit();if(SUCCEEDED(hr))hr=encoder->Commit();return SUCCEEDED(hr);}
}
