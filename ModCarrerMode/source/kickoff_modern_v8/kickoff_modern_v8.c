#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "kickoff_spacing.h"

typedef uintptr_t (__fastcall *Call8)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
typedef uintptr_t (__fastcall *Call4)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);
static uintptr_t base, active_assignment;
static LONG started;
static volatile LONG stop_requested;
static SRWLOCK state_lock=SRWLOCK_INIT;
static float receiver_target[4];
static BOOL target_valid, armed, pass_prepared;
static uintptr_t cached_receiver, cached_kicker;
static uintptr_t other_actors[10];
static unsigned int other_count;
static ULONGLONG created_at;
typedef uintptr_t (__fastcall *Call6F)(uintptr_t,uintptr_t,float,float,float,float);
static Call6F physical_original;
static uintptr_t physical_slot;
static BOOL physical_patched;
static char log_path[MAX_PATH];
static void *relay_page;
static Call8 factory_original, position_original;
static Call6F placement_original;
static Call4 pass_original;
typedef struct {DWORD rva; DWORD destination; unsigned char saved[5]; BOOL patched; unsigned char applied[5];} Patch;
static Patch patches[4]={{0x525E442,0x5258460,{0},FALSE,{0}},{0x51CDE19,0x4DCCBD0,{0},FALSE,{0}},{0x52E593C,0x3D0CFD0,{0},FALSE,{0}},{0x4D3FD33,0x488C550,{0},FALSE,{0}}};

static BOOL read_at(uintptr_t p,void *out,SIZE_T n) {
 SIZE_T got=0;
 return p && ReadProcessMemory(GetCurrentProcess(),(void*)p,out,n,&got) && got==n;
}
static uintptr_t pointer_at(uintptr_t p) {uintptr_t v=0;read_at(p,&v,sizeof(v));return v;}
static void event(const char *name) {
 FILE *f=NULL;SYSTEMTIME t;
 if(fopen_s(&f,log_path,"ab") || !f)return;
 GetLocalTime(&t);fprintf(f,"%04u-%02u-%02u %02u:%02u:%02u %s\n",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,name);fclose(f);
}
static BOOL alive(void) {
 return active_assignment && pointer_at(active_assignment)==base+0x2336210;
}
static BOOL eligible_receiver(void) {
 uintptr_t kicker;
 uint32_t receiver_info[5],kicker_info[5];
 if(!active_assignment || !cached_receiver || pointer_at(cached_receiver)!=base+0x22FE740)return FALSE;
 kicker=pointer_at(active_assignment+0x88);
 if(!kicker || kicker==cached_receiver || pointer_at(kicker)!=base+0x22FE740)return FALSE;
 if(!read_at(pointer_at(cached_receiver+0xA0),receiver_info,sizeof(receiver_info)) ||
    !read_at(pointer_at(kicker+0xA0),kicker_info,sizeof(kicker_info)))return FALSE;
 /* AI role 28 is a substitute. No reserve, referee or opposite team can
    become the receiver targeted by this plugin. */
 return receiver_info[1]>0 && receiver_info[1]<10000000U && receiver_info[3]<=1U &&
        receiver_info[3]==kicker_info[3] && receiver_info[4]<=27U && kicker_info[4]<=27U;
}

