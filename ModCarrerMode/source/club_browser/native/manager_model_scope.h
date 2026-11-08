#pragma once
// The committed market mapping is usable only by its live career/save owner.
// No SQLite, save mutation or club-specific model overwrite in the game DLL.
#include <string>
#include <map>
#include <sstream>
#include <cstdint>
#include <algorithm>
namespace managerModels {
using Fields=std::map<std::string,std::string>;
inline bool number(const std::string& s,uint64_t& out){out=0;if(s.empty()||s.size()>20)return false;for(char c:s){if(c<'0'||c>'9'||out>(UINT64_MAX-uint64_t(c-'0'))/10)return false;out=out*10+c-'0';}return true;}
inline bool fields(std::string text,Fields& out){out.clear();if(text.size()>524288)return false;if(text.compare(0,3,"\xef\xbb\xbf")==0)text.erase(0,3);std::istringstream in(text);std::string line;while(std::getline(in,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.empty())continue;auto p=line.find('=');if(p==std::string::npos||!p||!out.emplace(line.substr(0,p),line.substr(p+1)).second)return false;}return true;}
inline uint64_t value(const Fields& f,const char* key){auto it=f.find(key);uint64_t n=0;return it!=f.end()&&number(it->second,n)?n:0;}
inline std::string path(std::string p){if(p.compare(0,4,"\\\\?\\")==0)p.erase(0,4);std::replace(p.begin(),p.end(),'/','\\');for(char& c:p)if(c>='A'&&c<='Z')c+=32;return p;}
struct Scope{uint64_t pid=0,created=0,context=0,epoch=0,club=0,date=0;};
struct Mapping{Fields owner;std::map<int,int> clubs;};
inline bool parse(const std::string& text,Mapping& result){
 result={};if(text.size()>524288)return false;std::istringstream in(text);std::string line;if(!std::getline(in,line))return false;if(!line.empty()&&line.back()=='\r')line.pop_back();if(line!="S16MGR2")return false;
 while(std::getline(in,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.empty())continue;auto p=line.find('=');if(p==std::string::npos||!p)return false;auto key=line.substr(0,p),v=line.substr(p+1);if(key=="row"){auto sep=v.find('|');uint64_t club=0,asset=0;if(sep==std::string::npos||!number(v.substr(0,sep),club)||!number(v.substr(sep+1),asset)||!club||club>200000||asset>200000||result.clubs.size()>=4096||!result.clubs.emplace(int(club),int(asset)).second)return false;}else if(!result.owner.emplace(key,v).second)return false;}
 return value(result.owner,"schema")==2&&result.owner.count("path")&&result.owner.count("operation")&&result.owner.count("branch")&&result.owner.count("digest")&&result.owner.count("revision");
}
inline bool event(const Fields& e,const Scope& s){return value(e,"schema")==3&&value(e,"pid")==s.pid&&value(e,"process_created_100ns")==s.created&&value(e,"complete_file")==1&&e.count("save_type")&&e.at("save_type")=="SaveType_Career"&&e.count("path")&&e.count("operation")&&(e.at("operation")=="read"||e.at("operation")=="write")&&value(e,"access_tick_ms")>0;}
inline bool matches(const Mapping& m,const Scope& s,const Fields& e){auto& f=m.owner;return event(e,s)&&value(f,"pid")==s.pid&&value(f,"created")==s.created&&value(f,"context")==s.context&&value(f,"epoch")==s.epoch&&value(f,"club")==s.club&&value(f,"date")==s.date&&value(f,"access_tick_ms")==value(e,"access_tick_ms")&&f.at("operation")==e.at("operation")&&path(f.at("path"))==path(e.at("path"));}
}
