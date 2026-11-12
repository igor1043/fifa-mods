#pragma once
#include <cstdint>
namespace frontend_stadium {
// Completion observes engine state; it never dispatches a background command.
// A custom career screen can stop BackgroundDP callbacks after loading starts.
struct CompletionSample {
 bool pending=false,career=false,currentCareer=false,sceneLoaded=false,customRoute=false,drawn=false;
 uint32_t team=0,currentTeam=0,preparedEpoch=0,currentEpoch=0,requests=0,requestsAtPost=0;
 int slot=-1,activeSlot=-1,nativeState=-1;
};
inline bool reloadCompleted(const CompletionSample&s){
 return s.pending&&s.team&&s.team==s.currentTeam&&s.career==s.currentCareer
     &&(!s.career||(s.currentEpoch&&s.currentEpoch==s.preparedEpoch))
     &&(s.nativeState==0||s.nativeState==12)&&s.sceneLoaded
     &&s.slot>=0&&s.activeSlot==s.slot&&s.requests>s.requestsAtPost
     &&(!s.customRoute||s.drawn);
}
inline bool deferQueuedBackground(bool dedicated,bool queued,bool awaiting,bool started,
                                  uint32_t requests,uint32_t posted,int nativeState,bool loaded){
 return dedicated&&queued&&loaded&&(nativeState==0||nativeState==12)
     &&(!awaiting||(!started&&requests==posted));
}
}
