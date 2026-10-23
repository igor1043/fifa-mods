#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

enum class EntranceScene { Unknown, StadiumPan, Presentation, ToKickoff, Gameplay };
enum class EntranceAnthem { Unknown, Inactive, Active };
struct EntranceIntroLifetime {
    uintptr_t fixture=0,registry=0;
    bool sawActive=false,ended=false;
    uint64_t missingSince=0;
    void reset(){fixture=registry=0;sawActive=ended=false;missingSince=0;}
    bool observe(uintptr_t key,uintptr_t owner,uint64_t now,bool known,bool active,bool completed,
                 int phase,bool paused,bool replay,bool nis,bool organisation=false){
        if(fixture!=key||registry!=owner){reset();fixture=key;registry=owner;}
        if(!known){missingSince=0;return ended;}
        if(active){
            if(ended&&!paused&&!replay&&phase>=0&&phase<=2){ended=false;sawActive=false;}
            sawActive=true;missingSince=0;
        }else if(sawActive&&!ended){
            // Pauses may suspend a service; an absent service in a menu is
            // not an end signal. A readable completion bit is conclusive.
            if(completed&&!nis)ended=true;
            else if(organisation&&!paused&&!replay&&!nis){
                if(!missingSince)missingSince=now;
                if(now-missingSince>=150)ended=true;
            }else missingSince=0;
        }
        return ended;
    }
};
static bool entrance_skip_ended(bool stateValid,int nativePhase,int sports,const char* camera,
                                bool intro,bool nis,bool paused,bool replay){
    // This is the native playable camera at 0:00, after a skipped ceremony.
    // The opening's "steadycam fake kickoff" is deliberately excluded.
    return stateValid&&nativePhase==0&&(sports==2||sports==15)&&!intro&&!nis&&!paused&&!replay&&
           camera&&!strncmp(camera,"bc: broadcast pos",17);
}
struct EntranceLineups {
    uintptr_t fixture=0,pendingOwner=0,activeOwner=0;
    int pendingSide=-1,activeSide=-1;
    unsigned shown=0,closed=0;
    bool finished=false,newCycle=false;
    void reset(){fixture=0;pendingOwner=activeOwner=0;pendingSide=activeSide=-1;shown=closed=0;finished=newCycle=false;}
    void post(uintptr_t key,uintptr_t owner,int side){
        if(side<0||side>1)return;
        if(fixture!=key){reset();fixture=key;}
        if(finished){reset();fixture=key;newCycle=true;}
        pendingOwner=owner;pendingSide=side;
    }
    bool shown_overlay(uintptr_t owner){
        if(owner!=pendingOwner||pendingSide<0)return false;
        activeOwner=owner;activeSide=pendingSide;shown|=1u<<activeSide;closed&=~(1u<<activeSide);
        pendingOwner=0;pendingSide=-1;return true;
    }
    bool removed_overlay(uintptr_t owner){
        if(owner!=activeOwner||activeSide<0)return false;
        closed|=1u<<activeSide;activeSide=-1;
        if(shown==3&&closed==3&&pendingSide<0)finished=true;
        return true;
    }
};
static bool entrance_kickoff_assignment(int phase,int state,int contextPhase) {
    // User-marked post-lineup scene has an active KickOffScriptAssignment,
    // phase 4/state 2, alongside the still-active general intro phase 3.
    return phase==4 && (state==2 || state==3) && contextPhase>=3 && contextPhase<=32;
}
[[maybe_unused]] static bool entrance_organisation_stage(int introPhase,const char* camera,bool kickoffAssignment=false) {
    // User-marked native IntroScriptAssignment: phase 3 is the team lineup;
    // phase 5 begins the organisation. Inspect only this assignment class.
    // 'steadycam fake kickoff' also runs in opening phase 1, before lineups.
    // It cannot identify the end of the anthem and must never consume an intro.
    return kickoffAssignment || (introPhase>=5 && introPhase<=32) ||
        (camera && !strncmp(camera,"bc: broadcast pos",17));
}
struct EntrancePolicy {
    uintptr_t fixture=0;
    bool armed=false,consumed=false,sawPresentation=false,sawAnthem=false;
    int lastPlayableClock=0;
    int lastIntroPhase=-1;
    EntranceScene lastScene=EntranceScene::Unknown;
    bool visible(bool validMatch,bool paused,bool replay,uintptr_t key,int clock,EntranceScene scene,
                 EntranceAnthem anthem=EntranceAnthem::Unknown,int introPhase=-1) {
        if(!validMatch)return false;
        if(fixture!=key){leave();fixture=key;}
        if(paused || replay){
            // Keep the ceremony's props while paused. Only the verified end
            // stage can consume it; audio/pan changes in menus cannot rearm it.
            if(scene==EntranceScene::ToKickoff){
                consumed=true;
                if(introPhase>=3 && introPhase<=32)lastIntroPhase=introPhase;
                else if(lastIntroPhase<3 && introPhase<0)lastIntroPhase=5;
            }else if(!replay && !armed && !consumed && clock==0 && scene==EntranceScene::Presentation &&
                     introPhase>=0 && introPhase<5){
                // Joining a running, paused introduction still shows its props.
                armed=true;sawPresentation=true;lastIntroPhase=introPhase;
            }
            return armed&&!consumed;
        }
        // Restarting during the ceremony keeps both clubs and clock 0. The
        // verified intro script rolls from lineup/end (3+) back to its
        // opening (0-2). Pause pans leave the script phase unchanged.
        if(consumed && clock==0 && lastIntroPhase>=3 && introPhase>=0 && introPhase<=2){
            armed=false;consumed=false;sawPresentation=false;sawAnthem=false;
            lastPlayableClock=0;
        }
        if(introPhase>=0 && introPhase<=32)lastIntroPhase=introPhase;
        // A pause camera can also be a stadium pan at 0:00. Rearm only after
        // an observed playable clock rolls back, or after leave/new fixture.
        if(scene==EntranceScene::StadiumPan && clock==0 && consumed && lastPlayableClock>0){
            armed=false;consumed=false;sawPresentation=false;sawAnthem=false;
            lastPlayableClock=0;
        }
        if(scene!=EntranceScene::Unknown)lastScene=scene;
        if(scene==EntranceScene::Gameplay){
            if(clock>0)lastPlayableClock=clock;
            // Loading can briefly expose an old clock. Only real gameplay or
            // the end of an armed presentation is allowed to consume it.
            if(armed || clock>0)consumed=true;
        }
        if(!consumed && !armed && clock==0 &&
           (scene==EntranceScene::StadiumPan || scene==EntranceScene::Presentation))armed=true;
        if(armed && scene==EntranceScene::Presentation)sawPresentation=true;
        // Audio can change during the anthem/camera transitions. It is only
        // diagnostic: the user wants the props through the away-team lineup.
        if(armed && scene==EntranceScene::Presentation){
            if(anthem==EntranceAnthem::Active)sawAnthem=true;
        }
        // A confirmed organisation stage also closes an intro when this module
        // joins a running match, or the opening was skipped before it armed.
        if(scene==EntranceScene::ToKickoff){
            consumed=true;
            // Hot-joining after the script has gone still observes its end.
            // Remember that boundary so restarting at clock 0 rearms too.
            if(lastIntroPhase<3 && introPhase<0)lastIntroPhase=5;
        }
        return armed && !consumed;
    }
    void leave(){fixture=0;armed=false;consumed=false;sawPresentation=false;sawAnthem=false;lastPlayableClock=0;lastIntroPhase=-1;lastScene=EntranceScene::Unknown;}
};

static constexpr size_t EntranceRecordBytes=0x50;
static constexpr float EntranceHiddenHeight=-3000;
static float entrance_render_height(bool visible,float pitchHeight){return visible?pitchHeight:EntranceHiddenHeight;}
static constexpr size_t EntranceMaxOriginals=127;
static size_t entrance_clean(unsigned char* records,size_t count) {
    size_t changed=0;
    for(size_t i=0;i<count;++i){
        auto r=records+i*EntranceRecordBytes;
        if(r[0x42]){r[0x42]=0;r[0x40]=r[0x41]=0xff;r[0x45]=0;++changed;}
    }
    return changed;
}
static void entrance_static_position(unsigned char* record,float height) {
    const float position[4]={0,height,0,0};
    memcpy(record+0x20,position,sizeof(position));
    // Native reset 43a8d87 copies previous (+30) back to current (+20).
    // Keep both on the pitch; visibility is controlled by the draw list.
    memcpy(record+0x30,position,sizeof(position));
}
static void entrance_new_record(unsigned char* record,float height) {
    memset(record,0,EntranceRecordBytes);
    entrance_static_position(record,height);
    record[0x40]=record[0x41]=0xff;
    record[0x42]=1;
}
