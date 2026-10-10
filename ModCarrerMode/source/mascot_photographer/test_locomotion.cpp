#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include "mascot_placement_policy.h"
#include "mascot_walk_clips.h"
#include "mascot_pose_policy.h"
struct MascotFrameContext { uintptr_t renderer,records;size_t count,selected;int home;unsigned int generation; };
static LONG mascotPlacementSession=1;
static unsigned int mascotPlacementGeneration=1;
static wchar_t gameDirectory[MAX_PATH];
static float targetPosition[3]={5850,0,3150},originalPosition[3]{},originalYaw=0;
static float mascotBindPose[31][16];
static uintptr_t mascotAnimatedRenderer,mascotAnimatedRecords;
static size_t mascotAnimatedIndex;
static unsigned int mascotPrivateSlot=73;
static bool mascotAnimationBound;
template<class T>static bool get(uintptr_t p,T& v){if(!p)return false;memcpy(&v,(void*)p,sizeof(v));return true;}
static void log_event(const char*,...){}
#include "mascot_walk_runtime.h"

static int check_pose_library(const float* frames,const float* times,unsigned int count,float duration) {
    for(unsigned int i=0;i+1<count;++i)for(unsigned int n=0;n<8;++n) {
        const float t=times[i]+(times[i+1]-times[i])*(float)n/8;
        float sampled[31*7],pose[31][16];
        mascot_sample_baked_clip(frames,times,count,duration,t,sampled);
        mascot_retarget_baked_pose(sampled,pose);
        if(!mascot_pose_upright(pose))return 1;
        mascot_ground_pose(pose);
        float feet[2][3];mascot_pose_feet(pose,feet);
        if(fabsf(fminf(feet[0][1],feet[1][1])-mascotFootMarkers.floor)>.01f)return 2;
        mascot_blend_local_pose(pose,0,1.0f/30);mascot_orient_pose(pose,.5f);
        if(!mascot_pose_upright(pose))return 3;
    }
    return 0;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 1;
    wcsncpy_s(gameDirectory,argv[1],_TRUNCATE);
    for(int club:{1035,1043,383,568,569}) {
        wchar_t path[MAX_PATH];_snwprintf_s(path,MAX_PATH,_TRUNCATE,L"%ls\\data\\sceneassets\\mascot\\%d\\bind.bin",gameDirectory,club);
        FILE* f=nullptr;if(_wfopen_s(&f,path,L"rb")||!f)return 2;
        const size_t got=fread(mascotBindPose,1,sizeof(mascotBindPose),f);fclose(f);if(got!=sizeof(mascotBindPose))return 3;
        mascot_load_foot_markers(club);if(!mascotFootMarkersReady)return 4;
        if(check_pose_library(&mascotIdleFrames[0][0],mascotIdleTimes,mascotIdleFrameCount,mascotIdleDuration) ||
           check_pose_library(&mascotCheerFrames[0][0],mascotCheerTimes,mascotCheerFrameCount,mascotCheerDuration) ||
           check_pose_library(&mascotWalkFrames[0][0],mascotWalkTimes,mascotWalkFrameCount,mascotWalkDuration))return 5;
        for(int direction:{-1,1}) {
            alignas(16) unsigned char record[80]{};
            MascotFrameContext frame{1,(uintptr_t)record,1,0,club,1};
            targetPosition[2]=direction<0?3150.0f:-3150.0f;
            mascotWalkRuntime={};mascot_walk_reset(frame,1000);
            if(mascotWalkRuntime.idleRemaining!=20)return 13;
            MascotWalkRuntime& s=mascotWalkRuntime;
            s.direction=direction<0?1:-1;s.idleRemaining=0;s.yaw=1.2f;
            float moved=0,expectedDistance=0;bool wasWalking=false,finished=false;uint64_t now=1000;
            for(unsigned int tick=0;tick<18000;++tick) {
                const float oldZ=s.position[2],oldPhase=s.walkTime;
                mascot_walk_update(frame,2,now,.016f);now+=16;
                if(tick==0)expectedDistance=fabsf(mascotGoalLineDestinations[s.nextWaypoint]-oldZ);
                float inputYaw=0,outputYaw=0;get((uintptr_t)record+0x1c,inputYaw);get((uintptr_t)record+0x2c,outputYaw);
                if(inputYaw!=0 || outputYaw!=0)return 6;
                if(s.turning && fabsf(s.position[2]-oldZ)>.001f)return 7;
                if(s.walkTime>oldPhase) {
                    const float expected=mascot_walk_advance(oldPhase,s.walkTime-oldPhase);
                    if(fabsf(fabsf(s.position[2]-oldZ)-expected)>.025f)return 8;
                    if((s.position[2]-oldZ)*s.direction<-.001f)return 9;
                    moved+=fabsf(s.position[2]-oldZ);
                }
                if(tick==300) {
                    const float z=s.position[2],yaw=s.yaw,phase=s.walkTime,idle=s.idleRemaining;
                    for(unsigned int pause=0;pause<500;++pause){mascot_walk_update(frame,2,now,0);now+=16;}
                    if(z!=s.position[2]||yaw!=s.yaw||phase!=s.walkTime||idle!=s.idleRemaining)return 10;
                }
                if(s.walking)wasWalking=true;
                if(wasWalking&&!s.walking){finished=true;break;}
            }
            if(!finished||fabsf(moved-expectedDistance)>.06f)return 11;
            if(s.idleRemaining!=20)return 14;
            printf("PASS club=%d direction=%d route_cm=%.3f pause=unchanged yaw=palette poses=upright\n",club,direction,moved);
            mascotAnimatedRenderer=frame.renderer;mascotAnimatedRecords=frame.records;mascotAnimatedIndex=0;mascotAnimationBound=true;
            const uint16_t slot=73;memcpy(record+0x40,&slot,sizeof(slot));
            mascot_walk_restore_live(frame.renderer,frame.records,frame.count);
            float restoredYaw=0;get((uintptr_t)record+0x1c,restoredYaw);if(restoredYaw!=originalYaw)return 12;
        }
    }
    {
        alignas(16) unsigned char record[80]{};
        MascotFrameContext frame{1,(uintptr_t)record,1,0,1043,1};
        mascot_walk_reset(frame,1000);
        unsigned int seen=1u<<mascotWalkRuntime.waypoint;
        for(unsigned int choice=0;choice<30;++choice) {
            MascotWalkRuntime& s=mascotWalkRuntime;
            if(seen==((1u<<mascotGoalLineDestinationCount)-1))seen=1u<<s.waypoint;
            s.walking=s.turning=false;s.idleRemaining=0;
            mascot_walk_update(frame,2,1000+choice*16,.016f);
            if(seen&(1u<<s.nextWaypoint))return 15;
            seen|=1u<<s.nextWaypoint;
            s.position[2]=mascotGoalLineDestinations[s.nextWaypoint];s.waypoint=s.nextWaypoint;
        }
        printf("PASS waypoint bag: all ten destinations before repetition, 20 seconds dwell\n");
    }
    alignas(16) unsigned char benchmarkRecord[80]{};
    MascotFrameContext benchmark{1,(uintptr_t)benchmarkRecord,1,0,569,1};
    mascotWalkRuntime={};targetPosition[2]=3150;mascot_walk_reset(benchmark,1000);mascotWalkRuntime.idleRemaining=0;
    LARGE_INTEGER frequency{},begin{},end{};
    QueryPerformanceFrequency(&frequency);QueryPerformanceCounter(&begin);
    for(unsigned int i=0;i<10000;++i)mascot_walk_update(benchmark,2,1000+i*16,.016f);
    QueryPerformanceCounter(&end);
    const double micros=(double)(end.QuadPart-begin.QuadPart)*1.0e6/(double)frequency.QuadPart/10000;
    printf("Offline locomotion cost: %.2f us/callback (no engine/driver/log cost)\n",micros);
    return 0;
}
