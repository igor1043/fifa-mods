// Exercise scene(), including the real guard that rejected kickoff friendlies.
#include "standball.cpp"
#include <assert.h>

static unsigned char managerData[128],worldData[128],gameData[128],registryData[1024];
static unsigned char teamData[2][256],statsData[2][256],pageChain[5][512],tournamentChain[5][4096];
static uintptr_t teamPairs[4];
static char pageText[64];
template<class T>static void put(void* at,const T& value){memcpy(at,&value,sizeof(value));}
static void page(const char* text){strcpy_s(pageText,text);nextScene=0;scene();}
static void leave(){page("game/screens/playnow/teamselect");assert(desired==-1&&!visible&&!session.key);}
static void server(const char* key,unsigned value){char text[32];sprintf_s(text,"%u",value);assert(WritePrivateProfileStringA("selection",key,text,contextPath));}
static void friendly(unsigned comp){
 server("schema",1);server("process_id",GetCurrentProcessId());server("home",1043);server("away",567);
 server("competition",0);server("round",0);server("league",7);server("asset",comp);
 assert(WritePrivateProfileStringA("selection","mode","friendly_same_league",contextPath));
}
static void live(unsigned comp,unsigned round){
 put((void*)(image+56170408),(uintptr_t)tournamentChain[0]);
 const unsigned offsets[]={504,3544,1712,80};
 for(unsigned i=0;i<4;++i)put(tournamentChain[i]+offsets[i],(uintptr_t)tournamentChain[i+1]);
 put(tournamentChain[4]+276,1043u);put(tournamentChain[4]+280,567u);
 put(tournamentChain[4]+40,comp);put(tournamentChain[4]+44,round);
}
int main(int argc,char** argv){
 assert(argc==2);strcpy_s(iniPath,argv[1]);
 char temp[MAX_PATH];assert(GetTempPathA(MAX_PATH,temp));assert(GetTempFileNameA(temp,"stb",0,contextPath));
 image=(uintptr_t)VirtualAlloc(nullptr,0x5000000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(image);
 put((void*)(image+58757168),(uintptr_t)pageChain[0]);
 const unsigned offsets[]={232,192,136,472};
 for(unsigned i=0;i<3;++i)put(pageChain[i]+offsets[i],(uintptr_t)pageChain[i+1]);
 put(pageChain[3]+offsets[3],(uintptr_t)pageText);
 put((void*)(image+0x3517420),(uintptr_t)managerData);
 put(managerData,image+0x2226730);put(managerData+8,(uintptr_t)worldData);
 put(worldData,image+0x2225d90);put(worldData+0x10,(uintptr_t)gameData);
 put(gameData,image+0x2309370);put(gameData+0x20,(uintptr_t)registryData);
 const unsigned row=8+15*32;put(registryData+row,15);put(registryData+row+16,2);put(registryData+row+24,(uintptr_t)teamPairs);
 for(unsigned i=0;i<2;++i){
  teamPairs[i*2+1]=(uintptr_t)teamData[i];put(teamData[i],image+0x22fe9f0);
  put(teamData[i]+0x30,(uintptr_t)registryData);put(teamData[i]+0x58,(int)i);
  put(teamData[i]+0x50,(uintptr_t)statsData[i]);put(statsData[i]+0x80,i?567:1043);
 }
 // Reproduce the failure from the user's match: no tournament pointer, but
 // Server16's verified same-league context already selects competition 1738.
 friendly(1738);page("");assert(visible&&desired==asset("brasileirao")&&competition==1738);
 assert(selectionSource==SelectionSource::Friendly);
 page("game/screens/instantReplay/ReplayScreen");assert(visible&&desired==asset("brasileirao"));
 // No Server context and no tournament chain still gives the required generic.
 leave();server("process_id",GetCurrentProcessId()+1);page("");
 assert(visible&&desired>=0&&strstr(standAssets[desired].slug,"generic"));
 const int firstGeneric=desired;page("game/screens/pause/ingame");assert(visible&&desired==firstGeneric);
 // A context arriving late replaces the generic without creating another match.
 friendly(1747);page("");assert(visible&&desired==asset("cbf"));
 // Temporary read gaps keep the established support for this same fixture.
 server("process_id",GetCurrentProcessId()+1);page("");assert(visible&&desired==asset("cbf"));
 // Real cups always win over an old friendly context for the same clubs.
 friendly(1738);live(195,0);page("");assert(visible&&strstr(standAssets[desired].slug,"generic"));
 assert(selectionSource==SelectionSource::Native);
 const unsigned national[]={1741,1747,1757};
 for(unsigned comp:national){live(comp,0);page("");assert(visible&&desired==asset("cbf"));}
 live(2325,2338);page("");assert(visible&&desired==asset("paulistao"));
 live(1738,0);page("");assert(visible&&desired==asset("brasileirao"));
 // An unverified/mismatched friendly context cannot apply branded supports.
 leave();put((void*)(image+56170408),(uintptr_t)0);friendly(1738);server("home",999);
 page("");assert(visible&&strstr(standAssets[desired].slug,"generic"));
 leave();assert(DeleteFileA(contextPath));VirtualFree((void*)image,0,MEM_RELEASE);
 puts("PASS actual scene selection: missing tournament chain + verified friendly, generic fallback, replay, late context, read gap, real cup priority, A/B/C/D/Paulista and mismatched context");
}
