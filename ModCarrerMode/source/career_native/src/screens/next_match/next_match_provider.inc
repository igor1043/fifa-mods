/* Same FIFA provider thread as the existing next-match card. Read-only,
 * copied rows, no asynchronous native pointers and no guesses at match actors. */
static void native_next_formation(int team,char*out,size_t size) {
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,id=-1;void*backend;
    if(!out||!size)return;out[0]=0;
    if(!native_names||!is_readable_range(native_names,sizeof(void*)))return;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))return;
    __try {
        __try {
            void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"teamformationteamstylelinks");q=1;native_name_db.where_int(query,"teamid",0,team);
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1)id=native_name_db.integer(&result,0,"formationid");
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            if(id<0||id>2047)return;
            native_name_db.query_init(query,1,"formations");q=1;native_name_db.where_int(query,"formationid",0,id);
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1){const char*name=native_name_db.string(&result,0,"formationname");
                if(name&&is_readable_range(name,1)&&name[0]&&name[0]!='#')lstrcpynA(out,name,(int)size);}
        }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}
    }__except(EXCEPTION_EXECUTE_HANDLER){out[0]=0;}
}
static void native_next_details_refresh(void) {
    NextMatchSnapshot snapshot={0};NativeClubRosterLink links[CLUB_PLAYER_CAPACITY];
    FceCompetition competition;int s,competition_id=0;
    if(!next_match_take_refresh())return;
    if(!g_next_match_fixture_valid||native_club<=0||!native_names){next_match_publish(&snapshot);return;}
    snapshot.valid=1;snapshot.fixture=g_next_match_fixture.id;snapshot.date=g_next_match_fixture.date_raw;
    snapshot.time=-1;
    {char time[16];if(fce_format_time(g_next_match_fixture.time_raw,time,sizeof(time))) {int hour=0,minute=0;
        if(sscanf(time,"%d:%d",&hour,&minute)==2&&hour>=0&&hour<24&&minute>=0&&minute<60)snapshot.time=hour*100+minute;}}
    if(fce_resolve_competition(native_view.nodes,native_view.node_count,g_next_match_fixture.competition_object,&competition)==FCE_OK) {
        competition_id=competition.competition;
    }
    if(!snapshot.competition[0])lstrcpynA(snapshot.competition,"Competição da carreira",sizeof(snapshot.competition));
    snapshot.sides[0].team=g_next_match_fixture.home;snapshot.sides[1].team=g_next_match_fixture.away;
    for(s=0;s<2;++s){NextMatchSide*side=snapshot.sides+s;unsigned int colors[3]={0};int colors_valid=0,captain=0,valid=0;SIZE_T count,i;
        count=native_club_roster_links(side->team,links,CLUB_PLAYER_CAPACITY,&valid);
        for(i=0;i<count;++i)if(native_club_player_row(side->team,links[i].player,side->rows+side->count)) {
            side->rows[side->count].number=links[i].number;side->rows[side->count].squad_position=links[i].position;++side->count;
        }
        side->roster_valid=valid&&side->count==(int)count;
        colors_valid=native_club_player_identity(side->team,colors,&captain);
        for(i=0;i<(SIZE_T)side->count;++i){side->rows[i].club_colors_valid=colors_valid;memcpy(side->rows[i].club_colors,colors,sizeof(colors));side->rows[i].captain=captain>0&&side->rows[i].player_id==captain;}
        native_team_name(side->team,side->name,sizeof(side->name));native_game_manager_fallback(side->team,side->manager,sizeof(side->manager));
        native_next_formation(side->team,side->formation,sizeof(side->formation));
        if(!side->formation[0]&&side->roster_valid){int roles[3]={0},field=0,keepers=0;
            for(i=0;i<(SIZE_T)side->count;++i){int p=side->rows[i].squad_position;if(p<0||p>=28)continue;++field;if(p==0)++keepers;else ++roles[p<=8?0:p<=19?1:2];}
            if(field==11&&keepers==1)snprintf(side->formation,sizeof(side->formation),"%d-%d-%d (estimativa por posições)",roles[0],roles[1],roles[2]);}
    }
    {char label[64]={0},detail[160]={0},fallback_name[256]={0},fallback_key[256]={0};int cap=0,dom=0,intl=0;
        int override=native_next_match_stadium_config(&g_next_match_fixture,competition_id,snapshot.stadium_key,sizeof(snapshot.stadium_key));
        native_next_match_stadium(&g_next_match_fixture,competition_id,snapshot.stadium,sizeof(snapshot.stadium),label,sizeof(label),detail,sizeof(detail));
        if(native_game_stadium_fallback(g_next_match_fixture.home,fallback_name,sizeof(fallback_name),&cap,fallback_key,sizeof(fallback_key),&dom,&intl)){
            if(!snapshot.stadium[0])lstrcpynA(snapshot.stadium,fallback_name,sizeof(snapshot.stadium));
            if(!override)lstrcpynA(snapshot.stadium_key,fallback_key,sizeof(snapshot.stadium_key));
            if(!override||!lstrcmpiA(snapshot.stadium_key,fallback_key))snapshot.capacity=cap;
        }
        if(detail[0]){snapshot.venue_pending=1;lstrcpynA(snapshot.venue_note,"Local ainda será escolhido ao iniciar a partida. Imagem representativa da primeira opção.",sizeof(snapshot.venue_note));snapshot.capacity=0;}
        snapshot.attendance=crowd_runtime_attendance_percent();
    }
    next_match_publish(&snapshot);
}
