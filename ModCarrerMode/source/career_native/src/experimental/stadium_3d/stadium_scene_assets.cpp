#define NOMINMAX
#include "stadium_scene_assets.h"
#include "../../platform/mod_paths.h"
#include <windows.h>
#include <fstream>
#include <sstream>
#include <algorithm>
namespace stadium_scene {namespace {
const size_t max_bytes=512*1024*1024;
bool safe_key(const std::string&s){return !s.empty()&&s.size()<240&&s!="."&&s!=".."&&s.find_first_of("/\\:*?\"<>|\r\n")==s.npos;}
bool file(const std::string&path,std::vector<uint8_t>&raw){
    std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)return false;auto size=in.tellg();if(size<=0||size>std::streamoff(max_bytes))return false;
    raw.resize((size_t)size);in.seekg(0);return bool(in.read((char*)raw.data(),size));
}
// Windows' bundled libarchive reader. A stdout-only extraction into owned RAM;
// no -C, no filesystem extraction, no Python dependency and no game injection.
bool archive_command(const std::string&args,std::vector<uint8_t>&out,size_t cap){
    char directory[MAX_PATH]={};if(!GetSystemDirectoryA(directory,MAX_PATH))return false;
    std::string executable=std::string(directory)+"\\tar.exe",command="\""+executable+"\" "+args;
    SECURITY_ATTRIBUTES security={sizeof(security),nullptr,TRUE};HANDLE read=nullptr,write=nullptr;
    if(!CreatePipe(&read,&write,&security,1024*1024))return false;SetHandleInformation(read,HANDLE_FLAG_INHERIT,0);
    HANDLE nul=CreateFileA("NUL",GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,0,nullptr);
    STARTUPINFOA startup={sizeof(startup)};startup.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;startup.wShowWindow=SW_HIDE;
    startup.hStdOutput=write;startup.hStdError=nul;startup.hStdInput=nul;PROCESS_INFORMATION process={};
    BOOL started=CreateProcessA(executable.c_str(),command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&process);
    CloseHandle(write);if(nul!=INVALID_HANDLE_VALUE)CloseHandle(nul);if(!started){CloseHandle(read);return false;}
    bool ok=true;DWORD begin=GetTickCount();out.clear();
    for(;;){DWORD available=0;if(!PeekNamedPipe(read,nullptr,0,nullptr,&available,nullptr)){if(GetLastError()!=ERROR_BROKEN_PIPE)ok=false;break;}
        if(available){uint8_t buffer[65536];DWORD count=0;if(!ReadFile(read,buffer,std::min<DWORD>(available,sizeof(buffer)),&count,nullptr)||!count){ok=false;break;}
            if(out.size()+count>cap){ok=false;break;}out.insert(out.end(),buffer,buffer+count);
        }else if(WaitForSingleObject(process.hProcess,0)==WAIT_OBJECT_0)break;else Sleep(1);
        if(GetTickCount()-begin>30000){ok=false;break;}
    }
    if(!ok)TerminateProcess(process.hProcess,1);WaitForSingleObject(process.hProcess,2000);
    DWORD code=1;GetExitCodeProcess(process.hProcess,&code);CloseHandle(process.hThread);CloseHandle(process.hProcess);CloseHandle(read);
    if(!ok||code){out.clear();return false;}return true;
}
bool unpack(std::vector<uint8_t>&raw,std::vector<uint8_t>&decoded){
    if(raw.size()>=4&&!memcmp(raw.data(),"RX3",3)){decoded=std::move(raw);return true;}
    bool ok=fifa_player::decode_container(raw,decoded,max_bytes);raw.clear();raw.shrink_to_fit();return ok;
}
Preview finish(std::vector<uint8_t>&mesh,std::vector<uint8_t>&textures,Preview result){
    auto model=std::make_shared<fifa_player::Model>();
    if(fifa_player::read_stadium(mesh,textures,*model))result.model=std::move(model);
    else result.error="Este modelo de estádio ainda não é compatível com a prévia 3D.";
    return result;
}
Preview package(const std::string&root,const std::string&key,Preview result){
    std::string base=root+"/StadiumGBD/"+key;std::vector<uint8_t>raw,mesh,textures;
    if(file(base+"/model.rx3",raw)&&unpack(raw,mesh)&&file(base+"/texture_day.rx3",raw)&&unpack(raw,textures)){
        result.source=base;return finish(mesh,textures,std::move(result));}
    for(const char*ext:{".zip",".rar"}){
        std::string path=base+ext;if(GetFileAttributesA(path.c_str())==INVALID_FILE_ATTRIBUTES)continue;
        std::vector<uint8_t>listing;if(!archive_command("-tf \""+path+"\"",listing,1024*1024)){result.error="Não foi possível ler o pacote do estádio.";continue;}
        std::istringstream lines(std::string(listing.begin(),listing.end()));std::string entry,model_entry,texture_entry;
        while(std::getline(lines,entry)){if(!entry.empty()&&entry.back()=='\r')entry.pop_back();
            if(entry.empty()||entry.size()>1024||entry.find('"')!=entry.npos||entry.find("..")!=entry.npos||entry.front()=='/'||entry.front()=='\\'||entry.find(':')!=entry.npos)continue;
            if(entry=="model.rx3"||(entry.size()>10&&entry.compare(entry.size()-10,10,"/model.rx3")==0))model_entry=entry;
        }
        if(model_entry.empty()){result.error="O pacote não contém o modelo do estádio.";continue;}texture_entry=model_entry.substr(0,model_entry.size()-9)+"texture_day.rx3";
        if(!archive_command("-xOf \""+path+"\" -- \""+model_entry+"\"",raw,max_bytes)||!unpack(raw,mesh)){result.error="Não foi possível ler a geometria do estádio.";continue;}
        if(!archive_command("-xOf \""+path+"\" -- \""+texture_entry+"\"",raw,max_bytes)||!unpack(raw,textures)){result.error="Não foi possível ler as texturas do estádio.";continue;}
        result.source=path;return finish(mesh,textures,std::move(result));
    }
    if(result.error.empty())result.error="Modelo 3D não disponível para este estádio.";return result;
}
}
Preview original(const std::string&root,int id){
    Preview result;result.stadium=id;result.name="Estádio original";if(id<=0||id>10000){result.error="Estádio não identificado.";return result;}
    fifa_player::Assets assets(root);std::string base="data/sceneassets/stadium/stadium_"+std::to_string(id);std::vector<uint8_t>mesh,textures;
    if(!assets.read_packaged(base+".rx3",mesh)||!assets.read_packaged(base+"_1_textures.rx3",textures)){result.error="Modelo 3D não disponível para este estádio.";return result;}
    result.source=base+".rx3";return finish(mesh,textures,std::move(result));
}
Preview load(const std::string&root,int club,const std::string&preferred){
    Preview result;if(club<=0||club>200000){result.error="Clube não identificado.";return result;}
    std::ifstream in(career_paths::read(root+"/ModCarrerMode","data\\catalogs","club_stadium_fallback.tsv"));std::string line,key=preferred;
    while(std::getline(in,line)){std::istringstream row(line);std::string f[5];for(auto&i:f)std::getline(row,i,'|');
        if(atoi(f[0].c_str())!=club)continue;result.stadium=atoi(f[1].c_str());result.capacity=atoi(f[2].c_str());result.name=f[3];if(key.empty())key=f[4];break;}
    // A configured custom stadium never silently becomes a different arena.
    result.key=key;
    if(!key.empty()){if(!safe_key(key)){result.error="Referência de estádio inválida.";return result;}return package(root,key,std::move(result));}
    auto native=original(root,result.stadium);native.name=result.name;native.capacity=result.capacity;return native;
}
}
