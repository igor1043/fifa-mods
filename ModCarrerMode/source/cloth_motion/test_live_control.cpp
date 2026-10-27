#include "live_control.h"
#define CHECK(c) do {if(!(c)){std::fprintf(stderr,"FAIL live control line %d: %s\n",__LINE__,#c);return 1;}}while(false)
int main() {
    char valid[]="\xef\xbb\xbf[other]\nenabled=0\n[cloth_motion]\n ; keep\n enabled = 1 ; note\n[other2]\nenabled=0\n";
    CHECK(cloth_control::parse_enabled(valid)==1);
    char off[]="[cloth_motion]\nenabled=0\n";CHECK(cloth_control::parse_enabled(off)==0);
    char invalid[]="[cloth_motion]\nenabled=invalid\n";CHECK(cloth_control::parse_enabled(invalid)==-1);
    char missing[]="[other]\nenabled=1\n";CHECK(cloth_control::parse_enabled(missing)==-1);
    char folder[MAX_PATH]{},path[MAX_PATH]{};CHECK(GetTempPathA(MAX_PATH,folder)>0&&GetTempFileNameA(folder,"clt",0,path));
    FILE* file=nullptr;CHECK(!fopen_s(&file,path,"wb")&&file);std::fputs("[cloth_motion]\nenabled=1\n",file);std::fclose(file);
    CHECK(cloth_control::read_enabled(path)==1);
    char replaced[MAX_PATH]{};sprintf_s(replaced,"%s.new",path);
    CHECK(!fopen_s(&file,replaced,"wb")&&file);std::fputs("[cloth_motion]\nenabled=0\n",file);std::fclose(file);
    CHECK(MoveFileExA(replaced,path,MOVEFILE_REPLACE_EXISTING));CHECK(cloth_control::read_enabled(path)==0);
    CHECK(cloth_control::publish(path,false));CHECK(!fopen_s(&file,path,"rb")&&file);
    char data[128]{};CHECK(std::fgets(data,sizeof(data),file));std::fclose(file);
    unsigned long pid=0,value=9;unsigned long long tick=0;
    CHECK(sscanf_s(data,"CM1 %lu %llu %lu",&pid,&tick,&value)==3&&pid==GetCurrentProcessId()&&value==0&&GetTickCount64()-tick<1000);
    CHECK(DeleteFileA(path));CHECK(cloth_control::read_enabled(path)==-1);
    std::puts("live control: strict INI parsing, atomic external toggle, native acknowledgement and missing-file fallback passed");return 0;
}
