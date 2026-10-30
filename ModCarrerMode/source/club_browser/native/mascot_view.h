#pragma once
namespace clubmascot {
inline int number(const std::string&s,int low,int high){try{size_t end=0;int n=std::stoi(s,&end);return end==s.size()&&n>=low&&n<=high?n:-1;}catch(...){return -1;}}
struct View{
 int club=0,career=0;uint64_t consumed=0,submitted=0;bool ready=false;std::string error;
 std::future<std::shared_ptr<clubanim::Clip>> staticClip;clubscene::Assets staticAssets;std::array<int,96>staticPages{};
 void enter(clublineup::View&worker,int id,int activeCareer){club=id;career=activeCareer;consumed=submitted=0;ready=false;error.clear();clubscene::intent(false,0);clubanim::activate({});if(career>0){worker.career=career;worker.request(club,"mascot");}}
 void poll(clublineup::View&worker,ID3D11Device*device){
  if(staticClip.valid()&&staticClip.wait_for(std::chrono::milliseconds(0))==std::future_status::ready){
   auto clip=staticClip.get();if(worker.kind=="mascot"&&worker.sequence==staticAssets.sequence&&club==staticAssets.club&&career==staticAssets.career){
    if(!clip){error="Geometria estável do mascote indisponível.";return;}
    staticAssets.animation=std::move(clip);clubscene::submit(staticAssets,staticPages);submitted=staticAssets.sequence;ready=true;
   }
  }
  worker.poll(device);if(worker.kind!="mascot"||worker.club!=club)return;
  if(worker.status=="error"){error=worker.message;return;}
  if(worker.status!="ready"||consumed==worker.sequence)return;
  consumed=worker.sequence;ready=true;auto&v=worker.lastValues;
  if(v["career"]!=std::to_string(career)){error="A carreira mudou. Abra o mascote novamente.";return;}
  // Missing means empty: never fall back to another mascot or previous actor.
  if(v["actor"]=="0")return;
  clubscene::Assets a;a.sequence=worker.sequence;a.club=club;a.career=career;a.single=true;a.hash=v["hash"];a.pages=number(v["pages"],1,96);
  int height=number(v["height"],20,500);std::array<int,96>bindings{};auto parts=clubroster::split(v["bindings"],',');
  if(v["actor"]!="1"||v["renderer"]!="native"||height<0||!clubscene::validAssets(a)||parts.size()!=96){error="Modelo do mascote incompatível.";return;}
  for(int i=0;i<96;++i){bindings[i]=number(parts[i],0,a.pages-1);if(bindings[i]<0){error="Material do mascote inválido.";return;}}
  clubscene::playerHeight=float(height);
  if(v["stable_stream"]=="1"){
   staticAssets=a;staticPages=bindings;ready=false;
   auto path=worker.gameRoot/L"data/sceneassets/server16_club_xi"/std::to_wstring(GetCurrentProcessId())/a.hash/L"animation.bin";
   staticClip=std::async(std::launch::async,[path](){return clubanim::load(path,0);});return;
  }
  clubscene::submit(a,bindings);submitted=a.sequence;
 }
};
}
