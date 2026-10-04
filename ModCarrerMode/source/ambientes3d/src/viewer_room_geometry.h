#pragma once
#include "viewer_core.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <tuple>
#include <array>

namespace studio::room_geometry {
using namespace fifa_player;
inline constexpr float pi=3.14159265358979f;
inline const Vec3 white={.96f,.965f,.97f},metal={.55f,.59f,.62f},ink={.065f,.08f,.095f};
inline Vec3 add(Vec3 a,Vec3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline Vec3 sub(Vec3 a,Vec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline Vec3 mul(Vec3 a,float s){return {a.x*s,a.y*s,a.z*s};}
inline Vec3 normalized(Vec3 a){float n=sqrtf(a.x*a.x+a.y*a.y+a.z*a.z);return n>.00001f?mul(a,1/n):Vec3{0,1,0};}
inline Vec3 cross(Vec3 a,Vec3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
struct Builder {
    Model room;
    Vec3 origin={};float angle=0;
    Vec3 point(Vec3 p)const{return add(origin,{p.x*cosf(angle)+p.z*sinf(angle),p.y,-p.x*sinf(angle)+p.z*cosf(angle)});}
    Vec3 direction(Vec3 p)const{return {p.x*cosf(angle)+p.z*sinf(angle),p.y,-p.x*sinf(angle)+p.z*cosf(angle)};}
    Vec3 local(Vec3 p)const{p=sub(p,origin);return {p.x*cosf(angle)-p.z*sinf(angle),p.y,p.x*sinf(angle)+p.z*cosf(angle)};}
    void frame(Vec3 p={},float yaw=0){origin=p;angle=yaw;}
    void face(const std::string&name,Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 normal,Vec3 color,int texture=-1,bool blend=false,float u=1,float v=1){
        Part p;p.name=name;p.asset="studio/room/"+name;p.color=color;p.texture=texture;p.blend=blend;p.native_normals=true;
        Vec3 positions[]={a,b,c,d};float uv[][2]={{0,0},{u,0},{u,v},{0,v}};
        for(int i=0;i<4;++i){Vertex q={};q.position=point(positions[i]);q.normal=direction(normal);q.u=uv[i][0];q.v=uv[i][1];p.vertices.push_back(q);}
        p.indices={0,1,2,0,2,3};room.parts.push_back(std::move(p));
    }
    void box(const std::string&name,Vec3 p,Vec3 size,Vec3 color,int texture=-1){
        float x=p.x-size.x/2,X=p.x+size.x/2,y=p.y-size.y/2,Y=p.y+size.y/2,z=p.z-size.z/2,Z=p.z+size.z/2;
        face(name,{x,Y,Z},{X,Y,Z},{X,y,Z},{x,y,Z},{0,0,1},color,texture);
        face(name,{X,Y,z},{x,Y,z},{x,y,z},{X,y,z},{0,0,-1},color,texture);
        face(name,{x,Y,z},{x,Y,Z},{x,y,Z},{x,y,z},{-1,0,0},color,texture);
        face(name,{X,Y,Z},{X,Y,z},{X,y,z},{X,y,Z},{1,0,0},color,texture);
        face(name,{x,Y,z},{X,Y,z},{X,Y,Z},{x,Y,Z},{0,1,0},color,texture);
        face(name,{x,y,Z},{X,y,Z},{X,y,z},{x,y,z},{0,-1,0},color,texture);
    }
    void tube(const std::string&name,Vec3 a,Vec3 b,float radius,Vec3 color,int sides=16,bool caps=true){
        auto axis=normalized(sub(b,a));auto u=normalized(cross(axis,fabsf(axis.y)<.9f?Vec3{0,1,0}:Vec3{0,0,1}));auto v=cross(axis,u);
        for(int i=0;i<sides;++i){float t=i*2*pi/sides,T=(i+1)*2*pi/sides;auto n=add(mul(u,cosf(t)),mul(v,sinf(t)));auto N=add(mul(u,cosf(T)),mul(v,sinf(T)));
            auto A=add(a,mul(n,radius)),B=add(a,mul(N,radius)),C=add(b,mul(N,radius)),D=add(b,mul(n,radius));
            face(name,A,B,C,D,normalized(add(n,N)),color);
            if(caps){face(name,a,B,A,a,mul(axis,-1),color);face(name,b,D,C,b,axis,color);}
        }
    }
    void rounded_box(const std::string&name,Vec3 center,Vec3 size,float radius,Vec3 color,int texture=-1){
        Vec3 half=mul(size,.5f);radius=std::min(radius,std::min({half.x,half.y,half.z})*.92f);Vec3 inner={half.x-radius,half.y-radius,half.z-radius};
        Part p;p.name=name;p.asset="studio/room/"+name;p.color=color;p.texture=texture;p.native_normals=true;
        auto knots=[&](float h){return std::array<float,9>{-h,-h+radius*.134f,-h+radius*.5f,-h+radius,0,h-radius,h-radius*.5f,h-radius*.134f,h};};
        for(int axis=0;axis<3;++axis)for(float side:{-1.f,1.f}){int a=(axis+1)%3,d=(axis+2)%3;auto A=knots((&half.x)[a]),D=knots((&half.x)[d]);
            for(int u=0;u<8;++u)for(int v=0;v<8;++v){uint32_t start=uint32_t(p.vertices.size());int us[]={u,u+1,u+1,u},vs[]={v,v,v+1,v+1};
                for(int k=0;k<4;++k){Vec3 q={};(&q.x)[axis]=(&half.x)[axis]*side;(&q.x)[a]=A[us[k]];(&q.x)[d]=D[vs[k]];Vec3 core={std::clamp(q.x,-inner.x,inner.x),std::clamp(q.y,-inner.y,inner.y),std::clamp(q.z,-inner.z,inner.z)},normal=normalized(sub(q,core));Vertex vertex={};vertex.position=point(add(center,add(core,mul(normal,radius))));vertex.normal=direction(normal);vertex.u=float(us[k])/8;vertex.v=float(vs[k])/8;p.vertices.push_back(vertex);}
                for(auto i:{0,1,2,0,2,3})p.indices.push_back(start+unsigned(i));
            }
        }room.parts.push_back(std::move(p));
    }
    void rim(const std::string&name,Vec3 center,float width,float depth,float corner,float thickness,Vec3 color){
        Vec3 points[48];for(int i=0;i<48;++i){int segment=i/12;float a=(-pi+segment*pi/2)+float(i%12)*pi/22;float x=(segment==0||segment==3?-1:1)*(width*.5f-corner),z=segment<2?-1.f:1.f;points[i]=add(center,{x+corner*cosf(a),0,z*(depth*.5f-corner)+corner*sinf(a)});}
        for(int i=0;i<48;++i)tube(name,points[i],points[(i+1)%48],thickness,color,8);
    }
    void frustum(const std::string&name,Vec3 p,float bottom,float top,float height,Vec3 color,int sides=32){
        for(int i=0;i<sides;++i){float a=i*2*pi/sides,A=(i+1)*2*pi/sides;Vec3 n=normalized({cosf((a+A)/2),(bottom-top)/height,sinf((a+A)/2)});
            face(name,add(p,{bottom*cosf(a),0,bottom*sinf(a)}),add(p,{bottom*cosf(A),0,bottom*sinf(A)}),add(p,{top*cosf(A),height,top*sinf(A)}),add(p,{top*cosf(a),height,top*sinf(a)}),n,color);
        }
    }
    void disc(const std::string&name,Vec3 p,float radius,Vec3 color,int sides=80){
        for(int i=0;i<sides;++i){float a=i*2*pi/sides,A=(i+1)*2*pi/sides;face(name,p,add(p,{radius*cosf(A),0,radius*sinf(A)}),add(p,{radius*cosf(a),0,radius*sinf(a)}),p,{0,1,0},color);}
    }
    void floor_crest(const std::string&name,Vec3 p,float height){
        int t=room.crest_texture;if(t<0)return;const auto&tex=room.textures[t];float w=height*float(tex.width)/float(tex.height);
        face(name,add(p,{-w/2,0,-height/2}),add(p,{w/2,0,-height/2}),add(p,{w/2,0,height/2}),add(p,{-w/2,0,height/2}),{0,1,0},{1,1,1},t,true);
    }
    void crest(const std::string&name,Vec3 center,float height){
        int t=room.crest_texture;if(t<0)return;const auto&tex=room.textures[t];float width=height*float(tex.width)/float(tex.height);
        face(name,add(center,{-width/2,height/2,0}),add(center,{width/2,height/2,0}),add(center,{width/2,-height/2,0}),add(center,{-width/2,-height/2,0}),{0,0,1},{1,1,1},t,true);
    }
    void panel(const std::string&name,Vec3 c,float width,float height,int texture){
        face(name,add(c,{-width/2,height/2,0}),add(c,{width/2,height/2,0}),add(c,{width/2,-height/2,0}),add(c,{-width/2,-height/2,0}),{0,0,1},{1,1,1},texture);
    }
    int texture(Texture t){room.textures.push_back(std::move(t));return int(room.textures.size())-1;}
    void batch(){
        // Keep a locker/item selectable as one object while batching its faces.
        using Key=std::tuple<std::string,int,bool,float,float,float>;
        std::map<Key,size_t>groups;std::vector<Part>parts;
        for(auto&p:room.parts){Key k{p.name,p.texture,p.blend,p.color.x,p.color.y,p.color.z};auto at=groups.find(k);
            if(at==groups.end()){groups.emplace(k,parts.size());parts.push_back(std::move(p));}
            else{auto&dst=parts[at->second];auto offset=uint32_t(dst.vertices.size());dst.vertices.insert(dst.vertices.end(),p.vertices.begin(),p.vertices.end());for(auto idx:p.indices)dst.indices.push_back(offset+idx);}
        }room.parts=std::move(parts);
    }
};
// Shared procedural materials and native ball placement, independent of each room.
Texture text_label(const std::wstring&,Vec3 background,Vec3 foreground,int height=64);
Texture surface_material(bool wood);
void sports_bottle(Builder&,const std::string&,Vec3,Vec3,int variation=0);
void game_ball(Builder&,const Model&,const std::string&,Vec3,float,std::map<int,int>&);
}
