#pragma once
#include <limits.h>
#include <math.h>

// v13 reuses the game's ANT evaluated poses. It temporarily requests a
// standing idle or home-goal reaction from one CrowdAI slot, then copies only
// that slot's validated pose into the mascot's private SLE pool entry 73.
static volatile LONG mascotAnimationEnabled;
static volatile LONG mascotAnimationHome = -1;
static volatile LONG mascotSceneGeneration;
static volatile LONG mascotAnimationMode;      // 0 inactive, 2 mirror crowd, 3 home-goal cheer
static volatile LONG mascotRequestedBehavior = -1;
static uintptr_t mascotOriginalCrowdAssignments;
static uintptr_t mascotLastAppliedCrowd;
static LONG mascotLastAppliedBehavior = INT_MIN;
static bool mascotAnimationInitialized;
static bool mascotAnimationBound;
static uint16_t mascotPreviousBinding = 3;
static uintptr_t mascotAnimatedRenderer, mascotAnimatedRecords;
static size_t mascotAnimatedIndex;
static int mascotAnimatedStadium = -1, mascotAnimatedLight = -1, mascotAnimatedCold = -1;
static unsigned int mascotPrivateSlot = 73;
static unsigned int mascotAnimatedGeneration;
static uintptr_t mascotInitAttemptRenderer, mascotInitAttemptRecords;
static size_t mascotInitAttemptIndex;
static unsigned int mascotInitAttemptGeneration;
static DWORD mascotInitAttemptTick;
static float mascotBindPose[31][16];
static float mascotLastPose[31][16];

static void mascot_set_animation_active(bool enabled, int home)
{
    const LONG next = enabled ? 1 : 0;
    const LONG previous = InterlockedExchange(&mascotAnimationEnabled, next);
    const LONG oldHome = InterlockedExchange(&mascotAnimationHome, home);
    if (previous != next || oldHome != home) {
        InterlockedIncrement(&mascotSceneGeneration);
        if (!enabled) {
            InterlockedExchange(&mascotAnimationMode, 0);
            InterlockedExchange(&mascotRequestedBehavior, -1);
        }
    }
}

static uintptr_t mascot_current_crowd()
{
    uintptr_t manager, world, game, registry, vt, pairs;
    int key, count;
    if (!get(image + 0x3517420, manager) || !get(manager, vt) || vt != image + 0x2226730 ||
        !get(manager + 8, world) || !get(world, vt) || vt != image + 0x2225d90 ||
        !get(world + 0x10, game) || !get(game, vt) || vt != image + 0x2309370 ||
        !get(game + 0x20, registry) || !registry ||
        !get(registry + 8 + 81 * 32, key) || key != 81 ||
        !get(registry + 8 + 81 * 32 + 16, count) || count < 1 || count > 8 ||
        !get(registry + 8 + 81 * 32 + 24, pairs) || !readable(pairs, (size_t)count * 16)) return 0;
    for (int i = 0; i < count; ++i) {
        uintptr_t object, self, callback;
        if (!get(pairs + i * 16 + 8, object) || !object ||
            !get(object + 0x2918, self) || self != object ||
            !get(object + 0x28e8, callback) || callback != image + 0x2312f88) continue;
        return object;
    }
    return 0;
}

