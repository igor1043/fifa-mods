/* Executed only at the existing FIFA provider boundary. Present requests a
 * refresh, never invokes a native query. Every result is copied and freed. */
typedef struct BrowserLeague {int valid,nation;char name[128];} BrowserLeague;
static void native_clubs_browser_refresh(void){
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,ok=0,n=0,i=0,club=0;unsigned token=0;
    int catalog=clubs_browser_take_catalog_request(),roster=clubs_browser_take_roster_request(&club,&token);
    ClubBrowserRow*rows=NULL;BrowserLeague*leagues=NULL;int*members=NULL;char(*countries)[128]=NULL;SIZE_T written=0;
    void*backend=NULL;
    if(!catalog&&!roster)return;
    if(!native_names||!is_readable_range(native_names,sizeof(void*)))goto done;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))goto done;
    if(catalog){
        rows=(ClubBrowserRow*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,CLUB_BROWSER_CAPACITY*sizeof(*rows));
        leagues=(BrowserLeague*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,4097*sizeof(*leagues));
        members=(int*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,200001*sizeof(*members));
        countries=(char(*)[128])HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,256*128);
        if(!rows||!leagues||!members||!countries)goto done;
        __try {__try {
            void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"leagues");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
            if(n<0||n>4096)__leave;
            for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"leagueid"),nation=native_name_db.integer(&result,i,"countryid");
                int level=native_name_db.integer(&result,i,"level");const char*name=native_name_db.string(&result,i,"leaguename");
                /* 78 is the game's national-team grouping, not a club league. */
                if(id<=0||id>4096||id==78||nation<0||nation>255||level<1||level>7)continue;
                leagues[id].valid=1;leagues[id].nation=nation;if(name)lstrcpynA(leagues[id].name,name,128);}
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            native_name_db.query_init(query,1,"nations");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
            if(n<0||n>3000)__leave;
            for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"nationid");const char*name=native_name_db.string(&result,i,"nationname");if(id>0&&id<256&&name)lstrcpynA(countries[id],name,128);}
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            native_name_db.query_init(query,1,"leagueteamlinks");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
            if(n<0||n>50000)__leave;
            for(i=0;i<n;++i){int team=native_name_db.integer(&result,i,"teamid"),league=native_name_db.integer(&result,i,"leagueid");
                if(native_name_db.integer(&result,i,"secondarytable")||team<=0||team>200000||league<=0||league>4096||!leagues[league].valid)continue;
                if(!members[team])members[team]=league;else if(members[team]!=league)members[team]=-1;}
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            native_name_db.query_init(query,1,"teams");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
            if(n<0||n>CLUB_BROWSER_CAPACITY)__leave;
            for(i=0;i<n;++i){int team=native_name_db.integer(&result,i,"teamid"),league;ClubBrowserRow*out;const char*name;
                if(team<=0||team>200000||(league=members[team])<=0)continue;
                name=native_name_db.string(&result,i,"teamname");if(!name||!*name)continue;
                out=rows+written++;out->team=team;out->league=league;out->nation=leagues[league].nation;
                out->attack=native_name_db.integer(&result,i,"attackrating");out->midfield=native_name_db.integer(&result,i,"midfieldrating");out->defense=native_name_db.integer(&result,i,"defenserating");
                out->prestige=native_name_db.integer(&result,i,"internationalprestige");
                lstrcpynA(out->name,name,128);lstrcpynA(out->league_name,leagues[league].name,128);lstrcpynA(out->nation_name,countries[out->nation],128);
            }ok=1;
        }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
        __except(EXCEPTION_EXECUTE_HANDLER){ok=0;written=0;}
    }
done:
    if(catalog)clubs_browser_publish_catalog(ok?rows:NULL,ok?written:0,native_club);
    if(rows)HeapFree(GetProcessHeap(),0,rows);if(leagues)HeapFree(GetProcessHeap(),0,leagues);
    if(members)HeapFree(GetProcessHeap(),0,members);if(countries)HeapFree(GetProcessHeap(),0,countries);
    if(roster){ClubPlayerRow players[CLUB_PLAYER_CAPACITY];NativeClubRosterLink links[CLUB_PLAYER_CAPACITY];int valid=0,captain=0,colors_valid=0;
        unsigned int colors[3]={0};SIZE_T count=0,k,loaded=0;char name[128]={0};
        count=native_club_roster_links(club,links,CLUB_PLAYER_CAPACITY,&valid);
        for(k=0;k<count;++k)if(native_club_player_row(club,links[k].player,players+loaded)){
            players[loaded].squad_position=links[k].position;players[loaded].number=links[k].number;++loaded;}
        if(valid&&loaded==count){colors_valid=native_club_player_identity(club,colors,&captain);
            for(k=0;k<loaded;++k){players[k].club_colors_valid=colors_valid;memcpy(players[k].club_colors,colors,sizeof(colors));players[k].captain=captain>0&&players[k].player_id==captain;}
            native_team_name(club,name,sizeof(name));native_profile_league_refresh(club);
            coach_profile_publish_team_fixtures(club,name,native_view.fixtures,native_view.fixture_count,native_view.date);
        }else loaded=0;
        clubs_browser_publish_roster(club,token,players,loaded,name);
    }
}
