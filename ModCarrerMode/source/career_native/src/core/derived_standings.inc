/* FIFA16 foreign leagues can retain the season definition without retaining
 * a scored fixture/standing row. ResponseStandingsList (FCE +0x6a810) then
 * calls +0x40ce0. Use that SAME calculation, on FCE's owner thread, once per
 * campaign revision. No screen object, UI input or career-file writes. */
typedef struct {
    void *vtable;
    unsigned char *begin,*end,*capacity;
    void *allocator;
    const char *label;
    int flags,padding;
} DerivedNativeVector;
_Static_assert(sizeof(DerivedNativeVector)==56,"FCE native standings vector ABI");
#ifndef DERIVED_ALLOCATOR
#define DERIVED_ALLOCATOR() ((void *(*)(void))(module+0x85030))()
#define DERIVED_GATHER(c,s,v) ((void (*)(void *,int,DerivedNativeVector *))(module+0x32290))(c,s,v)
#define DERIVED_CALCULATE(w,s,d,v) ((void (*)(void *,int,int,DerivedNativeVector *))(module+0x40ce0))(w,s,d,v)
#endif
static SRWLOCK derived_lock=SRWLOCK_INIT;
static FceDerivedStanding *derived_rows;
static size_t derived_count,derived_capacity,derived_cursor,derived_jobs_count;
static int derived_jobs[6000],derived_date;
static LONG derived_epoch,derived_revision;
static unsigned long long derived_key;
static int derived_complete,derived_disabled;
static ULONGLONG derived_next;
#ifndef DERIVED_PHASE_IS_LEAGUE
static unsigned char derived_league_phases[65536];
static int derived_formats_loaded;
static int derived_phase_is_league(unsigned stage) {
    char path[MAX_PATH],line[512],key[128],mode[128],*slash;FILE *file;unsigned id;
    if(!derived_formats_loaded) {
        if(!GetModuleFileNameA((HMODULE)module,path,sizeof(path)))return 0;
        slash=strrchr(path,'\\');if(!slash)return 0;slash[1]=0;
        if(strlen(path)+strlen("data\\compdata\\settings.txt")>=sizeof(path))return 0;
        strcat(path,"data\\compdata\\settings.txt");file=fopen(path,"rb");if(!file)return 0;
        while(fgets(line,sizeof(line),file)) {
            if(sscanf(line,"%u,%127[^,],%127[^\r\n]",&id,key,mode)==3 && id<65536
                && !strcmp(key,"match_stagetype") && !strcmp(mode,"LEAGUE"))derived_league_phases[id]=1;
        }
        fclose(file);derived_formats_loaded=1;
    }
    return stage<65536 && derived_league_phases[stage];
}
#define DERIVED_PHASE_IS_LEAGUE(s) derived_phase_is_league(s)
#endif
static void derived_report(const char *event,int date,size_t jobs,size_t rows) {
    FILE *file=log_path[0]?fopen(log_path,"ab"):NULL;
    if(file){fprintf(file,"event=%s date=%d epoch=%ld phases=%llu rows=%llu\n",event,date,
        InterlockedCompareExchange(&generation,0,0),(unsigned long long)jobs,(unsigned long long)rows);fclose(file);}
}
static void derived_write(void) {
    char path[MAX_PATH],temporary[MAX_PATH],directory[MAX_PATH];FILE *file;
    FILETIME created,exited,kernel,user;ULARGE_INTEGER value;size_t i;int ok=1;
    if(!runtime_log_dir[0] || !GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user))return;
    value.LowPart=created.dwLowDateTime;value.HighPart=created.dwHighDateTime;
    snprintf(directory,sizeof(directory),"%s\\runtime",runtime_log_dir);CreateDirectoryA(directory,NULL);
    snprintf(path,sizeof(path),"%s\\career_derived_standings.json",directory);
    snprintf(temporary,sizeof(temporary),"%s\\career_derived_standings.%lu.tmp",directory,(unsigned long)GetCurrentProcessId());
    file=fopen(temporary,"wb");if(!file)return;
    AcquireSRWLockShared(&derived_lock);
    if(fprintf(file,"{\"schema\":1,\"pid\":%lu,\"created\":%llu,\"epoch\":%ld,\"date\":%d,\"revision\":%ld,\"rows\":[",
       (unsigned long)GetCurrentProcessId(),(unsigned long long)value.QuadPart,derived_epoch,derived_date,derived_revision)<0)ok=0;
    for(i=0;ok && i<derived_count;++i) {
        const FceDerivedStanding *d=derived_rows+i;const FceStanding *s=&d->standing;
        if(fprintf(file,"%s[%d,%d,%d,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u]",i?",":"",s->standing_id,s->competition_object,s->team,
            s->home_wins,s->home_draws,s->home_losses,s->away_wins,s->away_draws,s->away_losses,s->played,d->home_gf,d->home_ga,d->away_gf,d->away_ga)<0)ok=0;
    }
    ReleaseSRWLockShared(&derived_lock);
    if(fputs("]}",file)==EOF)ok=0;if(fclose(file)!=0)ok=0;
    if(ok)MoveFileExA(temporary,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);else DeleteFileA(temporary);
}
static unsigned long long derived_signature(const FceModel *m) {
    unsigned long long hash=1469598103934665603ULL;size_t i,j;
    const unsigned char *bytes=(const unsigned char *)m->standings;
    for(i=0;i<m->standing_count*sizeof(*m->standings);++i){hash^=bytes[i];hash*=1099511628211ULL;}
    for(i=0;i<m->node_count;++i) {
        const unsigned char *p=(const unsigned char *)(m->nodes+i);
        for(j=0;j<sizeof(*m->nodes);++j){hash^=p[j];hash*=1099511628211ULL;}
    }
    return hash;
}
unsigned long fce_runtime_derived_revision(void) {
    return (unsigned long)InterlockedCompareExchange(&derived_revision,0,0);
}
size_t fce_runtime_derived_copy(FceDerivedStanding *out,size_t capacity,int date) {
    size_t n=0;
    AcquireSRWLockShared(&derived_lock);
    if(derived_complete && !derived_disabled && derived_date==date &&
       derived_epoch==InterlockedCompareExchange(&generation,0,0)) {
        n=derived_count;
        if(out) {if(capacity<n)n=capacity;memcpy(out,derived_rows,n*sizeof(*out));}
    }
    ReleaseSRWLockShared(&derived_lock);return n;
}
static int derived_i32(const unsigned char *p,size_t offset) {
    int v;memcpy(&v,p+offset,sizeof(v));return v;
}
static void derived_free_vector(DerivedNativeVector *v) {
    if(v->begin && v->allocator) {
        void **methods=*(void ***)v->allocator;
        ((void (*)(void *,void *,size_t))methods[3])(v->allocator,v->begin,0);
    }
    memset(v,0,sizeof(*v));
}
static void derived_tick(void *iface) {
    FceLiveSnapshot *snapshot;const FceModel *m;
    unsigned char *hub,*connector,*manager,*list,**first,**last;
    void *clock=NULL;void *wrapper[3];FceRawTable competitions={0};
    unsigned long long key;size_t i,j,n;int stage,any_played=0,failed=0;
    LONG epoch=InterlockedCompareExchange(&generation,0,0);
    DerivedNativeVector vector={0};ULONGLONG started=GetTickCount64();
    if(started<derived_next || !fce_runtime_is_stable())return;
    derived_next=started+250;
    snapshot=fce_runtime_cached_acquire();if(!snapshot)return;m=&snapshot->model;
    key=derived_signature(m);
    if(derived_epoch==epoch && derived_date==m->date && derived_key==key &&
       (derived_complete||derived_disabled)){fce_runtime_release(snapshot);return;}
    __try {
        hub=*(unsigned char **)((unsigned char *)iface+0x18);
        connector=*(unsigned char **)(hub+0x28);manager=*(unsigned char **)(connector+0x18);
        list=*(unsigned char **)(hub+0x20);first=*(unsigned char ***)(list+8);last=*(unsigned char ***)(list+0x10);
        if(last<first || last-first>16) __leave;
        for(;first<last;++first)if(*first && *(int *)(*first+0x20)==5){clock=*first;break;}
        if(!clock || !fce_date_valid(m->date))__leave;
        if(derived_epoch!=epoch || derived_date!=m->date || derived_key!=key) {
            if(!copy_table(manager,0x48,&competitions))__leave;
            AcquireSRWLockExclusive(&derived_lock);
            derived_epoch=epoch;derived_date=m->date;derived_key=key;
            derived_count=derived_cursor=derived_jobs_count=0;derived_complete=derived_disabled=0;
            InterlockedIncrement(&derived_revision);
            for(i=0;i<competitions.count && derived_jobs_count<6000;++i) {
                const unsigned char *p=competitions.bytes+i*competitions.stride;
                unsigned id=(unsigned)p[0x10]+256*(unsigned)p[0x11];
                if(competitions.stride<0x16 || p[0xa]!=1 || p[0x12]!=4 || !DERIVED_PHASE_IS_LEAGUE(id))continue;
                derived_jobs[derived_jobs_count++]=(int)id;
            }
            ReleaseSRWLockExclusive(&derived_lock);
            free((void *)competitions.bytes);competitions.bytes=NULL;
            derived_report("derived_standings_started",m->date,derived_jobs_count,0);
        }
        if(derived_cursor>=derived_jobs_count) {
            AcquireSRWLockExclusive(&derived_lock);derived_complete=1;ReleaseSRWLockExclusive(&derived_lock);
            InterlockedIncrement(&derived_revision);derived_write();fce_runtime_request_refresh();
            derived_report("derived_standings_complete",m->date,derived_jobs_count,derived_count);__leave;
        }
        stage=derived_jobs[derived_cursor++];
        /* Exactly as ResponseStandingsList: an actual score in this phase
         * takes precedence. Never run the fallback over a played campaign. */
        for(i=0;i<m->standing_count;++i)if(m->standings[i].played &&
            fce_model_ancestor(m,m->standings[i].competition_object,4)==stage){any_played=1;break;}
        if(any_played)__leave;
        vector.vtable=module+0x907e8;
        vector.allocator=DERIVED_ALLOCATOR();
        vector.label="Server16 career standings";
        DERIVED_GATHER(connector,stage,&vector);
        if(!vector.begin || vector.end<vector.begin || (size_t)(vector.end-vector.begin)%0x9c)__leave;
        n=(size_t)(vector.end-vector.begin)/0x9c;
        if(n<2 || n>256)__leave;
        for(i=0;i<n;++i)if(derived_i32(vector.begin+i*0x9c,4)<=0)__leave;
        wrapper[0]=connector;wrapper[1]=clock;wrapper[2]=hub;
        DERIVED_CALCULATE(wrapper,stage,m->date,&vector);
        for(i=0;i<n;++i) {
            const unsigned char *p=vector.begin+i*0x9c;
            int slot=derived_i32(p,0),team=derived_i32(p,4);FceDerivedStanding row;
            unsigned values[10];static const size_t offsets[]={0x74,0x78,0x7c,0x88,0x8c,0x90,0x80,0x84,0x94,0x98};
            for(j=0;j<10;++j){int v=derived_i32(p,offsets[j]);if(v<0||v>1000){failed=1;break;}values[j]=(unsigned)v;}
            if(failed)break;
            for(j=0;j<m->standing_count;++j)if(m->standings[j].standing_id==slot && m->standings[j].team==team)break;
            if(j==m->standing_count){failed=1;break;}
            memset(&row,0,sizeof(row));row.standing=m->standings[j];
            row.standing.home_wins=values[0];row.standing.home_draws=values[1];row.standing.home_losses=values[2];
            row.standing.away_wins=values[3];row.standing.away_draws=values[4];row.standing.away_losses=values[5];
            row.standing.played=values[0]+values[1]+values[2]+values[3]+values[4]+values[5];
            row.home_gf=values[6];row.home_ga=values[7];row.away_gf=values[8];row.away_ga=values[9];
            if(!row.standing.played)continue;
            AcquireSRWLockExclusive(&derived_lock);
            if(derived_count==derived_capacity) {
                size_t capacity=derived_capacity?derived_capacity*2:512;
                FceDerivedStanding *rows=capacity<=65536?realloc(derived_rows,capacity*sizeof(*rows)):NULL;
                if(rows){derived_rows=rows;derived_capacity=capacity;}else failed=1;
            }
            if(!failed)derived_rows[derived_count++]=row;
            ReleaseSRWLockExclusive(&derived_lock);
            if(failed)break;
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {failed=1;}
    __try {derived_free_vector(&vector);} __except(EXCEPTION_EXECUTE_HANDLER) {failed=1;}
    if(competitions.bytes)free((void *)competitions.bytes);
    if(failed) {
        AcquireSRWLockExclusive(&derived_lock);derived_disabled=1;derived_count=0;ReleaseSRWLockExclusive(&derived_lock);
        report("derived_standings_rejected",0,m,GetTickCount64()-started);
    }
    /* One phase per owner tick; no all-leagues loop inside a UI provider. */
    derived_next=GetTickCount64()+100;
    fce_runtime_release(snapshot);
}