static bool mascot_read_confirmed_score(uintptr_t& matchKey, int& homeClub, int& awayClub,
                                        int& homeScore, int& awayScore)
{
    uintptr_t manager, world, game, registry, vt, pairs;
    int key, count;
    if (!get(image + 0x3517420, manager) || !get(manager, vt) || vt != image + 0x2226730 ||
        !get(manager + 8, world) || !get(world, vt) || vt != image + 0x2225d90 ||
        !get(world + 0x10, game) || !get(game, vt) || vt != image + 0x2309370 ||
        !get(game + 0x20, registry) || !registry ||
        !get(registry + 8 + 15 * 32, key) || key != 15 ||
        !get(registry + 8 + 15 * 32 + 16, count) || count != 2 ||
        !get(registry + 8 + 15 * 32 + 24, pairs) || !readable(pairs, 32)) return false;
    uintptr_t team[2]{};
    int club[2] = {-1, -1};
    for (int i = 0; i < 2; ++i) {
        uintptr_t candidate, stats;
        int side;
        if (!get(pairs + i * 16 + 8, candidate) || !candidate ||
            !get(candidate, vt) || vt != image + 0x22fe9f0 ||
            !get(candidate + 0x30, manager) || manager != registry ||
            !get(candidate + 0x58, side) || side < 0 || side > 1 || team[side] ||
            !get(candidate + 0x50, stats) || !get(stats + 0x80, club[side]) ||
            club[side] <= 0 || club[side] > 1000000) return false;
        team[side] = candidate;
    }
    uintptr_t cache, cacheVtable, getter, rows, homeCallback, awayCallback, again;
    int h, a, h2, a2;
    if (!get(image + 0x34a30b0, cache) || !cache || !get(cache, cacheVtable) ||
        cacheVtable != image + 0x21141f0 || !get(cacheVtable + 16, getter) ||
        getter != image + 0x3acbff0 || !get(cache + 8, rows) || !readable(rows, 249 * 16) ||
        !get(rows + 21 * 16 + 8, homeCallback) || !get(rows + 6 * 16 + 8, awayCallback) ||
        homeCallback != image + 0x3acc040 || awayCallback != image + 0x3acc040 ||
        !get(rows + 21 * 16, h) || !get(rows + 6 * 16, a) ||
        !get(rows + 21 * 16, h2) || !get(rows + 6 * 16, a2) ||
        h != h2 || a != a2 || h < 0 || h > 99 || a < 0 || a > 99 ||
        !get(cache + 8, again) || again != rows ||
        !get(image + 0x34a30b0, again) || again != cache) return false;
    homeClub = club[0]; awayClub = club[1]; homeScore = h; awayScore = a;
    const uintptr_t generation = (uintptr_t)(unsigned int)InterlockedCompareExchange(&mascotSceneGeneration, 0, 0);
    matchKey = rows ^ team[0] ^ (team[1] << 11 | team[1] >> (sizeof(uintptr_t) * 8 - 11)) ^
        (generation * (uintptr_t)0x9e3779b97f4a7c15ULL);
    return matchKey != 0;
}

static bool mascot_invert_affine(const float* matrix, float* output)
{
    for (size_t i = 0; i < 16; ++i) if (!isfinite(matrix[i]) || fabsf(matrix[i]) > 20000) return false;
    if (fabsf(matrix[15] - 1) > 0.001f) return false;
    const float a=matrix[0], b=matrix[4], c=matrix[8], d=matrix[1], e=matrix[5], f=matrix[9],
                g=matrix[2], h=matrix[6], i=matrix[10];
    const float determinant=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
    if (!isfinite(determinant) || fabsf(determinant) < 0.0001f) return false;
    memset(output, 0, 16 * sizeof(float)); output[15]=1;
    const float rows[9]={e*i-f*h,c*h-b*i,b*f-c*e,f*g-d*i,a*i-c*g,c*d-a*f,d*h-e*g,b*g-a*h,a*e-b*d};
    for (size_t row=0;row<3;++row) for (size_t column=0;column<3;++column)
        output[column*4+row]=rows[row*3+column]/determinant;
    for (size_t row=0;row<3;++row)
        output[12+row]=-(output[row]*matrix[12]+output[4+row]*matrix[13]+output[8+row]*matrix[14]);
    return true;
}

static void* allocate_near(uintptr_t origin);
static bool install_call(unsigned char* site, int32_t relative);
static void __fastcall mascot_crowd_assignment_hook(void* object);

