#pragma once
#include <map>
#include <fstream>
#include <filesystem>
#include <string>
#include <vector>
#include "graphics.h"
namespace clublineup {
namespace fs=std::filesystem;
struct View{
 fs::path folder;uint64_t sequence=0,lastPoll=0;int club=0,career=0;std::string status="loading",message;HANDLE job=nullptr;
 void configure(const fs::path& game){folder=game/L"ModCarrerMode/runtime/club_browser"/std::to_wstring(GetCurrentProcessId());std::error_code error;fs::create_directories(folder,error);}
 bool startWorker(const fs::path& game){
  configure(game);auto exe=game/L"Server16Python.exe";if(!fs::is_regular_file(exe))return false;
  // A reused Windows PID must not replay an earlier session's request.
  std::error_code cleanup;fs::remove(folder/L"request.tsv",cleanup);fs::remove(folder/L"status.tsv",cleanup);
  std::vector<wchar_t> environment;auto strings=GetEnvironmentStringsW();if(!strings)return false;
  for(auto* p=strings;*p;p+=wcslen(p)+1){std::wstring entry=p;if(entry.rfind(L"SERVER16_CLUB_BROWSER_WORKER=",0)==0||entry.rfind(L"SERVER16_TRANSFER_MARKET_WORKER=",0)==0)continue;environment.insert(environment.end(),entry.begin(),entry.end());environment.push_back(0);}FreeEnvironmentStringsW(strings);
  const std::wstring flag=L"SERVER16_CLUB_BROWSER_WORKER=1";environment.insert(environment.end(),flag.begin(),flag.end());environment.push_back(0);environment.push_back(0);
  std::wstring command=L"\""+exe.wstring()+L"\" --club-environment-worker preview --game-root \""+game.wstring()+L"\" --pid "+std::to_wstring(GetCurrentProcessId());
  STARTUPINFOW startup{};startup.cb=sizeof startup;startup.dwFlags=STARTF_USESHOWWINDOW|STARTF_USESTDHANDLES;startup.wShowWindow=SW_HIDE;
  SECURITY_ATTRIBUTES security{sizeof security,nullptr,TRUE};HANDLE output=CreateFileW((folder/L"worker.log").c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,0,nullptr);
  if(output==INVALID_HANDLE_VALUE||input==INVALID_HANDLE_VALUE){if(output!=INVALID_HANDLE_VALUE)CloseHandle(output);if(input!=INVALID_HANDLE_VALUE)CloseHandle(input);return false;}
  startup.hStdOutput=startup.hStdError=output;startup.hStdInput=input;PROCESS_INFORMATION process{};
  job=CreateJobObjectW(nullptr,nullptr);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
  bool ok=job&&SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limits,sizeof limits)&&CreateProcessW(exe.c_str(),command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|CREATE_UNICODE_ENVIRONMENT|CREATE_SUSPENDED,environment.data(),game.c_str(),&startup,&process);
  CloseHandle(output);CloseHandle(input);
  if(ok){ok=AssignProcessToJobObject(job,process.hProcess)!=FALSE;if(ok)ok=ResumeThread(process.hThread)!=DWORD(-1);if(!ok)TerminateProcess(process.hProcess,1);CloseHandle(process.hThread);CloseHandle(process.hProcess);}
  if(!ok&&job){CloseHandle(job);job=nullptr;}return ok;
 }
 void stop(){if(job){CloseHandle(job);job=nullptr;}}
 bool request(int id){
  club=id;sequence=(std::max)(sequence+1,GetTickCount64());status="loading";message.clear();lastPoll=0;
  std::error_code error;fs::create_directories(folder,error);if(error){status="error";message="Não foi possível preparar a visualização.";return false;}
  auto target=folder/L"request.tsv",temp=folder/L"request.new";{
   std::ofstream out(temp,std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<sequence<<"\nclub="<<club<<"\n";if(!out){status="error";return false;}
  }
  if(!MoveFileExW(temp.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){status="error";message="Não foi possível enviar o pedido de visualização.";return false;}return true;
 }
 void poll(ID3D11Device* device){
  if(status!="loading"||GetTickCount64()-lastPoll<50)return;lastPoll=GetTickCount64();if(lastPoll-sequence>140000){status="error";message="A renderização demorou mais que o esperado. Selecione novamente para tentar de novo.";return;}std::error_code error;auto file=folder/L"status.tsv";auto size=fs::file_size(file,error);if(error||size>4096)return;
  std::ifstream input(file,std::ios::binary);std::map<std::string,std::string> values;std::string line;while(std::getline(input,line)){auto equal=line.find('=');if(equal!=std::string::npos)values.emplace(line.substr(0,equal),line.substr(equal+1));}
  try{if(values["schema"]!="1"||std::stoul(values["pid"])!=GetCurrentProcessId()||std::stoull(values["seq"])!=sequence||std::stoi(values["club"])!=club)return;}catch(...){return;}
  if(values["status"]=="error"){status="error";message=values["message"].substr(0,250);return;}
  if(values["status"]!="ready"||values["players"]!="11")return;
  clubscene::Assets assets;assets.sequence=sequence;assets.club=club;assets.career=career;assets.hash=values["hash"];std::array<int,clubscene::slots> bindings{};
  try{assets.pages=std::stoi(values["pages"]);std::istringstream in(values["bindings"]);std::string field;for(auto& b:bindings){if(!std::getline(in,field,','))return;b=std::stoi(field);if(b<0||b>=assets.pages)return;}if(std::getline(in,field,','))return;}catch(...){return;}
  if(values["renderer"]!="native"||!clubscene::validAssets(assets))return;
  clubscene::submit(assets,bindings);status="ready";
 }
};
}
