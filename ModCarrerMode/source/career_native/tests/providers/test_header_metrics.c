#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "../../src/host/dinput8_wrapper.c"
#include <assert.h>

typedef struct HeaderQuery { const char *table; int club,user; } HeaderQuery;
static int queries, query_frees, result_frees, domestic=20, international=14;
static int confidence=86,manager_rows=1,selected_user,change_scope,expected_user;
static int today=20261230,windows[4]={701,831,101,131},cash=94661315,currency,calendar_rows=1,money_rows=1;
static const char *current_table;
static char field[96], efficiency[32], prestige[32];
static int published_club,published_confidence;
static int published_days,published_cash,published_currency,published_manager;
static char published_date[32];

static void *query_init(void *raw,int mode,const char *table) {
    HeaderQuery *query=(HeaderQuery *)raw;
    assert(mode==1 && (!strcmp(table,"teams") || !strcmp(table,"career_managerinfo")
        || !strcmp(table,"career_calendar") || !strcmp(table,"career_managerpref")));
    memset(raw,0,56); query->table=table; query->user=-1; ++queries; return raw;
}
static void where_int(void *raw,const char *key,int op,int club) {
    HeaderQuery *query=(HeaderQuery *)raw;assert(op==0);
    if(!strcmp(query->table,"teams")){assert(!strcmp(key,"teamid"));query->club=club;}
    else if(!strcmp(key,"clubteamid"))query->club=club;
    else {assert(!strcmp(key,"userid") || !strcmp(key,"managerprefid"));query->user=club;}
}
static void *result_init(void *raw) { *(int *)raw=0; return raw; }
static void execute(void *backend,void *raw,void *result) {
    HeaderQuery *query=(HeaderQuery *)raw;(void)backend;
    if(!strcmp(query->table,"teams") || !strcmp(query->table,"career_managerinfo"))assert(query->club==native_club);
    current_table=query->table;*(int *)result=1;
    if(!strcmp(query->table,"career_managerinfo")){
        assert(query->user==expected_user);*(int *)result=manager_rows;
        if(change_scope)Fifa16CareerContextRead.sequence+=2;
    }
    if(!strcmp(query->table,"career_calendar"))*(int *)result=calendar_rows;
    if(!strcmp(query->table,"career_managerpref")){assert(query->user==expected_user);*(int *)result=money_rows;}
}
static int count(void *raw) { return *(int *)raw; }
static int integer(void *raw,int row,const char *key) {
    assert(*(int *)raw==1 && row==0);
    if(!strcmp(current_table,"career_managerinfo")){assert(!strcmp(key,"boardconfidence"));return confidence;}
    if(!strcmp(current_table,"career_calendar")){
        if(!strcmp(key,"currdate"))return today;
        if(!strcmp(key,"transferwindowstart1"))return windows[0];
        if(!strcmp(key,"transferwindowend1"))return windows[1];
        if(!strcmp(key,"transferwindowstart2"))return windows[2];
        assert(!strcmp(key,"transferwindowend2"));return windows[3];
    }
    if(!strcmp(current_table,"career_managerpref")){
        if(!strcmp(key,"transferbudget"))return cash;
        assert(!strcmp(key,"currency"));return currency;
    }
    if(!strcmp(key,"domesticprestige")) return domestic;
    assert(!strcmp(key,"internationalprestige")); return international;
}
static void result_free(void *raw) { (void)raw; ++result_frees; }
static void query_free(void *raw) { (void)raw; ++query_frees; }
static void prepare(void *provider) { (void)provider; field[0]=0; }
static void set_string(void *provider,const char *key,const char *value) {
    (void)provider;
    if(!strcmp(key,"ID")) lstrcpynA(field,value,sizeof(field));
    else if(!strcmp(key,"PARAM")) {
        if(!strcmp(field,"CAREER_HEADER_EFFICIENCY")) lstrcpynA(efficiency,value,sizeof(efficiency));
        if(!strcmp(field,"CAREER_HEADER_PRESTIGE")) lstrcpynA(prestige,value,sizeof(prestige));
        if(!strcmp(field,"CAREER_HEADER_DATE"))lstrcpynA(published_date,value,sizeof(published_date));
    }
}
static void set_int(void *provider,const char *key,int value) {
    (void)provider;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_CLUB_ID")) published_club=value;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_BOARD_CONFIDENCE"))published_confidence=value;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_MARKET_DAYS"))published_days=value;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_CASH"))published_cash=value;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_CURRENCY"))published_currency=value;
    if(!strcmp(key,"PARAM") && !strcmp(field,"CAREER_HEADER_MANAGER"))published_manager=value;
}
int main(void) {
    FceFixture fixtures[7]={0};
    void *vtable[2]={NULL,(void *)execute}; void **backend=vtable; void *service=&backend;
    unsigned char career_service[32]={0},contexts[8*0x318]={0};
    int i;
    assert(native_header_efficiency(14,19)==45);
    assert(native_header_efficiency(0,0)==-1 && native_header_efficiency(1,4)==-1);
    assert(native_header_efficiency(1,0)==0 && native_header_efficiency(1,3)==100);
    assert(native_header_efficiency(INT_MAX,INT_MAX)==33);
    assert(native_header_prestige_value(20,20)==50);
    assert(native_header_prestige_value(20,14)==43);
    assert(native_header_prestige_value(0,0)==-1 && native_header_prestige_value(21,10)==-1);
    assert(native_header_market_days(20261230,windows)==2);
    assert(native_header_market_days(20260701,windows)==0 && native_header_market_days(20260831,windows)==0);
    assert(native_header_market_days(20260901,windows)==122);
    assert(native_header_market_days(20260131,windows)==0 && native_header_market_days(20260201,windows)==150);
    {int local[4]={1201,131,401,430};
        assert(native_header_market_days(20261231,local)==0 && native_header_market_days(20270115,local)==0);
        assert(native_header_market_days(20270201,local)==59);
        local[0]=local[1]=0;local[2]=301;local[3]=331;
        assert(native_header_market_days(20280228,local)==2 && native_header_market_days(20270228,local)==1);
        local[2]=1332;assert(native_header_market_days(20261230,local)==-1);
    }
    native_club=1043; native_view.date=20261107;
    for(i=0;i<7;++i) {
        fixtures[i].id=i+1; fixtures[i].date_raw=20260101+i;
        fixtures[i].home=1043; fixtures[i].away=241;
        fixtures[i].played_raw=1; fixtures[i].home_score=0; fixtures[i].away_score=1;
        fixtures[i].competition_object=100+i;
    }
    fixtures[0].home_score=2; /* A win in one competition. */
    fixtures[1].home_score=1; /* A draw in a different competition. */
    fixtures[3].played_raw=0;
    fixtures[4].date_raw=20270101; /* Future results cannot affect the header. */
    fixtures[5]=fixtures[0]; /* Duplicate snapshot of an already counted fixture. */
    fixtures[6].home=598; /* Another club's result. */
    native_view.fixtures=fixtures; native_view.fixture_count=7;
    native_coach_record(native_club);
    assert(g_coach_record.games==3 && g_coach_record.points==4);
    assert(native_header_efficiency(g_coach_record.games,g_coach_record.points)==44);
    assert(g_coach_record.percent==33); /* Existing win-rate consumers retain their definition. */
    native_names=&service;
    native_name_db.query_init=query_init; native_name_db.where_int=where_int;
    native_name_db.result_init=result_init; native_name_db.count=count;
    native_name_db.integer=integer; native_name_db.result_free=result_free; native_name_db.query_free=query_free;
    g_prepare_field=prepare; g_set_string=set_string; g_set_int=set_int;
    *(uintptr_t *)career_service=(uintptr_t)vtable;
    *(uintptr_t *)(career_service+0x18)=(uintptr_t)contexts;
    *(int *)(contexts+0x18c)=1;*(int *)(contexts+0x1a4)=native_club;
    Fifa16CareerContextRead.pid=GetCurrentProcessId();
    Fifa16CareerContextRead.service=(uintptr_t)career_service;
    Fifa16CareerContextRead.vtable=(uintptr_t)vtable;
    Fifa16CareerContextRead.epoch=fce_runtime_context_epoch();
    publish_header_metrics(&i);
    assert(published_club==1043 && !strcmp(efficiency,"44%") && !strcmp(prestige,"4,3/5"));
    assert(published_confidence==86);
    assert(published_manager==1 && !strcmp(published_date,"30/12/2026") && published_days==2
        && published_cash==94661315 && published_currency==0);
    cash=0;currency=2;today=20270101;publish_header_metrics(&i);
    assert(published_cash==0 && published_currency==2 && published_days==0 && !strcmp(published_date,"01/01/2027"));
    currency=3;publish_header_metrics(&i);assert(published_cash==-1 && published_currency==-1);
    currency=0;cash=94661315;today=20261230;
    calendar_rows=0;publish_header_metrics(&i);assert(!published_date[0] && published_days==-1 && published_cash==cash);calendar_rows=1;
    money_rows=2;publish_header_metrics(&i);assert(published_cash==-1 && published_currency==-1);money_rows=1;
    confidence=0;publish_header_metrics(&i);assert(published_confidence==0);
    confidence=100;publish_header_metrics(&i);assert(published_confidence==100);
    confidence=101;publish_header_metrics(&i);assert(published_confidence==-1);
    confidence=-1;publish_header_metrics(&i);assert(published_confidence==-1);
    confidence=86;manager_rows=0;publish_header_metrics(&i);assert(published_confidence==-1);
    manager_rows=2;publish_header_metrics(&i);assert(published_confidence==-1);
    manager_rows=1;change_scope=1;publish_header_metrics(&i);assert(published_confidence==-1);change_scope=0;
    *(int *)(contexts+0x18c)=0;publish_header_metrics(&i);assert(published_confidence==-1 && !published_manager
        && !published_date[0] && published_days==-1 && published_cash==-1); /* Player career. */
    *(int *)(contexts+0x18c)=1;
    *(int *)(contexts+0x1a4)=598;publish_header_metrics(&i);assert(published_confidence==-1); /* Foreign club. */
    *(int *)(contexts+0x1a4)=1043;
    selected_user=expected_user=1;*(int *)(career_service+0x14)=selected_user;
    *(int *)(contexts+0x318+0x18c)=1;*(int *)(contexts+0x318+0x1a4)=1043;
    confidence=24;publish_header_metrics(&i);assert(published_confidence==24); /* Another user, same club. */
    native_club=112893; domestic=12; international=8;
    memset(&g_coach_record,0,sizeof(g_coach_record)); publish_header_metrics(&i);
    assert(published_club==112893 && !efficiency[0] && !strcmp(prestige,"2,5/5"));
    assert(published_confidence==-1);
    *(int *)(contexts+0x318+0x1a4)=112893;confidence=59;publish_header_metrics(&i);assert(published_confidence==59);
    native_names=NULL;publish_header_metrics(&i);assert(published_confidence==-1);
    assert(queries==query_frees && queries==result_frees);
    puts("PASS career hubs: board rating, native dates, save-specific transfer windows, New Year/leap year, cash/currency, selected user, player/foreign/changed contexts and balanced read-only queries");
    return 0;
}
