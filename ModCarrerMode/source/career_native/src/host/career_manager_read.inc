/* Global league evidence for coach decisions, using the already validated
 * career DB read API on FIFA's UI owner. No DB setter or save write is used.
 * The companion requests an exact PID/session/club/day; stale requests expire.
 */
static const char *manager_league_fields[]={
    "teamid","leagueid","secondarytable","nummatchesplayed","points",
    "homewins","homedraws","homelosses","awaywins","awaydraws","awaylosses",
    "homegf","homega","awaygf","awayga","currenttableposition"};
static ULONGLONG g_manager_read_next;

static void drain_manager_read(void)
{
    PreparedViewRecord request;CareerContextRead captured,verified;
    MarketReadRows rows={0};void *names,*backend;uintptr_t context;
    ULONGLONG tick=GetTickCount64();int ok=0;FILE *file=NULL;
    char path[MAX_PATH],temporary[MAX_PATH],request_path[MAX_PATH];
    if(tick<g_manager_read_next)return;g_manager_read_next=tick+2000;
    if(g_current_stats_provider_owner || !fce_runtime_is_stable()
        || !native_name_db.query_init || !native_name_db.where_int || !native_name_db.result_init
        || !native_name_db.count || !native_name_db.integer || !native_name_db.result_free || !native_name_db.query_free)return;
    snprintf(request_path,sizeof(request_path),"%s\\runtime\\manager_market\\read_request.tsv",g_mod_dir);
    if(!prepared_view_read_file(request_path,&request) || tick<request.captured
        || tick-request.captured>12000 || !prepared_view_scope(&request,&captured))return;
    names=bank_mail_service(captured.registry,0x4456560,8);
    if(!names || !is_readable_range(names,sizeof(void *)))return;
    backend=*(void **)names;if(!is_readable_range(backend,16))return;
    context=(uintptr_t)request.context;
    snprintf(path,sizeof(path),"%s\\runtime\\manager_market\\live_leagues.tsv",g_mod_dir);
    snprintf(temporary,sizeof(temporary),"%s.new",path);
    __try {
        __try {
            if(!market_read_table(backend,"leagueteamlinks",manager_league_fields,
                (int)(sizeof(manager_league_fields)/sizeof(manager_league_fields[0])),"secondarytable",0,&rows)
                || rows.count<=0 || !prepared_view_scope(&request,&verified)
                || captured.sequence!=verified.sequence)__leave;
            file=fopen(temporary,"wb");if(!file)__leave;
            fprintf(file,"schema=1\npid=%lu\nprocess_created_100ns=%llu\nepoch=%lu\ncontext=%llx\nregistry=%llx\nclub=%u\ndate=%d\ncaptured_ms=%llu\n",
                GetCurrentProcessId(),request.created,captured.epoch,(unsigned long long)context,
                (unsigned long long)captured.registry,request.club,request.date,(unsigned long long)tick);
            if(!market_write_rows(file,"league",&rows) || !prepared_view_scope(&request,&verified)
                || captured.sequence!=verified.sequence)__leave;
            fputs("complete=1\n",file);ok=!ferror(file);
        } __finally {
            if(file){if(fclose(file))ok=0;file=NULL;}
            free(rows.values);
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {ok=0;}
    if(ok)MoveFileExA(temporary,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
    else DeleteFileA(temporary);
}
