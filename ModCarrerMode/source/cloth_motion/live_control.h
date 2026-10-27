#pragma once
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <cctype>

namespace cloth_control {
inline char* trim(char* text) {
    while(*text&&std::isspace(static_cast<unsigned char>(*text)))++text;
    size_t n=std::strlen(text);while(n&&std::isspace(static_cast<unsigned char>(text[n-1])))text[--n]=0;
    return text;
}
inline int parse_enabled(char* data) {
    bool section=false;int result=-1;char* context=nullptr;
    if(std::strlen(data)>=3&&static_cast<unsigned char>(data[0])==0xef&&
       static_cast<unsigned char>(data[1])==0xbb&&static_cast<unsigned char>(data[2])==0xbf)data+=3;
    for(char* line=strtok_s(data,"\r\n",&context);line;line=strtok_s(nullptr,"\r\n",&context)) {
        line=trim(line);if(*line==';'||*line=='#'||!*line)continue;
        if(*line=='[') {const auto end=std::strchr(line,']');if(!end)return -1;*end=0;section=_stricmp(trim(line+1),"cloth_motion")==0;continue;}
        if(!section)continue;char* equals=std::strchr(line,'=');if(!equals)continue;*equals=0;
        if(_stricmp(trim(line),"enabled"))continue;
        char* value=trim(equals+1);char* comment=std::strpbrk(value,";#");if(comment)*comment=0;value=trim(value);
        if(!std::strcmp(value,"0"))result=0;else if(!std::strcmp(value,"1"))result=1;else return -1;
    }
    return result;
}
inline int read_enabled(const char* path) {
    HANDLE file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return -1;
    char data[65537]{};DWORD size=0;const auto bytes=GetFileSize(file,nullptr);
    const bool ok=bytes>0&&bytes<=65536&&ReadFile(file,data,bytes,&size,nullptr)&&size==bytes;
    CloseHandle(file);return ok?parse_enabled(data):-1;
}
inline bool publish(const char* path,bool enabled) {
    char temporary[MAX_PATH]{},data[128]{};
    if(sprintf_s(temporary,"%s.%lu.tmp",path,GetCurrentProcessId())<0)return false;
    const int size=sprintf_s(data,"CM1 %lu %llu %u\n",GetCurrentProcessId(),GetTickCount64(),enabled?1u:0u);
    HANDLE file=CreateFileA(temporary,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;DWORD written=0;
    const bool ok=WriteFile(file,data,static_cast<DWORD>(size),&written,nullptr)&&written==static_cast<DWORD>(size);
    CloseHandle(file);
    if(ok&&MoveFileExA(temporary,path,MOVEFILE_REPLACE_EXISTING))return true;
    DeleteFileA(temporary);return false;
}
}
