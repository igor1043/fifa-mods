#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <initializer_list>
#include <utility>
#include "entrance_selection.h"

static void directory(const char* root,const char* suffix){
    char path[MAX_PATH];_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\%s",root,suffix);
    assert(CreateDirectoryA(path,nullptr));
}
int main(){
    char temp[MAX_PATH],root[MAX_PATH],settings[MAX_PATH],metadata[MAX_PATH],context[MAX_PATH],name[81];
    assert(GetTempPathA(MAX_PATH,temp));assert(GetTempFileNameA(temp,"eid",0,root));
    assert(DeleteFileA(root));assert(CreateDirectoryA(root,nullptr));
    directory(root,"FSW");directory(root,"data");directory(root,"data\\sceneassets");
    directory(root,"data\\sceneassets\\entrance_props");directory(root,"data\\sceneassets\\entrance_props\\competitions");
    for(const char* id:{"195","245","9999","1738","1761","1764"}){
        char suffix[128];_snprintf_s(suffix,sizeof(suffix),_TRUNCATE,"data\\sceneassets\\entrance_props\\competitions\\%s",id);
        directory(root,suffix);
        _snprintf_s(metadata,MAX_PATH,_TRUNCATE,"%s\\%s\\asset.ini",root,suffix);
        assert(WritePrivateProfileStringA("asset","schema","1",metadata));
    }
    _snprintf_s(settings,MAX_PATH,_TRUNCATE,"%s\\FSW\\settings.ini",root);
    assert(!EntranceSelection::select(root,settings,195,245,name));
    assert(WritePrivateProfileStringA("movies","195","UEFA - Champions League",settings));
    assert(WritePrivateProfileStringA("comp","245","Stadium of final,10,3,0",settings));
    assert(WritePrivateProfileStringA("movies","0","Default must never select",settings));
    assert(WritePrivateProfileStringA("unrelated","9999","Never select",settings));
    assert(EntranceSelection::select(root,settings,195,245,name)&&!strcmp(name,"245"));
    assert(EntranceSelection::select(root,settings,195,219,name)&&!strcmp(name,"195"));
    assert(EntranceSelection::select(root,settings,195,9999,name)&&!strcmp(name,"195"));
    assert(!EntranceSelection::select(root,settings,9999,0,name));
    assert(!EntranceSelection::select(root,settings,0,0,name));
    assert(!EntranceSelection::configured(settings,1000000));
    _snprintf_s(metadata,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\245\\asset.ini",root);
    assert(DeleteFileA(metadata));
    assert(EntranceSelection::select(root,settings,195,245,name)&&!strcmp(name,"195"));
    assert(WritePrivateProfileStringA("movies","195",nullptr,settings));
    assert(!EntranceSelection::select(root,settings,195,245,name));
    assert(WritePrivateProfileStringA("SCOREBOARD","195","Any scoreboard name",settings));
    assert(EntranceSelection::select(root,settings,195,0,name)&&!strcmp(name,"195"));
    // Current competition/final IDs select exactly the identically named folder.
    // A phase has priority; missing phase packages inherit the main competition.
    assert(WritePrivateProfileStringA("movies","1761","Serie A",settings));
    assert(WritePrivateProfileStringA("comp","1764","Phase",settings));
    assert(EntranceSelection::select(root,settings,1761,1764,name)&&!strcmp(name,"1764"));
    assert(EntranceSelection::select(root,settings,1761,0,name)&&!strcmp(name,"1761"));
    _snprintf_s(metadata,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\1761\\asset.ini",root);
    assert(DeleteFileA(metadata));
    assert(!EntranceSelection::select(root,settings,1761,0,name));
    assert(WritePrivateProfileStringA("asset","schema","1",metadata));
    _snprintf_s(context,MAX_PATH,_TRUNCATE,"%s\\friendly_context.ini",root);
    unsigned resolved=0;bool isFriendly=false;char pid[16];
    _snprintf_s(pid,sizeof(pid),_TRUNCATE,"%lu",GetCurrentProcessId());
    assert(!EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    for(const auto& item:{std::pair<const char*,const char*>{"schema","1"},{"process_id",pid},{"home","1043"},
                        {"away","567"},{"competition","0"},{"round","0"},{"mode","friendly_same_league"},
                        {"league","13"},{"asset","1738"},{"resolved_competition","195"}})
        assert(WritePrivateProfileStringA("selection",item.first,item.second,context));
    assert(EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    assert(isFriendly&&resolved==195&&!strcmp(name,"195"));
    // Real cup/round cannot be replaced by league art, even when unsupported.
    assert(!EntranceSelection::select_match(root,settings,context,9999,0,1043,567,resolved,isFriendly,name)&&!isFriendly);
    assert(!EntranceSelection::select_match(root,settings,context,0,777,1043,567,resolved,isFriendly,name)&&!isFriendly);
    assert(EntranceSelection::select_match(root,settings,context,195,0,1043,567,resolved,isFriendly,name)&&!isFriendly);
    assert(!EntranceSelection::select_match(root,settings,context,0,0,569,567,resolved,isFriendly,name));
    assert(WritePrivateProfileStringA("selection","competition","1314",context));
    assert(!EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    assert(WritePrivateProfileStringA("selection","competition","0",context));
    assert(WritePrivateProfileStringA("selection","process_id","0",context));
    assert(!EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    assert(WritePrivateProfileStringA("selection","process_id",pid,context));
    assert(WritePrivateProfileStringA("selection","mode","none",context));
    assert(!EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    assert(WritePrivateProfileStringA("selection","mode","friendly_same_league",context));
    HANDLE handle=CreateFileA(context,FILE_WRITE_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,0,nullptr);
    assert(handle!=INVALID_HANDLE_VALUE);FILETIME stale{1,0};assert(SetFileTime(handle,nullptr,nullptr,&stale));CloseHandle(handle);
    assert(!EntranceSelection::select_match(root,settings,context,0,0,1043,567,resolved,isFriendly,name));
    assert(DeleteFileA(context));
    assert(DeleteFileA(settings));
    for(const char* id:{"195","245","9999","1738","1761","1764"}){
        _snprintf_s(metadata,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\asset.ini",root,id);
        if(strcmp(id,"245"))assert(DeleteFileA(metadata));
        char* slash=strrchr(metadata,'\\');*slash=0;assert(RemoveDirectoryA(metadata));
    }
    for(const char* suffix:{"data\\sceneassets\\entrance_props\\competitions","data\\sceneassets\\entrance_props","data\\sceneassets","data","FSW"}){
        _snprintf_s(metadata,MAX_PATH,_TRUNCATE,"%s\\%s",root,suffix);assert(RemoveDirectoryA(metadata));
    }
    assert(RemoveDirectoryA(root));puts("PASS exact phase override and main competition inheritance, same-league friendly, wrong clubs/process/stale context rejected");
}
