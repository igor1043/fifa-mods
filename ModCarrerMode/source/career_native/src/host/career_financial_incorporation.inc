/* Creation-only native UPDATE on the verified career/UI owner. The original
 * FIFA serializer saves these fields normally; DATA and the base DB are never
 * patched. Pending choices are process-local and cannot survive a restart. */
#include "financial_incorporation_policy.h"
static FinancialIncorporation g_financial_start;
static int g_financial_calendar_current,g_financial_calendar_season;
static int financial_current_page(char page[128]) {
    static const unsigned offsets[]={232,192,136,472};uintptr_t node=0;unsigned i;
    if(!read_card_scope((uintptr_t)g_module_base+0x3809030,&node,8))return 0;
    for(i=0;i<4;++i)if(!node||!read_card_scope(node+offsets[i],&node,8))return 0;
    return node&&read_card_scope(node,page,128)&&memchr(page,0,128)!=NULL;
}
static void financial_status(const char *state,unsigned club,int before,int after) {
    char folder[MAX_PATH],path[MAX_PATH],temporary[MAX_PATH];FILE *file;
    snprintf(folder,sizeof(folder),"%s\\runtime\\financial_incorporation",g_mod_dir);CreateDirectoryA(folder,NULL);
    snprintf(path,sizeof(path),"%s\\status.ini",folder);snprintf(temporary,sizeof(temporary),"%s.new",path);
    file=fopen(temporary,"wb");if(!file)return;
    fprintf(file,"schema=1\npid=%lu\ngeneration=%u\nstatus=%s\nclub=%u\namount=%d\nbefore=%d\nafter=%d\ncalendar_current=%d\ncalendar_season_start=%d\n",
        GetCurrentProcessId(),g_financial_start.generation,state,club,g_financial_start.amount,before,after,
        g_financial_calendar_current,g_financial_calendar_season);
    if(!fclose(file))MoveFileExA(temporary,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
}
static int financial_incorporation_capture(const char *wire) {
    CareerContextRead context;uintptr_t current;unsigned club;int date,action,amount;char page[128];
    if(!bank_mail_string(wire,80)||!financial_wire(wire,&action,&amount))return 0;
    if(action==2){
        if(g_financial_start.phase==FINANCIAL_CHOOSING||g_financial_start.phase==FINANCIAL_ARMED){g_financial_start.phase=FINANCIAL_IDLE;financial_status("cancelled",0,0,0);}return 1;
    }
    if(!financial_current_page(page)||strcmp(page,"game/screens/career/Setup"))return 0;
    /* Setup can reuse an old frontend service. A populated live career is
     * never a legal source for a new-start grant. */
    if(bank_input_context(&context,&current,&club,&date))return 0;
    if(action==0){financial_begin(&g_financial_start);g_financial_calendar_current=g_financial_calendar_season=0;financial_status("choosing",0,0,0);return 1;}
    if(g_financial_start.phase==FINANCIAL_IDLE)financial_begin(&g_financial_start);
    if(!financial_arm(&g_financial_start,amount,GetTickCount64(),fce_runtime_context_epoch()))return 0;
    financial_status(amount?"waiting_new_career":"disabled",0,0,0);return 1;
}
static int financial_update(void *backend,unsigned user,int before,int season_before,int after,int season_after) {
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,ok=0;
    void (*set_int)(void *,const char *,int)=(void (*)(void *,const char *,int))(g_module_base+0x4462640);
    __try {__try {
        unsigned char (*execute)(void *,void *,void *)=(unsigned char (*)(void *,void *,void *))(*(void ***)backend)[1];
        native_name_db.query_init(query,3,"career_managerpref");q=1;
        set_int(query,"transferbudget",after);set_int(query,"startofseasontransferbudget",season_after);
        native_name_db.where_int(query,"managerprefid",0,(int)user);
        native_name_db.where_int(query,"transferbudget",0,before);
        native_name_db.where_int(query,"startofseasontransferbudget",0,season_before);
        native_name_db.result_init(&result);r=1;ok=execute(backend,query,&result)!=0;
    } __finally {if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){ok=0;}
    return ok;
}
typedef struct {CareerContextRead captured;void *backend;uintptr_t preference;unsigned club;int user,today;} FinancialGrantScope;
static int financial_grant_scope(void *context) {
    FinancialGrantScope *s=(FinancialGrantScope *)context;
    return market_read_same_context(&s->captured,(int)s->club,s->today);
}
static int financial_grant_write(void *context,int before,int season_before,int after,int season_after) {
    FinancialGrantScope *s=(FinancialGrantScope *)context;
    volatile LONG *money=(volatile LONG *)(s->preference+0x2ac);
    volatile LONG *season=(volatile LONG *)(s->preference+0x2c4);
    if(!financial_grant_scope(s)||!financial_mirrors_match(*money,*season,before,season_before))return 0;
    if(!financial_update(s->backend,(unsigned)s->user,before,season_before,after,season_after))return 0;
    if(!financial_grant_scope(s))return 0;
    /* The SQL row and active Career preference are separate native objects.
     * Keeping only SQL updated reports success while the game still spends
     * the old budget. Synchronize both verified mirrors on their owner; FIFA
     * then serializes them normally, without editing DATA/INDEX ourselves. */
    if(InterlockedCompareExchange(season,season_after,season_before)!=season_before)return 0;
    if(InterlockedCompareExchange(money,after,before)!=before)return 0;
    return *money==after&&*season==season_after;
}
static int financial_grant_read(void *context,int *money,int *season) {
    FinancialGrantScope *s=(FinancialGrantScope *)context;MarketReadRows check={0};int ok;
    static const char *fields[]={"transferbudget","startofseasontransferbudget"};
    if(!market_read_table(s->backend,"career_managerpref",fields,2,"managerprefid",s->user,&check))return 0;
    ok=check.count==1;
    if(ok){
        *money=check.values[0];*season=check.values[1];
        ok=financial_mirrors_match(*(int *)(s->preference+0x2ac),*(int *)(s->preference+0x2c4),*money,*season);
    }free(check.values);return ok;
}
static void drain_financial_incorporation(void) {
    static ULONGLONG next;CareerContextRead captured;uintptr_t context;unsigned club;int today,user,before,season_before,after,season_after,ok=0;
    unsigned char *names;void *backend;char page[128];MarketReadRows calendar={0},money={0};ULONGLONG tick=GetTickCount64();
    FinancialGrantScope grant;FinancialBudgetOps operations;
    static uintptr_t observed_context;static unsigned observed_generation,observed_epoch;static int observed_money,observed_season;static ULONGLONG observed_since;
    static const char *calendar_fields[]={"currdate","startdate"};
    static const char *money_fields[]={"transferbudget","startofseasontransferbudget"};
    if(g_current_stats_provider_owner||(!frontend_ui_is_owner()&&Fifa16CareerContextRead.owner_thread!=GetCurrentThreadId()))return;
    if(g_financial_start.phase!=FINANCIAL_ARMED||tick<next)return;next=tick+100;
    if(tick<g_financial_start.armed||tick-g_financial_start.armed>900000){g_financial_start.phase=FINANCIAL_REJECTED;financial_status("expired",0,0,0);return;}
    if(!financial_current_page(page))return;
    _strlwr_s(page,sizeof(page));
    if(strstr(page,"/mainmenu")||strstr(page,"/mainhub")||strstr(page,"/load")||strstr(page,"/selectcareer")||strstr(page,"/careertype")){
        g_financial_start.phase=FINANCIAL_IDLE;financial_status("cancelled_navigation",0,0,0);return;
    }
    if(!fce_runtime_is_stable()||!bank_input_context(&captured,&context,&club,&today)||captured.owner_thread!=GetCurrentThreadId())return;
    if(captured.epoch<g_financial_start.epoch)return;
    if(!native_name_db.query_init||!native_name_db.integer||!native_name_db.where_int||!native_name_db.count
       ||!native_name_db.result_init||!native_name_db.result_free||!native_name_db.query_free
       ||memcmp(g_module_base+0x4462640,"\x48\x89\x5c\x24\x08",5))return;
    names=bank_mail_service(captured.registry,0x4456560,8);if(!names)return;
    backend=*(void **)names;if(!is_readable_range(backend,16)||*(uintptr_t *)backend!=(uintptr_t)g_module_base+0x21b5770)return;
    user=*(int *)(captured.service+0x14);if(user<0||user>7)return;
    if(!market_read_table(backend,"career_calendar",calendar_fields,2,NULL,0,&calendar))return;
    /* Calendar construction can briefly expose no row or a stale current day.
     * Wait for publication; the season reference need not equal the first day. */
    if(calendar.count!=1){free(calendar.values);return;}
    g_financial_calendar_current=calendar.values[0];g_financial_calendar_season=calendar.values[1];
    ok=financial_creation_calendar(&g_financial_start,calendar.values[0],calendar.values[1],today);free(calendar.values);
    if(!ok)return;
    if(!market_read_table(backend,"career_managerpref",money_fields,2,"managerprefid",user,&money))return;
    if(money.count!=1){free(money.values);return;}
    before=money.values[0];season_before=money.values[1];free(money.values);
    if(!financial_mirrors_match(*(int *)(context+0x2ac),*(int *)(context+0x2c4),before,season_before))return;
    /* Do not race native initial-budget construction. Require the same
     * newly-created context and values on several owner-thread observations. */
    if(observed_generation!=g_financial_start.generation||observed_context!=context||observed_epoch!=captured.epoch||observed_money!=before||observed_season!=season_before){
        observed_generation=g_financial_start.generation;observed_context=context;observed_epoch=captured.epoch;observed_money=before;observed_season=season_before;observed_since=tick;return;
    }
    if(tick-observed_since<300)return;
    if(!financial_plan(before,season_before,g_financial_start.amount,&after,&season_after)){
        g_financial_start.phase=FINANCIAL_REJECTED;financial_status("budget_limit",club,before,before);return;
    }
    if(!market_read_same_context(&captured,(int)club,today))return;
    /* Consume before calling the setter. An exception or lost acknowledgement
     * cannot replay this addition on a later UI tick, reload or saved game. */
    g_financial_start.club=club;grant.captured=captured;grant.backend=backend;grant.preference=context;grant.club=club;grant.user=user;grant.today=today;
    operations.context=&grant;operations.scope=financial_grant_scope;operations.write=financial_grant_write;operations.read=financial_grant_read;
    ok=financial_commit(&g_financial_start,operations,before,season_before,&after,&season_after);
    if(!ok)return;
    if(ok==1){financial_status("applied",club,before,after);append_loader_log("financial_incorporation_applied_once");}
    else{financial_status("update_unconfirmed_no_retry",club,before,after);append_loader_log("financial_incorporation_not_replayed_after_unconfirmed_update");}
}
