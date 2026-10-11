#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef void (__fastcall *RenderFn)(void*,int);
static uintptr_t base;
static RenderFn previous;
static LONG started,stopped,busy;
static ULONGLONG lastTick;
static char script[65536],logPath[MAX_PATH],scriptPath[MAX_PATH];
static FILETIME loadedTime;
static void log_event(const char* s){FILE* f=NULL;if(!fopen_s(&f,logPath,"ab")&&f){fprintf(f,"%llu %s\n",GetTickCount64(),s);fclose(f);}}
static BOOL read_at(uintptr_t a,void* b,SIZE_T n){SIZE_T got;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,b,n,&got)&&got==n;}
static BOOL swap(void* before,void* after){DWORD old,ignored;void* found;void* volatile* slot=(void* volatile*)(base+0x2205ec0);if(!VirtualProtect((void*)slot,8,PAGE_READWRITE,&old))return FALSE;found=InterlockedCompareExchangePointer(slot,after,before);VirtualProtect((void*)slot,8,old,&ignored);return found==before;}
static void __fastcall render_hook(void* self,int phase){
 ULONGLONG now=GetTickCount64();
 previous(self,phase);
 if(phase||stopped||now-lastTick<100||InterlockedCompareExchange(&busy,1,0))return;
 lastTick=now;
 {
  WIN32_FILE_ATTRIBUTE_DATA attr;
  if(GetFileAttributesExA(scriptPath,GetFileExInfoStandard,&attr)&&CompareFileTime(&attr.ftLastWriteTime,&loadedTime)!=0){
   FILE* f=NULL;
   if(!fopen_s(&f,scriptPath,"rb")&&f){size_t n=fread(script,1,sizeof(script)-1,f);BOOL good=!ferror(f)&&feof(f);fclose(f);if(good){script[n]=0;loadedTime=attr.ftLastWriteTime;log_event("script_loaded");}else script[0]=0;}
  }
  if(script[0])((void (__fastcall*)(const char*,size_t,const char*))(base+0x4ac35e0))(script,strlen(script),"flamengo_pyro");
 }
 InterlockedExchange(&busy,0);
}
static DWORD WINAPI worker(void* unused){
 IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;uintptr_t target;HMODULE owner=NULL;
 (void)unused;base=(uintptr_t)GetModuleHandleA(NULL);
 if(!read_at(base,&dos,sizeof(dos))||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<0||
 !read_at(base+(uintptr_t)dos.e_lfanew,&nt,sizeof(nt))||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64){log_event("unsupported_image");return 0;}
 if(!read_at(base+0x2205ec0,&target,8)){log_event("missing_render_slot");return 0;}
 if(target!=base+0x436b530){
  char path[MAX_PATH];const char* name;
  if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,(LPCSTR)target,&owner)){log_event("unknown_hook_owner");return 0;}
  GetModuleFileNameA(owner,path,MAX_PATH);name=strrchr(path,'\\');name=name?name+1:path;
  if(strncmp(name,"multiball_visual_v",18)!=0){FreeLibrary(owner);log_event("render_hook_conflict");return 0;}
  /* Pin the existing callback owner for the lifetime of this chain. */
  GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)target,&owner);FreeLibrary(owner);
 }
 previous=(RenderFn)target;
 if(stopped||!swap((void*)previous,(void*)render_hook)){log_event("install_conflict");return 0;}
 log_event("installed native_render_thread_lua_bridge preserves_multiball");return 0;
}
__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void){return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* root){HANDLE h;HMODULE pin=NULL;
 if(!root||InterlockedCompareExchange(&started,1,0))return FALSE;
 _snprintf_s(logPath,MAX_PATH,_TRUNCATE,"%s\\..\\logs\\flamengo_pyro.log",root);
 _snprintf_s(scriptPath,MAX_PATH,_TRUNCATE,"%s\\flamengo_pyro\\runtime.lua",root);
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pin))return FALSE;
 log_event("start experimental_flamengo_1043");h=CreateThread(NULL,0,worker,NULL,0,NULL);if(!h)return FALSE;CloseHandle(h);return TRUE;
}
__declspec(dllexport) BOOL WINAPI Fifa16ModStop(void){InterlockedExchange(&stopped,1);if(previous&&!swap((void*)render_hook,(void*)previous)){log_event("stop_chain_conflict");return FALSE;}log_event("stopped");return TRUE;}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(h);return TRUE;}
