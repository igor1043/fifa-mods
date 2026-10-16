#define main earlier_revision_main
#include "test_shirt_revision.cpp"
#undef main
#define cloth_particles cloth_v07
#include "J:/mods/fifa 16/estudos fifa 16/77_CLOTH_HEM_CURVATURE_20261016/baseline_v07/source/particle_solver.h"
#undef cloth_particles

static bool fold_guard() {
    const std::string name="fold_guard_and_self_contact";
    Mesh mesh;mesh.piece=Piece::Jersey;mesh.mass={1,1,1,0};
    mesh.rest={{-.03f,0,0},{0,0,0},{.03f,0,0},{0,1,0}};mesh.hemFolds={{0,1,2}};
    State state;state.position={{0,.03f,0},{0,0,0},{.001f,.03f,0},{0,1,0}};
    auto before=state.position;const auto initial=state.position;
    const float oldRatio=length(state.position[0]-state.position[2])/(length(state.position[0]-state.position[1])+length(state.position[2]-state.position[1]));
    for(unsigned pass=0;pass<24;++pass)finish_hem_folds(mesh,state,mesh.rest,&before);
    const float ratio=length(state.position[0]-state.position[2])/(length(state.position[0]-state.position[1])+length(state.position[2]-state.position[1]));
    CHECK(ratio>.819f&&state.position[3].y==1&&state.foldContacts>0);
    for(size_t i=0;i<4;++i)CHECK(length((state.position[i]-initial[i])-(before[i]-initial[i]))<1e-6f);
    // The guard must leave a broad, natural curve untouched.
    state.position={{-.03f,0,0},{0,-.008f,0},{.03f,0,0},{0,1,0}};const auto broad=state.position;
    finish_hem_folds(mesh,state,mesh.rest,nullptr);
    CHECK(!std::memcmp(broad.data(),state.position.data(),4*sizeof(Vec)));
    mesh.selfVertices={0,2};mesh.selfExclude.resize(4);
    state.position={{0,0,0},{0,1,0},{.001f,0,0},{0,2,0}};before=state.position;
    finish_hem_self_contact(mesh,state,&before);
    CHECK(std::abs(length(state.position[0]-state.position[2])-.004f)<1e-6f&&state.selfContacts==1);
    CHECK(length(state.position[0]-before[0])<1e-6f&&length(state.position[2]-before[2])<1e-6f);
    // Two-ring topology and coincident bind seams are excluded.
    state.position[2]=state.position[0]+Vec{.001f,0,0};mesh.selfExclude[0]={2};const auto excluded=state.position;
    finish_hem_self_contact(mesh,state,nullptr);CHECK(!std::memcmp(excluded.data(),state.position.data(),4*sizeof(Vec)));
    mesh.selfExclude[0].clear();mesh.rest[2]=mesh.rest[0]+Vec{.001f,0,0};
    finish_hem_self_contact(mesh,state,nullptr);CHECK(!std::memcmp(excluded.data(),state.position.data(),4*sizeof(Vec)));
    std::printf("hem safeguard chord_arc_before_after=%.6f/%.6f separation_m=.004 broad_folds_seams_and_velocity_preserved\n",oldRatio,ratio);
    return true;
}

