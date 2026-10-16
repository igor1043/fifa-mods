#pragma once
#include "particle_solver.h"
#include <cstddef>
#include <cstring>

namespace cloth_particles {
// Point-array descriptor produced by native 4a8c4c0. count is the number
// of actual points; capacity includes padding and two sentinel indices.
struct PointSet {uintptr_t data=0;uint32_t capacity=0,count=0,bytes=0,prefix=0;};
struct ConstraintSet {uintptr_t data=0;uint32_t count=0,padded=0;};
struct NativeEdge {uint16_t a,b;float rest;};
struct Point {float x=0,y=0,z=0,w=0;};
struct ColliderSet {uint32_t count=0,capacity=0;uintptr_t data=0;};
struct NativeCapsule {float fields[16]{};};
static_assert(sizeof(PointSet)==24&&sizeof(ConstraintSet)==16&&sizeof(NativeEdge)==8&&sizeof(Point)==16,"native x64 layouts");
struct View {
    uintptr_t instance=0,definition=0,currentHeader=0,previousHeader=0,restHeader=0,normalHeader=0,historyHeader=0;
    PointSet current{},previous{},rest{},normal{},history{};
    std::vector<Point> currentPoints,previousPoints,targets,normals,historyPoints;
};
template<class Reader,class T>bool value(Reader& read,uintptr_t at,T& target){return read(at,&target,sizeof(target));}
template<class Reader>bool body_capsules(Reader& read,uintptr_t instance,std::vector<BodyCapsule>& out) {
    out.clear();
    for(uintptr_t offset:{uintptr_t(0x40),uintptr_t(0x48)}) {
        uintptr_t header=0;ColliderSet set{};
        if(!value(read,instance+offset,header))return false;
        if(!header)continue;
        if(!value(read,header,set)||set.count>64||set.capacity<set.count||set.capacity>128)return false;
        if(!set.count)continue;
        if(!set.data)return false;
        NativeCapsule raw[64];if(!read(set.data,raw,set.count*sizeof(NativeCapsule)))return false;
        for(unsigned i=0;i<set.count;++i) {
            const auto* f=raw[i].fields;
            const Vec center{f[0]*.01f,f[1]*.01f,f[2]*.01f},axis{f[4],f[5],f[6]};
            const float a=f[3]*.01f,b=(offset==0x48?f[11]:f[3])*.01f,halfLength=f[7]*.01f;
            if(!finite(center)||!finite(axis)||length(axis)<.9f||length(axis)>1.1f||
               !std::isfinite(a)||!std::isfinite(b)||!std::isfinite(halfLength)||
               a<.002f||b<.002f||a>.4f||b>.4f||halfLength<0||halfLength>1.2f)return false;
            out.push_back({center,unit(axis),halfLength,a,b});
        }
    }
    return true;
}
template<class Reader>bool points(Reader& read,uintptr_t header,PointSet& desc,std::vector<Point>& output) {
    if(!value(read,header,desc)||!desc.data||desc.count<3||desc.count>4096||desc.capacity<desc.count||
       desc.capacity>8192||desc.bytes<desc.capacity*16||desc.bytes>131072)return false;
    output.resize(desc.count);return read(desc.data,output.data(),output.size()*sizeof(Point));
}
template<class Reader>bool view(Reader& read,uintptr_t instance,View& out) {
    out.instance=instance;
    if(!value(read,instance,out.currentHeader)||!value(read,instance+8,out.previousHeader)||
       !value(read,instance+0x10,out.definition)||!value(read,instance+0xf0,out.restHeader)||
       !value(read,instance+0xf8,out.historyHeader)||!value(read,instance+0x100,out.normalHeader))return false;
    if(!points(read,out.currentHeader,out.current,out.currentPoints)||
       !points(read,out.previousHeader,out.previous,out.previousPoints)||
       !points(read,out.restHeader,out.rest,out.targets)||!points(read,out.normalHeader,out.normal,out.normals)||
       !points(read,out.historyHeader,out.history,out.historyPoints))return false;
    return out.current.count==out.previous.count&&out.current.count==out.rest.count&&
           out.current.count==out.normal.count&&out.current.count==out.history.count;
}
template<class Reader>bool build_mesh(Reader& read,const View& source,Mesh& mesh,Piece piece=Piece::Generic) {
    const size_t count=source.current.count;
    uintptr_t bind=0;PointSet desc{};std::vector<Point> raw;
    if(!value(read,source.definition+0x90,bind)||!points(read,bind,desc,raw)||desc.count!=count)return false;
    mesh=Mesh{};mesh.piece=piece;mesh.rest.resize(count);mesh.normals.resize(count);mesh.mass.resize(count);
    uintptr_t bindNormal=0;PointSet normalDesc{};std::vector<Point> rawNormal;
    if(!value(read,source.definition+0x98,bindNormal)||!points(read,bindNormal,normalDesc,rawNormal)||normalDesc.count!=count)return false;
    for(size_t i=0;i<count;++i) {
        mesh.rest[i]={raw[i].x*.01f,raw[i].y*.01f,raw[i].z*.01f};
        mesh.normals[i]={rawNormal[i].x,rawNormal[i].y,rawNormal[i].z};
        mesh.mass[i]=source.currentPoints[i].w;
    }
    for(unsigned group=0;group<3;++group) {
        uintptr_t pointer=0;ConstraintSet set{};
        if(!value(read,source.definition+0xa0+group*8,pointer)||!value(read,pointer,set)||
           !set.data||set.count>20000||set.padded<set.count||set.padded>20004)return false;
        std::vector<NativeEdge> edges(set.count);
        if(!read(set.data,edges.data(),edges.size()*sizeof(NativeEdge)))return false;
        for(const auto& e:edges) {
            // The engine appends two inert sentinel points to vector batches.
            if(e.a>=count||e.b>=count) {
                if(e.a>count+1||e.b>count+1)return false;
                continue;
            }
            if(e.a==e.b)continue;
            if(!std::isfinite(e.rest)||e.rest<=0||e.rest>200)return false;
            const float measured=length(mesh.rest[e.a]-mesh.rest[e.b]);
            if(std::abs(measured-e.rest*.01f)>std::max(.002f,measured*.1f))return false;
            mesh.edges.push_back({e.a,e.b,e.rest*.01f,static_cast<Family>(group)});
        }
    }
    return mesh.prepare();
}
inline void targets(const View& view,std::vector<Vec>& positions,std::vector<Vec>& normals) {
    positions.resize(view.targets.size());normals.resize(view.normals.size());
    for(size_t i=0;i<positions.size();++i) {
        positions[i]={view.targets[i].x*.01f,view.targets[i].y*.01f,view.targets[i].z*.01f};
        normals[i]=unit({view.normals[i].x,view.normals[i].y,view.normals[i].z});
    }
}
inline bool output(const View& view,const State& state,float dt,std::vector<Point>& current,std::vector<Point>& previous) {
    if(state.position.size()!=view.current.count||state.velocity.size()!=view.current.count)return false;
    current=view.currentPoints;previous=view.previousPoints;
    for(size_t i=0;i<current.size();++i) {
        const Vec p=state.position[i]*100;
        const Vec q=(state.position[i]-(state.velocity[i]+state.previousMeanVelocity)*std::max(dt,0.0f))*100;
        if(!finite(p)||!finite(q))return false;
        current[i].x=p.x;current[i].y=p.y;current[i].z=p.z;
        previous[i].x=q.x;previous[i].y=q.y;previous[i].z=q.z;
        // Do not touch inverse mass (w), padding, sentinel or fixed count.
    }
    return true;
}
}
