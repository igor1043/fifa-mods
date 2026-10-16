#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "native_particles.h"
#include <chrono>
#include <cstdio>
#include <string>

using namespace cloth_particles;
#define CHECK(condition) do {if(!(condition)){std::fprintf(stderr,"FAIL asset %s line %d: %s\n",filename.c_str(),__LINE__,#condition);return false;}}while(false)
struct Fixture {
    std::vector<Point> bind,current,previous,posed,normals;
    std::vector<NativeEdge> edges[3];
    PointSet bindSet{},currentSet{},previousSet{},posedSet{},normalSet{};
    ConstraintSet groups[3]{};
    unsigned char instance[0x108]{},definition[0x120]{};
    template<class T>void link(unsigned char* base,size_t offset,T* pointer) {
        const uintptr_t address=reinterpret_cast<uintptr_t>(pointer);std::memcpy(base+offset,&address,8);
    }
    void connect() {
        const auto desc=[](std::vector<Point>& v){const auto n=static_cast<uint32_t>(v.size());return PointSet{reinterpret_cast<uintptr_t>(v.data()),n,n,n*16,2};};
        bindSet=desc(bind);currentSet=desc(current);previousSet=desc(previous);posedSet=desc(posed);normalSet=desc(normals);
        link(instance,0,&currentSet);link(instance,8,&previousSet);link(instance,0x10,definition);
        link(instance,0xf0,&posedSet);link(instance,0xf8,&bindSet);link(instance,0x100,&normalSet);link(definition,0x90,&bindSet);link(definition,0x98,&normalSet);
        for(unsigned i=0;i<3;++i) {
            const auto n=static_cast<uint32_t>(edges[i].size());
            groups[i]={reinterpret_cast<uintptr_t>(edges[i].data()),n,(n+3)&~3u};link(definition,0xa0+i*8,&groups[i]);
        }
    }
};
static Fixture pairJersey,pairShorts,bodyShorts[2];
static std::string bodyRoot;
static bool run_span_collision() {
    const std::string filename="cloth_span_crossing_leg";
    const BodyCapsule leg{{0,0,0},{0,1,0},.20f,.08f,.08f};
    Vec a{-.11f,.04f,.01f},b{.11f,.04f,.01f},probe=a;
    CHECK(!project_capsule(probe,leg,.01f,{0,0,1}));probe=b;
    CHECK(!project_capsule(probe,leg,.01f,{0,0,1}));
    CHECK(project_capsule_edge(a,b,1,1,leg,.01f,{0,0,1}));
    const float t=segment_parameter(a,b,{0,-.2f,0},{0,.2f,0});
    probe=lerp(a,b,t);const auto saved=probe;
    project_capsule(probe,leg,.01f,{0,0,1});CHECK(length(probe-saved)<1e-5f);
    a={-.11f,0,.01f};b={.11f,0,.01f};const auto fixed=a;
    for(unsigned i=0;i<8;++i)project_capsule_edge(a,b,0,1,leg,.01f,{0,0,1});
    CHECK(length(a-fixed)==0&&finite(b));
    std::puts("cloth edge contact: endpoints outside, interior crossing and fixed endpoint passed");return true;
}
static bool run_folding_panel() {
    const std::string filename="compressed_material_panel";constexpr unsigned side=17;
    Mesh mesh;mesh.piece=Piece::Jersey;
    for(unsigned y=0;y<side;++y)for(unsigned x=0;x<side;++x) {
        const float u=static_cast<float>(x)/(side-1),v=static_cast<float>(y)/(side-1);
        mesh.rest.push_back({(u-.5f)*.32f,1.5f-v*.32f,.002f*std::sin(u*3.14159265f)});
        mesh.normals.push_back({0,0,1});mesh.mass.push_back(x==0||x==side-1?0.0f:1.0f);
    }
    const auto edge=[&](unsigned a,unsigned b,Family family) {
        mesh.edges.push_back({static_cast<uint16_t>(a),static_cast<uint16_t>(b),length(mesh.rest[a]-mesh.rest[b]),family});
    };
    for(unsigned y=0;y<side;++y)for(unsigned x=0;x<side;++x) {
        const unsigned i=y*side+x;
        if(x+1<side)edge(i,i+1,Family::Structural);
        if(y+1<side)edge(i,i+side,Family::Structural);
        if(x+1<side&&y+1<side){edge(i,i+side+1,Family::Shear);edge(i+1,i+side,Family::Shear);}
        if(x+2<side)edge(i,i+2,Family::Bend);
        if(y+2<side)edge(i,i+side*2,Family::Bend);
    }
    CHECK(mesh.prepare());
    float compression[2]{},curvature[2]{},depth[2]{};
    for(unsigned revision=0;revision<2;++revision) {
        // Homogeneous material panel: chest stabilization has its own
        // factory-shirt regression test and is not a material parameter.
        Config config{};config.shoulderInset=0;config.chestVolume=0;config.torsoInset=0;config.chestStability=0;config.jerseyShrink=0;
        if(revision==0){config.compression=3e-4f;config.bend=1e-4f;config.foldInset=0;config.waistClearance=.010f;config.jerseyFreedom=1;}
        State state;auto target=mesh.rest;
        CHECK(step(mesh,state,target,mesh.normals,1.0f/60,config)==Result::Reset);
        for(unsigned frame=1;frame<=180;++frame) {
            const float shrink=.12f*smooth(static_cast<float>(frame)/60);
            for(size_t i=0;i<target.size();++i){target[i]=mesh.rest[i];target[i].x*=1-shrink;}
            CHECK(step(mesh,state,target,mesh.normals,1.0f/60,config)==Result::Stepped);
        }
        unsigned edges=0;
        for(const auto& e:mesh.edges)if(e.family==Family::Structural){compression[revision]+=std::max(0.0f,1-length(state.position[e.a]-state.position[e.b])/e.rest);++edges;}
        compression[revision]/=static_cast<float>(edges);
        for(unsigned y=1;y+1<side;++y)for(unsigned x=1;x+1<side;++x) {
            const unsigned i=y*side+x;
            const float second=state.position[i-1].z+state.position[i+1].z-2*state.position[i].z;
            curvature[revision]+=second*second;depth[revision]=std::max(depth[revision],std::abs(state.position[i].z-target[i].z));
        }
        curvature[revision]=std::sqrt(curvature[revision]/static_cast<float>((side-2)*(side-2)));
        for(size_t i=0;i<target.size();++i)if(!mesh.mass[i])CHECK(length(state.position[i]-target[i])<1e-6f);
    }
    std::printf("material buckling old/new mean_compression=%.5f/%.5f fold_curvature_m=%.6f/%.6f depth_m=%.5f/%.5f\n",compression[0],compression[1],curvature[0],curvature[1],depth[0],depth[1]);
    // Under the same imposed width, demand visibly non-flat buckling and
    // less material shortening instead of measuring a configuration value.
    CHECK(compression[1]<compression[0]*.9f&&curvature[1]>curvature[0]*2&&depth[1]>.005f);
    return true;
}
static bool run_asset(const std::string& filename) {
    FILE* file=nullptr;CHECK(!fopen_s(&file,filename.c_str(),"rb")&&file);
    char magic[4];uint32_t counts[4];
    CHECK(fread(magic,1,4,file)==4&&!std::memcmp(magic,"CFX2",4));CHECK(fread(counts,4,4,file)==4);
    CHECK(counts[0]>=300&&counts[0]<4096);
    Fixture f;f.bind.resize(counts[0]);f.normals.resize(counts[0]);
    for(uint32_t i=0;i<counts[0];++i) {
        float row[9];CHECK(fread(row,4,9,file)==9);
        f.bind[i]={row[0],row[1],row[2],row[8]};f.normals[i]={row[4],row[5],row[6],row[7]};
    }
    for(unsigned i=0;i<3;++i){f.edges[i].resize(counts[i+1]);CHECK(fread(f.edges[i].data(),8,counts[i+1],file)==counts[i+1]);}
    CHECK(fgetc(file)==EOF);fclose(file);
    f.current=f.previous=f.posed=f.bind;f.connect();
    if(filename.find("simjersey_0_0_0_0_1_0.cfx")!=std::string::npos)pairJersey=f;
    if(filename.find("simshorts_0_0_0.cfx")!=std::string::npos)pairShorts=f;
    for(unsigned g=0;g<2;++g)if(filename.find("simshorts_0_0_"+std::to_string(g)+".cfx")!=std::string::npos)bodyShorts[g]=f;
    auto reader=[](uintptr_t at,void* out,size_t size){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,size,&got)&&got==size;};
    View v;Mesh mesh;CHECK(view(reader,reinterpret_cast<uintptr_t>(f.instance),v));
    const Piece piece=filename.find("simshorts_")!=std::string::npos?Piece::Shorts:Piece::Jersey;
    CHECK(build_mesh(reader,v,mesh,piece));
    size_t fixed=0;for(float m:mesh.mass)if(!m)++fixed;CHECK(fixed>20&&fixed<mesh.rest.size());
    std::vector<Vec> target,normal;targets(v,target,normal);const auto baseline=target,baselineNormal=normal;
    State state;const Config config{};CHECK(step(mesh,state,target,normal,1.0f/60,config)==Result::Reset);
    float shapeChange=0;unsigned shapeCount=0;
    for(size_t i=0;i<target.size();++i)if(mesh.fit[i]>.5f) {
        const Vec shift=state.fitted[i]-target[i];
        shapeChange+=piece==Piece::Jersey?std::abs(target[i].x)-std::abs(state.fitted[i].x):-dot(shift,normal[i]);++shapeCount;
    }
    CHECK(shapeCount>10);
    if(piece==Piece::Jersey)CHECK(shapeChange/static_cast<float>(shapeCount)>.004f);
    else {
        float lift=0;unsigned lifted=0;
        for(size_t i=0;i<target.size();++i)if(mesh.hem[i]>.8f) {
            const Vec up=leg_up(mesh,target,mesh.rest[i].x<0?0:1);
            lift+=dot(state.fitted[i]-target[i],up);++lifted;
        }
        CHECK(lifted>8&&lift/static_cast<float>(lifted)>.008f);
        // Measure the requested 12 -> 15 mm change on both factory shorts,
        // in neutral and rotated poses. Anchors stay at the animated target;
        // the added movement follows each leg, with no lateral widening.
        Config prior=config;prior.shortsHemLift=.012f;
        float maximumAdded=0;unsigned checkedHem=0;
        for(float angle:{0.0f,.78539816f,-.78539816f}) {
            auto posedTarget=target,posedNormal=normal;
            const auto rotate=[&](Vec p){return Vec{p.x,std::cos(angle)*p.y-std::sin(angle)*p.z,std::sin(angle)*p.y+std::cos(angle)*p.z};};
            for(size_t i=0;i<target.size();++i){posedTarget[i]=rotate(target[i]);posedNormal[i]=rotate(normal[i]);}
            State oldState,newState;
            CHECK(step(mesh,oldState,posedTarget,posedNormal,1.0f/60,prior)==Result::Reset);
            CHECK(step(mesh,newState,posedTarget,posedNormal,1.0f/60,config)==Result::Reset);
            for(size_t i=0;i<target.size();++i) {
                const Vec up=leg_up(mesh,posedTarget,mesh.rest[i].x<0?0:1);
                const Vec delta=newState.fitted[i]-oldState.fitted[i];
                CHECK(length(delta-up*(.003f*mesh.hem[i]))<.000001f);
                maximumAdded=std::max(maximumAdded,length(delta));
                if(mesh.hem[i]>.8f){CHECK(dot(delta,up)>.0024f);++checkedHem;}
                if(!mesh.mass[i])CHECK(length(newState.position[i]-posedTarget[i])<1e-6f&&length(delta)<1e-6f);
            }
            CHECK(step(mesh,oldState,posedTarget,posedNormal,1.0f/60,config)==Result::Stepped);
            CHECK(oldState.cachedLift==config.shortsHemLift);
            for(size_t i=0;i<target.size();++i)CHECK(length(oldState.fittedBind[i]-newState.fittedBind[i])<1e-6f);
        }
        CHECK(maximumAdded>.0029f&&maximumAdded<.003001f&&checkedHem>24);
        std::printf("shorts lift %s poses=3 max_added_m=%.6f fixed_points_preserved reload_cache_updated\n",filename.c_str(),maximumAdded);
    }
    if(piece==Piece::Jersey) {
        float chest=0;unsigned countChest=0;
        const Vec pivot=jersey_pivot(mesh,target);
        for(size_t i=0;i<target.size();++i)if(mesh.chest[i]>.5f) {
            const Vec scale=(target[i]-pivot)*(-config.jerseyShrink*mesh.freeFit[i]);
            chest+=dot(state.fitted[i]-target[i]-scale,normal[i])+config.torsoInset*mesh.torso[i];++countChest;
        }
        CHECK(countChest>3&&chest/static_cast<float>(countChest)>.0005f);
        for(size_t i=0;i<target.size();++i)if(mesh.waist[i]>.6f)
            CHECK(std::abs(state.fitted[i].x-target[i].x)<=config.torsoInset+std::abs(target[i].x-pivot.x)*config.jerseyShrink+.00002f);
    }
    const auto animate=[&](float t) {
        const float angle=.18f*std::sin(t*3),cs=std::cos(angle),sn=std::sin(angle);
        for(size_t i=0;i<target.size();++i) {
            const Vec p=baseline[i];const float sleeve=clamp((std::abs(p.x)-.12f)/.3f,0,1);
            target[i]={cs*p.x+sn*p.z+.3f*t,p.y+.012f*std::sin(t*6),-sn*p.x+cs*p.z+.04f*sleeve*std::sin(t*4)};
            const Vec n=baselineNormal[i];normal[i]=unit({cs*n.x+sn*n.z,n.y,-sn*n.x+cs*n.z});
        }
    };
    float maxOffset=0,minClearance=1,response=0;double milliseconds=0;
    for(unsigned frame=1;frame<=180;++frame) {
        animate(static_cast<float>(frame)/60);
        const auto start=std::chrono::steady_clock::now();
        CHECK(step(mesh,state,target,normal,1.0f/60,config)==Result::Stepped);
        milliseconds+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        for(size_t i=0;i<target.size();++i) {
            CHECK(finite(state.position[i])&&finite(state.velocity[i]));
            const float displacement=length(state.position[i]-target[i]);
            if(!mesh.mass[i]){CHECK(displacement<1e-5f);continue;}
            maxOffset=std::max(maxOffset,displacement);minClearance=std::min(minClearance,dot(state.position[i]-state.fitted[i],normal[i]));
            response=std::max(response,length(state.position[i]-(target[i]+normal[i]*config.clearance)));
            CHECK(displacement<.16f);CHECK(length(state.velocity[i])<6.01f);
        }
    }
    CHECK(minClearance>(piece==Piece::Shorts?-.015f:-config.collisionInset-config.foldInset-.001f)&&response>.0005f);
    const auto reference60=state.position;float maxRateRms=0;
    // F7 must not leave static constraints from an earlier configuration.
    State cached=state,recomputed=state;recomputed.constraintsCached=false;
    Config changed=config;changed.pin*=1.1f;changed.chestStability=.5f;
    CHECK(step(mesh,cached,target,normal,1.0f/60,changed)==Result::Stepped);
    CHECK(step(mesh,recomputed,target,normal,1.0f/60,changed)==Result::Stepped);
    for(size_t i=0;i<target.size();++i)CHECK(length(cached.position[i]-recomputed.position[i])<1e-7f);
    for(unsigned rate:{30u,120u}) {
        animate(0);State rateState;
        CHECK(step(mesh,rateState,target,normal,0,config)==Result::Paused&&!rateState.ready);
        CHECK(step(mesh,rateState,target,normal,1.0f/static_cast<float>(rate),config)==Result::Reset);
        for(unsigned frame=1;frame<=rate*3;++frame) {
            animate(static_cast<float>(frame)/static_cast<float>(rate));
            CHECK(step(mesh,rateState,target,normal,1.0f/static_cast<float>(rate),config)==Result::Stepped);
        }
        float squared=0;
        for(size_t i=0;i<target.size();++i){const Vec d=rateState.position[i]-reference60[i];squared+=dot(d,d);}
        const float rms=std::sqrt(squared/static_cast<float>(target.size()));
        CHECK(rms<.015f);maxRateRms=std::max(maxRateRms,rms);
    }
    const auto paused=state.position;CHECK(step(mesh,state,target,normal,0,config)==Result::Paused);
    CHECK(!std::memcmp(paused.data(),state.position.data(),paused.size()*sizeof(Vec)));
    for(auto& p:target)p.x+=10;CHECK(step(mesh,state,target,normal,1.0f/60,config)==Result::Reset);
    std::vector<Point> out,prev;CHECK(output(v,state,1.0f/60,out,prev));
    for(size_t i=0;i<out.size();++i)CHECK(out[i].w==f.current[i].w&&prev[i].w==f.previous[i].w);
    f.currentSet.capacity=0;CHECK(!view(reader,reinterpret_cast<uintptr_t>(f.instance),v));
    std::printf("%s points=%zu pins=%zu max_offset_m=%.5f min_surface_m=%.5f rate_rms_m=%.5f cpu_ms_per_garment=%.3f mean_fit_m=%.5f\n",filename.c_str(),mesh.rest.size(),fixed,maxOffset,minClearance,maxRateRms,milliseconds/180,shapeChange/static_cast<float>(shapeCount));
    return true;
}
static bool run_contact_pair() {
    const std::string filename="animated_jersey_shorts_pair";
    CHECK(!pairJersey.bind.empty()&&!pairShorts.bind.empty());
    pairJersey.connect();pairShorts.connect();
    auto reader=[](uintptr_t at,void* out,size_t size){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,size,&got)&&got==size;};
    View views[2];Mesh meshes[2];State states[2];std::vector<Vec> positions[2],normals[2],base[2],baseNormals[2];
    Fixture* fixtures[]={&pairJersey,&pairShorts};const Config config{};
    for(unsigned g=0;g<2;++g) {
        CHECK(view(reader,reinterpret_cast<uintptr_t>(fixtures[g]->instance),views[g]));
        CHECK(build_mesh(reader,views[g],meshes[g],g==0?Piece::Jersey:Piece::Shorts));
        targets(views[g],positions[g],normals[g]);base[g]=positions[g];baseNormals[g]=normals[g];
        CHECK(step(meshes[g],states[g],positions[g],normals[g],1.0f/60,config)==Result::Reset);
    }
    // Reproduce a shirt already penetrating the waistband, then run a moving
    // hip and alternating legs with a prior-frame contact surface as well.
    for(size_t i=0;i<states[0].position.size();++i)if(meshes[0].waist[i]>.3f)states[0].position[i]-=normals[0][i]*.02f;
    float maximumResidual=0,shortsResponse=0;ContactSurface prior;double pairMilliseconds=0;
    for(unsigned frame=1;frame<=240;++frame) {
        const float t=static_cast<float>(frame)/60,angle=.35f*std::sin(t*2),cs=std::cos(angle),sn=std::sin(angle);
        for(unsigned g=0;g<2;++g)for(size_t i=0;i<base[g].size();++i) {
            const Vec p=base[g][i],n=baseNormals[g][i];
            const float leg=g==1?smooth((.98f-p.y)/.25f)*(p.x<0?-1.0f:1.0f)*std::sin(t*5):0;
            positions[g][i]={cs*p.x+sn*p.z+.4f*t,p.y+.012f*std::sin(t*7),-sn*p.x+cs*p.z+leg*.07f};
            normals[g][i]=unit({cs*n.x+sn*n.z,n.y,-sn*n.x+cs*n.z});
        }
        const auto start=std::chrono::steady_clock::now();
        CHECK(step(meshes[1],states[1],positions[1],normals[1],1.0f/60,config)==Result::Stepped);
        ContactSurface surface;
        for(auto i:meshes[1].waistSamples)surface.samples.push_back({states[1].position[i],contact_normal(meshes[1],states[1].position,normals[1],i)});
        surface.prepare();
        const auto& used=frame%2==0&&!prior.samples.empty()?prior:surface;
        CHECK(step(meshes[0],states[0],positions[0],normals[0],1.0f/60,config,&used)==Result::Stepped);
        pairMilliseconds+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        for(size_t i=0;i<states[0].position.size();++i) {
            CHECK(finite(states[0].position[i]));
            if(meshes[0].waist[i]>.3f) {
                Vec probe=states[0].position[i];project_contact(probe,normals[0][i],&used,config);
                maximumResidual=std::max(maximumResidual,length(probe-states[0].position[i]));
            }
        }
        for(size_t i=0;i<states[1].position.size();++i)if(meshes[1].fit[i]>.5f)
            shortsResponse=std::max(shortsResponse,length(states[1].position[i]-states[1].fitted[i]));
        prior=std::move(surface);
    }
    CHECK(states[0].contacts>100&&maximumResidual<.003f&&shortsResponse>.004f);
    std::printf("animated garment pair contacts=%llu max_residual_m=%.6f shorts_dynamic_offset_m=%.6f pair_cpu_ms=%.3f\n",
        static_cast<unsigned long long>(states[0].contacts),maximumResidual,shortsResponse,pairMilliseconds/240);
    return true;
}
static bool run_contact_grid() {
    const std::string filename="contact_grid_equivalence_and_cost";
    auto& f=pairShorts;f.connect();
    auto reader=[](uintptr_t at,void* out,size_t size){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,size,&got)&&got==size;};
    View v;Mesh mesh;CHECK(view(reader,reinterpret_cast<uintptr_t>(f.instance),v)&&build_mesh(reader,v,mesh,Piece::Shorts));
    ContactSurface indexed;
    for(auto i:mesh.waistSamples)indexed.samples.push_back({mesh.rest[i],mesh.normals[i]});
    indexed.prepare();CHECK(indexed.indexed);auto brute=indexed;brute.indexed=false;
    std::vector<ContactSample> queries;const Config config{};size_t visits=0;float error=0;
    for(unsigned i=0;i<4096;++i) {
        const auto& s=indexed.samples[i%indexed.samples.size()];
        const Vec offset{static_cast<float>(static_cast<int>(i*37%101)-50)*.002f,
            static_cast<float>(static_cast<int>(i*19%101)-50)*.0015f,static_cast<float>(static_cast<int>(i*11%101)-50)*.002f};
        queries.push_back({s.position+offset,s.normal});
        const auto a=contact_plane(queries.back().position,s.normal,&indexed,config,&visits),b=contact_plane(queries.back().position,s.normal,&brute,config);
        CHECK(a.valid==b.valid);
        if(a.valid)error=std::max(error,std::max(length(a.position-b.position),length(a.normal-b.normal)));
    }
    CHECK(error<1e-6f&&visits<queries.size()*indexed.samples.size()*3/4);
    ContactSurface large=indexed;large.indexed=false;
    for(unsigned copy=1;copy<3;++copy)for(auto sample:indexed.samples){sample.position.y+=static_cast<float>(copy)*.001f;large.samples.push_back(sample);}
    large.prepare();CHECK(large.indexed&&large.packets.empty()&&!large.nodes.empty());auto largeBrute=large;largeBrute.indexed=false;
    for(size_t i=0;i<512;++i) {
        const auto& q=queries[i];const auto a=contact_plane(q.position,q.normal,&large,config),b=contact_plane(q.position,q.normal,&largeBrute,config);
        CHECK(a.valid==b.valid);if(a.valid)CHECK(length(a.position-b.position)<1e-6f&&length(a.normal-b.normal)<1e-6f);
    }
    CHECK(!contact_plane({1e20f,1e20f,1e20f},{0,0,1},&indexed,config).valid);
    double milliseconds[2]{};float checksum=0;
    for(unsigned mode=0;mode<2;++mode) {
        const auto start=std::chrono::steady_clock::now();const auto* surface=mode?&brute:&indexed;
        for(unsigned repeat=0;repeat<8;++repeat)for(const auto& q:queries) {
            const auto p=contact_plane(q.position,q.normal,surface,config);if(p.valid)checksum+=p.position.z;
        }
        milliseconds[mode]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    }
    std::printf("contact search algorithm=simd4_kdtree samples=%zu queries=%zu mean_scalar_candidates=%.2f brute_candidates=%zu optimized_ms=%.3f brute_ms=%.3f plane_error_m=%.9f checksum=%.3f\n",
        indexed.samples.size(),queries.size(),static_cast<double>(visits)/queries.size(),indexed.samples.size(),milliseconds[0],milliseconds[1],error,checksum);
    return true;
}
static bool run_waist_span() {
    const std::string filename="shirt_span_crossing_shorts";const Config config{};constexpr float radius=.13f;
    ContactSurface surface;
    for(unsigned i=0;i<64;++i){const float a=6.2831853f*static_cast<float>(i)/64;const Vec n{std::sin(a),0,std::cos(a)};surface.samples.push_back({n*radius+Vec{0,1,0},n});}
    surface.prepare();Mesh mesh;mesh.piece=Piece::Jersey;mesh.mass={1,1,0};mesh.waist={1,1,0};mesh.waistEdges={{0,1,.08f,Family::Structural}};
    const Vec left{std::sin(-.30f),0,std::cos(-.30f)},right{std::sin(.30f),0,std::cos(.30f)};
    std::vector<Vec> normals{left,right,{0,1,0}};State state;
    state.position={left*(radius+config.waistClearance)+Vec{0,1,0},right*(radius+config.waistClearance)+Vec{0,1,0},{0,2,0}};state.velocity.resize(3);
    const float before=((state.position[0]+state.position[1])*.5f).z;
    finish_waist_contact(mesh,state,normals,&surface,config);
    const float after=((state.position[0]+state.position[1])*.5f).z;
    CHECK(before<radius+config.waistClearance-.004f&&after>radius+config.waistClearance-.001f&&state.position[2].y==2);
    std::printf("waist span gap_before_m=%.6f gap_after_m=%.6f contacts=%llu\n",before-radius,after-radius,static_cast<unsigned long long>(state.contacts));return true;
}
static bool run_body_contact(unsigned gender) {
    const std::string filename="native_leg_capsules_gender_"+std::to_string(gender);
    auto& f=bodyShorts[gender];CHECK(!f.bind.empty());f.connect();
    FILE* file=nullptr;CHECK(!fopen_s(&file,(bodyRoot+"simshorts_0_0_"+std::to_string(gender)+".body").c_str(),"rb")&&file);
    char magic[4];uint32_t n;CHECK(fread(magic,1,4,file)==4&&!std::memcmp(magic,"BDX4",4)&&fread(&n,4,1,file)==1);
    std::vector<NativeCapsule> raw[2];
    for(uint32_t k=0;k<n;++k){uint32_t kind;NativeCapsule shape;CHECK(fread(&kind,4,1,file)==1&&kind>=1&&kind<=2);CHECK(fread(&shape,64,1,file)==1);raw[kind-1].push_back(shape);}
    fclose(file);ColliderSet groups[2];
    for(unsigned k=0;k<2;++k){const auto count=static_cast<uint32_t>(raw[k].size());groups[k]={count,(count+3)&~3u,reinterpret_cast<uintptr_t>(raw[k].data())};f.link(f.instance,0x40+k*8,&groups[k]);}
    auto reader=[](uintptr_t at,void* out,size_t size){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(at),out,size,&got)&&got==size;};
    View v;Mesh mesh;CHECK(view(reader,reinterpret_cast<uintptr_t>(f.instance),v)&&build_mesh(reader,v,mesh,Piece::Shorts));
    std::vector<BodyCapsule> initial,body;CHECK(body_capsules(reader,reinterpret_cast<uintptr_t>(f.instance),initial)&&initial.size()==6);
    size_t thigh=initial.size();
    for(size_t i=0;i<initial.size();++i)if(initial[i].center.x>0&&initial[i].center.y>.6f){thigh=i;break;}
    CHECK(thigh<initial.size());
    std::vector<Vec> target,normal;targets(v,target,normal);const auto base=target,baseNormal=normal;
    State state;const Config config{};CHECK(step(mesh,state,target,normal,1.0f/60,config,nullptr,&initial)==Result::Reset);
    float residual=0,spanResidual=0;double milliseconds=0;unsigned injections=0,worstFrame=0;Edge worst{};
    for(unsigned frame=1;frame<=240;++frame) {
        const float time=static_cast<float>(frame)/60,yaw=.3f*std::sin(time*1.5f),cy=std::cos(yaw),sy=std::sin(yaw);
        const auto pose=[&](Vec p,bool direction) {
            const float sign=p.x<0?-1.0f:1.0f;
            const float angle=.85f*sign*std::sin(time*7.5f),cs=std::cos(angle),sn=std::sin(angle);
            // All collider and cloth points use the same animated leg space.
            const Vec origin=direction?Vec{}:Vec{sign*.105f,.98f,0};
            Vec q=p-origin;q={q.x,cs*q.y-sn*q.z,sn*q.y+cs*q.z};q+=origin;
            q={cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z};if(!direction)q.x+=time*.35f;
            return q;
        };
        for(size_t i=0;i<target.size();++i) {
            const bool leg=base[i].y<.95f;
            target[i]=leg?pose(base[i],false):Vec{cy*base[i].x+sy*base[i].z+time*.35f,base[i].y,-sy*base[i].x+cy*base[i].z};
            const float sign=base[i].x<0?-1.0f:1.0f,angle=leg?.85f*sign*std::sin(time*7.5f):0,cs=std::cos(angle),sn=std::sin(angle);
            const Vec q{baseNormal[i].x,cs*baseNormal[i].y-sn*baseNormal[i].z,sn*baseNormal[i].y+cs*baseNormal[i].z};
            normal[i]={cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z};
        }
        body=initial;
        for(size_t k=0;k<body.size();++k) {
            const float sign=initial[k].center.x<0?-1.0f:1.0f,angle=.85f*sign*std::sin(time*7.5f),cs=std::cos(angle),sn=std::sin(angle);
            const Vec axis=initial[k].axis,q{axis.x,cs*axis.y-sn*axis.z,sn*axis.y+cs*axis.z};
            body[k].center=pose(initial[k].center,false);body[k].axis={cy*q.x+sy*q.z,q.y,-sy*q.x+cy*q.z};
        }
        if(frame==60||frame==120) {
            const auto& c=body[thigh];
            for(size_t i=0;i<state.position.size();++i)if(mesh.mass[i]&&base[i].x>0&&std::abs(base[i].y-initial[thigh].center.y)<.06f) {
                state.position[i]=c.center+Vec{c.radiusA*.4f,0,0};++injections;break;
            }
        }
        const auto start=std::chrono::steady_clock::now();
        CHECK(step(mesh,state,target,normal,1.0f/60,config,nullptr,&body)==Result::Stepped);
        milliseconds+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        for(size_t i=0;i<target.size();++i)if(mesh.mass[i]) {
            CHECK(finite(state.position[i]));
            for(const auto& capsule:body){Vec p=state.position[i];project_capsule(p,capsule,config.bodyMargin,normal[i]);residual=std::max(residual,length(p-state.position[i]));}
        }
        for(const auto& e:mesh.collisionEdges)for(const auto& capsule:body) {
            Vec a=state.position[e.a],b=state.position[e.b];
            project_capsule_edge(a,b,mesh.mass[e.a],mesh.mass[e.b],capsule,config.bodyMargin,normal[e.a]+normal[e.b]);
            const float left=std::max(length(a-state.position[e.a]),length(b-state.position[e.b]));
            if(left>spanResidual){spanResidual=left;worstFrame=frame;worst=e;}
        }
    }
    groups[0].count=1000;CHECK(!body_capsules(reader,reinterpret_cast<uintptr_t>(f.instance),body));
    std::printf("native leg collision gender=%u capsules=%zu point_contacts=%llu edge_contacts=%llu max_residual_m=%.6f span_residual_m=%.6f cpu_ms=%.3f\n",gender,initial.size(),
        static_cast<unsigned long long>(state.bodyContacts),static_cast<unsigned long long>(state.edgeContacts),residual,spanResidual,milliseconds/240);
    std::printf("worst span frame=%u indices=%u/%u inverse_mass=%.1f/%.1f rest_y=%.3f/%.3f\n",worstFrame,worst.a,worst.b,mesh.mass[worst.a],mesh.mass[worst.b],mesh.rest[worst.a].y,mesh.rest[worst.b].y);
    CHECK(injections==2&&state.bodyContacts+state.edgeContacts>0&&residual<.002f&&spanResidual<.002f);
    return true;
}
int main(int argc,char** argv) {
    if(argc!=3){std::fputs("Usage: test_particle_assets cloth_fixture_directory body_fixture_directory\n",stderr);return 1;}
    bodyRoot=std::string(argv[2])+"\\";
    const std::string root=std::string(argv[1])+"\\";WIN32_FIND_DATAA row{};
    HANDLE search=FindFirstFileA((root+"*.cfx").c_str(),&row);if(search==INVALID_HANDLE_VALUE)return 2;
    unsigned count=0;bool ok=true;
    do{if(!(row.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)){ok=run_asset(root+row.cFileName);++count;if(!ok)break;}}while(FindNextFileA(search,&row));
    FindClose(search);if(!ok||count!=18)return 3;
    if(!run_contact_pair())return 4;
    if(!run_contact_grid()||!run_waist_span())return 7;
    if(!run_span_collision()||!run_folding_panel())return 6;
    if(!run_body_contact(0)||!run_body_contact(1))return 5;
    std::puts("18 factory RX3 assets: native binding, cloth response, finite bounds, pins, contact, pause, teleport and inverse masses passed");return 0;
}
