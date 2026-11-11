// Separate renderables: the gallery's own loading card never changes the
// dressing-room loader, game UI, save or renderables belonging to other mods.
void loading(bool show){
 loadingVisible=show;
 if(!show){for(auto&c:loadingParts)visibility(*c,false);return;}
 if(loadingClub!=club){
  for(auto&c:loadingParts){visibility(*c,false);retired.push_back(std::move(c));}
  loadingParts.clear();loadingClub=club;
 }
 if(loadingParts.empty())for(const char* key:{"backdrop","panel","progress","badge"}){
  auto c=std::make_unique<Component>();c->key=std::string("loading_")+key;
  c->type="s16_trophy_loading_"+std::to_string(GetCurrentProcessId())+"_"+std::to_string(club.load())+"_"+key;
  c->model="data/sceneassets/server16_trophy_room/loading-"+std::string(key)+".rx3";c->submesh="gallery_part_1";
  c->texture="data/sceneassets/server16_trophy_room/loading-"+std::string(!strcmp(key,"panel")?"texture":!strcmp(key,"progress")?"gold":"white")+".rx3";c->diffuse="gallery_cm";
  if(!strcmp(key,"badge")){c->texture="data/ui/imgassets/crest/light/l"+std::to_string(club.load())+".dds";c->diffuse="";c->alpha=true;}
  c->aux="data/sceneassets/server16_trophy_room/normal.rx3";c->normal="gallery_nm";
  c->coeffTexture="data/sceneassets/server16_trophy_room/matte.rx3";c->coeff="gallery_coeff";c->baked=true;
  c->matrices.push_back({1,0,0,0,0,1,0,0,0,0,1,0,originX,1000,0,1});loadingParts.push_back(std::move(c));
 }
 for(auto&c:loadingParts){
  if(!c->attempted)c->failed=!create(*c);
  if(c->object&&!c->failed&&!c->loaded)c->loaded=loaded(*c);
  if(c->key=="loading_progress"){
   float fraction=componentCount?std::min(1.f,float(loadedCount)/float(componentCount)):.2f;
   float offset=componentCount?0.f:(1.f+sinf(float(GetTickCount64()%4000)*.0015707963f))*.4f;
   auto&m=c->matrices.front();m[0]=fraction;m[12]=originX-459.f+459.f*fraction+918.f*offset;
  }
  visibility(*c,c->loaded&&!c->failed);
 }
 camera.apply(false);
}
