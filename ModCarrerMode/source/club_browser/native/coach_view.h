#pragma once
#include "coach_profile.h"
namespace clubcoach {
struct View{
 Profile profile;int club=0,tab=0,scroll=0;bool ready=false;uint64_t consumed=0,submitted=0;std::string error,modelMessage,profileRevision;clubscene::Assets loading;std::array<int,96> bindings{};std::future<std::shared_ptr<clubanim::Clip>> clip;
 void clear(){profile={};club=tab=scroll=0;ready=false;consumed=submitted=0;error.clear();modelMessage.clear();profileRevision.clear();}
 void request(clublineup::View&worker,int id,int career){clear();club=id;worker.career=career;worker.request(id,"coach");clubscene::intent(false,0);}
 void setTab(int next){tab=(next+3)%3;scroll=0;}
 void navigate(int step){if(tab!=2)return;int count=int(profile.competitions.size()+profile.history.size());scroll=std::clamp(scroll/3+step,0,(std::max)(0,(count+2)/3-1))*3;}
 void poll(clublineup::View&worker,ID3D11Device*device){
  worker.poll(device);if(worker.status=="error"){error=worker.message;return;}
  if(worker.status=="ready"&&worker.kind=="coach"&&worker.club==club&&(worker.sequence!=consumed||worker.lastValues["profile_revision"]!=profileRevision)){
   const bool newRequest=worker.sequence!=consumed;auto file=worker.folder/L"coach.tsv";std::error_code e;auto size=std::filesystem::file_size(file,e);if(e||size>256000){error="Perfil do técnico indisponível.";return;}std::ifstream in(file,std::ios::binary);if(!parse(in,club,profile)){error="Dados do técnico incompatíveis.";return;}consumed=worker.sequence;profileRevision=worker.lastValues["profile_revision"];ready=true;
   if(!newRequest)return; // Metadata refresh must not restart the native actor.
   auto&v=worker.lastValues;modelMessage=v["message"];if(v["actor"]!="1")return;
   clubscene::Assets a;a.sequence=worker.sequence;a.club=club;a.career=worker.career;a.single=true;a.player=100000000+club;a.hash=v["hash"];a.pages=number(v["pages"],1,96);if(v["player"]!=std::to_string(a.player)||v["renderer"]!="native"||!clubscene::validAssets(a)){modelMessage="Modelo do técnico incompatível.";return;}
   auto parts=clubroster::split(v["bindings"],',');if(parts.size()!=96){modelMessage="Materiais do técnico incompletos.";return;}for(int i=0;i<96;++i){bindings[i]=number(parts[i],0,a.pages-1);if(bindings[i]<0){modelMessage="Material do técnico inválido.";return;}}
   clubscene::playerHeight=float(number(v["height"],130,230,185));loading=a;
   if(v["animated"]=="1"){auto path=worker.gameRoot/L"data/sceneassets/server16_club_xi"/std::to_wstring(GetCurrentProcessId())/a.hash/L"animation.bin";clip=std::async(std::launch::async,[path,id=a.player](){return clubanim::load(path,id);});}
   else{clubscene::submit(a,bindings);submitted=a.sequence;}
  }
  if(clip.valid()&&clip.wait_for(std::chrono::milliseconds(0))==std::future_status::ready){auto result=clip.get();if(loading.sequence==worker.sequence&&worker.kind=="coach"&&club==loading.club){if(!result){modelMessage="Animação do técnico indisponível.";return;}loading.animation=std::move(result);clubscene::submit(loading,bindings);submitted=loading.sequence;}}
 }
};
}
