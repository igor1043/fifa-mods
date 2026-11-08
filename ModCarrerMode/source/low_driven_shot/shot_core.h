#pragma once
#include <windows.h>
#include <Xinput.h>
#include <stdint.h>
#include <string.h>

// Timing-compatible port of the supplied double-tap filter. No game data writes.
struct ShotState {
    int phase, reserved;
    uint64_t started;
    DWORD packet;
    XINPUT_GAMEPAD last;
    int previousShot, previousTrigger;
    uint64_t pressed, released, outputPressed, charge;
};
static_assert(sizeof(ShotState)==72,"Shot state ABI");
inline void shot_process(ShotState &s,const XINPUT_STATE &in,XINPUT_STATE &out,
    uint64_t now,int enabled,int height,int threshold,WORD button,int mode,int finesseTap) {
    const bool shot=(in.Gamepad.wButtons&button)!=0;
    const bool trigger=in.Gamepad.bLeftTrigger>threshold;
    const bool finesse=(in.Gamepad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER) || in.Gamepad.bRightTrigger>threshold;
    out=in;
    if(shot&&!s.previousShot)s.pressed=now;
    if(!shot&&s.previousShot)s.released=now;
    if(!s.phase&&enabled&&mode==2&&shot&&!s.previousShot&&s.released&&s.pressed-s.released<=300) {
        s.phase=3;s.started=now;s.released=0;
    }
    if(!s.phase&&enabled&&mode==2&&shot&&!s.previousShot){s.phase=5;s.started=now;}
    if(s.phase==5) {
        if(shot){if(finesse||now-s.started>=uint64_t(height)*4)s.phase=0;}
        else{s.phase=6;s.released=now+60;s.started=now;}
    }
    if(s.phase==6&&shot&&!s.previousShot){s.phase=2;s.started=now;}
    if(s.phase==6&&now-s.started>=60)s.phase=0;
    if(!s.phase&&enabled&&mode!=2&&trigger&&shot){s.phase=1;s.started=s.pressed;}
    else if(!s.phase&&enabled&&mode==0&&trigger&&!shot&&!s.previousTrigger&&s.released&&now-s.released<=150) {
        s.phase=2;s.started=now-40;
    }
    if(s.phase==1&&(!shot||now-s.started>=80+uint64_t(height)*8)){s.phase=mode==1?4:2;s.started=now;}
    if(s.phase==2&&now-s.started>=40){s.phase=3;s.started=now;}
    if(s.phase==3) {
        uint64_t duration=60;
        if(mode==2){duration=s.charge>60?s.charge:60;uint64_t cap=finesse?finesseTap:1000;if(duration>=cap)duration=cap;}
        if(now-s.started>=duration){s.phase=4;s.started=now;}
    }
    if(s.phase==4&&!shot&&(mode!=1||!trigger)){s.phase=0;s.released=0;}
    if(s.phase) {
        if(mode!=2)out.Gamepad.bLeftTrigger=0;
        if(mode==1&&trigger)out.Gamepad.wButtons|=XINPUT_GAMEPAD_LEFT_SHOULDER;
        if(s.phase==1||s.phase==3||s.phase==6)out.Gamepad.wButtons|=button;
        else out.Gamepad.wButtons&=~button;
    }
    if(out.Gamepad.wButtons&button){if(!(s.last.wButtons&button))s.outputPressed=now;}
    else if((s.last.wButtons&button)&&(!s.phase||s.phase==2))s.charge=now-s.outputPressed;
    if(memcmp(&out.Gamepad,&s.last,sizeof(s.last)))++s.packet;
    out.dwPacketNumber=s.packet;s.last=out.Gamepad;s.previousShot=shot;s.previousTrigger=trigger;
}