static bool mascot_install_crowd_hook()
{
    unsigned char* site = (unsigned char*)(image + 0x4f530aa);
    const unsigned char callBytes[5] = {0xe8,0x11,0x0b,0x00,0x00};
    const unsigned char prefix[16] = {0x53,0x56,0x57,0x48,0x83,0xec,0x40,0x8b,0x05,0x7b,0x52,0x80,0xfe,0x48,0x89,0xce};
    if (!readable((uintptr_t)site, 5) || memcmp(site, callBytes, 5) ||
        !readable(image + 0x4f53bc0, 16) || memcmp((void*)(image + 0x4f53bc0), prefix, 16)) return false;
    int32_t originalDisplacement; memcpy(&originalDisplacement, site + 1, 4);
    if ((uintptr_t)site + 5 + originalDisplacement != image + 0x4f53bc0) return false;
    mascotOriginalCrowdAssignments = image + 0x4f53bc0;
    unsigned char* relay = (unsigned char*)allocate_near((uintptr_t)site);
    if (!relay) return false;
    const unsigned char jump[6] = {0xff,0x25,0,0,0,0}; memcpy(relay, jump, 6);
    const uintptr_t destination = (uintptr_t)&mascot_crowd_assignment_hook; memcpy(relay + 6, &destination, 8);
    DWORD old;
    if (!VirtualProtect(relay, 4096, PAGE_EXECUTE_READ, &old)) return false;
    FlushInstructionCache(GetCurrentProcess(), relay, 14);
    const int64_t distance = (int64_t)(uintptr_t)relay - (int64_t)((uintptr_t)site + 5);
    if (distance < INT32_MIN || distance > INT32_MAX || !install_call(site, (int32_t)distance)) {
        VirtualFree(relay, 0, MEM_RELEASE); return false;
    }
    log_event("animation_hook installed crowd_assignment=4f530aa private_pose_slot=73 crowd_mirror=1 home_goal=14");
    return true;
}

static void __fastcall mascot_crowd_assignment_hook(void* object)
{
    const LONG requested = InterlockedCompareExchange(&mascotRequestedBehavior, 0, 0);
    // Preserve one restoration after an active mascot, then pass through
    // untouched when no supported mascot is active.
    if (requested < 0 && mascotLastAppliedBehavior < 0) {
        ((void (__fastcall*)(void*))mascotOriginalCrowdAssignments)(object); return;
    }
    const uintptr_t current = mascot_current_crowd();
    if ((uintptr_t)object == current && current &&
        (requested != mascotLastAppliedBehavior || current != mascotLastAppliedCrowd)) {
        const int saved = *(int*)(current + 4);
        const unsigned char savedDirty = *(unsigned char*)(current + 0x408);
        if (requested >= 0) *(int*)(current + 4) = requested;
        *(unsigned char*)(current + 0x408) = 1;
        ((void (__fastcall*)(void*))mascotOriginalCrowdAssignments)(object);
        *(int*)(current + 4) = saved;
        if (requested < 0) *(unsigned char*)(current + 0x408) = savedDirty;
        mascotLastAppliedCrowd = current;
        mascotLastAppliedBehavior = requested;
        log_event("crowd_animation_request behavior=%ld crowd=%p", requested, (void*)current);
        return;
    }
    ((void (__fastcall*)(void*))mascotOriginalCrowdAssignments)(object);
}

