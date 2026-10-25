#pragma once
#include <map>
#include <fstream>
#include <filesystem>
#include <string>
#include <vector>
#include "../../club_environment/room/native/room_helper_process_r61.h"
#include "graphics.h"
namespace clublineup {
namespace fs=std::filesystem;
struct View{
 fs::path folder,gameRoot;uint64_t sequence=0,lastPoll=0;int club=0,career=0;std::string status="loading",message;HANDLE job=nullptr,child=nullptr;
 void configure(const fs::path& game){gameRoot=game;folder=game/L"ModCarrerMode/runtime/club_browser"/std::to_wstring(GetCurrentProcessId());std::error_code error;fs::create_directories(folder,error);}
 bool running()const{return child&&WaitForSingleObject(child,0)==WAIT_TIMEOUT;}
 void launchLog(const char* event,DWORD error=0){std::ofstream out(folder/L"launcher.log",std::ios::app);out<<GetTickCount64()<<" "<<event<<" win32="<<error<<"\n";}
 bool startWorker(const fs::path& game){
  if(running())return true;stop();configure(game);auto exe=game/L"Server16Python.exe";if(!fs::is_regular_file(exe)){launchLog("MISSING_SERVER16",ERROR_FILE_NOT_FOUND);return false;}
  // A reused Windows PID must not replay an earlier session's request.
  std::error_code cleanup;fs::remove(folder/L"request.tsv",cleanup);fs::remove(folder/L"status.tsv",cleanup);
  // FIFA can inherit the frozen Server's extraction directory. This is an
  // independent helper and must survive a closed/restarted Server session.
  auto inherited=room_helper::independentEnvironment();std::vector<std::wstring> entries;
  for(auto* p=inherited.data();*p;p+=wcslen(p)+1){if(_wcsnicmp(p,L"SERVER16_CLUB_BROWSER_WORKER=",29)==0||_wcsnicmp(p,L"SERVER16_TRANSFER_MARKET_WORKER=",32)==0)continue;entries.emplace_back(p);}
  entries.emplace_back(L"SERVER16_CLUB_BROWSER_WORKER=1");std::sort(entries.begin(),entries.end(),[](const auto&a,const auto&b){return _wcsicmp(a.c_str(),b.c_str())<0;});std::vector<wchar_t> environment;
  for(const auto&entry:entries){environment.insert(environment.end(),entry.begin(),entry.end());environment.push_back(0);}environment.push_back(0);
  std::wstring command=L"\""+exe.wstring()+L"\" --club-environment-worker preview --game-root \""+game.wstring()+L"\" --pid "+std::to_wstring(GetCurrentProcessId());
  STARTUPINFOEXW startup{};startup.StartupInfo.cb=sizeof startup;startup.StartupInfo.dwFlags=STARTF_USESHOWWINDOW|STARTF_USESTDHANDLES;startup.StartupInfo.wShowWindow=SW_HIDE;
  SECURITY_ATTRIBUTES security{sizeof security,nullptr,TRUE};HANDLE output=CreateFileW((folder/L"worker.log").c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,0,nullptr);
  if(output==INVALID_HANDLE_VALUE||input==INVALID_HANDLE_VALUE){if(output!=INVALID_HANDLE_VALUE)CloseHandle(output);if(input!=INVALID_HANDLE_VALUE)CloseHandle(input);return false;}
  startup.StartupInfo.hStdOutput=startup.StartupInfo.hStdError=output;startup.StartupInfo.hStdInput=input;PROCESS_INFORMATION process{};
  SIZE_T bytes=0;InitializeProcThreadAttributeList(nullptr,1,0,&bytes);std::vector<unsigned char> storage(bytes);startup.lpAttributeList=reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(storage.data());
  const bool initialized=InitializeProcThreadAttributeList(startup.lpAttributeList,1,0,&bytes)!=FALSE;HANDLE handles[]={input,output};
  const bool restricted=initialized&&UpdateProcThreadAttribute(startup.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,handles,sizeof handles,nullptr,nullptr);
  job=CreateJobObjectW(nullptr,nullptr);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
  bool ok=restricted&&job&&SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limits,sizeof limits)&&CreateProcessW(exe.c_str(),command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|CREATE_UNICODE_ENVIRONMENT|CREATE_SUSPENDED|EXTENDED_STARTUPINFO_PRESENT,environment.data(),game.c_str(),&startup.StartupInfo,&process);
  DWORD error=ok?0:GetLastError();if(initialized)DeleteProcThreadAttributeList(startup.lpAttributeList);
  CloseHandle(output);CloseHandle(input);
  if(ok){ok=AssignProcessToJobObject(job,process.hProcess)!=FALSE;if(ok)ok=ResumeThread(process.hThread)!=DWORD(-1);if(!ok){error=GetLastError();TerminateProcess(process.hProcess,1);}CloseHandle(process.hThread);if(ok)child=process.hProcess;else CloseHandle(process.hProcess);}
  if(!ok&&job){CloseHandle(job);job=nullptr;}launchLog(ok?"WORKER_STARTED_INDEPENDENT":"WORKER_START_FAILED",error);return ok;
 }
 void stop(){if(job){CloseHandle(job);job=nullptr;}if(child){CloseHandle(child);child=nullptr;}}
 bool request(int id){
  if(!running()&&!startWorker(gameRoot)){status="error";message="Não foi possível iniciar o auxiliar dos titulares. Consulte launcher.log.";return false;}
  club=id;sequence=(std::max)(sequence+1,GetTickCount64());status="loading";message.clear();lastPoll=0;
  std::error_code error;fs::create_directories(folder,error);if(error){status="error";message="Não foi possível preparar a visualização.";return false;}
  auto target=folder/L"request.tsv",temp=folder/L"request.new";{
   std::ofstream out(temp,std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<sequence<<"\nclub="<<club<<"\n";if(!out){status="error";return false;}
  }
  if(!MoveFileExW(temp.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){status="error";message="Não foi possível enviar o pedido de visualização.";return false;}return true;
 }
 void poll(ID3D11Device* device){
  if(status!="loading"||GetTickCount64()-lastPoll<50)return;lastPoll=GetTickCount64();if(child&&!running()){DWORD exit=0;GetExitCodeProcess(child,&exit);launchLog("WORKER_EXITED",exit);status="error";message="O auxiliar dos titulares encerrou. Selecione Atualizar para tentar novamente; consulte worker.log.";return;}if(lastPoll-sequence>140000){status="error";message="A renderização demorou mais que o esperado. Selecione novamente para tentar de novo.";return;}std::error_code error;auto file=folder/L"status.tsv";auto size=fs::file_size(file,error);if(error||size>4096)return;
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
