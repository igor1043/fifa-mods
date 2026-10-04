/* Global-player catalog capture. All FIFA DB calls stay on native_prepare's
 * provider thread; the UI and image worker only receive copied values. */
typedef struct NativeSearchEditedName {int player;char name[128];} NativeSearchEditedName;
typedef struct NativeSearchTeamName {int team;char name[128];} NativeSearchTeamName;
static int __cdecl native_search_edited_compare(const void*a,const void*b){
    const NativeSearchEditedName*x=(const NativeSearchEditedName*)a,*y=(const NativeSearchEditedName*)b;return x->player<y->player?-1:x->player>y->player?1:0;
}
static int __cdecl native_search_team_compare(const void*a,const void*b){
    const NativeSearchTeamName*x=(const NativeSearchTeamName*)a,*y=(const NativeSearchTeamName*)b;return x->team<y->team?-1:x->team>y->team?1:0;
}
static const char *native_search_team_label(const NativeSearchTeamName*rows,SIZE_T count,int team){
    SIZE_T lo=0,hi=count;while(lo<hi){SIZE_T mid=lo+(hi-lo)/2;if(rows[mid].team<team)lo=mid+1;else hi=mid;}
    return lo<count&&rows[lo].team==team?rows[lo].name:"";
}
static const char *native_search_edited_label(const NativeSearchEditedName*rows,SIZE_T count,int player){
    SIZE_T lo=0,hi=count;while(lo<hi){SIZE_T mid=lo+(hi-lo)/2;if(rows[mid].player<player)lo=mid+1;else hi=mid;}
    return lo<count&&rows[lo].player==player?rows[lo].name:"";
}
static void native_search_resolve_label(int keys[4],char*out,size_t size){
    int i;if(!out||!size)return;out[0]=0;if(!g_resolve_player_name||!native_names)return;
    for(i=0;i<4&&!out[0];++i)if(keys[i]>0){int item[2]={0,keys[i]};
        __try{g_resolve_player_name(item,native_names,out,(int)size);}__except(EXCEPTION_EXECUTE_HANDLER){out[0]=0;}out[size-1]=0;}
}
static SIZE_T native_search_read_edited(void*backend,NativeSearchEditedName**out){
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,n=0,i;SIZE_T count=0;NativeSearchEditedName*rows=NULL;
    *out=NULL;__try{__try{
        void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
        native_name_db.query_init(query,1,"editedplayernames");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>PLAYER_SEARCH_RESULT_CAPACITY)__leave;
        rows=(NativeSearchEditedName*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(SIZE_T)(n?n:1)*sizeof(*rows));if(!rows)__leave;
        for(i=0;i<n;++i){const char*name=NULL;rows[count].player=native_name_db.integer(&result,i,"playerid");
            if(rows[count].player<=0||rows[count].player>524287)continue;
            name=native_name_db.string(&result,i,"commonname");if(!name||!*name)name=native_name_db.string(&result,i,"playerjerseyname");
            if(!name||!*name)name=native_name_db.string(&result,i,"surname");if(!name||!*name)name=native_name_db.string(&result,i,"firstname");
            if(!name||!*name)continue;lstrcpynA(rows[count].name,name,sizeof(rows[count].name));++count;
        }
        qsort(rows,count,sizeof(*rows),native_search_edited_compare);
    }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){if(rows)HeapFree(GetProcessHeap(),0,rows);rows=NULL;count=0;}
    *out=rows;return count;
}
static SIZE_T native_search_read_teams(void*backend,NativeSearchTeamName**out,int*valid){
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,n=0,i;SIZE_T count=0;NativeSearchTeamName*rows=NULL;*out=NULL;*valid=0;
    __try{__try{
        void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
        native_name_db.query_init(query,1,"teams");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>60000)__leave;rows=(NativeSearchTeamName*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,(SIZE_T)(n?n:1)*sizeof(*rows));if(!rows)__leave;
        for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"teamid");const char*name=native_name_db.string(&result,i,"teamname");
            if(id<=0||id>200000||!name||!*name)continue;rows[count].team=id;lstrcpynA(rows[count].name,name,sizeof(rows[count].name));++count;}
        qsort(rows,count,sizeof(*rows),native_search_team_compare);*valid=1;
    }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){if(rows)HeapFree(GetProcessHeap(),0,rows);rows=NULL;count=0;*valid=0;}
    *out=rows;return count;
}
static void native_search_publish_catalog(unsigned serial){
    void*backend=NULL;PlayerSearchIndexRow*rows=NULL;NativeSearchEditedName*edited=NULL;NativeSearchTeamName*teams=NULL;
    int*team_by_player=NULL,*number_by_player=NULL,*position_by_player=NULL;unsigned char*club_team=NULL,*valid_league=NULL;
    SIZE_T written=0,edited_count=0,team_count=0;int valid=0,teams_valid=0;
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,i,n=0;
    if(!native_names||!is_readable_range(native_names,sizeof(void*)))goto done;native_name_db_bind();backend=*(void**)native_names;
    if(!backend||!is_readable_range(backend,sizeof(void*)))goto done;
    rows=(PlayerSearchIndexRow*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,PLAYER_SEARCH_RESULT_CAPACITY*sizeof(*rows));
    team_by_player=(int*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,524288*sizeof(int));
    number_by_player=(int*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,524288*sizeof(int));
    position_by_player=(int*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,524288*sizeof(int));
    club_team=(unsigned char*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,200001);
    valid_league=(unsigned char*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,4097);
    if(!rows||!team_by_player||!number_by_player||!position_by_player||!club_team||!valid_league)goto done;
    edited_count=native_search_read_edited(backend,&edited);
    team_count=native_search_read_teams(backend,&teams,&teams_valid);if(!teams_valid)goto done;
    __try{__try{
        void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
        native_name_db.query_init(query,1,"leagues");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>4096)__leave;
        for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"leagueid"),level=native_name_db.integer(&result,i,"level");
            if(id>0&&id<=4096&&id!=78&&level>=1&&level<=7)valid_league[id]=1;}
        native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
        native_name_db.query_init(query,1,"leagueteamlinks");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>100000)__leave;
        for(i=0;i<n;++i){int team=native_name_db.integer(&result,i,"teamid"),league=native_name_db.integer(&result,i,"leagueid");
            if(native_name_db.integer(&result,i,"secondarytable")||team<=0||team>200000||league<=0||league>4096||!valid_league[league])continue;club_team[team]=1;}
        native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
        native_name_db.query_init(query,1,"teamplayerlinks");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>1000000)__leave;
        for(i=0;i<n;++i){int player=native_name_db.integer(&result,i,"playerid"),team=native_name_db.integer(&result,i,"teamid");
            if(player<=0||player>524287||team<=0||team>200000||(team!=native_club&&!club_team[team]))continue;
            if(!team_by_player[player]||team==native_club){team_by_player[player]=team;number_by_player[player]=native_name_db.integer(&result,i,"jerseynumber");
                {int p=native_name_db.integer(&result,i,"position");position_by_player[player]=p>=0&&p<=33?p+1:0;}}
        }
        native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
        native_name_db.query_init(query,1,"players");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n<0||n>500000)__leave;
        for(i=0;i<n&&written<PLAYER_SEARCH_RESULT_CAPACITY;++i){int player=native_name_db.integer(&result,i,"playerid"),birthdate;PlayerSearchIndexRow*out;int keys[4];const char*label;
            if(player<=0||player>524287)continue;out=rows+written;memset(out,0,sizeof(*out));out->player_id=player;out->team_id=team_by_player[player];
            out->number=number_by_player[player];out->position=position_by_player[player]?position_by_player[player]-1:-1;
            birthdate=native_name_db.integer(&result,i,"birthdate");out->age=native_squad_player_age(birthdate,native_view.date);
            out->overall=native_name_db.integer(&result,i,"overallrating");
            label=native_search_edited_label(edited,edited_count,player);
            if(label&&*label)lstrcpynA(out->name,label,sizeof(out->name));else{
                keys[0]=native_name_db.integer(&result,i,"commonnameid");keys[1]=native_name_db.integer(&result,i,"playerjerseynameid");
                keys[2]=native_name_db.integer(&result,i,"lastnameid");keys[3]=native_name_db.integer(&result,i,"firstnameid");native_search_resolve_label(keys,out->name,sizeof(out->name));}
            if(!out->name[0])_snprintf_s(out->name,sizeof(out->name),_TRUNCATE,"#%d",player);
            label=native_search_team_label(teams,team_count,out->team_id);if(label&&*label)lstrcpynA(out->team_name,label,sizeof(out->team_name));++written;
        }
        valid=1;
    }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){valid=0;written=0;}
