#include "entrance_policy.h"
#include <assert.h>
#include <stdio.h>
int main(){
    using S=EntranceScene;
    using A=EntranceAnthem;
    EntranceIntroLifetime lifetime;
    assert(!lifetime.observe(1,100,1000,true,true,false,1,false,false,false));
    assert(!lifetime.observe(1,100,1100,true,false,false,-1,true,false,false));
    assert(!lifetime.observe(1,100,1500,true,false,false,-1,true,false,false)); // pause does not finish intro
    assert(!lifetime.observe(1,100,1600,false,false,false,-1,false,false,false)); // unreadable RAM
    assert(!lifetime.observe(1,100,1700,true,false,false,-1,false,false,true)); // anthem NIS transition
    assert(!lifetime.observe(1,100,1800,true,true,false,3,false,false,false));
    assert(!lifetime.observe(1,100,1900,true,false,false,-1,false,false,false));
    assert(!lifetime.observe(1,100,2000,true,true,false,3,false,false,false)); // brief readable gap
    assert(!lifetime.observe(1,100,2100,true,false,false,-1,false,false,false));
    assert(!lifetime.observe(1,100,10000,true,false,false,-1,false,false,false)); // no NIS flag during a longer hymn gap
    assert(!lifetime.observe(1,100,10100,true,false,false,-1,false,false,false,true));
    assert(lifetime.observe(1,100,10250,true,false,false,-1,false,false,false,true)); // A bypassed both lineups; native phase is playable at 0:00
    assert(lifetime.observe(1,100,2300,false,false,false,-1,true,false,false)); // latched while paused
    assert(lifetime.observe(1,100,2400,true,true,false,1,true,false,false));
    assert(!lifetime.observe(1,100,2500,true,true,false,1,false,false,false)); // match restart, same clubs
    assert(lifetime.observe(1,100,2600,true,false,true,-1,true,false,false)); // native completion, even paused
    assert(!lifetime.observe(2,101,2700,true,false,true,-1,false,false,false)); // other fixture, no stale completion
    assert(!entrance_skip_ended(true,3,2,"bc: broadcast pos 0.00",false,false,false,false));
    assert(!entrance_skip_ended(true,0,2,"bc: steadycam fake kickoff",false,false,false,false));
    assert(!entrance_skip_ended(true,0,2,"bc: broadcast pos 0.00",true,false,false,false));
    assert(!entrance_skip_ended(true,0,2,"bc: broadcast pos 0.00",false,true,false,false));
    assert(!entrance_skip_ended(true,0,2,"bc: broadcast pos 0.00",false,false,true,false));
    assert(!entrance_skip_ended(true,0,2,"bc: broadcast pos 0.00",false,false,false,true));
    assert(entrance_skip_ended(true,0,2,"bc: broadcast pos 0.00",false,false,false,false));
    assert(entrance_skip_ended(true,0,15,"bc: broadcast pos 0.00",false,false,false,false));
    EntranceLineups l;
    l.post(1,100,0);assert(l.shown_overlay(100)&&l.shown==1&&!l.finished);
    // The away request can arrive before the previous home widget closes.
    l.post(1,100,1);assert(l.removed_overlay(100)&&l.closed==1&&!l.finished);
    assert(l.shown_overlay(100)&&l.shown==3&&!l.finished);
    assert(!l.removed_overlay(200)&&!l.finished); // unrelated overlay owner
    assert(l.removed_overlay(100)&&l.closed==3&&l.finished);
    assert(!l.removed_overlay(100)&&l.finished); // duplicate close
    l.post(1,100,0);assert(l.newCycle&&!l.finished&&l.shown==0);
    l.reset();l.post(2,200,1);assert(l.shown_overlay(200)); // reverse order
    assert(l.removed_overlay(200)&&!l.finished);
    l.post(2,200,0);assert(l.shown_overlay(200));assert(l.removed_overlay(200)&&l.finished);
    l.reset();l.post(3,300,0);assert(l.shown_overlay(300));assert(l.removed_overlay(300));
    l.post(3,300,1);assert(l.shown_overlay(300));
    l.post(3,300,1);assert(l.removed_overlay(300)&&!l.finished); // replacement still pending
    assert(l.shown_overlay(300)&&l.closed==1);assert(l.removed_overlay(300)&&l.finished);
    EntrancePolicy p;
    assert(!p.visible(false,false,false,10,0,S::StadiumPan));
    // RAM regression: transient clock 9 while loading used to consume the intro.
    assert(!p.visible(true,false,false,10,9,S::Unknown));
    assert(!p.consumed);
    assert(p.visible(true,false,false,10,0,S::StadiumPan));
    assert(p.visible(true,true,false,10,0,S::Presentation));
    assert(!p.consumed && p.armed);
    assert(p.visible(true,false,false,10,0,S::Presentation));
    assert(p.visible(true,false,false,10,9,S::Unknown));
    assert(p.visible(true,false,true,10,0,S::Presentation));
    assert(p.visible(true,false,false,10,0,S::Presentation));
    assert(!p.visible(true,false,false,10,0,S::ToKickoff)); // remove while clock is still zero
    assert(p.consumed);
    // The user's pause regression: returning to a 0:00 pan after the cutoff
    // is not a new match and must never bring the objects back.
    assert(!p.visible(true,false,false,10,0,S::StadiumPan));
    assert(!p.visible(true,true,false,10,0,S::Presentation));
    assert(!p.visible(true,false,false,10,0,S::StadiumPan));
    assert(p.consumed);
    assert(!p.visible(true,false,false,10,0,S::Presentation));
    assert(!p.visible(true,false,false,10,500,S::Gameplay));
    assert(!p.visible(true,false,false,10,500,S::Presentation));
    assert(!p.visible(true,false,false,10,270000,S::Presentation));
    assert(!p.visible(true,false,true,10,0,S::StadiumPan));
    assert(!p.visible(true,true,false,10,0,S::StadiumPan));
    assert(!p.visible(true,false,false,10,0,S::StadiumPan)); // a played match never rearms on a clock rollback
    assert(!p.visible(true,false,false,10,0,S::Presentation));
    assert(!p.visible(true,false,false,10,0,S::ToKickoff));
    assert(p.visible(true,false,false,20,0,S::Presentation));
    p.leave();assert(!p.visible(true,false,false,30,200,S::Gameplay));
    assert(!p.visible(true,false,false,30,0,S::Presentation));
    p.leave();assert(p.visible(true,false,false,30,0,S::StadiumPan));
    assert(!p.visible(true,false,false,30,0,S::ToKickoff)); // skipped presentation
    assert(!p.visible(true,false,false,30,0,S::Unknown));
    // Regression from the user's working v2 match: the general intro remains
    // active after the anthem. Remove at the subscene exit while clock is 0.
    p.leave();
    assert(p.visible(true,false,false,30,0,S::StadiumPan,A::Inactive));
    assert(p.visible(true,false,false,30,0,S::Presentation,A::Inactive));
    assert(!p.consumed && !p.sawAnthem); // walking out precedes the anthem
    assert(p.visible(true,false,false,30,0,S::Presentation,A::Active));
    assert(p.sawAnthem);
    assert(p.visible(true,true,false,30,0,S::Presentation,A::Inactive));
    assert(!p.consumed); // pause can alter the audio snapshot
    assert(p.visible(true,false,true,30,0,S::Presentation,A::Inactive));
    assert(!p.consumed);
    assert(p.visible(true,false,false,30,0,S::Presentation,A::Unknown));
    assert(p.visible(true,false,false,30,0,S::Presentation,A::Inactive));
    assert(!p.consumed); // audio/camera transitions cannot remove props during hymns
    assert(!p.visible(true,false,false,30,0,S::ToKickoff,A::Inactive));
    assert(p.consumed);
    assert(!p.visible(true,false,false,30,0,S::Presentation,A::Active));
    assert(!p.visible(true,false,false,30,0,S::StadiumPan,A::Inactive));
    assert(!p.visible(true,true,false,30,0,S::StadiumPan,A::Inactive));
    assert(!p.visible(true,false,false,30,0,S::Presentation,A::Active));
    assert(!p.visible(true,false,false,30,500,S::Gameplay,A::Inactive));
    assert(!p.visible(true,false,false,30,0,S::StadiumPan,A::Inactive));
    assert(p.matchStarted&&p.consumed); // clock-positive gameplay is latched for this fixture
    assert(p.visible(true,false,false,31,0,S::Presentation,A::Unknown)); // a new fixture can show its intro
    assert(!entrance_organisation_stage(1,"bc: steadycam fake kickoff 2 2.15"));
    assert(!entrance_organisation_stage(3,"bc: steadycam fake kickoff m 0.13"));
    assert(!entrance_organisation_stage(-1,"bc: steadycam fake kickoff l 0.01"));
    assert(!entrance_organisation_stage(-1,nullptr));
    assert(!entrance_organisation_stage(0,"bc: stadium beauty fix 1 0.20"));
    assert(!entrance_organisation_stage(3,"bc: behind net caption 4 22.10"));
    assert(entrance_organisation_stage(5,"bc: iso high 0.00"));
    assert(entrance_organisation_stage(6,"bc: handheld sideline right 0.05"));
    assert(entrance_organisation_stage(-1,"bc: broadcast pos 0.00"));
    assert(!entrance_organisation_stage(-1,"bc: stadiumpancam_1 0.00"));
    assert(entrance_kickoff_assignment(4,2,3));
    assert(entrance_kickoff_assignment(4,3,3));
    assert(!entrance_kickoff_assignment(4,1,3)); // queued task is not active yet
    assert(!entrance_kickoff_assignment(4,2,1)); // opening still running
    assert(!entrance_kickoff_assignment(3,2,3));
    assert(entrance_organisation_stage(3,"bc: stadium beauty fix 2 6.64",true));
    p.leave();assert(p.visible(true,false,false,40,0,S::Presentation,A::Inactive));
    assert(!p.visible(true,false,false,40,0,S::ToKickoff,A::Inactive));
    assert(p.consumed); // stage 5 ends even if general intro and clock 0 continue
    assert(!p.visible(true,true,false,40,0,S::StadiumPan,A::Inactive));
    assert(!p.visible(true,false,false,40,0,S::Presentation,A::Inactive));
    p.leave();assert(!p.visible(true,false,false,50,0,S::ToKickoff,A::Inactive));
    assert(p.consumed); // joining a running match at the cutoff cannot rearm on pause
    assert(!p.visible(true,true,false,50,0,S::StadiumPan,A::Inactive));
    assert(!p.visible(true,false,false,50,0,S::StadiumPan,A::Inactive));
    assert(!p.visible(true,false,false,30,0,S::ToKickoff,A::Unknown));
    // User regression: restart before the ball is played retains clubs/clock.
    p.leave();assert(p.visible(true,false,false,60,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,60,0,S::Presentation,A::Inactive,3));
    assert(!p.visible(true,false,false,60,0,S::ToKickoff,A::Inactive,5));
    assert(p.consumed && p.lastPlayableClock==0);
    assert(!p.visible(true,false,false,60,0,S::StadiumPan,A::Inactive,5));
    assert(!p.visible(true,true,false,60,0,S::Presentation,A::Inactive,1));
    assert(p.consumed && p.lastIntroPhase==5); // overlay changes cannot reset it
    assert(!p.visible(true,false,true,60,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,60,0,S::Presentation,A::Inactive,1));
    assert(!p.consumed && !p.sawAnthem && p.lastIntroPhase==1);
    assert(p.visible(true,false,false,60,0,S::Presentation,A::Inactive,3));
    assert(!p.visible(true,false,false,60,0,S::ToKickoff,A::Inactive,5));
    assert(!p.visible(true,false,false,60,0,S::StadiumPan,A::Unknown,-1));
    assert(!p.visible(true,false,false,60,0,S::Presentation,A::Inactive,3));
    assert(p.consumed); // a partial read or a lineup alone cannot imitate restart
    // A different presentation ends by camera without visiting script phase 5.
    p.leave();assert(p.visible(true,false,false,70,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,70,0,S::Presentation,A::Inactive,3));
    assert(!p.visible(true,false,false,70,0,S::ToKickoff,A::Inactive,-1));
    assert(p.lastIntroPhase==3 && p.consumed);
    assert(p.visible(true,false,false,70,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,70,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,70,0,S::Presentation,A::Inactive,3));
    assert(!p.visible(true,false,false,70,0,S::ToKickoff,A::Inactive,5));
    p.leave();assert(p.visible(true,true,false,80,0,S::Presentation,A::Inactive,3));
    assert(p.armed&&!p.consumed); // hot-loaded during the user's paused lineup
    assert(p.visible(true,true,false,80,0,S::StadiumPan,A::Unknown,3));
    assert(p.visible(true,false,false,80,0,S::Presentation,A::Inactive,3));
    assert(!p.visible(true,true,false,80,0,S::ToKickoff,A::Inactive,5));
    assert(p.consumed); // actual organisation removes them even when paused
    assert(!p.visible(true,true,false,80,0,S::StadiumPan,A::Inactive,5));
    assert(!p.visible(true,true,false,80,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,false,false,80,0,S::Presentation,A::Inactive,1));
    p.leave();assert(!p.visible(true,false,false,90,0,S::ToKickoff,A::Unknown,-1));
    assert(p.consumed&&p.lastIntroPhase>=3); // module loaded at broadcast 0:00
    assert(!p.visible(true,true,false,90,0,S::StadiumPan,A::Unknown,-1));
    assert(p.visible(true,false,false,90,0,S::Presentation,A::Inactive,1));
    assert(p.visible(true,true,false,90,0,S::Presentation,A::Inactive,1));
    assert(!p.visible(true,false,false,90,0,S::ToKickoff,A::Inactive,5));
    p.leave();assert(p.visible(true,false,false,100,0,S::Presentation,A::Inactive,1));
    assert(!p.visible(true,false,false,100,0,S::ToKickoff,A::Inactive,1));
    assert(!p.visible(true,false,false,100,0,S::ToKickoff,A::Inactive,1));
    assert(p.consumed&&p.lastIntroPhase==1); // closing UI while intro 1 remains cannot rearm every frame
    EntrancePolicy live;
    assert(live.visible(true,false,false,110,0,S::Presentation));
    assert(!live.visible(true,false,false,110,24,S::Presentation,A::Unknown,-1,true));
    assert(live.matchStarted&&live.consumed&&!live.armed);
    assert(!live.visible(true,true,false,110,24,S::Presentation)); // pause stays hidden
    assert(!live.visible(true,false,true,110,24,S::Presentation)); // replay stays hidden
    assert(!live.visible(true,false,false,110,0,S::StadiumPan)); // clock rollback cannot rearm
    assert(live.visible(true,false,false,111,0,S::Presentation)); // only another fixture resets it
    unsigned char originals[3*EntranceRecordBytes];memset(originals,0x55,sizeof(originals));
    originals[0x42]=0;originals[EntranceRecordBytes+0x42]=1;originals[2*EntranceRecordBytes+0x42]=0;
    unsigned char before[sizeof(originals)];memcpy(before,originals,sizeof(before));
    assert(entrance_clean(originals,3)==1);
    assert(!memcmp(originals,before,EntranceRecordBytes));
    assert(!memcmp(originals+2*EntranceRecordBytes,before+2*EntranceRecordBytes,EntranceRecordBytes));
    assert(originals[EntranceRecordBytes+0x42]==0);
    unsigned char extra[EntranceRecordBytes];entrance_new_record(extra,2);
    float position[4];memcpy(position,extra+0x20,sizeof(position));
    assert(position[0]==0 && position[1]==2 && position[2]==0 && extra[0x42]==1 && extra[0x40]==255);
    assert(!memcmp(extra+0x20,extra+0x30,16));
    // Reproduce the renderer's reset copy, not just record construction.
    memcpy(extra+0x20,extra+0x30,16);
    memcpy(position,extra+0x20,sizeof(position));assert(position[1]==2);
    extra[0x40]=0x4a;extra[0x45]=7;
    const float wrong[4]={0,-3000,0,0};memcpy(extra+0x20,wrong,16);memcpy(extra+0x30,wrong,16);
    entrance_static_position(extra,2);
    memcpy(extra+0x20,extra+0x30,16);
    memcpy(position,extra+0x20,sizeof(position));assert(position[1]==2);
    assert(extra[0x40]==0x4a && extra[0x45]==7 && extra[0x42]==1);
    entrance_static_position(extra,entrance_render_height(false,2));
    memcpy(extra+0x20,extra+0x30,16);memcpy(position,extra+0x20,16);
    assert(position[1]==EntranceHiddenHeight&&extra[0x40]==0x4a&&extra[0x42]==1);
    entrance_static_position(extra,entrance_render_height(true,2));
    memcpy(extra+0x20,extra+0x30,16);memcpy(position,extra+0x20,16);assert(position[1]==2);
    puts("PASS v12: both lineup widgets must close; replacements/duplicate closes/reversed order are handled; retained static actor is moved below pitch after cutoff; anthem/audio/overlays preserve visible phase; pause/restart/skip/goal/halftime regressions.");
}
