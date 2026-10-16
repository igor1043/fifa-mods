#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "native_particles.h"
#define cloth_particles cloth_v05
#include "J:/mods/fifa 16/estudos fifa 16/75_CLOTH_SHIRT_CHEST_SLEEVES_20261015/baseline_v05/source/particle_solver.h"
#undef cloth_particles
#define cloth_particles cloth_v06
#include "J:/mods/fifa 16/estudos fifa 16/76_CLOTH_COMPACT_CONTACT_GRID_20261015/baseline_v06/source/particle_solver.h"
#undef cloth_particles
#include <cstdio>
#include <string>
#include <chrono>
using namespace cloth_particles;
namespace old=cloth_v05;
#define CHECK(c) do{if(!(c)){std::fprintf(stderr,"FAIL shirt revision %s line %d: %s\n",name.c_str(),__LINE__,#c);return false;}}while(false)
static old::Vec previous(Vec p){return {p.x,p.y,p.z};}
static bool asset(const std::string& name,Mesh& mesh) {
    FILE* file=nullptr;CHECK(!fopen_s(&file,name.c_str(),"rb")&&file);
    char magic[4];uint32_t counts[4];CHECK(fread(magic,1,4,file)==4&&!std::memcmp(magic,"CFX2",4));
    CHECK(fread(counts,4,4,file)==4);
    mesh=Mesh{};mesh.piece=name.find("simshorts_")!=std::string::npos?Piece::Shorts:Piece::Jersey;
    for(uint32_t i=0;i<counts[0];++i) {
        float p[9];CHECK(fread(p,4,9,file)==9);
        mesh.rest.push_back({p[0]*.01f,p[1]*.01f,p[2]*.01f});mesh.normals.push_back({p[4],p[5],p[6]});mesh.mass.push_back(p[8]);
    }
    for(unsigned family=0;family<3;++family)for(uint32_t i=0;i<counts[family+1];++i) {
        NativeEdge edge{};CHECK(fread(&edge,8,1,file)==1);
        if(edge.a>=counts[0]||edge.b>=counts[0]||edge.a==edge.b)continue;
        mesh.edges.push_back({edge.a,edge.b,edge.rest*.01f,static_cast<Family>(family)});
    }
    fclose(file);CHECK(mesh.prepare());return true;
}
static old::Mesh prior_mesh(const Mesh& mesh) {
    old::Mesh result;result.piece=mesh.piece==Piece::Shorts?old::Piece::Shorts:old::Piece::Jersey;
    for(auto p:mesh.rest)result.rest.push_back(previous(p));for(auto n:mesh.normals)result.normals.push_back(previous(n));
    result.mass=mesh.mass;
    for(const auto& e:mesh.edges)result.edges.push_back({e.a,e.b,e.rest,static_cast<old::Family>(e.family)});
    return result;
}
static bool body_fixture(const std::string& name,std::vector<BodyCapsule>& body) {
    FILE* file=nullptr;CHECK(!fopen_s(&file,name.c_str(),"rb")&&file);
    char magic[4];uint32_t count;CHECK(fread(magic,1,4,file)==4&&!std::memcmp(magic,"BDX4",4));CHECK(fread(&count,4,1,file)==1);
    for(uint32_t i=0;i<count;++i) {
        uint32_t kind;float f[16];CHECK(fread(&kind,4,1,file)==1&&fread(f,64,1,file)==1);
        body.push_back({{f[0]*.01f,f[1]*.01f,f[2]*.01f},{f[4],f[5],f[6]},f[7]*.01f,f[3]*.01f,(kind==2?f[11]:f[3])*.01f});
    }
    fclose(file);return true;
}
static Vec arm_pose(Vec p,float influence,float forearm,float time,bool direction) {
    const float sign=p.x<0?-1.0f:1.0f;
    const Vec shoulder=direction?Vec{}:Vec{sign*.185f,1.475f,-.02f};
    Vec q=p-shoulder;
    const float elbow=.45f*forearm*std::sin(time*6),ce=std::cos(elbow),se=std::sin(elbow);
    q={q.x,ce*q.y-se*q.z,se*q.y+ce*q.z};
    const float angle=.45f*influence*std::sin(time*5)*sign,cs=std::cos(angle),sn=std::sin(angle);
    q={cs*q.x-sn*q.y,sn*q.x+cs*q.y,q.z};q+=shoulder;
    if(!direction){q.x+=.2f*time;q.y+=.006f*std::sin(time*7);}
    return q;
}
static bool arms(const std::string& name,const std::string& bodyName) {
    Mesh mesh;CHECK(asset(name,mesh));std::vector<BodyCapsule> native;CHECK(body_fixture(bodyName,native));
    const Config config{};auto target=mesh.rest,normal=mesh.normals;auto body=native;
    append_sleeve_proxies(mesh,target,body);CHECK(body.size()>=2);
    const size_t bodyCount=body.size();
    State state;CHECK(step(mesh,state,target,normal,1.0f/60,config,nullptr,&body)==Result::Reset);
    float residual=0,spanResidual=0;unsigned injections=0;double milliseconds=0;
    for(unsigned frame=1;frame<=180;++frame) {
        const float time=static_cast<float>(frame)/60;
        for(size_t i=0;i<target.size();++i) {
            const auto p=mesh.rest[i];const float influence=smooth((std::abs(p.x)-.19f)/.07f),forearm=smooth((std::abs(p.x)-.36f)/.15f);
            target[i]=arm_pose(p,influence,forearm,time,false);
            // Use the same signed side as the point for its normal rotation.
            const float sign=p.x<0?-1.0f:1.0f,angle=.45f*influence*std::sin(time*5)*sign;
            const float elbow=.45f*forearm*std::sin(time*6),ce=std::cos(elbow),se=std::sin(elbow),cs=std::cos(angle),sn=std::sin(angle);
            const Vec n=mesh.normals[i],q{n.x,ce*n.y-se*n.z,se*n.y+ce*n.z};normal[i]={cs*q.x-sn*q.y,sn*q.x+cs*q.y,q.z};
        }
        body=native;
        for(auto& c:body) {
            const Vec center=c.center;const float influence=smooth((std::abs(center.x)-.19f)/.07f),forearm=smooth((std::abs(center.x)-.36f)/.15f);
            c.center=arm_pose(center,influence,forearm,time,false);
            c.axis=unit(arm_pose(center+c.axis*.001f,influence,forearm,time,false)-c.center);
        }
        append_sleeve_proxies(mesh,target,body);
        CHECK(body.size()==bodyCount);
        if(frame==60||frame==120) {
            const BodyCapsule* chosen=nullptr;
            for(const auto& c:body)if(c.center.x>.2f*time+.22f&&c.center.y>1.15f){chosen=&c;break;}
            CHECK(chosen);size_t point=target.size();float distance=100;
            for(size_t i=0;i<target.size();++i)if(mesh.mass[i]&&mesh.sleeve[i]>.8f) {
                const float d=length(target[i]-chosen->center);if(d<distance){distance=d;point=i;}
            }
            CHECK(point<target.size());state.position[point]=chosen->center+normal[point]*(chosen->radiusA*.4f);++injections;
        }
        const auto start=std::chrono::steady_clock::now();
        CHECK(step(mesh,state,target,normal,1.0f/60,config,nullptr,&body)==Result::Stepped);
        milliseconds+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        for(size_t i=0;i<target.size();++i) {
            CHECK(finite(state.position[i])&&finite(state.velocity[i]));
            if(!mesh.mass[i]){CHECK(length(state.position[i]-target[i])<1e-6f);continue;}
            if(mesh.sleeve[i]>.25f)for(const auto& c:body){Vec p=state.position[i];project_capsule(p,c,config.armMargin,normal[i]);residual=std::max(residual,length(p-state.position[i]));}
        }
        for(const auto& e:mesh.collisionEdges)for(const auto& c:body) {
            Vec a=state.position[e.a],b=state.position[e.b];project_capsule_edge(a,b,mesh.mass[e.a],mesh.mass[e.b],c,config.armMargin,normal[e.a]+normal[e.b]);
            spanResidual=std::max(spanResidual,std::max(length(a-state.position[e.a]),length(b-state.position[e.b])));
        }
    }
    std::printf("shirt arms %s native=%zu active=%zu long=%u contacts=%llu edges=%llu point_residual_m=%.6f span_residual_m=%.6f cpu_ms=%.3f\n",name.c_str(),native.size(),body.size(),mesh.longSleeves?1u:0u,
        static_cast<unsigned long long>(state.bodyContacts),static_cast<unsigned long long>(state.edgeContacts),residual,spanResidual,milliseconds/180);
    CHECK(injections==2&&state.bodyContacts+state.edgeContacts>0&&residual<.002f&&spanResidual<.002f);return true;
}
static bool compare(const std::string& name,const std::string& bodyName) {
    Mesh mesh;CHECK(asset(name,mesh));auto prior=prior_mesh(mesh);CHECK(prior.prepare());
    std::vector<BodyCapsule> initial;if(mesh.piece==Piece::Shorts)CHECK(body_fixture(bodyName,initial));
    float maximum=0,maximumVelocity=0;double chestNew=0,chestOld=0,hemNew=0,hemOld=0;unsigned chestCount=0,hemCount=0;
    float widthNew=0,widthOld=0;
    for(unsigned rate:{30u,60u,120u}) {
        State state;old::State before;const Config config{};old::Config priorConfig{};
        // Compare solver behavior at the same fit. The extra 3 mm lift in
        // 0.8.2 is checked separately on the real factory meshes.
        priorConfig.shortsHemLift=config.shortsHemLift;
        auto target=mesh.rest,normal=mesh.normals;std::vector<old::Vec> pt,pn;std::vector<old::BodyCapsule> pb;
        for(auto p:target)pt.push_back(previous(p));for(auto n:normal)pn.push_back(previous(n));
        for(const auto& c:initial)pb.push_back({previous(c.center),previous(c.axis),c.halfLength,c.radiusA,c.radiusB});
        const float dt=1.0f/static_cast<float>(rate);
        CHECK(step(mesh,state,target,normal,dt,config,nullptr,initial.empty()?nullptr:&initial)==Result::Reset);
        CHECK(old::step(prior,before,pt,pn,dt,priorConfig,nullptr,pb.empty()?nullptr:&pb)==old::Result::Reset);
        if(mesh.piece==Piece::Jersey)for(size_t i=0;i<target.size();++i)if(mesh.waist[i]>.6f) {
            widthNew=std::max(widthNew,std::abs(state.fitted[i].x));widthOld=std::max(widthOld,std::abs(before.fitted[i].x));
        }
        for(unsigned frame=1;frame<=rate*3;++frame) {
            const float time=static_cast<float>(frame)/static_cast<float>(rate),angle=.2f*std::sin(time*4),cs=std::cos(angle),sn=std::sin(angle);
            for(size_t i=0;i<target.size();++i) {
                const auto p=mesh.rest[i],n=mesh.normals[i];const float leg=mesh.piece==Piece::Shorts?smooth((.95f-p.y)/.3f):0;
                target[i]={cs*p.x+sn*p.z+.25f*time,p.y+.012f*std::sin(time*7),-sn*p.x+cs*p.z+leg*.07f*std::sin(time*6)*(p.x<0?-1.0f:1.0f)};
                normal[i]={cs*n.x+sn*n.z,n.y,-sn*n.x+cs*n.z};pt[i]=previous(target[i]);pn[i]=previous(normal[i]);
            }
            auto body=initial;
            for(size_t k=0;k<body.size();++k) {
                const auto p=initial[k].center,n=initial[k].axis;
                body[k].center={cs*p.x+sn*p.z+.25f*time,p.y+.012f*std::sin(time*7),-sn*p.x+cs*p.z};body[k].axis={cs*n.x+sn*n.z,n.y,-sn*n.x+cs*n.z};
                pb[k]={previous(body[k].center),previous(body[k].axis),body[k].halfLength,body[k].radiusA,body[k].radiusB};
            }
            CHECK(step(mesh,state,target,normal,dt,config,nullptr,body.empty()?nullptr:&body)==Result::Stepped);
            CHECK(old::step(prior,before,pt,pn,dt,priorConfig,nullptr,pb.empty()?nullptr:&pb)==old::Result::Stepped);
            for(size_t i=0;i<target.size();++i) {
                if(mesh.piece==Piece::Shorts) {
                    maximum=std::max(maximum,length(state.position[i]-Vec{before.position[i].x,before.position[i].y,before.position[i].z}));
                    maximumVelocity=std::max(maximumVelocity,length(state.velocity[i]-Vec{before.velocity[i].x,before.velocity[i].y,before.velocity[i].z}));
                }else if(frame>rate&&mesh.mass[i]) {
                    const Vec a=state.position[i]-state.fitted[i];const auto b=before.position[i]-before.fitted[i];
                    if(mesh.chest[i]>.3f){chestNew+=dot(a,a);chestOld+=old::dot(b,b);++chestCount;}
                    if(mesh.hem[i]>.5f){hemNew+=dot(a,a);hemOld+=old::dot(b,b);++hemCount;}
                }
            }
        }
    }
    if(mesh.piece==Piece::Shorts) {
        std::printf("shorts v05 same-lift comparison %s rates=30/60/120 position_delta_m=%.9f velocity_delta_m_s=%.9f\n",name.c_str(),maximum,maximumVelocity);
        CHECK(maximum<1e-5f&&maximumVelocity<1e-4f);
    }else {
        CHECK(chestCount&&hemCount);
        const double newChest=std::sqrt(chestNew/chestCount),oldChest=std::sqrt(chestOld/chestCount);
        const double newHem=std::sqrt(hemNew/hemCount),oldHem=std::sqrt(hemOld/hemCount);
        std::printf("shirt v05 comparison %s chest_rms_old_new_m=%.6f/%.6f hem_rms_old_new_m=%.6f/%.6f half_width_old_new_m=%.6f/%.6f\n",name.c_str(),oldChest,newChest,oldHem,newHem,widthOld,widthNew);
        CHECK(newChest<oldChest*.9&&newHem>oldHem*.8&&widthNew<widthOld&&widthOld-widthNew<.006f);
    }
    return true;
}
static bool compact06(const std::string& name) {
    Mesh mesh;CHECK(asset(name,mesh));cloth_v06::Mesh prior;prior.piece=cloth_v06::Piece::Jersey;
    for(auto p:mesh.rest)prior.rest.push_back({p.x,p.y,p.z});for(auto n:mesh.normals)prior.normals.push_back({n.x,n.y,n.z});prior.mass=mesh.mass;
    for(const auto& e:mesh.edges)prior.edges.push_back({e.a,e.b,e.rest,static_cast<cloth_v06::Family>(e.family)});CHECK(prior.prepare());
    auto target=mesh.rest,normal=mesh.normals;auto pt=prior.rest,pn=prior.normals;
    State state;cloth_v06::State before;const Config config{};const cloth_v06::Config oldConfig{};
    CHECK(step(mesh,state,target,normal,1.0f/60,config)==Result::Reset);
    CHECK(cloth_v06::step(prior,before,pt,pn,1.0f/60,oldConfig)==cloth_v06::Result::Reset);
    float widthOld=0,widthNew=0,lift=0,tighten[2]{};unsigned hems=0,panels[2]{};
    for(size_t i=0;i<target.size();++i) {
        if(mesh.waist[i]>.6f){widthOld=std::max(widthOld,std::abs(before.fitted[i].x));widthNew=std::max(widthNew,std::abs(state.fitted[i].x));}
        if(mesh.hem[i]>.8f){lift+=state.fitted[i].y-before.fitted[i].y;++hems;}
        if(mesh.chest[i]>.6f&&std::abs(mesh.rest[i].x)>.03f) {
            const unsigned side=mesh.rest[i].x<0?0:1;
            tighten[side]+=dot(state.fitted[i]-Vec{before.fitted[i].x,before.fitted[i].y,before.fitted[i].z},normal[i]);++panels[side];
        }
    }
    CHECK(hems&&panels[0]&&panels[1]);lift/=static_cast<float>(hems);
    for(unsigned side=0;side<2;++side)tighten[side]/=static_cast<float>(panels[side]);
    double chestNew[2]{},chestOld[2]{};unsigned count[2]{};
    for(unsigned frame=1;frame<=180;++frame) {
        const float t=static_cast<float>(frame)/60,a=.2f*std::sin(t*4),cs=std::cos(a),sn=std::sin(a);
        for(size_t i=0;i<target.size();++i) {
            const auto p=mesh.rest[i],n=mesh.normals[i];target[i]={cs*p.x+sn*p.z+.25f*t,p.y+.012f*std::sin(t*7),-sn*p.x+cs*p.z};
            normal[i]={cs*n.x+sn*n.z,n.y,-sn*n.x+cs*n.z};pt[i]={target[i].x,target[i].y,target[i].z};pn[i]={normal[i].x,normal[i].y,normal[i].z};
        }
        CHECK(step(mesh,state,target,normal,1.0f/60,config)==Result::Stepped);
        CHECK(cloth_v06::step(prior,before,pt,pn,1.0f/60,oldConfig)==cloth_v06::Result::Stepped);
        if(frame>60)for(size_t i=0;i<target.size();++i)if(mesh.chest[i]>.6f&&std::abs(mesh.rest[i].x)>.03f) {
            const unsigned side=mesh.rest[i].x<0?0:1;const Vec d=state.position[i]-state.fitted[i];const auto b=before.position[i]-before.fitted[i];
            chestNew[side]+=dot(d,d);chestOld[side]+=cloth_v06::dot(b,b);++count[side];
        }
    }
    double ratio[2]{};for(unsigned side=0;side<2;++side){CHECK(count[side]);ratio[side]=std::sqrt(chestNew[side]/chestOld[side]);}
    std::printf("shirt v06 compact %s width_reduction=%.6f hem_lift_m=%.6f chest_fit_left_right_m=%.6f/%.6f chest_rms_ratio_left_right=%.6f/%.6f\n",name.c_str(),(widthOld-widthNew)/widthOld,lift,tighten[0],tighten[1],ratio[0],ratio[1]);
    CHECK((widthOld-widthNew)/widthOld>.005f&&(widthOld-widthNew)/widthOld<.015f&&lift>.003f&&lift<.010f);
    CHECK(tighten[0]<-.0005f&&tighten[1]<-.0005f&&tighten[0]>-.004f&&tighten[1]>-.004f&&std::abs(tighten[0]-tighten[1])<.0015f);
    CHECK(ratio[0]<.97&&ratio[1]<.97);return true;
}
int main(int argc,char** argv) {
    if(argc!=4)return 1;
    const std::string root=std::string(argv[1])+"\\",shortsRoot=std::string(argv[2])+"\\",armsRoot=std::string(argv[3])+"\\";
    WIN32_FIND_DATAA row{};HANDLE search=FindFirstFileA((root+"*.cfx").c_str(),&row);if(search==INVALID_HANDLE_VALUE)return 2;
    unsigned shirts=0,shorts=0;bool ok=true;
    do {
        const std::string file=row.cFileName,name=root+file,stem=file.substr(0,file.size()-4);
        if(file.find("simshorts_")==0){const bool same=compare(name,shortsRoot+stem+".body");ok=same&&ok;++shorts;}
        else {const bool fit=compare(name,"");const bool compact=compact06(name);const bool contact=arms(name,armsRoot+stem+".body");ok=fit&&compact&&contact&&ok;++shirts;}
    }while(FindNextFileA(search,&row));FindClose(search);
    if(!ok||shirts!=16||shorts!=2)return 3;
    std::puts("shirt revision: 16 chest/fit/arm cases and two unchanged shorts at 30/60/120 passed");return 0;
}
