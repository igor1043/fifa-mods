#pragma once
#include <windows.h>
#include <string>
#include <vector>
#include <cstdint>
#include <algorithm>
namespace room_helper {
struct Retry {
 uint64_t next=0;unsigned failures=0;
 bool due(uint64_t now)const{return now>=next;}
 void failed(uint64_t now){if(failures<4)++failures;next=now+(failures==1?5000:failures==2?10000:failures==3?20000:30000);}
 void started(uint64_t now){next=now+1000;}
};
inline std::vector<wchar_t> independentEnvironment(){
 std::vector<wchar_t> out;std::vector<std::wstring> entries;auto*block=GetEnvironmentStringsW();
 if(block){for(auto*p=block;*p;p+=wcslen(p)+1){
  constexpr wchar_t key[]=L"PYINSTALLER_RESET_ENVIRONMENT=";
  if(_wcsnicmp(p,key,(sizeof(key)/sizeof(wchar_t))-1)==0)continue;
  entries.emplace_back(p);
 }FreeEnvironmentStringsW(block);}
 entries.emplace_back(L"PYINSTALLER_RESET_ENVIRONMENT=1");
 std::sort(entries.begin(),entries.end(),[](const auto&a,const auto&b){return _wcsicmp(a.c_str(),b.c_str())<0;});
 for(const auto&entry:entries){out.insert(out.end(),entry.begin(),entry.end());out.push_back(0);}
 out.push_back(0);return out;
}
inline bool spawn(const wchar_t*exe,std::wstring command,const wchar_t*cwd,const wchar_t*logPath,HANDLE&child,DWORD&error){
 child=nullptr;error=0;SECURITY_ATTRIBUTES security{sizeof(security),nullptr,TRUE};
 HANDLE output=CreateFileW(logPath,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
 if(output==INVALID_HANDLE_VALUE){error=GetLastError();return false;}
 // Only these two handles may enter the child; never inherit the game's other handles.
 if(!SetHandleInformation(output,HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT)){error=GetLastError();CloseHandle(output);return false;}
 HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
 if(input==INVALID_HANDLE_VALUE){error=GetLastError();CloseHandle(output);return false;}
 SIZE_T bytes=0;InitializeProcThreadAttributeList(nullptr,1,0,&bytes);std::vector<unsigned char> storage(bytes);
 STARTUPINFOEXW startup{};startup.StartupInfo.cb=sizeof(startup);startup.StartupInfo.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;
 startup.StartupInfo.wShowWindow=SW_HIDE;startup.StartupInfo.hStdInput=input;startup.StartupInfo.hStdOutput=output;startup.StartupInfo.hStdError=output;
 startup.lpAttributeList=reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(storage.data());
 const bool initialized=InitializeProcThreadAttributeList(startup.lpAttributeList,1,0,&bytes)!=FALSE;
 HANDLE inherited[]={input,output};PROCESS_INFORMATION process{};bool success=false;
 if(initialized&&UpdateProcThreadAttribute(startup.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,inherited,sizeof(inherited),nullptr,nullptr)){
  auto environment=independentEnvironment();
  success=CreateProcessW(exe,command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|CREATE_UNICODE_ENVIRONMENT|EXTENDED_STARTUPINFO_PRESENT,environment.data(),cwd,&startup.StartupInfo,&process)!=FALSE;
 }
 if(!success)error=GetLastError();
 if(initialized)DeleteProcThreadAttributeList(startup.lpAttributeList);
 CloseHandle(output);CloseHandle(input);
 if(success){CloseHandle(process.hThread);child=process.hProcess;}return success;
}
inline HANDLE existingWorker(unsigned gamePid,unsigned markerGame,unsigned helperPid,const wchar_t*expectedExe){
 if(gamePid!=markerGame||!helperPid)return nullptr;
 HANDLE worker=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,helperPid);
 if(!worker)return nullptr;
 wchar_t path[32768]{};DWORD length=32768;FILETIME created{},exit{},kernel{},user{},gameCreated{};
 const bool valid=WaitForSingleObject(worker,0)==WAIT_TIMEOUT&&QueryFullProcessImageNameW(worker,0,path,&length)&&
  _wcsicmp(path,expectedExe)==0&&GetProcessTimes(worker,&created,&exit,&kernel,&user)&&
  GetProcessTimes(GetCurrentProcess(),&gameCreated,&exit,&kernel,&user)&&CompareFileTime(&created,&gameCreated)>=0;
 if(!valid){CloseHandle(worker);return nullptr;}return worker;
}
}