static bool mascot_native_standing_pose(int requested, float pose[31][16], int& behaviorOut, int& clip)
{
    uintptr_t crowd = mascot_current_crowd(), wrapper, data, manager, impl, provider;
    if (!crowd || !get(image + 0x3504750, wrapper) || !get(wrapper + 0x10, data) ||
        !get(data + 0x90, manager) || !get(manager, impl) || !get(impl + 0x28, provider) || !provider) return false;
    const unsigned char posture = *(unsigned char*)(crowd + 4 + 8);
    const int behavior = *(int*)(crowd + 0x474);
    /* Keep the mascot standing: seated/non-standing crowd postures are never copied. */
    if (posture != 2 || (requested >= 0 && behavior != requested)) return false;
    const uintptr_t raw = provider + 0x10;
    if (!readable(raw, 31 * 64)) return false;
    float second[31][16];
    memcpy(pose, (void*)raw, sizeof(second)); MemoryBarrier(); memcpy(second, (void*)raw, sizeof(second));
    if (memcmp(pose, second, sizeof(second))) return false;
    for (size_t bone=0;bone<31;++bone) {
        for (size_t j=0;j<16;++j) if (!isfinite(pose[bone][j]) || fabsf(pose[bone][j])>1000) return false;
        if (fabsf(pose[bone][15]-1)>0.001f) return false;
    }
    if (pose[2][13] < 75 || pose[2][13] > 160 || pose[14][13] < 120) return false;
    behaviorOut = behavior;
    clip = *(int*)(crowd + 0x470);
    return true;
}

static void mascot_unbind_pose(uintptr_t renderer, uintptr_t records, size_t count)
{
    if (mascotAnimationBound && renderer == mascotAnimatedRenderer && records == mascotAnimatedRecords &&
        mascotAnimatedIndex < count && readable(records + mascotAnimatedIndex * 0x50, 0x50)) {
        uint16_t binding;
        if (get(mascotAnimatedRecords + mascotAnimatedIndex * 0x50 + 0x40, binding) && binding == mascotPrivateSlot)
            *(uint16_t*)(mascotAnimatedRecords + mascotAnimatedIndex * 0x50 + 0x40) = mascotPreviousBinding;
    }
    mascotAnimationBound = false; mascotAnimationInitialized = false;
}