static uintptr_t __fastcall factory_hook(uintptr_t a,uintptr_t b,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t f,uintptr_t g,uintptr_t h) {
 uintptr_t result=factory_original(a,b,c,d,e,f,g,h);
 AcquireSRWLockExclusive(&state_lock);
 active_assignment=pointer_at(result)==base+0x2336210?result:0;target_valid=FALSE;
 if(cached_receiver!=pointer_at(active_assignment+0x328) || cached_kicker!=pointer_at(active_assignment+0x88))other_count=0;
 cached_receiver=active_assignment?pointer_at(active_assignment+0x328):0;
 cached_kicker=active_assignment?pointer_at(active_assignment+0x88):0;
 armed=eligible_receiver();pass_prepared=FALSE;created_at=GetTickCount64();
 ReleaseSRWLockExclusive(&state_lock);
 event("kickoff_assignment_created");return result;
}
static uintptr_t __fastcall position_hook(uintptr_t actor_context,uintptr_t b,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t output,uintptr_t g,uintptr_t h) {
 uintptr_t result=position_original(actor_context,b,c,d,e,output,g,h);
 float v[4];BOOL first=FALSE;
 if(!read_at(output,v,sizeof(v)))return result;
 AcquireSRWLockExclusive(&state_lock);
 /* This call belongs to the receiver branch of Kickoff::Assignment.
    Root identity and actor identity further bind it to the current kickoff.
    Ignore the stadium entrance; only the original central kickoff target qualifies. */
 if(alive() && eligible_receiver() && actor_context>=0x40 && pointer_at(active_assignment+0x328)==actor_context-0x40 &&
    pointer_at(actor_context-0x40)==base+0x22FE740 &&
    isfinite(v[0]) && isfinite(v[1]) && isfinite(v[2]) &&
    fabsf(v[0])>=0.5f && fabsf(v[0])<=2.0f && fabsf(v[1])<0.2f &&
    fabsf(v[2])>=2.0f && fabsf(v[2])<=7.0f) {
  /* Original central receiver X is on his own half. Runtime goalkeeper X
     confirms that sign. Native geometry uses an approximately feet-sized
     scale; 36.0888 units is the candidate for an eleven-metre retreat. */
  v[0]=v[0]>0.0f?36.0888f:-36.0888f;v[2]=v[2]>0.0f?13.1232f:-13.1232f;
  /* Output is the caller's writable stack vector, before arrival-distance evaluation. */
  memcpy((void*)output,v,sizeof(v));memcpy(receiver_target,v,sizeof(v));
  first=!target_valid;target_valid=TRUE;
 }
 ReleaseSRWLockExclusive(&state_lock);
 if(first)event("receiver_navigation_target_replaced distance_native=36.0888 own_half_sign=same_as_original_central_target experimental=1");
 return result;
}
static BOOL space_other(uintptr_t actor,float v[4]) {
 uint32_t info[5],kicker_info[5];
 if(!actor || pointer_at(actor)!=base+0x22FE740 ||
    !read_at(pointer_at(actor+0xA0),info,sizeof(info)) ||
    !read_at(pointer_at(cached_kicker+0xA0),kicker_info,sizeof(kicker_info)))return FALSE;
 return kickoff_space_other(info[4],info[3],kicker_info[3],
                            actor==cached_kicker || actor==cached_receiver,v)!=0;
}
static uintptr_t __fastcall placement_hook(uintptr_t actor_context,uintptr_t position,float yaw,float a,float b,float c) {
 __declspec(align(16)) float v[4];unsigned int i;BOOL first=FALSE;
 if(actor_context>=0x40 && read_at(position,v,sizeof(v))) {
  AcquireSRWLockExclusive(&state_lock);
  if(armed && alive() && !pass_prepared && space_other(actor_context-0x40,v)) {
   for(i=0;i<other_count;i++)if(other_actors[i]==actor_context-0x40)break;
   if(i<other_count || other_count<10) {
    if(i==other_count){other_actors[other_count++]=actor_context-0x40;first=TRUE;}
    position=(uintptr_t)v;
   }
  }
  ReleaseSRWLockExclusive(&state_lock);
 }
 if(first)event("other_starting_player_outside_circle target_metres=10.25");
 return placement_original(actor_context,position,yaw,a,b,c);
}
static BOOL other_physical_target(uintptr_t transform,uintptr_t position,float v[4]) {
 unsigned int i;BOOL changed=FALSE;
 if(!read_at(position,v,sizeof(float)*4))return FALSE;
 AcquireSRWLockExclusive(&state_lock);
 if(armed && !alive() && (pass_prepared || GetTickCount64()-created_at>30000))armed=FALSE;
 if(armed)for(i=0;i<other_count;i++) {
  uintptr_t actor=other_actors[i];
  if(transform==pointer_at(actor+0x60) && space_other(actor,v)) {changed=TRUE;break;}
 }
 ReleaseSRWLockExclusive(&state_lock);
 return changed;
}

static uintptr_t __fastcall pass_hook(uintptr_t origin,uintptr_t scale,uintptr_t angle,uintptr_t output) {
 uintptr_t result=pass_original(origin,scale,angle,output);BOOL changed=FALSE;
 AcquireSRWLockExclusive(&state_lock);
 if(target_valid && alive() && output) {memcpy((void*)output,receiver_target,sizeof(receiver_target));changed=TRUE;pass_prepared=TRUE;}
 ReleaseSRWLockExclusive(&state_lock);
 if(changed)event("first_pass_target_replaced experimental=1");
 return result;
}

/* Cover the physical reset at kickoff placement and again at the actual kick.
   The receiver identity survives the short destruction/recreation gap. */
