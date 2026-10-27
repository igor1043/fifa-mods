#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include "club_atlas.h"
static std::vector<unsigned char> fixture_model(){
    // A body triangle and a separate token quad, with no game assets required.
    const unsigned kinds[2]={0x587aa1,0x5878f4};
    std::vector<unsigned char> vertices;
    const CrestMesh::Vertex points[]={
        {0,0,0,0,1,0,1,0,0,0,0},{1,0,0,0,1,0,1,0,0,.25f,0},{0,1,1,0,1,0,1,0,0,0,.25f},
        {0,0,2,0,1,0,1,0,0,.5f,.5f},{1,0,2,0,1,0,1,0,0,.75f,.5f},
        {1,1,2,0,1,0,1,0,0,.75f,.75f},{0,1,2,0,1,0,1,0,0,.5f,.75f}};
    for(const auto& vertex:points)CrestMesh::encode(vertex,vertices);
    std::vector<unsigned char> vb(CrestMesh::aligned(16+vertices.size()));
    CrestMesh::put32(vb,0,(unsigned)vb.size());CrestMesh::put32(vb,4,7);CrestMesh::put32(vb,8,20);CrestMesh::put32(vb,12,1);memcpy(vb.data()+16,vertices.data(),vertices.size());
    const unsigned short indices[]={0,1,2,3,4,5,3,5,6};std::vector<unsigned char> ib(CrestMesh::aligned(16+sizeof(indices)));
    CrestMesh::put32(ib,0,(unsigned)ib.size());CrestMesh::put32(ib,4,9);CrestMesh::put32(ib,8,2);memcpy(ib.data()+16,indices,sizeof(indices));
    std::vector<unsigned char> raw(48);memcpy(raw.data(),"RX3l",4);CrestMesh::put32(raw,4,4);CrestMesh::put32(raw,12,2);
    const std::vector<unsigned char>* sections[2]={&vb,&ib};
    for(unsigned i=0;i<2;++i){CrestMesh::put32(raw,16+i*16,kinds[i]);CrestMesh::put32(raw,20+i*16,(unsigned)raw.size());CrestMesh::put32(raw,24+i*16,(unsigned)sections[i]->size());raw.insert(raw.end(),sections[i]->begin(),sections[i]->end());}
    CrestMesh::put32(raw,8,(unsigned)raw.size());return raw;
}
int main(int argc,char** argv){
    using ClubAtlas::Pixel;
    // Real IEEE half values, including subnormals, round-trip exactly.
    for(unsigned i=0;i<65536;++i)if(((i>>10)&31)!=31)
        assert(CrestMesh::half_bits(EntranceCatalog::half((unsigned short)i))==i);
    Pixel source[16],decoded[16];unsigned char block[16];
    for(unsigned i=0;i<16;++i)source[i]={220,35,25,(unsigned char)(i%2?255:0)};
    ClubAtlas::encode(source,block);ClubAtlas::decode(block,decoded,3);
    for(unsigned i=0;i<16;++i){assert(source[i].a==decoded[i].a);assert(decoded[i].r>200&&decoded[i].b<40);}
    for(unsigned i=0;i<16;++i)source[i].a=0;
    ClubAtlas::encode(source,block);ClubAtlas::decode(block,decoded,3);
    for(auto pixel:decoded)assert(pixel.a==0);
    std::vector<Pixel> ring(64,{255,0,0,0});
    for(unsigned y=1;y<7;++y)for(unsigned x=1;x<7;++x)if(x==1||x==6||y==1||y==6)ring[y*8+x].a=255;
    const auto mask=CrestMesh::rectangles(ring,8,8);assert(mask.size()==4);
    double area=0;for(const auto& r:mask)area+=(r.right-r.left)*(r.bottom-r.top);
    assert(fabs(area-20./64)<1e-6); // centre and background are holes, not quads
    std::vector<Pixel> empty;assert(CrestMesh::rectangles(empty,0,0).empty());
    EntranceCatalog::Asset asset{};asset.slots=1;asset.token[0]={2048,2048,1024,0};
    std::vector<unsigned char> raw=fixture_model(),result,missing;
    assert(CrestMesh::build(raw,asset,mask,mask,result));
    assert(CrestMesh::build(raw,asset,{}, {},missing));
    EntranceCatalog::Section before{},after{};assert(EntranceCatalog::sections(raw,0x5878f4,before));assert(EntranceCatalog::sections(missing,0x5878f4,after));
    assert(EntranceCatalog::word32(after.data+4)<EntranceCatalog::word32(before.data+4));
    char relative[MAX_PATH]={};
    // Optional integration check against a supplied installation; the regular
    // build remains portable and never requires this user's U: drive.
    if(argc>1){assert(EntranceCatalog::load(argv[1],"libertadores-group-knockout",1615,0,asset));
        assert(ClubAtlas::prepare(argv[1],asset,1043,101083,relative));assert(strstr(relative,"/alpha18_"));
        assert(ClubAtlas::prepare(argv[1],asset,1043,999999,relative));assert(strstr(relative,"1043_999999"));}
    else assert(!ClubAtlas::prepare("__missing_fixture_root__",asset,1043,101083,relative));
    raw[0]=0;assert(!CrestMesh::build(raw,asset,mask,mask,result));
    puts("PASS v18: crest alpha/holes, IEEE half, model parsing, transparent geometry, missing crests and corrupt mesh fail safely.");
}