static void mascot_animate_instance(const MascotFrameContext& frame)
{
    const uintptr_t renderer=frame.renderer, records=frame.records;
    const size_t count=frame.count, selected=frame.selected;
    const int home=frame.home, stadium=frame.stadium, light=frame.light, cold=frame.cold;
    const bool animatedPackage=(home==1043 && (frame.packages&4)) || (home==383 && (frame.packages&8));
    if(!frame.mascotActive || !animatedPackage) {
        mascot_unbind_pose(renderer,records,count); mascot_set_animation_active(false,home); return;
    }
    if(!mascotAnimationInitialized || renderer!=mascotAnimatedRenderer || records!=mascotAnimatedRecords ||
        selected!=mascotAnimatedIndex || stadium!=mascotAnimatedStadium || light!=mascotAnimatedLight || cold!=mascotAnimatedCold ||
        frame.generation!=mascotAnimatedGeneration) {
        const DWORD tick=GetTickCount();
        const bool sameAttempt=renderer==mascotInitAttemptRenderer && records==mascotInitAttemptRecords &&
            selected==mascotInitAttemptIndex && frame.generation==mascotInitAttemptGeneration;
        if (sameAttempt && tick-mascotInitAttemptTick<250) return;
        mascotInitAttemptRenderer=renderer; mascotInitAttemptRecords=records;
        mascotInitAttemptIndex=selected; mascotInitAttemptGeneration=frame.generation; mascotInitAttemptTick=tick;
        mascot_unbind_pose(renderer,records,count);
        mascot_set_animation_active(false,home);
        wchar_t variant[MAX_PATH];
        const int chars=_snwprintf_s(variant,MAX_PATH,_TRUNCATE,L"%ls\\data\\sceneassets\\mascot\\%u\\model_animated.rx3",gameDirectory,(unsigned int)home);
        if(chars<0 || !mascot_rx3_file_valid(variant,false)) { log_event("animation_fallback invalid_variant club=%d",home); mascot_set_animation_active(false,home); return; }
        for(unsigned int type=0;type<23;++type) {
            uintptr_t begin;size_t n;
            if(!vector_bounds(renderer+0x30*(type+0x2f),0x50,begin,n)) return;
            for(size_t i=0;i<n;++i) if(*(uint16_t*)(begin+i*0x50+0x40)==mascotPrivateSlot && (type!=1 || i!=selected)) return;
        }
        if(*(unsigned char*)(renderer+mascotPrivateSlot*0xe00+0xf5d0)!=0) return;
        uintptr_t inverse;
        if(!get(renderer+0x4f440,inverse) || !readable(inverse,sizeof(mascotBindPose))) return;
        float inverseMatrices[31][16];memcpy(inverseMatrices,(void*)inverse,sizeof(inverseMatrices));
        for(size_t bone=0;bone<31;++bone) if(!mascot_invert_affine(inverseMatrices[bone],mascotBindPose[bone])) return;
        memcpy(mascotLastPose,mascotBindPose,sizeof(mascotLastPose));
        uint16_t previousBinding=3;
        if (!get(records+selected*0x50+0x40,previousBinding) || previousBinding>=74 || previousBinding==mascotPrivateSlot)
            previousBinding=3;
        mascotPreviousBinding=previousBinding;
        mascotAnimatedRenderer=renderer;mascotAnimatedRecords=records;mascotAnimatedIndex=selected;
        mascotAnimatedStadium=stadium;mascotAnimatedLight=light;mascotAnimatedCold=cold;
        mascotAnimatedGeneration=frame.generation;
        mascotAnimationInitialized=true;mascotAnimationBound=false;
        log_event("animation_ready club=%d instance=%zu slot=73 crowd_mirror=1 home_goal=14",home,selected+1);
    }
    mascot_set_animation_active(true,home);
    const LONG mode=InterlockedCompareExchange(&mascotAnimationMode,0,0);
    const int requestedBehavior=mode==3?14:-1;
    InterlockedExchange(&mascotRequestedBehavior,requestedBehavior);
    float pose[31][16];int behavior=-1,clip=-1;
    if(mascot_native_standing_pose(requestedBehavior,pose,behavior,clip)) {
        memcpy(mascotLastPose,pose,sizeof(mascotLastPose));
        memcpy((void*)(renderer+mascotPrivateSlot*0xe00+0xe7e0),pose,sizeof(pose));
        *(uint16_t*)(records+selected*0x50+0x40)=(uint16_t)mascotPrivateSlot;
        mascotAnimationBound=true;
        static LONG lastMode=-1;static int lastBehavior=-1,lastClip=-1;
        if(lastMode!=mode || lastBehavior!=behavior || lastClip!=clip) { log_event("animation_pose club=%d mode=%s behavior=%d clip=%d standing=1",home,mode==3?"home_goal":"crowd_native",behavior,clip);lastMode=mode;lastBehavior=behavior;lastClip=clip; }
    } else if(mascotAnimationBound) {
        memcpy((void*)(renderer+mascotPrivateSlot*0xe00+0xe7e0),mascotLastPose,sizeof(mascotLastPose));
    }
}

