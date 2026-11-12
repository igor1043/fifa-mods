#include "reload_completion.h"
#include "menu_page.h"
#include "reload_scope.h"
#include "../../common/scene_startup.h"
#include <cassert>
#include <iostream>
int main(){
 using namespace frontend_stadium;
 CompletionSample s;s.pending=s.career=s.currentCareer=s.customRoute=true;
 s.team=s.currentTeam=1043;s.preparedEpoch=s.currentEpoch=16;
 s.requestsAtPost=8;s.requests=9;s.slot=s.activeSlot=261;
 // Captured session: native models load on the room page, with no further
 // BackgroundDP callback. Only the render observer continues to run.
 s.nativeState=14;assert(!reloadCompleted(s));
 s.sceneLoaded=true;s.drawn=true;assert(!reloadCompleted(s));
 s.nativeState=0;assert(reloadCompleted(s));
 scene_startup::Sample room;room.club=1043;room.epoch=16;room.service=1;room.registry=2;
 room.context=room.loaderIdle=room.routeRequired=room.routeCurrent=true;room.phase=2;
 scene_startup::Gate gate;assert(!gate.allow(room,1000)&&gate.reason==3);
 if(reloadCompleted(s))room.phase=3;
 assert(!gate.allow(room,1016)&&gate.reason==4);assert(gate.allow(room,1766));
 auto good=s;
 for(int state:{-1,1,2,5,14}){s=good;s.nativeState=state;assert(!reloadCompleted(s));}
 s=good;s.nativeState=12;assert(reloadCompleted(s));
 s=good;s.pending=false;assert(!reloadCompleted(s));
 s=good;s.sceneLoaded=false;assert(!reloadCompleted(s));
 s=good;s.drawn=false;assert(!reloadCompleted(s));
 s.customRoute=false;assert(reloadCompleted(s)); // native fallback
 s=good;s.requests=8;assert(!reloadCompleted(s));
 s=good;s.activeSlot=176;assert(!reloadCompleted(s));
 s=good;s.currentTeam=1629;assert(!reloadCompleted(s));
 s=good;s.currentCareer=false;assert(!reloadCompleted(s));
 s=good;s.currentEpoch=17;assert(!reloadCompleted(s)); // same club, new save
 s.currentEpoch=0;assert(!reloadCompleted(s));
 // Reopening the same save requires the new route and its own settling time.
 s=good;s.currentEpoch=s.preparedEpoch=18;s.requests=10;s.requestsAtPost=9;
 s.slot=s.activeSlot=176;assert(reloadCompleted(s));
 room.epoch=18;room.request=10;room.slot=176;assert(!gate.allow(room,2000));assert(gate.allow(room,2750));
 for(auto card:{PageKind::DressingRoom,PageKind::TrophyRoom}){
  assert(isDedicatedRoomPage(card)&&!isBackgroundPage(card));
  assert(deferQueuedBackground(true,true,false,false,9,8,0,true)); // async preparation, not dispatched
  assert(deferQueuedBackground(true,true,true,false,9,9,12,true)); // ready queue, not dispatched
  assert(!deferQueuedBackground(true,true,true,true,9,9,0,true)); // accepted engine command
  assert(!deferQueuedBackground(true,true,true,false,10,9,0,true)); // native load already started
  assert(!deferQueuedBackground(true,true,false,false,9,8,14,true)); // awaiting native background acknowledgement
 }
 assert(!deferQueuedBackground(false,true,false,false,9,8,0,true)); // preserve Hub/idle stadium
 ReloadScope scope;scope.view=scope.background=scope.backgroundRegistry=scope.commands=1;
 scope.careerService=scope.careerRegistry=1;scope.epoch=16;scope.team=1043;scope.ownerThread=scope.careerThread=1;
 scope.career=scope.frontendCallback=scope.resolved=true;
 for(auto page:{PageKind::DressingRoom,PageKind::TrophyRoom}){
  scope.page=page;assert(scope.valid());
  assert(!canDispatchReload(scope,scope,0)&&!canDispatchReload(scope,scope,12));
  assert(canDispatchReload(scope,scope,14,true)); // finish already accepted load only
  auto stale=scope;stale.epoch++;assert(!canDispatchReload(scope,stale,14,true));
 }
 std::cout<<"PASS render-only reload completion: custom room, native idle/draw proof, club/save epoch isolation, re-entry and startup settling\n";
}
