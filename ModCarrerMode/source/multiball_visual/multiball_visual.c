#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include "ball_layout.h"
typedef void (__fastcall *RenderFn)(void*,int);
typedef unsigned char (__fastcall *SceneFn)(void*,void*);
static RenderFn render_original;
static SceneFn bounds_original,shadow_original;
static uintptr_t base;
static LONG started,stop_requested,observed;
static char log_path[MAX_PATH];
static const uintptr_t slots[3]={0x2205ec0,0x2205f98,0x2205f90};
static const uintptr_t native[3]={0x436b530,0x436b350,0x436ba90};
static void *hooks[3];
static BOOL installed[3];
static BOOL read_at(uintptr_t address,void *out,SIZE_T size) {
 SIZE_T got=0;
 return address && ReadProcessMemory(GetCurrentProcess(),(void*)address,out,size,&got) && got==size;
}
static void event(const char *message) {
 FILE *f=NULL;
 if(!fopen_s(&f,log_path,"ab") && f){fprintf(f,"%llu %s\n",GetTickCount64(),message);fclose(f);}
}
/* The borrowed native resources stay owned by the game. The object and its
   matrices are private stack copies, valid through the synchronous draw call.
   Native rendering itself queues stack-local uniforms, copying them internally. */
static BOOL snapshot(void *self,SIZE_T state_offset,unsigned char *object,unsigned char *state,int include_ball) {
 uintptr_t state_address;
 if(InterlockedCompareExchange(&stop_requested,0,0))return FALSE;
 if(!read_at((uintptr_t)self,object,0x38))return FALSE;
 memcpy(&state_address,object+state_offset,8);
 if(!state_address)return FALSE;
 /* Native update/render handoff uses this verified CRITICAL_SECTION. */
 EnterCriticalSection((CRITICAL_SECTION*)state_address);
 {
  BOOL ok=read_at(state_address,state,BALL_STATE_BYTES);
  LeaveCriticalSection((CRITICAL_SECTION*)state_address);
  if(!ok)return FALSE;
 }
 if(!ball_expand_snapshot(state,include_ball))return FALSE;
 memcpy(object+state_offset,&state,8);
 return TRUE;
}
static void __fastcall render_hook(void *self,int phase) {
 __declspec(align(16)) unsigned char object[0x40],state[BALL_STATE_BYTES];
 /* phase 1 is the engine's reset operation, not a draw. */
 render_original(self,phase);
 if(phase==0 && snapshot(self,0x30,object,state,0)) {
  render_original(object,0);
  ball_support_snapshot(state);
  render_original(object,0);
  if(InterlockedCompareExchange(&observed,1,0)==0)event("drawn 13 visual balls on low rounded holders shared_ball_material");
 }
}
static unsigned char __fastcall bounds_hook(void *self,void *context) {
 __declspec(align(16)) unsigned char object[0x40],state[BALL_STATE_BYTES];
 /* Keep ball slot 0 in the native culling list. Extra slots are 1..13. */
 if(snapshot(self,0x28,object,state,1))return bounds_original(object,context);
 return bounds_original(self,context);
}
static unsigned char __fastcall shadow_hook(void *self,void *context) {
 /* Shadow mesh allocation belongs to the original object. Do not make a
    temporary owner that loses the native lazy allocation. Main balls render
    without additional flat-shadow objects in this first visual prototype. */
 return shadow_original(self,context);
}
static BOOL exchange(unsigned int i,void *before,void *after) {
 DWORD old,ignored;void *seen;
 void *volatile *slot=(void *volatile*)(base+slots[i]);
 if(!VirtualProtect((void*)slot,8,PAGE_READWRITE,&old))return FALSE;
 seen=InterlockedCompareExchangePointer(slot,after,before);
 VirtualProtect((void*)slot,8,old,&ignored);
 return seen==before || seen==after;
}
static BOOL ready(void) {
 unsigned int i;uintptr_t actual;
 for(i=0;i<3;i++)if(!read_at(base+slots[i],&actual,8) || actual!=base+native[i])return FALSE;
 return TRUE;
}
static DWORD WINAPI install_worker(void *unused) {
 unsigned int i,attempt,stable=0;IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
 (void)unused;base=(uintptr_t)GetModuleHandleA(NULL);
 if(!read_at(base,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE ||
    !read_at(base+(uintptr_t)dos.e_lfanew,&nt,sizeof(nt)) ||
    nt.Signature!=IMAGE_NT_SIGNATURE || nt.FileHeader.TimeDateStamp!=0x577DE45C ||
    nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64) {event("unsupported_image");return 0;}
 for(attempt=0;attempt<600;attempt++) {
  if(InterlockedCompareExchange(&stop_requested,0,0))return 0;
  stable=ready()?stable+1:0;if(stable>=3)break;Sleep(200);
 }
 if(stable<3){event("native_slots_unavailable_or_conflict");return 0;}
 render_original=(RenderFn)(base+native[0]);bounds_original=(SceneFn)(base+native[1]);shadow_original=(SceneFn)(base+native[2]);
 hooks[0]=(void*)render_hook;hooks[1]=(void*)bounds_hook;hooks[2]=(void*)shadow_hook;
 /* The shadow hook is diagnostic/pass-through; only two slots need mutation. */
 for(i=0;i<2;i++) {
  if(!exchange(i,(void*)(base+native[i]),hooks[i]))break;
  installed[i]=TRUE;
 }
 if(i!=2){for(i=0;i<2;i++)if(installed[i]){exchange(i,hooks[i],(void*)(base+native[i]));installed[i]=FALSE;}event("install_failed_rolled_back");return 0;}
 event("installed experimental_render_only_13 perimeter_balls no_physics");return 0;
}
__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void){return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root) {
 HMODULE pinned=NULL;HANDLE worker;
 if(!mods_root || InterlockedCompareExchange(&started,1,0))return FALSE;
 if(_snprintf_s(log_path,sizeof(log_path),_TRUNCATE,"%s\\..\\logs\\multiball_visual.log",mods_root)<0)return FALSE;
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
 event("start v3 experimental low_rounded_holders");worker=CreateThread(NULL,0,install_worker,NULL,0,NULL);
 if(!worker)return FALSE;CloseHandle(worker);return TRUE;
}
__declspec(dllexport) BOOL WINAPI Fifa16ModStop(void) {
 unsigned int i;BOOL ok=TRUE;InterlockedExchange(&stop_requested,1);
 for(i=0;i<2;i++)if(installed[i]){
  if(exchange(i,hooks[i],(void*)(base+native[i])))installed[i]=FALSE;else ok=FALSE;
 }
 event(ok?"stopped native_slots_restored":"stop_conflict");return ok;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved) {
 (void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(module);return TRUE;
}
