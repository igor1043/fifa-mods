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
}