static BOOL physical_target(uintptr_t actor_context,uintptr_t position,float v[4]) {
 BOOL changed=FALSE;uint32_t info[5];
 if(!read_at(position,v,16))return FALSE;
 AcquireSRWLockExclusive(&state_lock);
 if(armed && !alive() && (pass_prepared || GetTickCount64()-created_at>30000))armed=FALSE;
 if(armed && cached_receiver && actor_context==pointer_at(cached_receiver+0x60) &&
    pointer_at(cached_receiver)==base+0x22FE740 &&
    read_at(pointer_at(cached_receiver+0xA0),info,sizeof(info)) && info[3]<=1U && info[4]<=27U &&
    isfinite(v[0]) && isfinite(v[1]) && isfinite(v[2]) &&
    fabsf(v[0])>=0.5f && fabsf(v[0])<=2.0f && fabsf(v[1])<0.2f &&
    fabsf(v[2])>=2.0f && fabsf(v[2])<=7.0f) {
  v[0]=v[0]>0.0f?36.0888f:-36.0888f;
  v[2]=v[2]>0.0f?13.1232f:-13.1232f;
  changed=TRUE;
 }
 ReleaseSRWLockExclusive(&state_lock);
 return changed;
}
static uintptr_t __fastcall physical_hook(uintptr_t transform,uintptr_t position,float yaw,float a,float b,float c) {
 __declspec(align(16)) float v[4];
 if(physical_target(transform,position,v)) {
  /* Native planar direction is (cos(yaw), 0, -sin(yaw)). */
  yaw=atan2f(v[2],-v[0]);
  position=(uintptr_t)v;
 } else if(other_physical_target(transform,position,v))position=(uintptr_t)v;
 return physical_original(transform,position,yaw,a,b,c);
}
static BOOL write_code(uintptr_t address,const void *bytes,SIZE_T n) {
 DWORD old=0,ignored=0;
 if(!VirtualProtect((void*)address,n,PAGE_EXECUTE_READWRITE,&old))return FALSE;
 memcpy((void*)address,bytes,n);
 FlushInstructionCache(GetCurrentProcess(),(void*)address,n);
 return VirtualProtect((void*)address,n,old,&ignored);
}
static BOOL supported(void) {
 IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
 if(!read_at(base,&dos,sizeof(dos)) || dos.e_magic!=IMAGE_DOS_SIGNATURE || dos.e_lfanew<0 || dos.e_lfanew>0x1000 ||
    !read_at(base+(uintptr_t)dos.e_lfanew,&nt,sizeof(nt)))return FALSE;
 return nt.Signature==IMAGE_NT_SIGNATURE && nt.FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64 &&
    nt.FileHeader.TimeDateStamp==0x577DE45C && nt.OptionalHeader.SizeOfImage>=0x9524000 && nt.OptionalHeader.SizeOfImage<=0x9525000;
}
static BOOL exchange_physical(uintptr_t before,uintptr_t after) {
 DWORD old=0,ignored=0;uintptr_t seen;
 if(!VirtualProtect((void*)physical_slot,sizeof(uintptr_t),PAGE_READWRITE,&old))return FALSE;
 seen=(uintptr_t)InterlockedCompareExchangePointer((void *volatile*)physical_slot,(void*)after,(void*)before);
 if(!VirtualProtect((void*)physical_slot,sizeof(uintptr_t),old,&ignored))return FALSE;
 return (seen==before || seen==after) && pointer_at(physical_slot)==after;
}
static BOOL calls_ready(void) {
 unsigned int i;unsigned char code[5];int32_t displacement;
 for(i=0;i<4;i++) {
  if(!read_at(base+patches[i].rva,code,5) || code[0]!=0xE8)return FALSE;
  memcpy(&displacement,code+1,4);
  if((uintptr_t)((intptr_t)(base+patches[i].rva+5)+displacement)!=base+patches[i].destination)return FALSE;
 }
 return pointer_at(base+0x2329980)==base+0x511A940;
}

