/* Career header presentation only. All queries use the current FIFA service;
 * no database rows, save buffers or existing dashboard definitions change. */
static int native_header_efficiency(int games,int points) {
    if(games<=0 || points<0 || (__int64)points>(__int64)games*3) return -1;
    return (int)((__int64)points*100/((__int64)games*3));
}
static int native_header_prestige_value(int domestic,int international) {
    if(domestic<0 || domestic>20 || international<0 || international>20
        || (domestic==0 && international==0)) return -1;
    /* FIFA club prestige is on a 0..20 scale. Publish tenths of a star. */
    return ((domestic+international)*10+4)/8;
}
static int native_header_prestige(int club) {
    unsigned __int64 query[7]={0},result=0;
    int query_ready=0,result_ready=0,value=-1,domestic=0,international=0;
    void *backend=NULL;
    if(club<=0) return -1;
    if(native_names && is_readable_range(native_names,sizeof(void *))) backend=*(void **)native_names;
    if(backend && is_readable_range(backend,sizeof(void *)) && native_name_db.query_init
        && native_name_db.where_int && native_name_db.result_init && native_name_db.count
        && native_name_db.integer && native_name_db.result_free && native_name_db.query_free) {
        __try {
            __try {
                void (*execute)(void *,void *,void *)=(void (*)(void *,void *,void *))(*(void ***)backend)[1];
                native_name_db.query_init(query,1,"teams");query_ready=1;
                native_name_db.where_int(query,"teamid",0,club);
                native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
                if(native_name_db.count(&result)==1) {
                    domestic=native_name_db.integer(&result,0,"domesticprestige");
                    international=native_name_db.integer(&result,0,"internationalprestige");
                    value=native_header_prestige_value(domestic,international);
                }
            } __finally {
                if(result_ready) native_name_db.result_free(&result);
                if(query_ready) native_name_db.query_free(query);
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {value=-1;}
    }
    if(value<0) {
        char name[256],image[256];int capacity=0;
        if(native_game_stadium_fallback(club,name,sizeof(name),&capacity,image,sizeof(image),&domestic,&international))
            value=native_header_prestige_value(domestic,international);
    }
    return value;
}
/* The header belongs to the selected manager career, not to the simulated
 * coaches market. Keep no rating cache: every provider refresh reads the
 * current native row on the provider's existing UI owner thread. */
static int native_header_manager_user(int club) {
    CareerContextRead scope;uintptr_t contexts,context;int selected;
    memcpy(&scope,&Fifa16CareerContextRead,sizeof(scope));
    if(club<=0 || scope.schema!=1 || scope.size!=sizeof(scope) || scope.sequence&1
        || scope.pid!=GetCurrentProcessId() || scope.epoch!=fce_runtime_context_epoch())return -1;
    __try {
        if(!is_readable_range((void *)scope.service,32)
            || *(uintptr_t *)scope.service!=scope.vtable)return -1;
        selected=*(int *)(scope.service+0x14);contexts=*(uintptr_t *)(scope.service+0x18);
        if(selected<0 || selected>7 || !contexts)return -1;
        context=contexts+(uintptr_t)selected*0x318;
        if(!is_readable_range((void *)context,0x318)
            || *(int *)(context+0x18c)!=1 || *(int *)(context+0x1a4)!=club
            || Fifa16CareerContextRead.sequence!=scope.sequence)return -1;
        return selected;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return -1;}
}
static int native_header_confidence(int club) {
    unsigned __int64 query[7]={0},result=0;
    int query_ready=0,result_ready=0,value=-1,user=native_header_manager_user(club);
    LONG sequence=Fifa16CareerContextRead.sequence;void *backend=NULL;
    if(user<0)return -1;
    if(native_names && is_readable_range(native_names,sizeof(void *)))backend=*(void **)native_names;
    if(!backend || !is_readable_range(backend,sizeof(void *)) || !native_name_db.query_init
        || !native_name_db.where_int || !native_name_db.result_init || !native_name_db.count
        || !native_name_db.integer || !native_name_db.result_free || !native_name_db.query_free)return -1;
    __try {
        __try {
            void (*execute)(void *,void *,void *)=(void (*)(void *,void *,void *))(*(void ***)backend)[1];
            native_name_db.query_init(query,1,"career_managerinfo");query_ready=1;
            native_name_db.where_int(query,"userid",0,user);
            native_name_db.where_int(query,"clubteamid",0,club);
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1) {
                value=native_name_db.integer(&result,0,"boardconfidence");
                if(value<0 || value>100)value=-1;
            }
        } __finally {
            if(result_ready)native_name_db.result_free(&result);
            if(query_ready)native_name_db.query_free(query);
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {value=-1;}
    if(Fifa16CareerContextRead.sequence!=sequence || native_header_manager_user(club)!=user)value=-1;
    return value;
}
static int native_header_read_row(const char *table,const char *filter,int id,
    const char *const *fields,int columns,int *values) {
    unsigned __int64 query[7]={0},result=0;void *backend=NULL;
    int q=0,r=0,ok=0,i;
    if(native_names && is_readable_range(native_names,sizeof(void *)))backend=*(void **)native_names;
    if(!backend || !is_readable_range(backend,sizeof(void *)) || !native_name_db.query_init
        || !native_name_db.where_int || !native_name_db.result_init || !native_name_db.count
        || !native_name_db.integer || !native_name_db.result_free || !native_name_db.query_free)return 0;
    __try {__try {
        void (*execute)(void *,void *,void *)=(void (*)(void *,void *,void *))(*(void ***)backend)[1];
        native_name_db.query_init(query,1,table);q=1;
        if(filter)native_name_db.where_int(query,filter,0,id);
        native_name_db.result_init(&result);r=1;execute(backend,query,&result);
        if(native_name_db.count(&result)==1){
            for(i=0;i<columns;++i)values[i]=native_name_db.integer(&result,0,fields[i]);
            ok=1;
        }
    } __finally {if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){ok=0;}
    return ok;
}
static int native_header_ordinal(int date) {
    int year=date/10000,month=(date/100)%100,days=date%100,m;
    if(!fce_date_valid(date))return -1;
    for(m=1;m<month;++m)days+=native_squad_days_in_month(year,m);
    --year;return year*365+year/4-year/100+year/400+days;
}
/* Native calendar window boundaries are MMDD and are specific to this save.
 * A window may cross New Year; do not assume January/July or a country rule. */
static int native_header_market_days(int today,const int *windows) {
    int year=today/10000,md=today%10000,best=-1,valid=0,i;
    if(!fce_date_valid(today))return -1;
    for(i=0;i<2;++i){
        int start=windows[i*2],end=windows[i*2+1],date,delta,y;
        if(start<=0 || start>1231 || end<=0 || end>1231
            || !fce_date_valid(year*10000+start) || !fce_date_valid(year*10000+end))continue;
        ++valid;
        if((start<=end && md>=start && md<=end) || (start>end && (md>=start || md<=end)))return 0;
        date=0;
        for(y=year;y<=year+4;++y){
            int candidate=y*10000+start;
            if(candidate>today && fce_date_valid(candidate)){date=candidate;break;}
        }
        if(!date)continue;
        delta=native_header_ordinal(date)-native_header_ordinal(today);
        if(delta>0 && (best<0 || delta<best))best=delta;
    }
    return valid?best:-1;
}
static void publish_header_career_state(void *provider) {
    static const char *calendar_fields[]={"currdate","transferwindowstart1","transferwindowend1","transferwindowstart2","transferwindowend2"};
    static const char *money_fields[]={"transferbudget","currency"};
    int user=native_header_manager_user(native_club),calendar[5]={0},money[2]={0};
    int date=0,days=-1,cash=-1,currency=-1;char date_text[32]="";
    LONG sequence=Fifa16CareerContextRead.sequence;
    if(user>=0){
        if(native_header_read_row("career_calendar",NULL,0,calendar_fields,5,calendar) && fce_date_valid(calendar[0])){
            date=calendar[0];days=native_header_market_days(date,calendar+1);
        }
        if(native_header_read_row("career_managerpref","managerprefid",user,money_fields,2,money)
            && money[0]>=0 && money[1]>=0 && money[1]<=2){cash=money[0];currency=money[1];}
        if(sequence!=Fifa16CareerContextRead.sequence || native_header_manager_user(native_club)!=user){
            date=0;days=cash=currency=-1;user=-1;
        }
    }
    if(date)snprintf(date_text,sizeof(date_text),"%02d/%02d/%04d",date%100,(date/100)%100,date/10000);
    publish_string_field(provider,"CAREER_HEADER_DATE",date_text);
    publish_int_field(provider,"CAREER_HEADER_MARKET_DAYS",days);
    publish_int_field(provider,"CAREER_HEADER_CASH",cash);
    publish_int_field(provider,"CAREER_HEADER_CURRENCY",currency);
    publish_int_field(provider,"CAREER_HEADER_MANAGER",user>=0);
}
static void publish_header_metrics(void *provider) {
    int efficiency=native_header_efficiency(g_coach_record.games,g_coach_record.points);
    int prestige=native_header_prestige(native_club);
    char value[32];
    publish_int_field(provider,"CAREER_HEADER_CLUB_ID",native_club);
    if(efficiency>=0) snprintf(value,sizeof(value),"%d%%",efficiency);else value[0]=0;
    publish_string_field(provider,"CAREER_HEADER_EFFICIENCY",value);
    if(prestige>=0) snprintf(value,sizeof(value),"%d,%d/5",prestige/10,prestige%10);else value[0]=0;
    publish_string_field(provider,"CAREER_HEADER_PRESTIGE",value);
    publish_int_field(provider,"CAREER_HEADER_BOARD_CONFIDENCE",native_header_confidence(native_club));
    publish_header_career_state(provider);
}
