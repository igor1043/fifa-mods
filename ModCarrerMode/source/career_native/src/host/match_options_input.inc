/* Only owned GameSettings events. All file copies stay in Server16's worker. */
static DWORD g_match_options_thread;
static ULONGLONG g_match_options_enter;
static int match_options_page(void)
{
    static const unsigned offsets[]={232,192,136,472};uintptr_t node=0;char page[96];unsigned i;
    if(!read_card_scope((uintptr_t)g_module_base+0x3809030,&node,8))return 0;
    for(i=0;i<4;++i)if(!node||!read_card_scope(node+offsets[i],&node,8))return 0;
    return node&&read_card_scope(node,page,sizeof(page))&&memchr(page,0,sizeof(page))&&!strcmp(page,"game/screens/settings/GameSettings");
}
static int match_options_capture(const char *kind,const char *wire,int fixture)
{
    typedef struct {DWORD owner,heartbeat,pid;LONG generation,home,away,phase;} CrowdHeader;
    CrowdHeader state={0};HANDLE mapping;const CrowdHeader *shared;
    char folder[MAX_PATH],path[MAX_PATH],temp[MAX_PATH];FILE *file;FILETIME created,exit,kernel,user;ULARGE_INTEGER identity;
    if(!match_options_page()||!bank_mail_string(wire,128))return 0;
    if(fixture){
        mapping=OpenFileMappingW(FILE_MAP_READ,FALSE,L"Local\\CGFS16_Crowd_v1");if(!mapping)return 0;
        shared=(const CrowdHeader *)MapViewOfFile(mapping,FILE_MAP_READ,0,0,sizeof(state));
        if(!shared){CloseHandle(mapping);return 0;}
        memcpy(&state,shared,sizeof(state));UnmapViewOfFile(shared);CloseHandle(mapping);
        if(!state.owner||state.pid!=GetCurrentProcessId()||state.phase!=1||state.home<=0||state.away<=0||(DWORD)(GetTickCount()-state.heartbeat)>=2000)return 0;
    }
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return 0;
    identity.LowPart=created.dwLowDateTime;identity.HighPart=created.dwHighDateTime;
    if(snprintf(folder,sizeof(folder),"%s\\runtime\\%s",g_mod_dir,!strcmp(kind,"movie")?"movie_selector":"stadium_options")>=(int)sizeof(folder))return 0;
    CreateDirectoryA(folder,NULL);
    if(snprintf(path,sizeof(path),"%s\\%s.tsv",folder,!strcmp(kind,"movie")?"request":kind)>=(int)sizeof(path))return 0;
    if(snprintf(temp,sizeof(temp),"%s.new",path)>=(int)sizeof(temp))return 0;
    file=fopen(temp,"wb");if(!file)return 0;
    fprintf(file,"schema=1\npid=%lu\ncreated=%llu\ngeneration=%ld\nhome=%ld\naway=%ld\ncaptured_tick=%llu\nwire=%s\n",GetCurrentProcessId(),(unsigned long long)identity.QuadPart,state.generation,state.home,state.away,(unsigned long long)(!strcmp(kind,"enter")?g_match_options_enter:GetTickCount64()),wire);
    if(fclose(file))return 0;
    return MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
}
static int match_options_movie(const char *wire)
{
    char normalized[128];size_t n;
    if(!bank_mail_string(wire,sizeof(normalized))||strncmp(wire,"S16MOVIE1|",10))return 0;
    n=strlen(wire);if(n>=sizeof(normalized))return 0;
    /* Both media choices have the same signature/index contract. */
    memcpy(normalized,"S16SCORE1|",10);memcpy(normalized+10,wire+10,n-9);
    return scoreboard_options_wire_valid(normalized)&&match_options_capture("movie",wire,0);
}
static void match_options_refresh(void *bridge)
{
    static ULONGLONG next;static char applied[65];char path[MAX_PATH],line[160],revision[65]={0};
    unsigned schema=0,pid=0;unsigned long long entry=0,requested_created=0;FILE *file;
    FILETIME created,exit,kernel,user;ULARGE_INTEGER identity;uintptr_t vtable=0,dispatch=0;
    if(GetCurrentThreadId()!=g_match_options_thread||!g_match_options_enter||!match_options_page()||GetTickCount64()<next)return;
    next=GetTickCount64()+500;
    snprintf(path,sizeof(path),"%s\\runtime\\stadium_options\\refresh.tsv",g_mod_dir);file=fopen(path,"rb");if(!file)return;
    while(fgets(line,sizeof(line),file)){
        if(sscanf(line,"schema=%u",&schema)==1)continue;
        if(sscanf(line,"pid=%u",&pid)==1)continue;
        if(sscanf(line,"created=%llu",&requested_created)==1)continue;
        if(sscanf(line,"entry_tick=%llu",&entry)==1)continue;
        if(!strncmp(line,"revision=",9)&&strcspn(line+9,"\r\n")==64&&strspn(line+9,"0123456789abcdef")==64)memcpy(revision,line+9,64);
    }fclose(file);
    if(schema!=1||pid!=GetCurrentProcessId()||entry!=g_match_options_enter||!revision[0]||!strcmp(revision,applied))return;
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return;
    identity.LowPart=created.dwLowDateTime;identity.HighPart=created.dwHighDateTime;if(identity.QuadPart!=requested_created)return;
    if(!read_card_scope((uintptr_t)bridge,&vtable,8)||vtable!=(uintptr_t)g_module_base+0x21aeb40
       ||!read_card_scope(vtable+0x28,&dispatch,8)||dispatch!=(uintptr_t)g_module_base+0x4047290
       ||memcmp((void *)dispatch,"\x48\x89\x5c\x24\x10",5))return;
    memcpy(applied,revision,sizeof(applied));
    ((void (*)(void *,const char *,const char *,const char *))dispatch)(bridge,"GameSettings","Server16RefreshGameSettings","");
}
