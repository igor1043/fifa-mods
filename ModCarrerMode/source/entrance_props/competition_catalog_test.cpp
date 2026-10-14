#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "club_atlas.h"
int main(int argc,char** argv){
    if(argc<3)return 2;
    if(!strcmp(argv[2],"--all-mesh")){
        std::vector<unsigned char> crestRaw;std::vector<ClubAtlas::Pixel> pixels;unsigned w=0,h=0;
        char path[MAX_PATH];_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\ui\\imgAssets\\crest\\light\\l1043.dds",argv[1]);
        if(!ClubAtlas::file(path,crestRaw)||!ClubAtlas::crest(crestRaw,pixels,w,h))return 5;
        auto mask=CrestMesh::rectangles(pixels,w,h);
        _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\*",argv[1]);
        WIN32_FIND_DATAA row{};HANDLE iterator=FindFirstFileA(path,&row);if(iterator==INVALID_HANDLE_VALUE)return 6;
        unsigned checked=0,trimmed=0;
        do {if(!(row.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)||!EntranceCatalog::slug(row.cFileName))continue;
            EntranceCatalog::Asset a{};if(!EntranceCatalog::load(argv[1],row.cFileName,1615,0,a)){printf("FAILED %s catalog\n",row.cFileName);FindClose(iterator);return 7;}
            ++checked;if(!a.slots)continue;
            std::vector<unsigned char> raw,model;_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\model.rx3",argv[1],row.cFileName);
            if(!ClubAtlas::file(path,raw)||!CrestMesh::build(raw,a,mask,mask,model)){printf("FAILED %s geometry\n",row.cFileName);FindClose(iterator);return 8;}
            EntranceCatalog::Section vb{},ib{};EntranceCatalog::sections(raw,0x587aa1,vb);EntranceCatalog::sections(raw,0x5878f4,ib);
            unsigned slots[64]={},indices=EntranceCatalog::word32(ib.data+4),width=EntranceCatalog::word32(ib.data+8);
            for(unsigned i=0;i<indices;i+=3){CrestMesh::Vertex tri[3];for(unsigned k=0;k<3;++k){auto p=ib.data+16+(size_t)(i+k)*width;unsigned index=width==2?EntranceCatalog::word16(p):EntranceCatalog::word32(p);tri[k]=CrestMesh::decode(vb.data+16+(size_t)index*20);}
                for(unsigned s=0;s<a.slots;++s)if(CrestMesh::in_slot(tri[0],a.token[s])&&CrestMesh::in_slot(tri[1],a.token[s])&&CrestMesh::in_slot(tri[2],a.token[s]))++slots[s];}
            for(unsigned s=0;s<a.slots;++s)if(!slots[s]){printf("FAILED %s token %u has no surface\n",row.cFileName,s);FindClose(iterator);return 10;}
            ++trimmed;
        }while(FindNextFileA(iterator,&row));FindClose(iterator);
        printf("PASS catalog=%u transparent_meshes=%u\n",checked,trimmed);return checked==147&&trimmed==106?0:9;
    }
    EntranceCatalog::Asset asset{};
    if(!EntranceCatalog::load(argv[1],argv[2],1615,0,asset)){puts("REJECTED");return 1;}
    char path[MAX_PATH]={};
    if(argc>3){
        unsigned home=argc>4?(unsigned)atoi(argv[4]):1043,away=argc>5?(unsigned)atoi(argv[5]):567;
        if(asset.slots&&!ClubAtlas::prepare(argv[1],asset,home,away,path)){puts("ATLAS_FAILED");return 3;}
        if(!asset.slots&&ClubAtlas::prepare(argv[1],asset,home,away,path))return 4;
    }
    printf("VALID slots=%u stamp=%016llx texture=%s\n",asset.slots,asset.stamp,path);
    return 0;
}
