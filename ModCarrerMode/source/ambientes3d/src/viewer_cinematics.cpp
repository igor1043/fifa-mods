#include "viewer_cinematics.h"
#include "viewer_dressing_room.h"
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <stdexcept>

namespace studio {
namespace {
Vec3 add(Vec3 a,Vec3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
Vec3 scale(Vec3 a,float b){return {a.x*b,a.y*b,a.z*b};}
bool finite(Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&fabsf(p.x)<=100000&&fabsf(p.y)<=100000&&fabsf(p.z)<=100000;}
float distance(Vec3 a,Vec3 b){return sqrtf((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z));}
float tangent(float a,float b){return a*b<=0?0:2*a*b/(a+b);}
template<class Value>float interpolate(const CameraScene&s,size_t left,float t,Value value){
    auto&a=s.keys[left];auto&b=s.keys[left+1];float span=b.time-a.time,u=(t-a.time)/span,A=value(a),B=value(b);
    if(b.transition==1)return A+(B-A)*u;
    float slope=(B-A)/span,m0=left&&a.transition!=2?tangent((A-value(s.keys[left-1]))/(a.time-s.keys[left-1].time),slope):0;
    float m1=left+2<s.keys.size()&&s.keys[left+2].transition!=2?tangent(slope,(value(s.keys[left+2])-B)/(s.keys[left+2].time-b.time)):0;
    float u2=u*u,u3=u2*u;return (2*u3-3*u2+1)*A+(u3-2*u2+u)*span*m0+(-2*u3+3*u2)*B+(u3-u2)*span*m1;
}
}
void validate_camera_scene(const CameraScene&s){
    if(s.name.empty()||s.name.size()>160||s.id.empty()||s.id.size()>120||s.environment<0||s.environment>7||s.keys.size()<2||s.keys.size()>256)throw std::runtime_error("Cena cinematográfica precisa de nome e 2 a 256 enquadramentos");
    float previous=-1;for(auto&k:s.keys){if(!std::isfinite(k.time)||k.time<0||k.time>600||k.time<=previous||!finite(k.position)||!finite(k.target)||distance(k.position,k.target)<1||!std::isfinite(k.fov)||k.fov<20||k.fov>90||k.transition<0||k.transition>2)throw std::runtime_error("Enquadramento cinematográfico inválido");previous=k.time;}
    if(s.keys.front().time!=0)throw std::runtime_error("A cena deve começar em zero segundos");
}
float camera_scene_duration(const CameraScene&s){return s.keys.empty()?0:s.keys.back().time;}
CameraKey capture_camera_key(const Camera&c,float time){auto f=c.forward();return {time,c.position,{c.position.x+f.x*c.distance,c.position.y+f.y*c.distance,c.position.z+f.z*c.distance},c.fov};}
void load_camera_library(const fs::path&path,Settings&s){if(!fs::exists(path))return;auto saved=load_settings(path);for(auto&film:saved.camera_scenes)if(std::none_of(s.camera_scenes.begin(),s.camera_scenes.end(),[&](auto&item){return item.id==film.id;}))s.camera_scenes.push_back(film);if(s.camera_scenes.size()>100)throw std::runtime_error("Biblioteca excede 100 cenas personalizadas");}
void save_camera_library(const fs::path&path,const Settings&s){if(s.camera_scenes.empty())return;Settings library;library.game=s.game;library.scene=1;library.pose=1;library.coach_target=false;library.camera_scenes=s.camera_scenes;load_camera_library(path,library);save_settings(path,library);}
Camera sample_camera_scene(const CameraScene&s,float time){
    validate_camera_scene(s);if(!std::isfinite(time))throw std::runtime_error("Tempo cinematográfico inválido");time=std::clamp(time,0.f,camera_scene_duration(s));CameraKey key=s.keys.back();
    if(time<s.keys.back().time){auto it=std::upper_bound(s.keys.begin(),s.keys.end(),time,[](float t,const auto&k){return t<k.time;});size_t left=it==s.keys.begin()?0:size_t(it-s.keys.begin()-1);auto&next=s.keys[left+1];key=s.keys[left];
        if(next.transition!=2){for(int axis=0;axis<3;++axis){(&key.position.x)[axis]=interpolate(s,left,time,[&](const auto&k){return (&k.position.x)[axis];});(&key.target.x)[axis]=interpolate(s,left,time,[&](const auto&k){return (&k.target.x)[axis];});}key.fov=interpolate(s,left,time,[](const auto&k){return k.fov;});}
    }
    Camera camera;camera.orbit=false;camera.position=key.position;camera.target=key.target;camera.fov=key.fov;camera.distance=distance(key.position,key.target);if(camera.distance<1)throw std::runtime_error("Câmera e alvo se cruzam: ajuste os enquadramentos");Vec3 d={key.target.x-key.position.x,key.target.y-key.position.y,key.target.z-key.position.z};camera.pitch=std::clamp(asinf(std::clamp(d.y/camera.distance,-1.f,1.f)),-1.5f,1.5f);camera.yaw=atan2f(d.x,-d.z);return camera;
}
float camera_scene_fade(const CameraScene&s,float time){float fade=0;for(auto&k:s.keys)if(k.transition==2)fade=std::max(fade,std::max(0.f,1-fabsf(time-k.time)/.18f));return fade;}
std::vector<CameraScene> cinematic_catalog(int environment,const fifa_player::Model&model,const std::vector<ClubPlayerRow>&roster,int player){
    std::vector<CameraScene>out;auto clip=[&](const char*id,const char*name,std::initializer_list<CameraKey>keys){CameraScene s{id,name,environment,keys};validate_camera_scene(s);out.push_back(std::move(s));};
    if(environment==1){
        clip("room-intro","Apresentação do vestiário",{{0,{0,194,638},{0,135,-175},70},{6,{170,191,450},{0,135,-170},67},{13,{280,188,180},{-120,140,-180},62},{18,{210,181,-60},{-160,153,-405},60}});
        clip("locker-tour","Passeio pelos armários",{{0,{-255,173,377},{-488,158,270},60},{8,{-252,173,55},{-488,158,40},57},{15,{-220,173,-287},{-350,160,-435},58},{23,{220,173,-290},{350,160,-435},58}});
        auto selected=std::find_if(roster.begin(),roster.end(),[&](auto&r){return r.player_id==player;});if(selected==roster.end()&&!roster.empty())selected=roster.begin();
        if(selected!=roster.end()){size_t index=size_t(selected-roster.begin());std::string token=" — "+std::string(selected->name)+" / uniforme";Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};bool found=false;
            for(auto&p:model.parts)if(p.name.find(token)!=std::string::npos&&p.asset.find("native/")!=std::string::npos)for(auto&v:p.vertices){found=true;for(int k=0;k<3;++k){(&lo.x)[k]=std::min((&lo.x)[k],(&v.position.x)[k]);(&hi.x)[k]=std::max((&hi.x)[k],(&v.position.x)[k]);}}
            if(found){Vec3 c=scale(add(lo,hi),.5f),n=index<8?Vec3{0,0,1}:index<16?Vec3{1,0,0}:Vec3{-1,0,0};Vec3 side={n.z,0,-n.x};clip("shirt-focus","Uniforme em destaque",{{0,add(add(c,scale(n,230)),{0,35,0}),c,56},{5,add(add(c,scale(n,145)),add(scale(side,24),{0,25,0})),add(c,{0,7,0}),45},{11,add(add(c,scale(n,95)),add(scale(side,-12),{0,17,0})),add(c,{0,13,0}),42}});}
        }
        clip("desk-study","Mesa e plano de jogo",{{0,{-155,183,264},{0,81,93},62},{6,{-90,163,230},{0,83,93},52},{13,{75,150,223},{14,94,56},43},{18,{140,166,172},{0,82,99},52}});
        clip("hydration","Hidratação e equipamentos",{{0,{-130,178,410},{-330,83,565},62},{7,{-200,165,502},{-403,107,683},54},{14,{-256,155,554},{-432,106,684},47}});
        clip("medical","Cuidados e recuperação",{{0,{120,181,348},{300,89,185},64},{8,{170,161,304},{295,90,157},53},{16,{200,168,356},{369,85,322},45}});
        clip("tactics","Quadros e análise tática",{{0,{-70,187,-186},{0,172,-373},56},{7,{45,185,-217},{0,174,-374},44},{8,{80,185,490},{210,189,707},62,2},{16,{115,190,523},{215,192,707},47}});
        clip("tv-sequence","Composição de TV — sequência completa",{{0,{0,194,638},{0,135,-175},70},{6,{210,182,245},{-120,140,-200},63},{7,{-252,173,140},{-488,160,25},59,2},{13,{-230,176,-290},{-300,161,-435},52},{14,{-120,178,242},{0,81,90},59,2},{21,{80,163,211},{14,93,56},45},{22,{-210,169,479},{-403,108,682},55,2},{28,{-266,160,550},{-432,105,683},45},{29,{80,192,500},{210,189,707},57,2},{35,{112,188,530},{210,189,707},47}});
    }else if(environment==0){
        clip("press-room","Apresentação da sala de imprensa",{{0,{0,185,975},{0,160,-330},66},{7,{320,180,520},{0,160,-330},62},{16,{215,185,165},{0,167,-344},60}});
        clip("press-table","Mesa da coletiva",{{0,{-180,193,140},{0,167,-344},64},{8,{180,190,130},{0,167,-344},62},{16,{30,190,110},{0,167,-344},64}});
    }
    if(environment==6){
        clip("gym-tour","Academia — visita completa",{{0,{-950,235,-260},{270,180,-1250},72},{8,{-650,235,-430},{440,175,-1420},69},{17,{-360,235,-770},{550,180,-1470},67},{25,{0,220,-350},{0,180,3500},73}});
        clip("gym-gallery","Mezanino e cardio",{{0,{-930,539,-1190},{400,280,-620},74},{9,{-580,532,-1200},{230,438,-1490},68},{18,{20,528,-1145},{400,440,-1450},66}});
        clip("gym-window","Do vidro para o campo",{{0,{0,210,-560},{0,170,3100},73},{8,{0,210,-180},{0,170,4000},70},{17,{0,290,400},{0,120,4500},72}});
    }else if(environment==7){
        clip("ct-overview","CT — apresentação do campo",{{0,{-6500,4800,900},{0,30,6350},70},{10,{-6100,4300,3900},{0,80,6350},70},{23,{-5800,3900,7600},{0,80,7500},70}});
        clip("ct-finishing","Treino de finalização",{{0,{900,240,1630},{0,140,2950},64},{8,{450,205,2010},{0,120,2930},65},{18,{-450,240,1750},{0,130,2870},66}});
        clip("ct-coach","Área de apoio do treinador",{{0,{-2860,227,2440},{-3400,110,2130},66},{8,{-3070,217,2350},{-3450,140,2150},59},{16,{-3000,220,1800},{-3310,70,1850},60}});
    }
    return out;
}
}