static DWORD WINAPI install_worker(void *unused) {
 unsigned int i,attempt,stable=0;uintptr_t address;DWORD old=0;unsigned char code[5];int32_t displacement;
 uintptr_t hooks[4]={(uintptr_t)factory_hook,(uintptr_t)position_hook,(uintptr_t)pass_hook,(uintptr_t)placement_hook};
 (void)unused;base=(uintptr_t)GetModuleHandleA(NULL);
 if(!supported()) {event("not_installed unsupported_image");return 0;}
 /* The executable prepares its code after the loader starts plugins.
    Wait for verified native destinations, as the bench plugin already does. */
 event("waiting_for_native_code");
 for(attempt=0;attempt<600;attempt++) {
  if(InterlockedCompareExchange(&stop_requested,0,0))return 0;
  stable=calls_ready()?stable+1:0;
  if(stable>=3)break;
  Sleep(200);
 }
 if(stable<3){event("not_installed native_code_not_ready_or_conflict");return 0;}

 for(i=0;i<4;i++) {
  if(!read_at(base+patches[i].rva,code,5) || code[0]!=0xE8) {event("not_installed call_signature_mismatch");return 0;}
  memcpy(&displacement,code+1,4);
  if((uintptr_t)((intptr_t)(base+patches[i].rva+5)+displacement)!=base+patches[i].destination) {event("not_installed call_destination_mismatch");return 0;}
  memcpy(patches[i].saved,code,5);
 }
 factory_original=(Call8)(base+0x5258460);position_original=(Call8)(base+0x4DCCBD0);placement_original=(Call6F)(base+0x488C550);pass_original=(Call4)(base+0x3D0CFD0);
 physical_slot=base+0x2329980;
 if(pointer_at(physical_slot)!=base+0x511A940){event("not_installed physical_slot_mismatch");return 0;}
 physical_original=(Call6F)(base+0x511A940);
 for(address=base+0x10000000;address<base+0x70000000;address+=0x10000) {
  relay_page=VirtualAlloc((void*)address,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
  if(relay_page)break;
 }
 if(!relay_page) {event("not_installed no_near_relay_memory");return 0;}
 for(i=0;i<4;i++) {
  unsigned char *relay=(unsigned char*)relay_page+i*32;
  /* mov rax, absolute hook; jmp rax. The original E8 establishes the return address. */
  relay[0]=0x48;relay[1]=0xB8;memcpy(relay+2,&hooks[i],8);relay[10]=0xFF;relay[11]=0xE0;
 }
 if(!VirtualProtect(relay_page,4096,PAGE_EXECUTE_READ,&old)) {event("not_installed relay_protection_failed");return 0;}
 FlushInstructionCache(GetCurrentProcess(),relay_page,4096);
 for(i=0;i<4;i++) {
  uintptr_t relay=(uintptr_t)relay_page+i*32;
  intptr_t distance=(intptr_t)relay-(intptr_t)(base+patches[i].rva+5);
  if(distance<INT32_MIN || distance>INT32_MAX)break;
  displacement=(int32_t)distance;code[0]=0xE8;memcpy(code+1,&displacement,4);
  if(memcmp((void*)(base+patches[i].rva),patches[i].saved,5) || !write_code(base+patches[i].rva,code,5))break;
  memcpy(patches[i].applied,code,5);
  patches[i].patched=TRUE;
 }
 if(i!=4) {
  for(i=0;i<4;i++)if(patches[i].patched){write_code(base+patches[i].rva,patches[i].saved,5);patches[i].patched=FALSE;}
  event("not_installed patch_failed_rolled_back");return 0;
 }
 {
  uintptr_t hook=(uintptr_t)physical_hook;
  if(!exchange_physical((uintptr_t)physical_original,hook)) {
   for(i=0;i<4;i++)if(patches[i].patched){write_code(base+patches[i].rva,patches[i].saved,5);patches[i].patched=FALSE;}
   event("not_installed physical_patch_failed_rolled_back");return 0;
  }
  physical_patched=TRUE;
 }
 event("installed v8 diagonal_receiver_navigation_physical_resets_and_first_pass requires_new_kickoff experimental=1");return 0;
}
__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void){return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root) {
 HANDLE thread;HMODULE pinned=NULL;
 if(!mods_root || InterlockedCompareExchange(&started,1,0))return FALSE;
 if(_snprintf_s(log_path,sizeof(log_path),_TRUNCATE,"%s\\..\\logs\\kickoff_modern_v8.log",mods_root)<0)return FALSE;
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
 event("start experimental_v8 full_behavior_unverified");
 thread=CreateThread(NULL,0,install_worker,NULL,0,NULL);if(!thread)return FALSE;CloseHandle(thread);return TRUE;
}
__declspec(dllexport) BOOL WINAPI Fifa16ModStop(void) {
 unsigned int i;BOOL ok=TRUE;
 InterlockedExchange(&stop_requested,1);
 AcquireSRWLockExclusive(&state_lock);active_assignment=0;target_valid=FALSE;armed=FALSE;cached_receiver=0;cached_kicker=0;other_count=0;ReleaseSRWLockExclusive(&state_lock);
 for(i=0;i<4;i++)if(patches[i].patched){if(memcmp((void*)(base+patches[i].rva),patches[i].applied,5)==0 && write_code(base+patches[i].rva,patches[i].saved,5))patches[i].patched=FALSE;else ok=FALSE;}
 if(physical_patched){uintptr_t original=(uintptr_t)physical_original;if(exchange_physical((uintptr_t)physical_hook,original))physical_patched=FALSE;else ok=FALSE;}
 event(ok?"stopped original_call_sites_restored":"stop_failed");return ok;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(module);return TRUE;}
