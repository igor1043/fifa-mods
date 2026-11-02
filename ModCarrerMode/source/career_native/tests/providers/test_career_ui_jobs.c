#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
static int stable,drains,calls,disabled,manager_drains;
static DWORD callback_thread;
static struct {unsigned sequence,pid,epoch,owner_thread;} Fifa16CareerContextRead;
static unsigned long fce_runtime_context_epoch(void) {return 7;}
static void drain_pending_stats_refresh(void) {++drains;}
static void drain_background_refresh(void) {}
static void drain_preview_refresh(void) {}
static void drain_bank_mail(void) {}
static void drain_market_read(void) {}
static void drain_manager_read(void) {++manager_drains;}
static void drain_prepared_views(void) {}
static int fce_runtime_is_stable(void) {return stable;}
static void append_loader_log(const char *message) {(void)message;++disabled;}
#include "../../src/host/career_ui_jobs.inc"
static void command(void) {++calls;callback_thread=GetCurrentThreadId();}
static void different(void) {}
static void broken(void) {RaiseException(0xe1640001,0,0,NULL);}
static int stadium_calls;
static int nested_stadium;
static void stadium(void) {++stadium_calls;assert(GetCurrentThreadId()==Fifa16CareerContextRead.owner_thread);if(nested_stadium)career_ui_jobs_tick();}
static DWORD WINAPI wrong_thread(void *unused) {(void)unused;career_ui_jobs_tick();return 0;}
int main(void)
{
    assert(!Fifa16CareerRegisterJobUiCallback(NULL));
    assert(Fifa16CareerRegisterJobUiCallback(command));
    assert(Fifa16CareerRegisterJobUiCallback(command));
    assert(!Fifa16CareerRegisterJobUiCallback(different));
    assert(calls==0);career_ui_jobs_tick();assert(drains==1 && !calls && !manager_drains);
    stable=1;career_ui_jobs_tick();assert(drains==2 && calls==1 && manager_drains==1);
    assert(callback_thread==GetCurrentThreadId());
    InterlockedExchangePointer(&g_career_job_ui_callback,NULL);
    assert(Fifa16CareerRegisterJobUiCallback(broken));
    career_ui_jobs_tick();assert(disabled==1 && !g_career_job_ui_callback);
    assert(Fifa16CareerRegisterJobUiCallback(command));career_ui_jobs_tick();assert(calls==2 && manager_drains==3);
    InterlockedExchangePointer(&g_career_job_ui_callback,NULL);
    assert(Fifa16CareerRegisterStadiumUiCallback(stadium));assert(!stadium_calls);
    Fifa16CareerContextRead.pid=GetCurrentProcessId();Fifa16CareerContextRead.epoch=7;Fifa16CareerContextRead.owner_thread=GetCurrentThreadId();
    {HANDLE thread=CreateThread(NULL,0,wrong_thread,NULL,0,NULL);assert(thread&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0);CloseHandle(thread);assert(!stadium_calls);}
    Fifa16CareerContextRead.epoch=8;career_ui_jobs_tick();assert(!stadium_calls);
    Fifa16CareerContextRead.epoch=7;Fifa16CareerContextRead.sequence=1;career_ui_jobs_tick();assert(!stadium_calls);
    Fifa16CareerContextRead.sequence=2;stable=0;career_ui_jobs_tick();assert(!stadium_calls);
    stable=1;career_ui_jobs_tick();assert(stadium_calls==1);
    assert(!Fifa16CareerRegisterStadiumUiCallback(different));
    nested_stadium=1;career_ui_jobs_tick();assert(stadium_calls==2&&!g_stadium_ui_running);nested_stadium=0;
    Fifa16CareerContextRead.owner_thread=0;career_ui_jobs_tick();assert(stadium_calls==2);
    Fifa16CareerContextRead.owner_thread=GetCurrentThreadId();
    InterlockedExchangePointer(&g_stadium_ui_callback,NULL);assert(Fifa16CareerRegisterStadiumUiCallback(broken));career_ui_jobs_tick();assert(!g_stadium_ui_callback&&!g_stadium_ui_running&&disabled==2);
    puts("PASS: UI commands stay on the stable engine caller; registration never runs callbacks; a second owner is rejected; failing callback is disabled; existing refresh pump always runs");
    return 0;
}