struct PairInput {
    Mesh mesh[2];std::vector<Vec> target[2],normal[2];std::vector<BodyCapsule> body[2];float dt=0;
};
static bool pipeline(const std::string& name,const std::string& shortsName,const std::string& armName,const std::string& legName,bool compress) {
    PairInput input;CHECK(asset(name,input.mesh[0])&&asset(shortsName,input.mesh[1]));
    std::vector<BodyCapsule> native[2];CHECK(body_fixture(armName,native[0])&&body_fixture(legName,native[1]));
    cloth_v07::Mesh oldMesh[2];
    for(unsigned g=0;g<2;++g) {
        oldMesh[g].piece=g?cloth_v07::Piece::Shorts:cloth_v07::Piece::Jersey;
        for(auto p:input.mesh[g].rest)oldMesh[g].rest.push_back({p.x,p.y,p.z});
        for(auto p:input.mesh[g].normals)oldMesh[g].normals.push_back({p.x,p.y,p.z});oldMesh[g].mass=input.mesh[g].mass;
        for(const auto& e:input.mesh[g].edges)oldMesh[g].edges.push_back({e.a,e.b,e.rest,static_cast<cloth_v07::Family>(e.family)});
        CHECK(oldMesh[g].prepare());input.target[g]=input.mesh[g].rest;input.normal[g]=input.mesh[g].normals;
    }
    State current[2];cloth_v07::State previousState[2];Config config;cloth_v07::Config oldConfig;
    // Isolate the hem safeguards from the requested shorts fit change.
    oldConfig.shortsHemLift=config.shortsHemLift;
    std::vector<cloth_v07::Vec> oldTarget[2],oldNormal[2];std::vector<cloth_v07::BodyCapsule> oldBody[2];
    double milliseconds[2]{};float residual=0,oldResidual=0,shortsDelta=0,maxFrameShift=0;uint64_t oldAcute=0,newAcute=0;
    float time=0;std::vector<Vec> last;
    for(unsigned frame=0;frame<360;++frame) {
        // Smooth physical animation with deliberately irregular render intervals.
        const float durations[]={1.f/60,1.f/70,1.f/120,1.f/47,1.f/61,1.f/59};input.dt=durations[frame%6];time+=input.dt;
        const float angle=.35f*std::sin(time*2),cs=std::cos(angle),sn=std::sin(angle);
        for(unsigned g=0;g<2;++g) {
            const auto pose=[&](Vec p,bool direction) {
                const float sign=p.x<0?-1.f:1.f;
                const float swing=g?.55f*sign*std::sin(time*6):0,ce=std::cos(swing),se=std::sin(swing);
                const Vec origin=direction?Vec{}:Vec{sign*.105f,.98f,0};
                Vec q=p;
                if(g&&(direction||p.y<.95f)){q-=origin;q={q.x,ce*q.y-se*q.z,se*q.y+ce*q.z};q+=origin;}
                q={cs*q.x+sn*q.z,q.y,-sn*q.x+cs*q.z};
                if(!direction){q.x+=.3f*time;q.y+=.01f*std::sin(time*7);}return q;
            };
            for(size_t i=0;i<input.target[g].size();++i) {
                input.target[g][i]=pose(input.mesh[g].rest[i],false);
                input.normal[g][i]=unit(pose(input.mesh[g].rest[i]+input.mesh[g].normals[i]*.001f,false)-input.target[g][i]);
                if(!g&&compress)input.target[g][i].y+=.045f*input.mesh[g].hem[i]*smooth((std::sin(time*3)+1)*.5f);
            }
            input.body[g]=native[g];
            for(auto& capsule:input.body[g]) {
                const auto center=capsule.center;capsule.center=pose(center,false);
                capsule.axis=unit(pose(center+capsule.axis*.001f,false)-capsule.center);
            }
            append_sleeve_proxies(input.mesh[g],input.target[g],input.body[g]);
            oldTarget[g].clear();oldNormal[g].clear();oldBody[g].clear();
            for(auto p:input.target[g])oldTarget[g].push_back({p.x,p.y,p.z});
            for(auto p:input.normal[g])oldNormal[g].push_back({p.x,p.y,p.z});
            for(const auto& b:input.body[g])oldBody[g].push_back({{b.center.x,b.center.y,b.center.z},{b.axis.x,b.axis.y,b.axis.z},b.halfLength,b.radiusA,b.radiusB});
        }
        // Inject a folded hem into both versions; normal animation stays identical.
        if(frame==90||frame==210) {
            CHECK(!input.mesh[0].hemFolds.empty());
            const auto f=input.mesh[0].hemFolds[input.mesh[0].hemFolds.size()/2];
            if(input.mesh[0].mass[f.a]&&input.mesh[0].mass[f.b]) {
                current[0].position[f.b]=current[0].position[f.a]+Vec{.001f,0,0};
                const auto a=previousState[0].position[f.a];previousState[0].position[f.b]=a+cloth_v07::Vec{.001f,0,0};
            }
        }
        // Alternate order of timing to avoid a consistent cache/thermal advantage.
        for(unsigned order=0;order<2;++order) {
            const unsigned mode=(order+frame)%2;const auto start=std::chrono::steady_clock::now();
            if(mode==0) {
                const auto result=step(input.mesh[1],current[1],input.target[1],input.normal[1],input.dt,config,nullptr,&input.body[1]);
                CHECK(result==(frame?Result::Stepped:Result::Reset));ContactSurface surface;
                for(auto i:input.mesh[1].waistSamples)surface.samples.push_back({current[1].position[i],contact_normal(input.mesh[1],current[1].position,input.normal[1],i)});
                surface.prepare();
                CHECK(step(input.mesh[0],current[0],input.target[0],input.normal[0],input.dt,config,&surface,&input.body[0])==(frame?Result::Stepped:Result::Reset));
                if(frame>30)milliseconds[0]+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
                for(size_t i=0;i<current[0].position.size();++i) {
                    CHECK(finite(current[0].position[i])&&finite(current[0].velocity[i])&&length(current[0].velocity[i])<6.01f);
                    if(!input.mesh[0].mass[i])CHECK(length(current[0].position[i]-current[0].fitted[i])<1e-6f);
                    if(input.mesh[0].waist[i]>.3f) {
                        Vec p=current[0].position[i];project_contact(p,input.normal[0][i],&surface,config);residual=std::max(residual,length(p-current[0].position[i]));
                    }
                    if(!last.empty()&&frame!=90&&frame!=210)maxFrameShift=std::max(maxFrameShift,length(current[0].position[i]-last[i]));
                }
                last=current[0].position;
            }else {
                const auto result=cloth_v07::step(oldMesh[1],previousState[1],oldTarget[1],oldNormal[1],input.dt,oldConfig,nullptr,&oldBody[1]);
                CHECK(result==(frame?cloth_v07::Result::Stepped:cloth_v07::Result::Reset));cloth_v07::ContactSurface surface;
                for(auto i:oldMesh[1].waistSamples)surface.samples.push_back({previousState[1].position[i],cloth_v07::contact_normal(oldMesh[1],previousState[1].position,oldNormal[1],i)});
                surface.prepare();
                CHECK(cloth_v07::step(oldMesh[0],previousState[0],oldTarget[0],oldNormal[0],input.dt,oldConfig,&surface,&oldBody[0])==(frame?cloth_v07::Result::Stepped:cloth_v07::Result::Reset));
                if(frame>30)milliseconds[1]+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
                for(size_t i=0;i<previousState[0].position.size();++i)if(oldMesh[0].waist[i]>.3f) {
                    auto p=previousState[0].position[i];cloth_v07::project_contact(p,oldNormal[0][i],&surface,oldConfig);
                    oldResidual=std::max(oldResidual,cloth_v07::length(p-previousState[0].position[i]));
                }
            }
        }
        for(size_t i=0;i<current[1].position.size();++i) {
            const auto p=previousState[1].position[i];shortsDelta=std::max(shortsDelta,length(current[1].position[i]-Vec{p.x,p.y,p.z}));
        }
        for(const auto& f:input.mesh[0].hemFolds) {
            const auto check=[](Vec a,Vec c,Vec b) {const float arc=length(a-c)+length(b-c);return length(a-b)<arc*.75f;};
            if(check(current[0].position[f.a],current[0].position[f.center],current[0].position[f.b]))++newAcute;
            const auto a=previousState[0].position[f.a],b=previousState[0].position[f.b],c=previousState[0].position[f.center];
            if(check({a.x,a.y,a.z},{c.x,c.y,c.z},{b.x,b.y,b.z}))++oldAcute;
        }
    }
    std::printf("hem pipeline %s compression=%u irregular_fps=47/59/60/61/70/120 folds=%zu self_vertices=%zu acute_old_new=%llu/%llu fold_corrections=%llu self_contacts=%llu waist_residual_m=%.6f old_waist_residual_m=%.6f shorts_delta_m=%.9f max_frame_shift_m=%.6f pair_old_new_ms=%.3f/%.3f\n",
        name.c_str(),compress?1u:0u,input.mesh[0].hemFolds.size(),input.mesh[0].selfVertices.size(),static_cast<unsigned long long>(oldAcute),static_cast<unsigned long long>(newAcute),
        static_cast<unsigned long long>(current[0].foldContacts),static_cast<unsigned long long>(current[0].selfContacts),residual,oldResidual,shortsDelta,maxFrameShift,milliseconds[1]/329,milliseconds[0]/329);
    CHECK(shortsDelta<1e-5f&&residual<.003f&&newAcute<=oldAcute&&maxFrameShift<.16f);return true;
}
int main(int argc,char** argv) {
    if(argc!=4)return 1;if(!fold_guard())return 2;
    const std::string root=std::string(argv[1])+"/",legs=std::string(argv[2])+"/",armsRoot=std::string(argv[3])+"/";
    for(unsigned gender=0;gender<2;++gender)for(unsigned sleeve=0;sleeve<2;++sleeve) {
        const std::string shirt="simjersey_0_0_"+std::to_string(sleeve)+"_0_1_"+std::to_string(gender),shorts="simshorts_0_0_"+std::to_string(gender);
        for(bool compress:{false,true})if(!pipeline(root+shirt+".cfx",root+shorts+".cfx",armsRoot+shirt+".body",legs+shorts+".body",compress))return 3;
    }
    std::puts("hem revision: curvature, local self contact, irregular timing and complete paired pipeline passed");return 0;
}
