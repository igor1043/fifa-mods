#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <queue>
#include <utility>
#include <vector>
#include <xmmintrin.h>

// Independently implemented CPU XPBD solver. The PES package is a behavioral
// reference; its copyrighted shader/DLL are not compiled, copied or loaded.
namespace cloth_particles {
struct Vec {
    float x=0,y=0,z=0;
    Vec operator+(Vec b)const{return {x+b.x,y+b.y,z+b.z};}
    Vec operator-(Vec b)const{return {x-b.x,y-b.y,z-b.z};}
    Vec operator-()const{return {-x,-y,-z};}
    Vec operator*(float s)const{return {x*s,y*s,z*s};}
    Vec operator/(float s)const{return *this*(1/s);}
    Vec& operator+=(Vec b){*this=*this+b;return *this;}
    Vec& operator-=(Vec b){*this=*this-b;return *this;}
};
inline float dot(Vec a,Vec b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline Vec cross(Vec a,Vec b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
inline float length(Vec a){return std::sqrt(dot(a,a));}
inline bool finite(Vec a){return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
inline Vec unit(Vec a){const float l=length(a);return l>1e-8f?a/l:Vec{0,1,0};}
inline Vec lerp(Vec a,Vec b,float t){return a+(b-a)*t;}
inline float clamp(float v,float low,float high){return std::max(low,std::min(high,v));}
inline float smooth(float v){v=clamp(v,0,1);return v*v*(3-2*v);}
inline Vec capped(Vec v,float limit){const float l=length(v);return l>limit?v*(limit/l):v;}
enum class Family : uint8_t { Structural,Shear,Bend };
enum class Piece : uint8_t { Generic,Jersey,Shorts };
struct Edge {uint16_t a=0,b=0;float rest=0;Family family=Family::Structural;};
struct Config {
    float stretch=1e-7f,compression=1e-6f,bend=4e-4f;
    float pin=4e-5f,damping=2.0f,airDrag=3.0f;
    float clearance=0.004f,collisionInset=0.002f,friction=0.025f;
    float maxDistance=0.12f,maxSpeed=6.0f,restAdaptation=0.12f;
    float wind=0.0f,motion=0.6f;
    float shoulderInset=.012f,shortsInset=.002f,shortsBodyInset=.008f;
    float shortsBend=.0006f,shortsPinScale=2.5f,shortsGravity=1.05f;
    float waistClearance=.006f,contactRadius=.10f,bodyMargin=.010f;
    float chestVolume=.001f,hemFreedom=1.7f,hemDamping=.75f;
    float foldInset=.010f,shortsHemLift=.015f,jerseyFreedom=3.0f;
    float torsoInset=.003f,chestStability=.88f,sleeveInset=.001f,armMargin=.004f;
    float jerseyShrink=.010f,chestMax=.022f;
    unsigned frequency=120,iterations=1;
};
inline float safe(float v,float low,float high,float fallback){return std::isfinite(v)?clamp(v,low,high):fallback;}
inline Config validate(Config c) {
    const Config d{};
    c.stretch=safe(c.stretch,1e-9f,1e-4f,d.stretch);
    c.compression=safe(c.compression,1e-7f,0.005f,d.compression);
    c.bend=safe(c.bend,1e-7f,0.01f,d.bend);
    c.pin=safe(c.pin,1e-6f,0.001f,d.pin);
    c.damping=safe(c.damping,0.3f,10.0f,d.damping);
    c.airDrag=safe(c.airDrag,0,10.0f,d.airDrag);
    c.clearance=safe(c.clearance,0,0.012f,d.clearance);
    c.collisionInset=safe(c.collisionInset,0.0005f,0.006f,d.collisionInset);
    c.friction=safe(c.friction,0,0.25f,d.friction);
    c.maxDistance=safe(c.maxDistance,0.025f,0.18f,d.maxDistance);
    c.maxSpeed=safe(c.maxSpeed,1,12,d.maxSpeed);
    c.restAdaptation=safe(c.restAdaptation,0,0.7f,d.restAdaptation);
    c.wind=safe(c.wind,0,2,d.wind);c.motion=safe(c.motion,0,1,d.motion);
    c.shoulderInset=safe(c.shoulderInset,0,.020f,d.shoulderInset);
    c.shortsInset=safe(c.shortsInset,0,.025f,d.shortsInset);
    c.shortsBodyInset=safe(c.shortsBodyInset,.004f,.025f,d.shortsBodyInset);
    c.shortsBend=safe(c.shortsBend,1e-5f,.005f,d.shortsBend);
    c.shortsPinScale=safe(c.shortsPinScale,1,5,d.shortsPinScale);
    c.shortsGravity=safe(c.shortsGravity,1,1.6f,d.shortsGravity);
    c.waistClearance=safe(c.waistClearance,.002f,.012f,d.waistClearance);
    c.contactRadius=safe(c.contactRadius,.035f,.10f,d.contactRadius);
    c.bodyMargin=safe(c.bodyMargin,.003f,.018f,d.bodyMargin);
    c.chestVolume=safe(c.chestVolume,0,.015f,d.chestVolume);
    c.hemFreedom=safe(c.hemFreedom,1,3,d.hemFreedom);
    c.hemDamping=safe(c.hemDamping,.5f,1,d.hemDamping);
    c.foldInset=safe(c.foldInset,0,.015f,d.foldInset);
    c.shortsHemLift=safe(c.shortsHemLift,0,.025f,d.shortsHemLift);
    c.jerseyFreedom=safe(c.jerseyFreedom,1,5,d.jerseyFreedom);
    c.torsoInset=safe(c.torsoInset,0,.006f,d.torsoInset);
    c.chestStability=safe(c.chestStability,0,.9f,d.chestStability);
    c.sleeveInset=safe(c.sleeveInset,0,.003f,d.sleeveInset);
    c.armMargin=safe(c.armMargin,.002f,.008f,d.armMargin);
    c.jerseyShrink=safe(c.jerseyShrink,0,.025f,d.jerseyShrink);
    c.chestMax=safe(c.chestMax,.010f,.050f,d.chestMax);
    if(c.frequency<90||c.frequency>300)c.frequency=d.frequency;
    if(c.iterations<1||c.iterations>4)c.iterations=d.iterations;
    return c;
}
struct ArmSection {std::vector<uint16_t> samples;float radius=0;};
struct FoldStencil {uint16_t a=0,center=0,b=0;};
struct Mesh {
    Piece piece=Piece::Generic;
    std::vector<Vec> rest,normals;
    std::vector<float> mass,distance;
    std::vector<float> fit,waist,chest,hem,torso,sleeve,freeFit;
    std::vector<uint16_t> waistSamples,leftShoulder,rightShoulder;
    std::vector<uint16_t> legTop[2],legHem[2];
    std::vector<Edge> collisionEdges;
    std::vector<Edge> waistEdges;
    std::vector<std::array<uint16_t,2>> contactBasis;
    std::vector<uint16_t> sleeveVertices;
    std::vector<FoldStencil> hemFolds;
    std::vector<uint16_t> selfVertices;
    std::vector<std::vector<uint16_t>> selfExclude;
    std::vector<ArmSection> armSections[2];
    bool longSleeves=false;
    std::vector<Edge> edges;
    bool prepare() {
        const size_t count=rest.size();
        if(count<3||count>4096||normals.size()!=count||mass.size()!=count||edges.empty()||edges.size()>40000)return false;
        size_t fixed=0;
        for(size_t i=0;i<count;++i) {
            if(!finite(rest[i])||!finite(normals[i])||!std::isfinite(mass[i])||mass[i]<0)return false;
            normals[i]=unit(normals[i]);
            // Factory mass scales vary radically by garment. XPBD's compliance
            // uses a consistent unit mass while preserving the fixed mask.
            if(mass[i]==0)++fixed;else mass[i]=1;
        }
        if(!fixed||fixed==count)return false;
        std::vector<std::vector<std::pair<uint16_t,float>>> neighbors(count);
        for(const auto& e:edges) {
            if(e.a>=count||e.b>=count||e.a==e.b||!std::isfinite(e.rest)||e.rest<1e-6f||e.rest>2)return false;
            if(e.family!=Family::Bend) {
                neighbors[e.a].push_back({e.b,e.rest});neighbors[e.b].push_back({e.a,e.rest});
            }
        }
        distance.assign(count,std::numeric_limits<float>::infinity());
        using Item=std::pair<float,uint16_t>;
        std::priority_queue<Item,std::vector<Item>,std::greater<Item>> queue;
        for(size_t i=0;i<count;++i)if(!mass[i]){distance[i]=0;queue.push({0.0f,static_cast<uint16_t>(i)});}
        while(!queue.empty()) {
            const auto row=queue.top();queue.pop();if(row.first!=distance[row.second])continue;
            for(const auto& edge:neighbors[row.second]) {
                const float next=row.first+edge.second;
                if(next<distance[edge.first]){distance[edge.first]=next;queue.push({next,edge.first});}
            }
        }
        for(auto& d:distance)if(!std::isfinite(d))d=0.35f;
        float top=-100,bottom=100;
        for(Vec p:rest){top=std::max(top,p.y);bottom=std::min(bottom,p.y);}
        fit.assign(count,0);waist.assign(count,0);chest.assign(count,0);hem.assign(count,0);
        torso.assign(count,0);sleeve.assign(count,0);longSleeves=false;
        freeFit.assign(count,0);waistEdges.clear();contactBasis.assign(count,{UINT16_MAX,UINT16_MAX});
        waistSamples.clear();leftShoulder.clear();rightShoulder.clear();collisionEdges.clear();sleeveVertices.clear();
        hemFolds.clear();selfVertices.clear();selfExclude.clear();
        for(unsigned leg=0;leg<2;++leg){legTop[leg].clear();legHem[leg].clear();armSections[leg].clear();}
        for(size_t i=0;i<count;++i) {
            const Vec p=rest[i];const auto index=static_cast<uint16_t>(i);
            if(piece==Piece::Shorts) {
                // Preserve the waistband and crotch anchors. Let the lower
                // shell settle closer to the leg instead of keeping a hoop.
                fit[i]=mass[i]?smooth((top-p.y-.06f)/.20f)*std::sqrt(normals[i].x*normals[i].x+normals[i].z*normals[i].z):0;
                hem[i]=mass[i]?(1-smooth((p.y-bottom)/.15f)):0;
                const unsigned leg=p.x<0?0:1;
                if(p.y>top-.10f)legTop[leg].push_back(index);
                if(p.y<bottom+.035f)legHem[leg].push_back(index);
                if(p.y>top-.25f)waistSamples.push_back(index);
            }else if(piece==Piece::Jersey) {
                const float x=std::abs(p.x);
                freeFit[i]=mass[i]?smooth(distance[i]/.07f):0;
                fit[i]=mass[i]?smooth((x-.105f)/.09f)*(1-smooth((x-.26f)/.10f))*
                    smooth((p.y-(top-.22f))/.10f)*(1-smooth((p.y-(top-.055f))/.05f)):0;
                waist[i]=smooth(((top-.43f)-p.y)/.10f);
                hem[i]=mass[i]?(1-smooth((p.y-bottom)/.18f)):0;
                torso[i]=mass[i]?(1-smooth((x-.185f)/.065f))*smooth((top-.10f-p.y)/.17f):0;
                sleeve[i]=smooth((x-.19f)/.07f);
                if(x>.45f)longSleeves=true;
                chest[i]=mass[i]&&p.z>0?smooth((normals[i].z-.1f)/.6f)*(1-smooth((x-.10f)/.075f))*
                    smooth((p.y-(top-.40f))/.13f)*(1-smooth((p.y-(top-.17f))/.09f)):0;
                if(p.y>top-.13f&&x>.045f&&x<.145f) {
                    (p.x<0?leftShoulder:rightShoulder).push_back(index);
                }
            }
        }
        // Protect the spans between particles as well as the particles.
        // Bend springs cross the fabric and are not surface edges.
        if(piece==Piece::Shorts) {
            // A local surface basis tracks the simulated shorts rather than
            // publishing the normals of their undeformed animated reference.
            for(auto i:waistSamples) {
                float best=.20f;
                for(size_t a=0;a<neighbors[i].size();++a)for(size_t b=a+1;b<neighbors[i].size();++b) {
                    const auto ia=neighbors[i][a].first,ib=neighbors[i][b].first;
                    const Vec da=rest[ia]-rest[i],db=rest[ib]-rest[i],n=cross(da,db);
                    const float orientation=dot(n,normals[i]);
                    const float score=orientation*orientation/(dot(da,da)*dot(db,db)+1e-16f);
                    if(score>best){best=score;contactBasis[i]=orientation>0?std::array<uint16_t,2>{ia,ib}:std::array<uint16_t,2>{ib,ia};}
                }
            }
            for(const auto& e:edges)if(e.family!=Family::Bend&&(mass[e.a]||mass[e.b]))collisionEdges.push_back(e);
            const auto key=[](const Edge& e){return (static_cast<uint32_t>(std::min(e.a,e.b))<<16)|std::max(e.a,e.b);};
            std::sort(collisionEdges.begin(),collisionEdges.end(),[&](const Edge& a,const Edge& b){return key(a)<key(b);});
            collisionEdges.erase(std::unique(collisionEdges.begin(),collisionEdges.end(),[&](const Edge& a,const Edge& b){return key(a)==key(b);}),collisionEdges.end());
        }else if(piece==Piece::Jersey) {
            // Use actual structural neighbors, never guessed surface triangles.
            // Opposing material directions give a local arc/chord safeguard
            // without making ordinary folds return to a flat reference shape.
            std::vector<std::vector<uint16_t>> structural(count);
            for(const auto& e:edges)if(e.family==Family::Structural) {
                structural[e.a].push_back(e.b);structural[e.b].push_back(e.a);
            }
            selfExclude.resize(count);
            for(size_t i=0;i<count;++i)if(mass[i]&&hem[i]>.05f&&sleeve[i]<.25f) {
                selfVertices.push_back(static_cast<uint16_t>(i));
                auto& excluded=selfExclude[i];excluded.push_back(static_cast<uint16_t>(i));
                for(const auto& a:neighbors[i]) {
                    excluded.push_back(a.first);
                    for(const auto& b:neighbors[a.first])excluded.push_back(b.first);
                }
                std::sort(excluded.begin(),excluded.end());excluded.erase(std::unique(excluded.begin(),excluded.end()),excluded.end());
                const auto& adjacent=structural[i];
                for(size_t a=0;a<adjacent.size();++a) {
                    uint16_t best=UINT16_MAX;float opposition=-.70f;
                    const Vec da=rest[adjacent[a]]-rest[i];const float la=length(da);
                    if(la<.005f)continue;
                    for(size_t b=0;b<adjacent.size();++b)if(a!=b) {
                        const Vec db=rest[adjacent[b]]-rest[i];const float lb=length(db);
                        if(lb<la*.5f||lb>la*2)continue;
                        const float aligned=dot(da,db)/(la*lb);
                        if(aligned<opposition){opposition=aligned;best=adjacent[b];}
                    }
                    if(best!=UINT16_MAX&&adjacent[a]<best)hemFolds.push_back({adjacent[a],static_cast<uint16_t>(i),best});
                }
            }
            for(const auto& e:edges)if(e.family==Family::Structural&&mass[e.a]&&mass[e.b]&&
                std::min(waist[e.a],waist[e.b])>.3f&&e.rest>.030f)waistEdges.push_back(e);
            for(size_t i=0;i<count;++i)if(mass[i]&&sleeve[i]>.25f)sleeveVertices.push_back(static_cast<uint16_t>(i));
            for(const auto& e:edges)if(e.family==Family::Structural&&(mass[e.a]||mass[e.b])&&
                std::min(sleeve[e.a],sleeve[e.b])>.25f)collisionEdges.push_back(e);
            // Native long-sleeve assets often have no arm colliders. Sections
            // of the animated reference sleeve provide a conservative proxy,
            // independent of the simulated points (no feedback inflation).
            for(unsigned side=0;side<2;++side)for(unsigned band=0;band<6;++band) {
                const float center=.32f+.09f*static_cast<float>(band);ArmSection section;Vec mean{};
                const Vec axis{side==0?-.84f:.84f,-.543f,0};
                for(size_t i=0;i<count;++i)if((rest[i].x<0?0u:1u)==side&&sleeve[i]>.25f) {
                    const float along=std::abs(rest[i].x)*.84f+(top-rest[i].y)*.543f;
                    if(std::abs(along-center)<.045f){section.samples.push_back(static_cast<uint16_t>(i));mean+=rest[i];}
                }
                if(section.samples.size()<8)continue;
                mean=mean/static_cast<float>(section.samples.size());float radius=0;
                for(auto i:section.samples){const Vec d=rest[i]-mean;radius+=length(d-axis*dot(d,axis));}
                section.radius=clamp(radius/static_cast<float>(section.samples.size())-.006f,.025f,.060f);
                armSections[side].push_back(std::move(section));
            }
        }
        return true;
    }
};
struct ContactSample {Vec position,normal;};
struct ContactSurface {
    std::vector<ContactSample> samples;
    struct Packet {alignas(16) float x[4]{},y[4]{},z[4]{},nx[4]{},ny[4]{},nz[4]{};unsigned valid=0;};
    std::vector<Packet> packets;
    struct Node {uint16_t sample=0;uint8_t axis=0;int32_t left=-1,right=-1;};
    // Balanced k-d tree; nearest-first traversal prunes using the current
    // fourth-nearest compatible sample. Snapshots remain immutable.
    std::vector<Node> nodes;std::vector<uint16_t> order;bool indexed=false;
    static float coordinate(Vec p,unsigned axis){return axis==0?p.x:axis==1?p.y:p.z;}
    void prepare() {
        indexed=false;packets.clear();nodes.clear();if(samples.empty()||samples.size()>4096)return;
        for(const auto& s:samples)if(!finite(s.position)||!finite(s.normal))return;
        // For the small native waist meshes, four-wide filtering is cheaper
        // than tree traversal. Larger custom surfaces use the k-d tree.
        if(samples.size()<=256) {
            packets.resize((samples.size()+3)/4);
            for(size_t i=0;i<samples.size();++i) {
                const auto& s=samples[i];auto& p=packets[i/4];const auto k=i%4;
                p.x[k]=s.position.x;p.y[k]=s.position.y;p.z[k]=s.position.z;
                p.nx[k]=s.normal.x;p.ny[k]=s.normal.y;p.nz[k]=s.normal.z;p.valid|=1u<<k;
            }
            indexed=true;return;
        }
        order.resize(samples.size());for(size_t i=0;i<order.size();++i)order[i]=static_cast<uint16_t>(i);
        nodes.clear();nodes.reserve(samples.size());
        const auto build=[&](auto&& self,size_t first,size_t end,unsigned depth)->int32_t {
            if(first==end)return -1;
            const unsigned axis=depth%3;const size_t middle=(first+end)/2;
            std::nth_element(order.begin()+first,order.begin()+middle,order.begin()+end,[&](uint16_t a,uint16_t b) {
                const float x=coordinate(samples[a].position,axis),y=coordinate(samples[b].position,axis);return x<y||(x==y&&a<b);
            });
            const auto index=static_cast<int32_t>(nodes.size());nodes.push_back({order[middle],static_cast<uint8_t>(axis),-1,-1});
            const auto left=self(self,first,middle,depth+1),right=self(self,middle+1,end,depth+1);
            nodes[static_cast<size_t>(index)].left=left;nodes[static_cast<size_t>(index)].right=right;return index;
        };
        build(build,0,order.size(),0);
        indexed=true;
    }
};
struct ContactPlane {Vec position,normal;bool valid=false;};
inline Vec contact_normal(const Mesh& mesh,const std::vector<Vec>& position,const std::vector<Vec>& normal,size_t i) {
    const auto basis=mesh.contactBasis[i];if(basis[0]==UINT16_MAX)return normal[i];
    const Vec n=cross(position[basis[0]]-position[i],position[basis[1]]-position[i]);
    if(dot(n,n)<1e-14f)return normal[i];
    const Vec direction=unit(n);if(dot(direction,normal[i])<.25f)return normal[i];
    return unit(direction*.8f+normal[i]*.2f);
}
inline Vec shoulder_axis(const Mesh& mesh,const std::vector<Vec>& target) {
    if(mesh.leftShoulder.empty()||mesh.rightShoulder.empty())return {1,0,0};
    Vec left{},right{};
    for(auto i:mesh.leftShoulder)left+=target[i];for(auto i:mesh.rightShoulder)right+=target[i];
    return unit(right/static_cast<float>(mesh.rightShoulder.size())-left/static_cast<float>(mesh.leftShoulder.size()));
}
inline Vec leg_up(const Mesh& mesh,const std::vector<Vec>& target,unsigned leg) {
    if(mesh.legTop[leg].empty()||mesh.legHem[leg].empty())return {0,1,0};
    Vec top{},bottom{};
    for(auto i:mesh.legTop[leg])top+=target[i];for(auto i:mesh.legHem[leg])bottom+=target[i];
    return unit(top/static_cast<float>(mesh.legTop[leg].size())-bottom/static_cast<float>(mesh.legHem[leg].size()));
}
inline Vec jersey_pivot(const Mesh& mesh,const std::vector<Vec>& target) {
    Vec center{};size_t count=0;
    for(auto i:mesh.leftShoulder){center+=target[i];++count;}for(auto i:mesh.rightShoulder){center+=target[i];++count;}
    if(!count)for(size_t i=0;i<target.size();++i)if(!mesh.mass[i]){center+=target[i];++count;}
    return count?center/static_cast<float>(count):Vec{};
}
inline Vec fit_offset(const Mesh& mesh,size_t i,Vec normal,Vec axis,const Config& c,Vec up={0,1,0}) {
    if(mesh.piece==Piece::Shorts)return normal*(-c.shortsInset*mesh.fit[i])+up*(c.shortsHemLift*mesh.hem[i]);
    if(mesh.piece==Piece::Jersey)return axis*((mesh.rest[i].x<0?1.0f:-1.0f)*c.shoulderInset*mesh.fit[i])+
        normal*(c.chestVolume*mesh.chest[i]-c.torsoInset*mesh.torso[i]);
    return {};
}
inline ContactPlane contact_plane(Vec point,Vec normal,const ContactSurface* surface,const Config& config,size_t* tested=nullptr) {
    if(!surface||surface->samples.empty())return {};
    float best[4]={1e6f,1e6f,1e6f,1e6f};const ContactSample* found[4]{};
    size_t foundIndex[4]={SIZE_MAX,SIZE_MAX,SIZE_MAX,SIZE_MAX};
    const float radius2=config.contactRadius*config.contactRadius;
    const auto insert=[&](size_t index,float d2) {
        const auto& sample=surface->samples[index];
        for(unsigned j=0;j<4;++j)if(d2<best[j]||(d2==best[j]&&index<foundIndex[j])) {
            for(unsigned k=3;k>j;--k){best[k]=best[k-1];found[k]=found[k-1];foundIndex[k]=foundIndex[k-1];}
            best[j]=d2;found[j]=&sample;foundIndex[j]=index;break;
        }
    };
    const auto visit=[&](size_t index) {
        if(tested)++*tested;const auto& sample=surface->samples[index];
        const Vec delta=point-sample.position;const float d2=dot(delta,delta);
        if(d2<=radius2&&dot(normal,sample.normal)>=.15f)insert(index,d2);
    };
    if(surface->indexed&&!surface->packets.empty()) {
        const auto px=_mm_set1_ps(point.x),py=_mm_set1_ps(point.y),pz=_mm_set1_ps(point.z);
        const auto nx=_mm_set1_ps(normal.x),ny=_mm_set1_ps(normal.y),nz=_mm_set1_ps(normal.z);
        for(size_t k=0;k<surface->packets.size();++k) {
            const auto& p=surface->packets[k];
            const auto dx=_mm_sub_ps(px,_mm_load_ps(p.x)),dy=_mm_sub_ps(py,_mm_load_ps(p.y)),dz=_mm_sub_ps(pz,_mm_load_ps(p.z));
            const auto d2=_mm_add_ps(_mm_add_ps(_mm_mul_ps(dx,dx),_mm_mul_ps(dy,dy)),_mm_mul_ps(dz,dz));
            const auto angle=_mm_add_ps(_mm_add_ps(_mm_mul_ps(nx,_mm_load_ps(p.nx)),_mm_mul_ps(ny,_mm_load_ps(p.ny))),_mm_mul_ps(nz,_mm_load_ps(p.nz)));
            const unsigned mask=static_cast<unsigned>(_mm_movemask_ps(_mm_and_ps(_mm_cmple_ps(d2,_mm_set1_ps(std::min(radius2,best[3]))),_mm_cmpge_ps(angle,_mm_set1_ps(.15f)))))&p.valid;
            if(!mask)continue;
            alignas(16) float distance[4];_mm_store_ps(distance,d2);
            for(unsigned lane=0;lane<4;++lane)if(mask&(1u<<lane)){if(tested)++*tested;insert(k*4+lane,distance[lane]);}
        }
    }else if(surface->indexed) {
        const auto search=[&](auto&& self,int32_t index)->void {
            if(index<0)return;const auto& node=surface->nodes[static_cast<size_t>(index)];
            const float delta=ContactSurface::coordinate(point,node.axis)-ContactSurface::coordinate(surface->samples[node.sample].position,node.axis);
            visit(node.sample);self(self,delta<0?node.left:node.right);
            if(delta*delta<=std::min(radius2,best[3]))self(self,delta<0?node.right:node.left);
        };
        search(search,0);
    }else {
        for(size_t i=0;i<surface->samples.size();++i)visit(i);
    }
    Vec center{},direction{};float total=0;
    for(unsigned j=0;j<4;++j)if(found[j]) {
        const float weight=1/(best[j]+.0001f);total+=weight;
        center+=found[j]->position*weight;direction+=found[j]->normal*weight;
    }
    if(total==0)return {};
    center=center/total;direction=unit(direction);
    float support=0;for(const auto* sample:found)if(sample)support=std::max(support,dot(sample->position-center,direction));
    center+=direction*support;
    return {center,direction,true};
}
inline bool project_plane(Vec& point,const ContactPlane& plane,const Config& config) {
    if(!plane.valid)return false;
    const float distance=dot(point-plane.position,plane.normal);
    if(distance>=config.waistClearance)return false;
    point+=plane.normal*std::min(.045f,config.waistClearance-distance);return true;
}
inline bool project_contact(Vec& point,Vec normal,const ContactSurface* surface,const Config& config) {
    return project_plane(point,contact_plane(point,normal,surface,config),config);
}
struct BodyCapsule {Vec center,axis;float halfLength=0,radiusA=0,radiusB=0;};
inline void append_sleeve_proxies(const Mesh& mesh,const std::vector<Vec>& target,std::vector<BodyCapsule>& body) {
    if(mesh.piece!=Piece::Jersey||(!mesh.longSleeves&&!body.empty()))return;
    for(unsigned side=0;side<2;++side) {
        const auto& sections=mesh.armSections[side];
        if(sections.size()<2)continue;
        Vec previous{};float previousRadius=0;
        for(size_t k=0;k<sections.size();++k) {
            if(k%2&&k+1<sections.size())continue;
            const auto& section=sections[k];Vec center{};
            for(auto i:section.samples)center+=target[i];center=center/static_cast<float>(section.samples.size());
            if(k){const Vec delta=center-previous;const float extent=length(delta);
                if(extent>.005f&&extent<.45f)body.push_back({(center+previous)*.5f,delta/extent,extent*.5f,previousRadius,section.radius});}
            previous=center;previousRadius=section.radius;
        }
    }
}
inline bool project_capsule(Vec& point,const BodyCapsule& capsule,float margin,Vec fallback) {
    const Vec relative=point-capsule.center;
    const float along=clamp(dot(relative,capsule.axis),-capsule.halfLength,capsule.halfLength);
    const float blend=capsule.halfLength>1e-6f?(along/capsule.halfLength+1)*.5f:.5f;
    const float radius=capsule.radiusA+(capsule.radiusB-capsule.radiusA)*blend+margin;
    const Vec center=capsule.center+capsule.axis*along,delta=point-center;
    const float squared=dot(delta,delta);if(squared>=radius*radius)return false;
    Vec direction=delta;
    if(squared<1e-12f) {
        direction=fallback-capsule.axis*dot(fallback,capsule.axis);
        if(length(direction)<1e-6f)direction=std::abs(capsule.axis.x)<.8f?Vec{1,0,0}:Vec{0,0,1};
    }
    point=center+unit(direction)*radius;return true;
}
// Closest points on two finite segments. Testing the middle of the cloth edge
// alone misses oblique intersections and fast poses near its endpoints.
inline float segment_parameter(Vec a,Vec b,Vec c,Vec d) {
    const Vec u=b-a,v=d-c,w=a-c;const float uu=dot(u,u),vv=dot(v,v),uv=dot(u,v),uw=dot(u,w),vw=dot(v,w);
    if(uu<1e-12f)return 0;
    if(vv<1e-12f)return clamp(-uw/uu,0,1);
    const float determinant=uu*vv-uv*uv;
    float s=determinant>1e-12f?clamp((uv*vw-vv*uw)/determinant,0,1):0;
    const float t=(uv*s+vw)/vv;
    if(t<0)s=clamp(-uw/uu,0,1);else if(t>1)s=clamp((uv-uw)/uu,0,1);
    return s;
}
struct CapsuleBounds {Vec low,high,start,end;};
inline CapsuleBounds capsule_bounds(const BodyCapsule& capsule,float margin) {
    const float radius=std::max(capsule.radiusA,capsule.radiusB)+margin;
    const Vec extent{std::abs(capsule.axis.x)*capsule.halfLength+radius,
        std::abs(capsule.axis.y)*capsule.halfLength+radius,std::abs(capsule.axis.z)*capsule.halfLength+radius};
    return {capsule.center-extent,capsule.center+extent,capsule.center-capsule.axis*capsule.halfLength,capsule.center+capsule.axis*capsule.halfLength};
}
inline uint8_t capsule_code(Vec p,const CapsuleBounds& b) {
    return static_cast<uint8_t>((p.x<b.low.x?1:0)|(p.x>b.high.x?2:0)|(p.y<b.low.y?4:0)|
        (p.y>b.high.y?8:0)|(p.z<b.low.z?16:0)|(p.z>b.high.z?32:0));
}
inline bool project_capsule_edge(Vec& a,Vec& b,float wa,float wb,const BodyCapsule& capsule,float margin,Vec fallback,const CapsuleBounds& bounds) {
    if(std::min(a.x,b.x)>bounds.high.x||std::max(a.x,b.x)<bounds.low.x||
       std::min(a.y,b.y)>bounds.high.y||std::max(a.y,b.y)<bounds.low.y||
       std::min(a.z,b.z)>bounds.high.z||std::max(a.z,b.z)<bounds.low.z)return false;
    // Native thigh volumes can overlap the immovable waistband in a high
    // stride. That span has no feasible contact solution without moving the
    // anchor. Keep the anchor and still collide its movable endpoint.
    if(wa==0){Vec fixed=a;if(project_capsule(fixed,capsule,margin,fallback))return false;}
    if(wb==0){Vec fixed=b;if(project_capsule(fixed,capsule,margin,fallback))return false;}
    const float t=segment_parameter(a,b,bounds.start,bounds.end),u=1-t;
    Vec point=lerp(a,b,t),corrected=point;
    if(!project_capsule(corrected,capsule,margin,fallback))return false;
    const float weight=wa*u*u+wb*t*t;if(weight<1e-8f)return false;
    // A mass-weighted contact at a point inside the edge; fixed vertices stay fixed.
    Vec push=corrected-point;
    const float change=length(push)*std::max(wa*u,wb*t)/weight;
    const float limit=length(b-a)*.5f+.002f;
    if(change>limit)push=push*(limit/change);
    a+=push*(wa*u/weight);b+=push*(wb*t/weight);return true;
}
inline bool project_capsule_edge(Vec& a,Vec& b,float wa,float wb,const BodyCapsule& capsule,float margin,Vec fallback) {
    return project_capsule_edge(a,b,wa,wb,capsule,margin,fallback,capsule_bounds(capsule,margin));
}
inline BodyCapsule interpolate(const BodyCapsule& a,const BodyCapsule& b,float t,Vec shift) {
    return {lerp(a.center+shift,b.center,t),unit(lerp(a.axis,b.axis,t)),
        a.halfLength+(b.halfLength-a.halfLength)*t,a.radiusA+(b.radiusA-a.radiusA)*t,a.radiusB+(b.radiusB-a.radiusB)*t};
}
struct ArmCandidates {std::vector<uint16_t> points,edges;};
struct SelfCell {int x=0,y=0,z=0,next=-1;uint16_t vertex=0;};
struct State {
    std::vector<Vec> position,velocity,previousTarget;
    std::vector<Vec> before,posed,pinLambda,bodyVelocity;
    std::vector<Vec> fitted,fittedBind;
    std::vector<ContactPlane> contactPlanes;
    std::vector<float> lambda,limits,pinCompliance,edgeLengths;
    std::vector<float> bindEdgeLengths;
    std::vector<float> bendCompliance;
    std::array<float,8> constraintProfile{};
    bool constraintsCached=false;
    std::vector<BodyCapsule> previousBody,body;
    std::vector<ArmCandidates> armCandidates;
    std::vector<CapsuleBounds> capsuleBounds;
    std::vector<uint8_t> bodyCodes;
    std::vector<SelfCell> selfCells;
    std::array<int,512> selfHeads{};
    std::vector<uint8_t> waistTouched;
    float cachedShoulder=-1,cachedShorts=-1,cachedChest=-1,cachedLift=-1,cachedTorso=-1,cachedShrink=-1;
    bool ready=false;Vec previousMeanVelocity{};
    uint64_t contacts=0,bodyContacts=0,edgeContacts=0,foldContacts=0,selfContacts=0,waistFallbacks=0;
    void reset(const Mesh& mesh,const std::vector<Vec>& targets,const std::vector<Vec>& normals,const Config& config) {
        constraintsCached=false;
        position=targets;velocity.assign(targets.size(),{});previousTarget=targets;previousMeanVelocity={};
        for(size_t i=0;i<targets.size();++i)if(mesh.mass[i])position[i]+=normals[i]*
            (config.clearance*(mesh.piece==Piece::Jersey?1-.7f*config.chestStability*mesh.chest[i]:1));
        ready=true;
    }
};
inline void finish_hem_folds(const Mesh& mesh,State& state,const std::vector<Vec>& target,std::vector<Vec>* before) {
    for(const auto& f:mesh.hemFolds) {
        const Vec u=state.position[f.a]-state.position[f.center],v=state.position[f.b]-state.position[f.center];
        const float uv=dot(u,v);
        // Broad bends remain free; only a turn tighter than about 70 degrees
        // over this two-edge material arc needs a distributed correction.
        if(uv<0&&uv*uv>=.11888704f*dot(u,u)*dot(v,v))continue;
        const float la=length(u),lb=length(v);if(la<1e-7f||lb<1e-7f)continue;
        const Vec chord=state.position[f.a]-state.position[f.b];const float span=length(chord);
        constexpr float ratio=.82f;
        const float violation=ratio*(la+lb)-span;if(violation<=0)continue;
        const Vec direction=span>1e-7f?chord/span:unit(target[f.a]-target[f.b]);
        const Vec ga=direction-u*(ratio/la),gb=-direction-v*(ratio/lb),gc=-(ga+gb);
        const float wa=mesh.mass[f.a],wb=mesh.mass[f.b],wc=mesh.mass[f.center];
        const float weight=wa*dot(ga,ga)+wb*dot(gb,gb)+wc*dot(gc,gc);if(weight<1e-8f)continue;
        const float scale=std::min(violation/weight,.004f/std::max({length(ga)*wa,length(gb)*wb,length(gc)*wc,1e-8f}));
        const Vec pa=ga*(scale*wa),pb=gb*(scale*wb),pc=gc*(scale*wc);
        state.position[f.a]+=pa;state.position[f.b]+=pb;state.position[f.center]+=pc;
        if(before){(*before)[f.a]+=pa;(*before)[f.b]+=pb;(*before)[f.center]+=pc;}
        ++state.foldContacts;
    }
}
inline unsigned self_hash(int x,int y,int z) {
    return (static_cast<unsigned>(x)*73856093u^static_cast<unsigned>(y)*19349663u^static_cast<unsigned>(z)*83492791u)&511u;
}
inline void finish_hem_self_contact(const Mesh& mesh,State& state,std::vector<Vec>* before) {
    if(mesh.selfVertices.empty())return;
    constexpr float gap=.004f,cell=.008f;
    state.selfHeads.fill(-1);state.selfCells.resize(mesh.selfVertices.size());
    // Relative coordinates avoid large world positions overflowing cell indices.
    const Vec origin=state.position[mesh.selfVertices[0]];
    const auto coordinate=[=](float value){return static_cast<int>(std::floor(clamp(value/cell,-1000000,1000000)));};
    for(size_t j=0;j<mesh.selfVertices.size();++j) {
        const auto i=mesh.selfVertices[j];const Vec p=state.position[i]-origin;
        auto& entry=state.selfCells[j];entry={coordinate(p.x),coordinate(p.y),coordinate(p.z),-1,i};
        const auto bucket=self_hash(entry.x,entry.y,entry.z);entry.next=state.selfHeads[bucket];state.selfHeads[bucket]=static_cast<int>(j);
    }
    for(size_t j=0;j<state.selfCells.size();++j) {
        const auto i=state.selfCells[j].vertex;const Vec p=state.position[i]-origin;
        for(int x=coordinate(p.x-gap);x<=coordinate(p.x+gap);++x)
        for(int y=coordinate(p.y-gap);y<=coordinate(p.y+gap);++y)
        for(int z=coordinate(p.z-gap);z<=coordinate(p.z+gap);++z)
        for(int k=state.selfHeads[self_hash(x,y,z)];k>=0;k=state.selfCells[static_cast<size_t>(k)].next) {
            const auto& candidate=state.selfCells[static_cast<size_t>(k)];const auto b=candidate.vertex;
            if(b<=i||candidate.x!=x||candidate.y!=y||candidate.z!=z)continue;
            const Vec delta=state.position[i]-state.position[b];const float d2=dot(delta,delta);if(d2>=gap*gap)continue;
            const Vec bind=mesh.rest[i]-mesh.rest[b];if(dot(bind,bind)<.012f*.012f)continue;
            const auto& excluded=mesh.selfExclude[i];if(std::binary_search(excluded.begin(),excluded.end(),b))continue;
            const float d=std::sqrt(d2);Vec direction;
            if(d>1e-7f)direction=delta/d;
            else if(before)direction=unit((*before)[i]-(*before)[b]);
            else direction=unit(bind);
            const Vec push=direction*((gap-d)*.5f);state.position[i]+=push;state.position[b]-=push;
            if(before){(*before)[i]+=push;(*before)[b]-=push;}
            ++state.selfContacts;
        }
    }
}
inline void finish_arm_contact(const Mesh& mesh,State& state,const std::vector<Vec>& normal,
                               const std::vector<BodyCapsule>& body,const Config& config,std::vector<Vec>* before,bool spans) {
    state.armCandidates.resize(body.size());
    // Broad phase once per substep, reused by the contact passes. Padding
    // covers the small corrections that can bring adjacent cloth into a box.
    for(size_t k=0;k<body.size();++k) {
        const auto& capsule=body[k];auto& candidates=state.armCandidates[k];candidates.points.clear();candidates.edges.clear();
        const float radius=std::max(capsule.radiusA,capsule.radiusB)+config.armMargin+.030f;
        const Vec extent{std::abs(capsule.axis.x)*capsule.halfLength+radius,
            std::abs(capsule.axis.y)*capsule.halfLength+radius,std::abs(capsule.axis.z)*capsule.halfLength+radius};
        const Vec low=capsule.center-extent,high=capsule.center+extent;
        for(auto i:mesh.sleeveVertices) {
            const auto p=state.position[i];
            if(p.x>=low.x&&p.x<=high.x&&p.y>=low.y&&p.y<=high.y&&p.z>=low.z&&p.z<=high.z)candidates.points.push_back(i);
        }
        if(spans)for(size_t j=0;j<mesh.collisionEdges.size();++j) {
            const auto& e=mesh.collisionEdges[j];const auto a=state.position[e.a],b=state.position[e.b];
            if(std::min(a.x,b.x)<=high.x&&std::max(a.x,b.x)>=low.x&&std::min(a.y,b.y)<=high.y&&
               std::max(a.y,b.y)>=low.y&&std::min(a.z,b.z)<=high.z&&std::max(a.z,b.z)>=low.z)candidates.edges.push_back(static_cast<uint16_t>(j));
        }
    }
    unsigned passes=2;
    for(unsigned pass=0;pass<passes;++pass) {
        bool refine=false;
        if(spans&&pass>0)for(size_t k=0;k<body.size();++k)for(auto j:state.armCandidates[k].edges) {
            const auto& e=mesh.collisionEdges[j];const unsigned repeats=mesh.mass[e.a]==0||mesh.mass[e.b]==0?4:1;
            for(unsigned repeat=0;repeat<repeats;++repeat) {
                const auto a=state.position[e.a],b=state.position[e.b];
                if(!project_capsule_edge(state.position[e.a],state.position[e.b],mesh.mass[e.a],mesh.mass[e.b],body[k],config.armMargin,normal[e.a]+normal[e.b],state.capsuleBounds[k]))break;
                if(length(state.position[e.a]-a)>.003f||length(state.position[e.b]-b)>.003f)refine=true;
                if(before){(*before)[e.a]+=state.position[e.a]-a;(*before)[e.b]+=state.position[e.b]-b;}
                ++state.edgeContacts;
            }
        }
        for(size_t k=0;k<body.size();++k)for(auto i:state.armCandidates[k].points) {
            const auto old=state.position[i];
            if(project_capsule(state.position[i],body[k],config.armMargin,normal[i])) {
                if(before)(*before)[i]+=state.position[i]-old;
                ++state.bodyContacts;
            }
        }
        if(spans&&pass==1&&refine)passes=3;
    }
}
inline void finish_body_contact(const Mesh& mesh,State& state,const std::vector<Vec>& normal,
                                const std::vector<BodyCapsule>& body,const Config& config,std::vector<Vec>* before=nullptr,bool spans=true) {
    if((mesh.piece!=Piece::Shorts&&mesh.piece!=Piece::Jersey)||body.empty())return;
    state.capsuleBounds.resize(body.size());
    for(size_t k=0;k<body.size();++k)state.capsuleBounds[k]=capsule_bounds(body[k],mesh.piece==Piece::Jersey?config.armMargin:config.bodyMargin);
    if(mesh.piece==Piece::Jersey){finish_arm_contact(mesh,state,normal,body,config,before,spans);return;}
    // Edge projection can move a vertex towards another volume; alternate the
    // two contact types and finish with the vertex constraints.
    const unsigned passes=spans?3:2;
    for(unsigned pass=0;pass<passes;++pass) {
        if(spans&&pass>0)for(size_t k=0;k<body.size();++k) {
            const BodyCapsule capsule=body[k];
            // Shared vertex outcodes reject an edge using two byte loads.
            // Refresh moved endpoints immediately: this is an exact broad
            // phase, without freezing candidates or changing the leg solver.
            state.bodyCodes.resize(state.position.size());
            for(size_t i=0;i<state.position.size();++i)state.bodyCodes[i]=capsule_code(state.position[i],state.capsuleBounds[k]);
            for(const auto& e:mesh.collisionEdges) {
                if(state.bodyCodes[e.a]&state.bodyCodes[e.b])continue;
                const unsigned repeats=mesh.mass[e.a]==0||mesh.mass[e.b]==0?4:1;
                for(unsigned repeat=0;repeat<repeats;++repeat) {
                    const Vec a=state.position[e.a],b=state.position[e.b];
                    if(project_capsule_edge(state.position[e.a],state.position[e.b],mesh.mass[e.a],mesh.mass[e.b],
                                            capsule,config.bodyMargin,normal[e.a]+normal[e.b],state.capsuleBounds[k])) {
                        if(before){(*before)[e.a]+=state.position[e.a]-a;(*before)[e.b]+=state.position[e.b]-b;}
                        state.bodyCodes[e.a]=capsule_code(state.position[e.a],state.capsuleBounds[k]);
                        state.bodyCodes[e.b]=capsule_code(state.position[e.b],state.capsuleBounds[k]);
                        ++state.edgeContacts;
                    }else break;
                }
            }
        }
        for(size_t i=0;i<state.position.size();++i)if(mesh.mass[i])for(const auto& capsule:body) {
            const Vec old=state.position[i];
            if(project_capsule(state.position[i],capsule,config.bodyMargin,normal[i])) {
                if(before)(*before)[i]+=state.position[i]-old;
                ++state.bodyContacts;
            }
        }
    }
}
inline void finish_waist_contact(const Mesh& mesh,State& state,const std::vector<Vec>& normal,
                                 const ContactSurface* surface,const Config& config) {
    if(mesh.piece!=Piece::Jersey||!surface)return;
    // Refresh the closest surface after solving: a plane selected at the
    // start can become stale when a hem vertex moves around the waistband.
    const auto vertex=[&](size_t i) {for(unsigned pass=0;pass<6;++pass) {
        const auto plane=contact_plane(state.position[i],normal[i],surface,config);
        bool corrected=false;
        if(pass<3)corrected=project_plane(state.position[i],plane,config);
        else if(plane.valid) {
            // Near a crease, successive nearest planes can alternate and
            // undo each other. An outward correction has a positive dot with
            // every accepted sample normal and cannot re-enter those planes.
            const Vec outward=unit(normal[i]);const float alignment=dot(outward,plane.normal);
            const float penetration=config.waistClearance-dot(state.position[i]-plane.position,plane.normal);
            if(penetration>.00005f&&alignment>.10f) {
                state.position[i]+=outward*std::min(.015f,penetration/alignment);
                corrected=true;++state.waistFallbacks;
            }
        }
        if(corrected) {
            const float inward=dot(state.velocity[i],plane.normal);
            if(inward<0)state.velocity[i]-=plane.normal*inward;
            ++state.contacts;
        }else break;
    }};
    for(size_t i=0;i<state.position.size();++i)if(mesh.mass[i]&&mesh.waist[i]>.01f)vertex(i);
    state.waistTouched.assign(state.position.size(),0);
    // A coarse span can cross the shorts even when its two endpoints are
    // outside. Protect its midpoint and refresh only the affected endpoints.
    for(const auto& e:mesh.waistEdges) {
        const Vec mid=(state.position[e.a]+state.position[e.b])*.5f;
        const auto plane=contact_plane(mid,unit(normal[e.a]+normal[e.b]),surface,config);Vec corrected=mid;
        if(project_plane(corrected,plane,config)) {
            const Vec push=corrected-mid;state.position[e.a]+=push;state.position[e.b]+=push;
            for(auto i:{e.a,e.b}) {
                const float inward=dot(state.velocity[i],plane.normal);if(inward<0)state.velocity[i]-=plane.normal*inward;
                state.waistTouched[i]=1;
            }
            ++state.contacts;
        }
    }
    for(size_t i=0;i<state.position.size();++i)if(state.waistTouched[i])vertex(i);
}
enum class Result { Stepped,Reset,Paused,Invalid };
inline Result step(const Mesh& mesh,State& state,const std::vector<Vec>& animatedTarget,
                   const std::vector<Vec>& normal,float dt,const Config& c,const ContactSurface* contact=nullptr,
                   const std::vector<BodyCapsule>* colliders=nullptr) {
    const size_t count=mesh.rest.size();
    if(animatedTarget.size()!=count||normal.size()!=count||mesh.distance.size()!=count||!std::isfinite(dt)||dt<0)return Result::Invalid;
    for(size_t i=0;i<count;++i)if(!finite(animatedTarget[i])||!finite(normal[i]))return Result::Invalid;
    if(dt<1e-6f)return Result::Paused;
    state.fitted.resize(count);
    const Vec axis=shoulder_axis(mesh,animatedTarget);
    const Vec pivot=mesh.piece==Piece::Jersey?jersey_pivot(mesh,animatedTarget):Vec{};
    Vec up[2]={{0,1,0},{0,1,0}},bindUp[2]={{0,1,0},{0,1,0}};
    if(mesh.piece==Piece::Shorts)for(unsigned leg=0;leg<2;++leg){up[leg]=leg_up(mesh,animatedTarget,leg);bindUp[leg]=leg_up(mesh,mesh.rest,leg);}
    for(size_t i=0;i<count;++i)state.fitted[i]=animatedTarget[i]+fit_offset(mesh,i,normal[i],axis,c,up[mesh.rest[i].x<0?0:1])+
        (animatedTarget[i]-pivot)*(-c.jerseyShrink*mesh.freeFit[i]);
    if(!state.ready||state.fittedBind.size()!=count||state.bindEdgeLengths.size()!=mesh.edges.size()||
       state.cachedShoulder!=c.shoulderInset||state.cachedShorts!=c.shortsInset||state.cachedChest!=c.chestVolume||
       state.cachedLift!=c.shortsHemLift||state.cachedTorso!=c.torsoInset||state.cachedShrink!=c.jerseyShrink) {
        state.fittedBind.resize(count);state.bindEdgeLengths.resize(mesh.edges.size());
        const Vec bindPivot=mesh.piece==Piece::Jersey?jersey_pivot(mesh,mesh.rest):Vec{};
        for(size_t i=0;i<count;++i)state.fittedBind[i]=mesh.rest[i]+fit_offset(mesh,i,mesh.normals[i],{1,0,0},c,bindUp[mesh.rest[i].x<0?0:1])+
            (mesh.rest[i]-bindPivot)*(-c.jerseyShrink*mesh.freeFit[i]);
        for(size_t i=0;i<mesh.edges.size();++i){const auto& e=mesh.edges[i];state.bindEdgeLengths[i]=length(state.fittedBind[e.a]-state.fittedBind[e.b]);}
        state.cachedShoulder=c.shoulderInset;state.cachedShorts=c.shortsInset;state.cachedChest=c.chestVolume;
        state.cachedLift=c.shortsHemLift;
        state.cachedTorso=c.torsoInset;
        state.cachedShrink=c.jerseyShrink;
    }
    const auto& target=state.fitted;
    const auto reset=[&]() {
        state.reset(mesh,target,normal,c);
        if(colliders) {
            state.previousBody=*colliders;
            finish_body_contact(mesh,state,normal,*colliders,c);
        }else state.previousBody.clear();
        finish_waist_contact(mesh,state,normal,contact,c);
        return Result::Reset;
    };
    if(!state.ready||state.position.size()!=count||dt>0.08f) {
        return reset();
    }
    Vec meanDelta{};
    float maxDelta=0;
    for(size_t i=0;i<count;++i){const Vec d=target[i]-state.previousTarget[i];meanDelta+=d;maxDelta=std::max(maxDelta,length(d));}
    meanDelta=meanDelta/static_cast<float>(count);
    if(length(meanDelta)>0.6f||maxDelta>0.8f)return reset();
    const Vec meanVelocity=meanDelta/dt;
    const Vec inertia=capped((meanVelocity-state.previousMeanVelocity)/dt,35.0f)*(-c.motion);
    const unsigned substeps=std::max(1u,static_cast<unsigned>(std::ceil(dt*static_cast<float>(c.frequency))));
    const float h=dt/static_cast<float>(substeps),hh=h*h;
    auto& before=state.before;auto& rest=state.posed;auto& pinLambda=state.pinLambda;auto& bodyVelocity=state.bodyVelocity;
    auto& lambda=state.lambda;auto& limits=state.limits;auto& pinCompliance=state.pinCompliance;auto& edgeLengths=state.edgeLengths;
    const std::array<float,8> constraintProfile{c.pin,c.maxDistance,c.shortsPinScale,c.hemFreedom,c.jerseyFreedom,c.chestStability,c.chestMax,c.bend};
    const bool refreshConstraints=!state.constraintsCached||state.constraintProfile!=constraintProfile||limits.size()!=count;
    before.resize(count);rest.resize(count);pinLambda.resize(count);bodyVelocity.resize(count);
    state.contactPlanes.resize(count);
    lambda.resize(mesh.edges.size());limits.resize(count);pinCompliance.resize(count);edgeLengths.resize(mesh.edges.size());
    state.bendCompliance.resize(mesh.edges.size());
    for(size_t i=0;i<count;++i) {
        state.position[i]+=meanDelta;
        bodyVelocity[i]=(target[i]-state.previousTarget[i]-meanDelta)/dt;
        if(refreshConstraints) {
            const float seam=clamp(mesh.distance[i]/0.15f,0,1);
            limits[i]=c.maxDistance*(0.12f+0.88f*seam);
            pinCompliance[i]=c.pin*(0.08f+std::pow(mesh.distance[i]/0.10f,2.0f))*(mesh.piece==Piece::Shorts?c.shortsPinScale:1);
            if(mesh.piece==Piece::Jersey)pinCompliance[i]*=(1+mesh.hem[i]*(c.hemFreedom-1))*
                (1+smooth(mesh.distance[i]/.18f)*(c.jerseyFreedom-1))*
                ((1-c.chestStability*mesh.chest[i])*(1-c.chestStability*mesh.chest[i]));
            if(mesh.piece==Piece::Jersey)limits[i]*=1-.5f*c.chestStability*mesh.chest[i];
            if(mesh.piece==Piece::Jersey)limits[i]=std::min(limits[i],c.chestMax+(c.maxDistance-c.chestMax)*(1-mesh.chest[i]));
        }
        state.contactPlanes[i]=mesh.piece==Piece::Jersey&&mesh.waist[i]>.01f?
            contact_plane(state.position[i],normal[i],contact,c):ContactPlane{};
    }
    for(size_t j=0;j<mesh.edges.size();++j) {
        const auto& edge=mesh.edges[j];
        if(refreshConstraints&&edge.family==Family::Bend&&mesh.piece==Piece::Jersey)state.bendCompliance[j]=c.bend*
            (1+.5f*(mesh.hem[edge.a]+mesh.hem[edge.b])*.5f)*(1-c.chestStability*(mesh.chest[edge.a]+mesh.chest[edge.b])*.5f);
        const float animated=length(target[edge.a]-target[edge.b]);
        const float seam=std::min(mesh.distance[edge.a],mesh.distance[edge.b]);
        const bool sleeve=std::abs(mesh.rest[edge.a].x)>0.25f||std::abs(mesh.rest[edge.b].x)>0.25f;
        float adaptation=(seam<0.08f||sleeve)?0.85f:c.restAdaptation;
        const float fittedRest=state.bindEdgeLengths[j];
        // Following an animated joint must not shorten the material whenever
        // the body bends. Preserve its arc length so compression can buckle.
        if(animated<fittedRest&&edge.family!=Family::Bend)adaptation=std::min(adaptation,c.restAdaptation);
        edgeLengths[j]=fittedRest+(animated-fittedRest)*adaptation;
    }
    state.constraintProfile=constraintProfile;state.constraintsCached=true;
    const float decay=std::exp(-c.damping*h),hemDecay=std::exp(-c.damping*c.hemDamping*h);
    const float chestDecay=std::exp(-c.damping*(1+3*c.chestStability)*h);
    const float stretchAlpha=c.stretch/hh,compressionAlpha=c.compression/hh;
    const float stretchInverse[3]={0,1/(1+stretchAlpha),1/(2+stretchAlpha)};
    const float compressionInverse[3]={0,1/(1+compressionAlpha),1/(2+compressionAlpha)};
    for(unsigned s=0;s<substeps;++s) {
        const float t=static_cast<float>(s+1)/static_cast<float>(substeps);
        state.body.clear();
        if(colliders)for(size_t k=0;k<colliders->size();++k)state.body.push_back(state.previousBody.size()==colliders->size()?
            interpolate(state.previousBody[k],(*colliders)[k],t,meanDelta):(*colliders)[k]);
        std::fill(lambda.begin(),lambda.end(),0.0f);std::fill(pinLambda.begin(),pinLambda.end(),Vec{});
        for(size_t i=0;i<count;++i) {
            const float seam=clamp(mesh.distance[i]/0.06f,0,1);
            rest[i]=lerp(state.previousTarget[i]+meanDelta,target[i],t);
            if(!mesh.mass[i]){state.position[i]=rest[i];state.velocity[i]=bodyVelocity[i];before[i]=rest[i];continue;}
            before[i]=state.position[i];
            const Vec body=bodyVelocity[i];
            float damping=mesh.piece==Piece::Jersey?decay+(hemDecay-decay)*mesh.hem[i]:decay;
            if(mesh.piece==Piece::Jersey)damping+=(chestDecay-damping)*mesh.chest[i];
            Vec velocity=body+(state.velocity[i]-body)*damping;
            velocity+=(Vec{0,-9.81f*(mesh.piece==Piece::Shorts?c.shortsGravity:1),0}+inertia)*h;
            const Vec n=unit(normal[i]);
            // Aerodynamic drag is relative to the animated body and follows
            // surface orientation. There is no clock-driven oscillation.
            const Vec air{c.wind,0,0};
            const float pressure=dot(velocity-body-air,n);
            velocity-=n*(pressure*std::min(1.0f,c.airDrag*h));
            state.position[i]+=capped(velocity,c.maxSpeed)*h;
            const float clearance=c.clearance*(mesh.piece==Piece::Jersey?1-.7f*c.chestStability*mesh.chest[i]:1);
            rest[i]+=n*(clearance*seam);
        }
        for(unsigned iteration=0;iteration<c.iterations;++iteration) {
            for(size_t j=0;j<mesh.edges.size();++j) {
                const auto& edge=mesh.edges[j];const float wa=mesh.mass[edge.a],wb=mesh.mass[edge.b];
                if(wa+wb==0)continue;
                const Vec delta=state.position[edge.a]-state.position[edge.b];const float len=length(delta);
                if(len<1e-7f)continue;
                const float constraint=len-edgeLengths[j];
                float compliance=edge.family==Family::Bend?(mesh.piece==Piece::Shorts?c.shortsBend:c.bend):(constraint<0?c.compression:c.stretch);
                if(edge.family==Family::Bend&&mesh.piece==Piece::Jersey)compliance=state.bendCompliance[j];
                const bool membrane=mesh.piece==Piece::Jersey&&edge.family!=Family::Bend;
                const float alpha=membrane?(constraint<0?compressionAlpha:stretchAlpha):compliance/hh;
                const float force=-constraint-alpha*lambda[j];
                const float correction=membrane?force*(constraint<0?compressionInverse:stretchInverse)[static_cast<unsigned>(wa+wb)]:force/(wa+wb+alpha);
                lambda[j]+=correction;
                const Vec impulse=delta*(correction/len);
                state.position[edge.a]+=impulse*wa;state.position[edge.b]-=impulse*wb;
            }
            for(size_t i=0;i<count;++i)if(mesh.mass[i]) {
                const float alpha=pinCompliance[i]/hh;
                const Vec change=(-(state.position[i]-rest[i])-pinLambda[i]*alpha)/(1+alpha);
                pinLambda[i]+=change;state.position[i]+=change;
                Vec offset=state.position[i]-rest[i];const float extent=length(offset);
                if(extent>limits[i])state.position[i]=rest[i]+offset*(limits[i]/extent);
                const Vec n=unit(normal[i]);
                const Vec bodySurface=lerp(state.previousTarget[i]+meanDelta,target[i],t);
                // The animated garment is not the skin. A 2 mm one-sided
                // plane prevented inward folds even where the shirt is loose.
                float inset=mesh.piece==Piece::Shorts?c.shortsBodyInset:
                    c.collisionInset+c.foldInset*smooth(mesh.distance[i]/.18f);
                if(mesh.piece==Piece::Jersey)inset=(inset*(1-.7f*c.chestStability*mesh.chest[i]))*(1-mesh.sleeve[i])+c.sleeveInset*mesh.sleeve[i];
                const float layer=mesh.piece==Piece::Jersey&&!contact?c.waistClearance*mesh.waist[i]:0;
                const float penetration=dot(state.position[i]-bodySurface,n)+inset-layer;
                if(penetration<0) {
                    const Vec push=n*(-penetration);
                    state.position[i]+=push;before[i]+=push; // Zero artificial bounce.
                    const Vec relative=(state.position[i]-before[i])-bodyVelocity[i]*h;
                    state.position[i]-=(relative-n*dot(relative,n))*c.friction;
                }
                if(mesh.piece==Piece::Jersey&&mesh.waist[i]>.01f) {
                    const Vec old=state.position[i];
                    if(project_plane(state.position[i],state.contactPlanes[i],c)) {
                        before[i]+=state.position[i]-old;++state.contacts;
                    }
                }
            }
            // Vertex collision runs at every physics substep. The more
            // expensive span constraints run at the last substep of a frame.
            finish_body_contact(mesh,state,normal,state.body,c,&before,s+1==substeps);
            if(mesh.piece==Piece::Jersey) {
                finish_hem_folds(mesh,state,target,&before);
                finish_hem_self_contact(mesh,state,&before);
            }
        }
        for(size_t i=0;i<count;++i)if(mesh.mass[i]) {
            if(!finite(state.position[i])||length(state.position[i]-rest[i])>0.30f) {
                return reset();
            }
            state.velocity[i]=capped((state.position[i]-before[i])/h,c.maxSpeed);
        }
    }
    finish_waist_contact(mesh,state,normal,contact,c);
    state.previousTarget=target;state.previousMeanVelocity=meanVelocity;
    if(colliders)state.previousBody=*colliders;else state.previousBody.clear();
    return Result::Stepped;
}
}