done:
    player_search_screen_publish_index(valid?rows:NULL,valid?written:0,serial,valid);
    if(rows)HeapFree(GetProcessHeap(),0,rows);if(edited)HeapFree(GetProcessHeap(),0,edited);if(teams)HeapFree(GetProcessHeap(),0,teams);
    if(team_by_player)HeapFree(GetProcessHeap(),0,team_by_player);if(number_by_player)HeapFree(GetProcessHeap(),0,number_by_player);if(position_by_player)HeapFree(GetProcessHeap(),0,position_by_player);
    if(club_team)HeapFree(GetProcessHeap(),0,club_team);if(valid_league)HeapFree(GetProcessHeap(),0,valid_league);
}
static void native_search_publish_detail(int player,int team,int number,int position,unsigned serial){
    PlayerSearchDetail detail;unsigned int colors[3]={0};int captain=0,found=0;char name[128]={0};memset(&detail,0,sizeof(detail));
    if(player>0&&player<=524287&&native_club_player_row(team,player,&detail.player)){
        found=1;detail.player.team_id=team;detail.player.number=number;detail.player.squad_position=position;
        if(team>0){if(native_club_player_identity(team,colors,&captain)){memcpy(detail.player.club_colors,colors,sizeof(colors));detail.player.club_colors_valid=1;detail.player.captain=captain==player;}
            native_team_name(team,name,sizeof(name));if(!name[0])native_team_name_query(team,name,sizeof(name));}
        lstrcpynA(detail.team_name,name,sizeof(detail.team_name));
    }
    player_search_screen_publish_detail(found?&detail:NULL,serial,found);
}
static void native_player_search_refresh(void){
    unsigned index_serial=0,detail_serial=0;int player=0,team=0,number=-1,position=-1;
    if(player_search_screen_take_detail_request(&player,&team,&number,&position,&detail_serial))native_search_publish_detail(player,team,number,position,detail_serial);
    if(player_search_screen_take_index_request(&index_serial))native_search_publish_catalog(index_serial);
}
