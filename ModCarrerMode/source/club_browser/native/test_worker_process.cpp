// Own launcher only; no FIFA process, hook or native scene is opened.
#include <cassert>
#include <iostream>
#include <cstdlib>
#include "render.cpp"

int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 if(argc>1&&std::wstring(argv[1])==L"--club-environment-worker"){
  wchar_t value[64]{};GetEnvironmentVariableW(L"PYINSTALLER_RESET_ENVIRONMENT",value,64);assert(!wcscmp(value,L"1"));
  GetEnvironmentVariableW(L"SERVER16_CLUB_BROWSER_WORKER",value,64);assert(!wcscmp(value,L"1"));
  assert(!GetEnvironmentVariableW(L"SERVER16_TRANSFER_MARKET_WORKER",value,64));
  wchar_t handleText[64]{};GetEnvironmentVariableW(L"XI_TEST_HANDLE",handleText,64);auto forbidden=(HANDLE)_wcstoui64(handleText,nullptr,10);DWORD flags=0;
  // Capture any pre-existing object before OpenEvent can recycle the numeric
  // value of an intentionally non-inherited handle. Compare objects, not IDs.
  HANDLE captured=nullptr;const bool wasValid=DuplicateHandle(GetCurrentProcess(),forbidden,GetCurrentProcess(),&captured,0,FALSE,DUPLICATE_SAME_ACCESS)!=FALSE;
  wchar_t eventName[128]{};GetEnvironmentVariableW(L"XI_TEST_EVENT",eventName,128);HANDLE known=OpenEventW(SYNCHRONIZE,FALSE,eventName);assert(known);
  using Compare=BOOL(WINAPI*)(HANDLE,HANDLE);auto compare=reinterpret_cast<Compare>(GetProcAddress(GetModuleHandleW(L"kernelbase.dll"),"CompareObjectHandles"));assert(compare&&(!wasValid||!compare(captured,known)));if(captured)CloseHandle(captured);CloseHandle(known);
  std::cout<<"child stdout captured\n";std::cerr<<"child stderr captured\n";
  if(GetEnvironmentVariableW(L"XI_TEST_RETRY",value,64)){
   assert(argc>4);auto path=fs::path(argv[4])/L"attempt.txt";unsigned attempt=0;{std::ifstream in(path);in>>attempt;}std::ofstream(path)<<attempt+1;
   return !wcscmp(value,L"always")||attempt<2?-1:37;
  }
  return 37;
 }
 if(argc!=3)return 2;
 const fs::path folder=argv[2];fs::create_directories(folder);
 SetEnvironmentVariableW(L"PYINSTALLER_RESET_ENVIRONMENT",L"0");
 SetEnvironmentVariableW(L"SERVER16_CLUB_BROWSER_WORKER",L"0");SetEnvironmentVariableW(L"SERVER16_TRANSFER_MARKET_WORKER",L"1");
 // Inherit a stale frozen environment deliberately. The real Server must reset
 // it, rather than depend on an extraction folder left by its parent.
 SetEnvironmentVariableW(L"_PYI_ARCHIVE_FILE",(folder/L"Server16Python.exe").c_str());
 SetEnvironmentVariableW(L"_PYI_APPLICATION_HOME_DIR",(folder/L"missing-extraction").c_str());SetEnvironmentVariableW(L"_PYI_PARENT_PROCESS_LEVEL",L"1");
 const auto eventName=L"Local\\XI_TEST_EVENT_"+std::to_wstring(GetCurrentProcessId());SetEnvironmentVariableW(L"XI_TEST_EVENT",eventName.c_str());
 SECURITY_ATTRIBUTES security{sizeof security,nullptr,TRUE};HANDLE forbidden=CreateEventW(&security,TRUE,FALSE,eventName.c_str());assert(forbidden);
 auto handleText=std::to_wstring((uintptr_t)forbidden);SetEnvironmentVariableW(L"XI_TEST_HANDLE",handleText.c_str());
 clublineup::View view;
 if(std::wstring(argv[1])==L"--fixture"){
  wchar_t self[32768]{};GetModuleFileNameW(nullptr,self,32768);fs::copy_file(self,folder/L"Server16Python.exe",fs::copy_options::overwrite_existing);
  assert(view.startWorker(folder));auto child=view.child;assert(view.startWorker(folder)&&child==view.child);
  assert(WaitForSingleObject(view.child,10000)==WAIT_OBJECT_0);DWORD code=0;assert(GetExitCodeProcess(view.child,&code)&&code==37);
  view.sequence=GetTickCount64();view.poll(nullptr);assert(view.status=="error");
  // Selecting again restarts the dead helper, without an automatic retry loop.
  assert(view.request(1043));assert(WaitForSingleObject(view.child,10000)==WAIT_OBJECT_0);
  std::ifstream stream(view.folder/L"worker.log");std::string text((std::istreambuf_iterator<char>(stream)),{});assert(text.find("stdout")!=std::string::npos&&text.find("stderr")!=std::string::npos);
 }else if(std::wstring(argv[1])==L"--retry"||std::wstring(argv[1])==L"--retry-permanent"){
  wchar_t self[32768]{};GetModuleFileNameW(nullptr,self,32768);fs::copy_file(self,folder/L"Server16Python.exe",fs::copy_options::overwrite_existing);
  fs::remove(folder/L"attempt.txt");SetEnvironmentVariableW(L"XI_TEST_RETRY",std::wstring(argv[1])==L"--retry-permanent"?L"always":L"1");view.configure(folder);assert(view.request(1043));const auto sequence=view.sequence;
  for(unsigned retry=1;retry<=2;++retry){
   assert(WaitForSingleObject(view.child,10000)==WAIT_OBJECT_0);view.lastPoll=0;view.poll(nullptr);
   assert(view.status=="loading"&&view.bootRetries==retry&&view.retryAt&&!view.child);
   view.retryAt=GetTickCount64();view.lastPoll=0;view.poll(nullptr);
   assert(view.child&&view.sequence==sequence&&view.club==1043&&fs::is_regular_file(view.folder/L"request.tsv"));
  }
  assert(WaitForSingleObject(view.child,10000)==WAIT_OBJECT_0);view.lastPoll=0;view.poll(nullptr);assert(view.status=="error"&&!view.retryAt);
  unsigned attempts=0;{std::ifstream in(folder/L"attempt.txt");in>>attempts;}assert(attempts==3);SetEnvironmentVariableW(L"XI_TEST_RETRY",nullptr);
 }else if(std::wstring(argv[1])==L"--frozen"){
  // The caller supplies an isolated Git+ZIP stage with a safe export test entry.
  assert(fs::is_regular_file(folder/L"fixture.bin"));fs::remove(folder/L"cold-export.json");
  assert(view.startWorker(folder));assert(WaitForSingleObject(view.child,60000)==WAIT_OBJECT_0);DWORD code=0;assert(GetExitCodeProcess(view.child,&code)&&code==0);
  assert(fs::is_regular_file(folder/L"cold-export.json"));
  std::ifstream service(view.folder/L"service.log");std::string text((std::istreambuf_iterator<char>(service)),{});assert(text.find("COLD_EXPORT_OK")!=std::string::npos);
 }else return 2;
 view.stop();assert(!view.child&&!view.job);CloseHandle(forbidden);
 std::cout<<"PASS independent frozen environment, restricted handles, captured errors and explicit restart\n";return 0;
}
