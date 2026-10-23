// Observe the stock InjuryList publications while preserving the installed
// career mod's callbacks. Capturing never changes a diagnosis or save field.
struct RoomInjuryRow {int player=0;std::string name,injury,returnLabel;};
SRWLOCK roomMedicalGate=SRWLOCK_INIT;std::vector<RoomInjuryRow> roomInjuries;
uintptr_t roomInjuryProvider=0;unsigned roomInjuryClub=0;int roomInjuryHead=0;uint64_t roomInjuryTick=0;
std::atomic<bool> roomMedicalDirty{false};
struct RoomInjuryPatch {uintptr_t source,target,previous=0,address=0;LONG64 before=0,after=0;bool installed=false;};
RoomInjuryPatch roomInjuryPatches[]={{0x5901eb1,0x5a51150},{0x5901ec7,0x5a511e0},{0x5901f18,0x5a511e0},{0x5901f6e,0x5a511e0},{0x5901fd7,0x5a511e0}};
void*roomMedicalRelay=nullptr;
void roomInjuryBatch(void*provider){
 const auto now=GetTickCount64();const unsigned club=validCareerClub;
 if(roomInjuryProvider!=(uintptr_t)provider||club!=roomInjuryClub||now-roomInjuryTick>5000){roomInjuries.clear();roomInjuryHead=0;roomInjuryProvider=(uintptr_t)provider;roomInjuryClub=club;}
 roomInjuryTick=now;
}
std::string roomInjuryText(const char*value){char text[256]{};if(!read((uintptr_t)value,text,255))return {};for(auto&c:text)if(c=='\t'||c=='\n'||c=='\r')c=' ';return text;}
void roomInjuryString(void*provider,const char*attribute,const char*value){
 if(!validCareerClub)return;const auto key=roomInjuryText(attribute),text=roomInjuryText(value);if(text.empty())return;
 AcquireSRWLockExclusive(&roomMedicalGate);roomInjuryBatch(provider);
 if(key=="PLAYERNAME"||key=="PLAYER_NAME"){
  auto i=std::find_if(roomInjuries.begin(),roomInjuries.end(),[&](const auto&r){return r.name==text;});
  if(i==roomInjuries.end()&&roomInjuries.size()<64)roomInjuries.push_back({roomInjuryHead,text,{},{}});
 }else if(!roomInjuries.empty()){
  auto&r=roomInjuries.back();if(key=="INJURY")r.injury=text;else if(key=="LENGTH")r.returnLabel=text;
 }
 roomMedicalDirty=true;ReleaseSRWLockExclusive(&roomMedicalGate);
}
void __fastcall roomInjuryId(void*p,const char*a,int value){
 ((void(__fastcall*)(void*,const char*,int))roomInjuryPatches[0].previous)(p,a,value);
 if(!validCareerClub)return;AcquireSRWLockExclusive(&roomMedicalGate);roomInjuryBatch(p);roomInjuryHead=value;ReleaseSRWLockExclusive(&roomMedicalGate);
}
template<size_t I>void __fastcall roomInjuryField(void*p,const char*a,const char*v){
 ((void(__fastcall*)(void*,const char*,const char*))roomInjuryPatches[I].previous)(p,a,v);roomInjuryString(p,a,v);
}
bool medicalExchange(RoomInjuryPatch&p,LONG64 from,LONG64 to){DWORD old=0;if(!VirtualProtect((void*)p.address,8,PAGE_EXECUTE_READWRITE,&old))return false;auto seen=InterlockedCompareExchange64((volatile LONG64*)p.address,to,from);DWORD ignored;VirtualProtect((void*)p.address,8,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(image+p.source),10);return seen==from;}
bool installMedicalCapture(){
 if(roomInjuryPatches[0].installed)return true;
 const uintptr_t callbacks[]={(uintptr_t)&roomInjuryId,(uintptr_t)&roomInjuryField<1>,(uintptr_t)&roomInjuryField<2>,(uintptr_t)&roomInjuryField<3>,(uintptr_t)&roomInjuryField<4>};
 if(!roomMedicalRelay){for(uintptr_t step=0x10000;step<0x70000000&&!roomMedicalRelay;step+=0x10000)roomMedicalRelay=VirtualAlloc((void*)(image+step),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!roomMedicalRelay)return false;}
 for(size_t i=0;i<std::size(roomInjuryPatches);++i){auto&p=roomInjuryPatches[i];unsigned char c[5]{};if(!read(image+p.source,c,5)||c[0]!=0xe8)return false;LONG d=0;memcpy(&d,c+1,4);p.previous=uintptr_t(intptr_t(image+p.source+5)+d);
  if(p.previous!=image+p.target){unsigned char jump[12]{};if(!read(p.previous,jump,12)||jump[0]!=0x48||jump[1]!=0xb8||jump[10]!=0xff||jump[11]!=0xe0)return false;uintptr_t fn=0;memcpy(&fn,jump+2,8);HMODULE owner=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)fn,&owner)||owner!=GetModuleHandleW(L"dinput8.dll"))return false;}
  const auto displacement=image+p.source+1;unsigned skip=0;auto aligned=displacement&~uintptr_t(7);if(displacement+4>aligned+8){skip=static_cast<unsigned>(aligned+8-displacement);aligned+=8;}
  const uintptr_t offset=0x100+i*0x200+(p.previous&255);const auto dest=uintptr_t(roomMedicalRelay)+offset;const auto delta=intptr_t(dest)-intptr_t(image+p.source+5);if(delta<INT32_MIN||delta>INT32_MAX)return false;
  const auto maskLow=(1u<<(skip*8))-1u;if((static_cast<uint32_t>(delta)&maskLow)!=(static_cast<uint32_t>(d)&maskLow))return false;
  unsigned char jump[14]={0xff,0x25,0,0,0,0};memcpy(jump+6,&callbacks[i],8);memcpy((void*)dest,jump,14);
  p.address=aligned;p.before=get<LONG64>(aligned);const unsigned shift=static_cast<unsigned>(displacement+skip-aligned)*8,bits=(4-skip)*8;const uint64_t mask=((uint64_t(1)<<bits)-1)<<shift;
  p.after=static_cast<LONG64>((static_cast<uint64_t>(p.before)&~mask)|((uint64_t(static_cast<uint32_t>(delta)>>(skip*8))<<shift)&mask));
 }
 DWORD old=0;if(!VirtualProtect(roomMedicalRelay,4096,PAGE_EXECUTE_READ,&old))return false;FlushInstructionCache(GetCurrentProcess(),roomMedicalRelay,4096);
 for(auto&p:roomInjuryPatches){if(!medicalExchange(p,p.before,p.after)){for(auto&done:roomInjuryPatches)if(done.installed){medicalExchange(done,done.after,done.before);done.installed=false;}return false;}p.installed=true;}
 log("MEDICAL_NATIVE_CAPTURE_READY: original InjuryList setters chained, read-only data");return true;
}
void flushMedicalCapture(){
 if(!roomMedicalDirty.exchange(false))return;
 unsigned pid=0,club=0,version=0,date=0;std::string magic;std::ifstream scope(folder/L"runtime/medical_scope.txt");
 if(!(scope>>magic>>version>>pid>>club>>date)||magic!="S16MEDICALSCOPE"||version!=1||pid!=GetCurrentProcessId()||club!=validCareerClub)return;
 std::ofstream f(folder/L"runtime/medical_native_capture.tsv.new");AcquireSRWLockShared(&roomMedicalGate);
 if(club!=roomInjuryClub){ReleaseSRWLockShared(&roomMedicalGate);return;}
 f<<"S16MEDICAL 1 "<<pid<<' '<<club<<' '<<date<<' '<<roomInjuryTick<<'\n';for(const auto&r:roomInjuries)f<<r.player<<'\t'<<r.name<<'\t'<<r.injury<<'\t'<<r.returnLabel<<'\n';ReleaseSRWLockShared(&roomMedicalGate);f.close();MoveFileExW((folder/L"runtime/medical_native_capture.tsv.new").c_str(),(folder/L"runtime/medical_native_capture.tsv").c_str(),MOVEFILE_REPLACE_EXISTING);
}
void stopMedicalCapture(){for(auto&p:roomInjuryPatches)if(p.installed){medicalExchange(p,p.after,p.before);p.installed=false;}}