static DWORD WINAPI mascot_animation_worker(void*)
{
    bool hookInstalled=false, baseline=false, candidate=false, previousActive=false;
    uintptr_t currentKey=0;
    int scoreHome=-1,scoreAway=-1,candidateHome=-1,candidateAway=-1,highHome=-1;
    uint64_t candidateSince=0,lastSample=0,celebrationUntil=0;
    for(unsigned attempt=0;attempt<600;++attempt) {
        if(!code_ready()) { Sleep(200);continue; }
        if(!hookInstalled) {
            if(mascot_install_crowd_hook()) hookInstalled=true;
            else { Sleep(200);continue; }
        }
        break;
    }
    if(!hookInstalled) { log_event("animation_disabled crowd_hook_guard_failed"); return 1; }
    log_event("animation_score_watcher started home_only=1 confirm_ms=750 crowd_mirror=1 celebration=14 duration_ms=26000");
    for(;;) {
        const uint64_t now=GetTickCount64();
        const bool active=InterlockedCompareExchange(&mascotAnimationEnabled,0,0)!=0;
        const int mascotClub=InterlockedCompareExchange(&mascotAnimationHome,0,0);
        if(!active || (mascotClub!=1043 && mascotClub!=383)) {
            if(previousActive) {
                InterlockedExchange(&mascotAnimationMode,0);InterlockedExchange(&mascotRequestedBehavior,-1);
                log_event("animation_idle no_supported_home_mascot");
            }
            previousActive=false;baseline=candidate=false;currentKey=0;celebrationUntil=0;lastSample=0;
            Sleep(100);continue;
        }
        if(!previousActive) {
            InterlockedExchange(&mascotAnimationMode,2);
            InterlockedExchange(&mascotRequestedBehavior,-1);
        }
        previousActive=true;
        uintptr_t key=0;int homeClub=-1,awayClub=-1,h=-1,a=-1;
        if(!mascot_read_confirmed_score(key,homeClub,awayClub,h,a) || homeClub!=mascotClub) {
            InterlockedExchange(&mascotAnimationMode,2);InterlockedExchange(&mascotRequestedBehavior,-1);
            baseline=candidate=false;lastSample=0;Sleep(100);continue;
        }
        key ^= (uintptr_t)(unsigned int)homeClub << 3;
        key ^= (uintptr_t)(unsigned int)awayClub << 29;
        if(key!=currentKey) {
            currentKey=key;baseline=candidate=false;highHome=-1;celebrationUntil=0;lastSample=0;
            InterlockedExchange(&mascotAnimationMode,2);InterlockedExchange(&mascotRequestedBehavior,-1);
        }
        if(lastSample && now-lastSample>2000) { baseline=candidate=false;celebrationUntil=0;InterlockedExchange(&mascotAnimationMode,2); }
        lastSample=now;
        if(celebrationUntil && now>=celebrationUntil) {
            celebrationUntil=0;InterlockedExchange(&mascotAnimationMode,2);InterlockedExchange(&mascotRequestedBehavior,-1);
            log_event("home_goal_celebration_finished score=%d:%d",h,a);
        }
        if(!baseline) {
            if(!candidate || h!=candidateHome || a!=candidateAway) { candidate=true;candidateHome=h;candidateAway=a;candidateSince=now; }
            if(now-candidateSince>=750) {
                scoreHome=h;scoreAway=a;highHome=h;baseline=true;candidate=false;
                log_event("goal_score_baseline home=%d away=%d",h,a);
            }
        } else if(h==scoreHome && a==scoreAway) candidate=false;
        else {
            if(!candidate || h!=candidateHome || a!=candidateAway) { candidate=true;candidateHome=h;candidateAway=a;candidateSince=now; }
            const bool homeGoal=(h==scoreHome+1 && a==scoreAway && h>highHome);
            if((h<scoreHome || a!=scoreAway) && celebrationUntil) {
                celebrationUntil=0;InterlockedExchange(&mascotAnimationMode,2);InterlockedExchange(&mascotRequestedBehavior,-1);
            }
            if(now-candidateSince>=750) {
                const int oldHome=scoreHome,oldAway=scoreAway;
                scoreHome=h;scoreAway=a;candidate=false;if(h>highHome)highHome=h;
                if(homeGoal) {
                    celebrationUntil=now+26000;InterlockedExchange(&mascotAnimationMode,3);InterlockedExchange(&mascotRequestedBehavior,14);
                    log_event("HOME_GOAL_CONFIRMED score=%d:%d previous=%d:%d; native_behavior=14 duration_ms=26000",h,a,oldHome,oldAway);
                } else {
                    InterlockedExchange(&mascotAnimationMode,2);InterlockedExchange(&mascotRequestedBehavior,-1);
                    log_event("score_change_without_home_goal score=%d:%d previous=%d:%d",h,a,oldHome,oldAway);
                }
            }
        }
        Sleep(100);
    }
}
