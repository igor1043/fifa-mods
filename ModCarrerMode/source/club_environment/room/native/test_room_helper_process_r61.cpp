#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "room_helper_process_r61.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cassert>
int wmain(int argc,wchar_t**argv){
 using namespace room_helper;
 if(argc==3&&std::wstring(argv[1])==L"--child"){
  wchar_t reset[8]{};GetEnvironmentVariableW(L"PYINSTALLER_RESET_ENVIRONMENT",reset,8);
  std::ofstream out{std::filesystem::path(argv[2])};out<<(_wcsicmp(reset,L"1")==0?"reset-ok":"reset-missing");
  std::cout<<"captured child stdout\n";std::cerr<<"captured child stderr\n";return 23;
 }
 Retry retry;assert(retry.due(0));retry.failed(100);assert(!retry.due(5099));assert(retry.due(5100));
 retry.failed(5100);assert(!retry.due(15099));assert(retry.due(15100));
 for(int n=0;n<10;++n)retry.failed(20000);assert(retry.next==50000);
 wchar_t self[32768]{},temporary[MAX_PATH]{};GetModuleFileNameW(nullptr,self,32768);GetTempPathW(MAX_PATH,temporary);
 auto root=std::filesystem::path(temporary)/(L"FIFA Vestiário helper test "+std::to_wstring(GetCurrentProcessId()));
 std::filesystem::create_directories(root);auto result=root/L"result.txt",log=root/L"launch.log";
 SetEnvironmentVariableW(L"PYINSTALLER_RESET_ENVIRONMENT",L"0");
 HANDLE child=nullptr;DWORD error=0;
 assert(spawn(self,L"\""+std::wstring(self)+L"\" --child \""+result.wstring()+L"\"",root.c_str(),log.c_str(),child,error));
 assert(child&&WaitForSingleObject(child,10000)==WAIT_OBJECT_0);DWORD code=0;assert(GetExitCodeProcess(child,&code)&&code==23);CloseHandle(child);
 std::ifstream in(result);std::string content;in>>content;assert(content=="reset-ok");
 std::ifstream logs(log);std::string text((std::istreambuf_iterator<char>(logs)),{});
 assert(text.find("stdout")!=std::string::npos&&text.find("stderr")!=std::string::npos);
 assert(!spawn(L"Z:\\does-not-exist.exe",L"missing",root.c_str(),log.c_str(),child,error));assert(!child&&error);
 assert(existingWorker(GetCurrentProcessId(),GetCurrentProcessId()+1,GetCurrentProcessId(),self)==nullptr);
 // Also exercise the exact bundled Server16 executable through the same launcher.
 if(argc==3){
  const std::filesystem::path game=argv[2];std::wstring exe=argv[1];
  std::wstring command=L"\""+exe+L"\" --club-environment-check --game-root \""+game.wstring()+L"\"";
  assert(spawn(exe.c_str(),command,game.c_str(),log.c_str(),child,error));
  assert(WaitForSingleObject(child,90000)==WAIT_OBJECT_0);assert(GetExitCodeProcess(child,&code)&&code==0);CloseHandle(child);
 }
 std::cout<<"PASS: retry, child exit, isolated environment, hidden launch, stdout/stderr and bundled runtime\n";
}
