#pragma once

// settings.ini is the only list of competition/round IDs. Names in its values
// belong to movies, scoreboards and stadiums; they are never model redirects.
namespace EntranceSelection {
static bool configured(const char* settings,unsigned id){
    if(!id||id>=1000000)return false;
    char key[16],value[2]={};
    _snprintf_s(key,sizeof(key),_TRUNCATE,"%u",id);
    for(const char* section:{"movies","Scoreboard","comp"})
        if(GetPrivateProfileStringA(section,key,"",value,sizeof(value),settings)>0)return true;
    return false;
}
static bool select(const char* game,const char* settings,unsigned competition,unsigned round,char (&name)[81]){
    name[0]=0;
    const DWORD attributes=GetFileAttributesA(settings);
    if(attributes==INVALID_FILE_ATTRIBUTES||(attributes&FILE_ATTRIBUTE_DIRECTORY))return false;
    for(unsigned id:{round,competition}){
        if(!configured(settings,id))continue;
        char path[MAX_PATH],key[16];
        _snprintf_s(key,sizeof(key),_TRUNCATE,"%u",id);
        if(_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\asset.ini",game,key)<0)continue;
        const DWORD file=GetFileAttributesA(path);
        if(file!=INVALID_FILE_ATTRIBUTES&&!(file&FILE_ATTRIBUTE_DIRECTORY)){strcpy_s(name,key);return true;}
    }
    return false;
}
static bool friendly(const char* game,const char* settings,const char* context,unsigned home,unsigned away,
                     unsigned& competition,char (&name)[81]){
    competition=0;name[0]=0;
    // Reject context left by another run or a different match. This file is
    // written atomically by Server16; settings.ini still owns allowed IDs.
    WIN32_FILE_ATTRIBUTE_DATA file{};FILETIME created{},exited{},kernel{},user{};
    if(!GetFileAttributesExA(context,GetFileExInfoStandard,&file)||
       !GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user)||
       CompareFileTime(&file.ftLastWriteTime,&created)<0)return false;
    if(GetPrivateProfileIntA("selection","schema",0,context)!=1||
       GetPrivateProfileIntA("selection","process_id",0,context)!=GetCurrentProcessId()||
       !home||!away||GetPrivateProfileIntA("selection","home",0,context)!=home||
       GetPrivateProfileIntA("selection","away",0,context)!=away||
       GetPrivateProfileIntA("selection","competition",1,context)!=0||
       GetPrivateProfileIntA("selection","round",1,context)!=0)return false;
    char mode[64]={};GetPrivateProfileStringA("selection","mode","",mode,sizeof(mode),context);
    if(strcmp(mode,"friendly_same_league"))return false;
    const unsigned league=GetPrivateProfileIntA("selection","league",0,context);
    const unsigned asset=GetPrivateProfileIntA("selection","asset",0,context);
    if(!league||league>=1000000||!select(game,settings,asset,0,name))return false;
    competition=asset;return true;
}
static bool select_match(const char* game,const char* settings,const char* context,unsigned competition,unsigned round,
                         unsigned home,unsigned away,unsigned& resolved,bool& isFriendly,char (&name)[81]){
    isFriendly=false;resolved=competition;
    if(competition||round)return select(game,settings,competition,round,name);
    isFriendly=friendly(game,settings,context,home,away,resolved,name);
    return isFriendly;
}
}
