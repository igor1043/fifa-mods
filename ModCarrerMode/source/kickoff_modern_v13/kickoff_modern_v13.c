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
static LONG kicker_oriented;
static LONG kicker_command_oriented;
static LONG kicker_input_oriented;
static int own_half_sign;
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
/* Only PassKickOff::PassSubSystem owns this command vtable slot. */
static Call4 command_original;
static uintptr_t command_slot;
static BOOL command_patched;
static char log_path[MAX_PATH];
static void *relay_page;
static Call8 factory_original, position_original;
static Call6F placement_original;
static Call4 pass_original;
static Call4 idle_original;
typedef uintptr_t (__fastcall *EncodeAngle)(uintptr_t,float);
typedef struct {DWORD rva; DWORD destination; unsigned char saved[5]; BOOL patched; unsigned char applied[5];} Patch;
enum { PATCH_COUNT=6 };
static Patch patches[PATCH_COUNT]={{0x525E442,0x5258460,{0},FALSE,{0}},{0x51CDE19,0x4DCCBD0,{0},FALSE,{0}},{0x52E593C,0x3D0CFD0,{0},FALSE,{0}},{0x4D3FD33,0x488C550,{0},FALSE,{0}},{0x51CDD83,0x4D39DE0,{0},FALSE,{0}},{0x4FE5883,0x4D39DE0,{0},FALSE,{0}}};

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
 if(cached_receiver!=pointer_at(active_assignment+0x328) || cached_kicker!=pointer_at(active_assignment+0x88)){other_count=0;own_half_sign=0;}
 cached_receiver=active_assignment?pointer_at(active_assignment+0x328):0;
 cached_kicker=active_assignment?pointer_at(active_assignment+0x88):0;
 armed=eligible_receiver();pass_prepared=FALSE;created_at=GetTickCount64();
 /* The first placement may precede the receiver navigation callback.
    Seed the mirrored defence sign from the native central receiver pose. */
 if(armed) {
  float central[4];int sign;
  if(read_at(pointer_at(cached_receiver+0x48)+0x330,central,sizeof(central)) &&
     (sign=kickoff_central_receiver_sign(central))!=0)own_half_sign=sign;
 }
 InterlockedExchange(&kicker_oriented,0);
 InterlockedExchange(&kicker_command_oriented,0);
 InterlockedExchange(&kicker_input_oriented,0);
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
  own_half_sign=v[0]>0.0f?1:-1;
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
static BOOL face_kicker(uintptr_t actor,uintptr_t position,float *yaw) {
 float v[4],defence[4]={0,0,0,1};uint32_t info[5];BOOL changed=FALSE;
 if(!read_at(position,v,sizeof(v)))return FALSE;
 AcquireSRWLockExclusive(&state_lock);
 if(armed && !alive() && (pass_prepared || GetTickCount64()-created_at>30000))armed=FALSE;
 /* Assignment can be recreated between navigation and the final pose.
    Keep the independently verified own-half sign across that short gap. */
 if(armed && own_half_sign && actor==cached_kicker &&
    pointer_at(actor)==base+0x22FE740 &&
    read_at(pointer_at(actor+0xA0),info,sizeof(info)) && info[3]<=1U && info[4]<=27U) {
  defence[0]=(float)own_half_sign*36.0888f;
  changed=kickoff_face_receiver(v,defence,yaw)!=0;
 }
 ReleaseSRWLockExclusive(&state_lock);
 if(changed && InterlockedCompareExchange(&kicker_oriented,1,0)==0)event("kicker_only_facing_own_defence_axis");
 return changed;
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
 if(actor_context>=0x40)face_kicker(actor_context-0x40,position,&yaw);
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

static uintptr_t __fastcall command_hook(uintptr_t subsystem,uintptr_t origin,uintptr_t target,uintptr_t unused) {
 float original=0,adjusted=0,requested[4];BOOL changed=FALSE;uintptr_t result;
 AcquireSRWLockExclusive(&state_lock);
 /* Bind the charge adjustment to this kickoff, actor and redirected target.
    The original command builder copies +0x24 into the pass request.
    Restore the per-instance field immediately after the native call. */
 if(armed && target_valid && pass_prepared && alive() && eligible_receiver() &&
    pointer_at(subsystem)==base+0x233A3C0 && pointer_at(subsystem+0x498)==cached_kicker &&
    read_at(target,requested,sizeof(requested)) &&
    isfinite(requested[0]) && isfinite(requested[2]) &&
    fabsf(requested[0]-receiver_target[0])<0.1f && fabsf(requested[2]-receiver_target[2])<0.1f &&
    read_at(subsystem+0x24,&original,sizeof(original)) && kickoff_soften_charge(original,&adjusted)) {
  memcpy((void*)(subsystem+0x24),&adjusted,sizeof(adjusted));changed=TRUE;
 }
 ReleaseSRWLockExclusive(&state_lock);
 result=command_original(subsystem,origin,target,unused);
 if(changed) {
  float current;char message[160];BOOL restored=FALSE;
  if(read_at(subsystem+0x24,&current,sizeof(current)) && current==adjusted) {
   memcpy((void*)(subsystem+0x24),&original,sizeof(original));restored=TRUE;
  }
  _snprintf_s(message,sizeof(message),_TRUNCATE,"first_pass_charge_scaled factor=0.75 original=%.5f adjusted=%.5f native_field_restored=%d",original,adjusted,(int)restored);
  event(message);
 }
 return result;
}

static uintptr_t __fastcall idle_hook(uintptr_t actor,uintptr_t native_command,uintptr_t c,uintptr_t d) {
 __declspec(align(16)) unsigned char command[0x50]={0};
 float position[4],defence[4]={0,0,0,1},yaw=0,priority=0,speed=1.0f;
 uint32_t encoded=0,flags=1,size=0x50,none=UINT32_MAX;uintptr_t vtable;BOOL changed=FALSE;unsigned char native_flags=0;uint32_t native_size=0;
 AcquireSRWLockExclusive(&state_lock);
 /* Both publishers can enqueue PlayKick/Stand for the same kicker:
    formation (+51CDD83) and player input (+4FE5883). Replacing only the
    formation command leaves the higher-priority input command active.
    Preserve each publisher's native priority and rotate in place. */
 if(armed && alive() && !pass_prepared && target_valid && own_half_sign &&
    actor==cached_kicker && eligible_receiver() && pointer_at(native_command)==base+0x23306A0 &&
    read_at(native_command+0x1C,&native_size,4) && native_size==0x48 &&
    read_at(native_command+8,&priority,4) && isfinite(priority) && priority>=0.0f && priority<=1.0f &&
    read_at(native_command+0x20,&native_flags,1) &&
    read_at(pointer_at(actor+0x48)+0x330,position,sizeof(position))) {
  defence[0]=(float)own_half_sign*36.0888f;
  changed=kickoff_face_receiver(position,defence,&yaw)!=0;
 }
 ReleaseSRWLockExclusive(&state_lock);
 if(!changed)return idle_original(actor,native_command,c,d);
 ((EncodeAngle)(base+0x51006B0))((uintptr_t)&encoded,yaw);
 vtable=base+0x2314990;
 memcpy(command,&vtable,8);memcpy(command+8,&priority,4);
 memcpy(command+0x18,&none,4);memcpy(command+0x1C,&size,4);
 memcpy(command+0x20,position,16);memcpy(command+0x40,&flags,4);
 memcpy(command+0x48,&encoded,4);memcpy(command+0x4C,&speed,4);
 if(InterlockedCompareExchange(native_flags?&kicker_command_oriented:&kicker_input_oriented,1,0)==0)
  event(native_flags?"kicker_formation_wait_faces_own_defence native_priority_preserved=1 position_preserved=1":
                     "kicker_input_wait_faces_own_defence native_priority_preserved=1 position_preserved=1");
 return idle_original(actor,(uintptr_t)command,c,d);
}

/* Explicit adoption lets a RAM-only update handle the already paused kickoff.
   The host passes only its current assignment pointer; all identities and
   geometry are verified inside the game before any angular state is changed. */
__declspec(dllexport) BOOL WINAPI Fifa16ModAdoptKickoff(const uintptr_t *input) {
 uintptr_t assignment,kicker,receiver,state;float position[4],target[4],defence[4]={0,0,0,1},yaw,previous[6];unsigned int i;
 const uintptr_t angle_offsets[6]={0x3D4,0x3D8,0x3F0,0x3F4,0x404,0x410};
 if(!input || !read_at((uintptr_t)input,&assignment,sizeof(assignment)) ||
    !command_patched || pointer_at(assignment)!=base+0x2336210)return FALSE;
 kicker=pointer_at(assignment+0x88);receiver=pointer_at(assignment+0x328);state=pointer_at(kicker+0x48);
 if(!kicker || !receiver || kicker==receiver || pointer_at(kicker)!=base+0x22FE740 ||
    !read_at(state+0x330,position,sizeof(position)) ||
    !read_at(pointer_at(receiver+0x48)+0x330,target,sizeof(target)) ||
    !isfinite(target[0]) || !isfinite(target[2]) ||
    fabsf(fabsf(target[0])-36.0888f)>0.1f || fabsf(fabsf(target[2])-13.1232f)>0.1f)return FALSE;
 defence[0]=target[0]>0?36.0888f:-36.0888f;
 if(!kickoff_face_receiver(position,defence,&yaw))return FALSE;
 for(i=0;i<6;i++)if(!read_at(state+angle_offsets[i],&previous[i],4) || !isfinite(previous[i]) || fabsf(previous[i])>3.15f)return FALSE;
 AcquireSRWLockExclusive(&state_lock);
 active_assignment=assignment;cached_kicker=kicker;cached_receiver=receiver;
 target_valid=TRUE;memcpy(receiver_target,target,sizeof(target));own_half_sign=target[0]>0?1:-1;
 armed=eligible_receiver();pass_prepared=FALSE;created_at=GetTickCount64();other_count=0;
 if(!armed){ReleaseSRWLockExclusive(&state_lock);return FALSE;}
 /* Synchronize the six observed heading/current/target samples. Neither
    position nor velocity nor the other players' state is modified. */
 for(i=0;i<6;i++)memcpy((void*)(state+angle_offsets[i]),&yaw,4);
 ReleaseSRWLockExclusive(&state_lock);
 event("paused_kickoff_adopted kicker_angular_state_rotated position_preserved=1");return TRUE;
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
 else {
  uintptr_t kicker;
  AcquireSRWLockShared(&state_lock);kicker=cached_kicker;ReleaseSRWLockShared(&state_lock);
  if(kicker && transform==pointer_at(kicker+0x60))face_kicker(kicker,position,&yaw);
 }
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
static BOOL exchange_slot(uintptr_t slot,uintptr_t before,uintptr_t after) {
 DWORD old=0,ignored=0;uintptr_t seen;
 if(!VirtualProtect((void*)slot,sizeof(uintptr_t),PAGE_READWRITE,&old))return FALSE;
 seen=(uintptr_t)InterlockedCompareExchangePointer((void *volatile*)slot,(void*)after,(void*)before);
 if(!VirtualProtect((void*)slot,sizeof(uintptr_t),old,&ignored))return FALSE;
 return (seen==before || seen==after) && pointer_at(slot)==after;
}
static BOOL calls_ready(void) {
 unsigned int i;unsigned char code[5];int32_t displacement;
 const unsigned char charge_load[5]={0xF3,0x0F,0x10,0x43,0x24};
 if(!read_at(base+0x52EE348,code,5) || memcmp(code,charge_load,5))return FALSE;
 for(i=0;i<PATCH_COUNT;i++) {
  if(!read_at(base+patches[i].rva,code,5) || code[0]!=0xE8)return FALSE;
  memcpy(&displacement,code+1,4);
  if((uintptr_t)((intptr_t)(base+patches[i].rva+5)+displacement)!=base+patches[i].destination)return FALSE;
 }
 return pointer_at(base+0x2329980)==base+0x511A940 &&
        pointer_at(base+0x233A3D0)==base+0x52E5860 &&
        pointer_at(base+0x233A3D8)==base+0x52EE300;
}

static DWORD WINAPI install_worker(void *unused) {
 unsigned int i,attempt,stable=0;uintptr_t address;DWORD old=0;unsigned char code[5];int32_t displacement;
 uintptr_t hooks[PATCH_COUNT]={(uintptr_t)factory_hook,(uintptr_t)position_hook,(uintptr_t)pass_hook,(uintptr_t)placement_hook,(uintptr_t)idle_hook,(uintptr_t)idle_hook};
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

 for(i=0;i<PATCH_COUNT;i++) {
  if(!read_at(base+patches[i].rva,code,5) || code[0]!=0xE8) {event("not_installed call_signature_mismatch");return 0;}
  memcpy(&displacement,code+1,4);
  if((uintptr_t)((intptr_t)(base+patches[i].rva+5)+displacement)!=base+patches[i].destination) {event("not_installed call_destination_mismatch");return 0;}
  memcpy(patches[i].saved,code,5);
 }
 factory_original=(Call8)(base+0x5258460);position_original=(Call8)(base+0x4DCCBD0);placement_original=(Call6F)(base+0x488C550);pass_original=(Call4)(base+0x3D0CFD0);idle_original=(Call4)(base+0x4D39DE0);
 physical_slot=base+0x2329980;
 if(pointer_at(physical_slot)!=base+0x511A940){event("not_installed physical_slot_mismatch");return 0;}
 physical_original=(Call6F)(base+0x511A940);
 command_slot=base+0x233A3D8;command_original=(Call4)(base+0x52EE300);
 for(address=base+0x10000000;address<base+0x70000000;address+=0x10000) {
  relay_page=VirtualAlloc((void*)address,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
  if(relay_page)break;
 }
 if(!relay_page) {event("not_installed no_near_relay_memory");return 0;}
 for(i=0;i<PATCH_COUNT;i++) {
  unsigned char *relay=(unsigned char*)relay_page+i*32;
  /* mov rax, absolute hook; jmp rax. The original E8 establishes the return address. */
  relay[0]=0x48;relay[1]=0xB8;memcpy(relay+2,&hooks[i],8);relay[10]=0xFF;relay[11]=0xE0;
 }
 if(!VirtualProtect(relay_page,4096,PAGE_EXECUTE_READ,&old)) {event("not_installed relay_protection_failed");return 0;}
 FlushInstructionCache(GetCurrentProcess(),relay_page,4096);
 for(i=0;i<PATCH_COUNT;i++) {
  uintptr_t relay=(uintptr_t)relay_page+i*32;
  intptr_t distance=(intptr_t)relay-(intptr_t)(base+patches[i].rva+5);
  if(distance<INT32_MIN || distance>INT32_MAX)break;
  displacement=(int32_t)distance;code[0]=0xE8;memcpy(code+1,&displacement,4);
  if(memcmp((void*)(base+patches[i].rva),patches[i].saved,5) || !write_code(base+patches[i].rva,code,5))break;
  memcpy(patches[i].applied,code,5);
  patches[i].patched=TRUE;
 }
 if(i!=PATCH_COUNT) {
  for(i=0;i<PATCH_COUNT;i++)if(patches[i].patched){write_code(base+patches[i].rva,patches[i].saved,5);patches[i].patched=FALSE;}
  event("not_installed patch_failed_rolled_back");return 0;
 }
 {
  uintptr_t hook=(uintptr_t)physical_hook;
  if(!exchange_slot(physical_slot,(uintptr_t)physical_original,hook)) {
   for(i=0;i<PATCH_COUNT;i++)if(patches[i].patched){write_code(base+patches[i].rva,patches[i].saved,5);patches[i].patched=FALSE;}
   event("not_installed physical_patch_failed_rolled_back");return 0;
  }
  physical_patched=TRUE;
 }
 if(!exchange_slot(command_slot,(uintptr_t)command_original,(uintptr_t)command_hook)) {
  if(exchange_slot(physical_slot,(uintptr_t)physical_hook,(uintptr_t)physical_original))physical_patched=FALSE;
  for(i=0;i<PATCH_COUNT;i++)if(patches[i].patched){write_code(base+patches[i].rva,patches[i].saved,5);patches[i].patched=FALSE;}
  event("not_installed command_patch_failed_rolled_back");return 0;
 }
 command_patched=TRUE;
 event("installed v13 first_pass_charge_factor=0.75 facing_own_defence_through_preparation requires_new_kickoff=1");return 0;
}
__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void){return 1;}
__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root) {
 HANDLE thread;HMODULE pinned=NULL;
 if(!mods_root || InterlockedCompareExchange(&started,1,0))return FALSE;
 if(_snprintf_s(log_path,sizeof(log_path),_TRUNCATE,"%s\\..\\logs\\kickoff_modern_v13.log",mods_root)<0)return FALSE;
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
 event("start experimental_v13 full_behavior_unverified");
 thread=CreateThread(NULL,0,install_worker,NULL,0,NULL);if(!thread)return FALSE;CloseHandle(thread);return TRUE;
}
__declspec(dllexport) BOOL WINAPI Fifa16ModStop(void) {
 unsigned int i;BOOL ok=TRUE;
 InterlockedExchange(&stop_requested,1);
 AcquireSRWLockExclusive(&state_lock);active_assignment=0;target_valid=FALSE;armed=FALSE;cached_receiver=0;cached_kicker=0;other_count=0;ReleaseSRWLockExclusive(&state_lock);
 for(i=0;i<PATCH_COUNT;i++)if(patches[i].patched){if(memcmp((void*)(base+patches[i].rva),patches[i].applied,5)==0 && write_code(base+patches[i].rva,patches[i].saved,5))patches[i].patched=FALSE;else ok=FALSE;}
 if(command_patched){if(exchange_slot(command_slot,(uintptr_t)command_hook,(uintptr_t)command_original))command_patched=FALSE;else ok=FALSE;}
 if(physical_patched){uintptr_t original=(uintptr_t)physical_original;if(exchange_slot(physical_slot,(uintptr_t)physical_hook,original))physical_patched=FALSE;else ok=FALSE;}
 event(ok?"stopped original_call_sites_restored":"stop_failed");return ok;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(module);return TRUE;}
