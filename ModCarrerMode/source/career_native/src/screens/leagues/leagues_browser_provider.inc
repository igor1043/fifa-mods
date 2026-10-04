/* Copies the currently loaded career season into the read-only leagues UI.
 * Called only from native_prepare(), at FIFA's existing statistics provider
 * boundary. The render thread never queries native services or save memory. */
typedef struct LeagueStageCandidate {int stage,count,teams[LEAGUE_BROWSER_TABLE_CAPACITY];} LeagueStageCandidate;
typedef struct LeagueRawStat {int player,team,competition,goals,assists;} LeagueRawStat;
static int league_browser_team_in(const ClubBrowserRow*rows,size_t count,int league,int team){size_t i;for(i=0;i<count;++i)if(rows[i].league==league&&rows[i].team==team)return 1;return 0;}
static const ClubBrowserRow*league_browser_team_row(const ClubBrowserRow*rows,size_t count,int league,int team){size_t i;for(i=0;i<count;++i)if(rows[i].league==league&&rows[i].team==team)return rows+i;return NULL;}
static int league_browser_team_nation(const ClubBrowserRow*rows,size_t count,int team){size_t i;for(i=0;i<count;++i)if(rows[i].team==team)return rows[i].nation;return -1;}
static int league_browser_raw_order(const void*a,const void*b){const LeagueRawStat*x=(const LeagueRawStat*)a,*y=(const LeagueRawStat*)b;
    if(x->player!=y->player)return (x->player>y->player)-(x->player<y->player);if(x->team!=y->team)return (x->team>y->team)-(x->team<y->team);
    if(x->competition!=y->competition)return (x->competition>y->competition)-(x->competition<y->competition);return 0;}
static int league_browser_table_order(const void*a,const void*b){const LeagueBrowserTableRow*x=(const LeagueBrowserTableRow*)a,*y=(const LeagueBrowserTableRow*)b;
    if(x->points!=y->points)return x->points>y->points?-1:1;if(x->won!=y->won)return x->won>y->won?-1:1;
    int xd=x->goals_for-x->goals_against,yd=y->goals_for-y->goals_against;if(xd!=yd)return xd>yd?-1:1;
    if(x->goals_for!=y->goals_for)return x->goals_for>y->goals_for?-1:1;return x->team-y->team;}
static int league_browser_cup_order(const void*a,const void*b){const LeagueBrowserCup*x=(const LeagueBrowserCup*)a,*y=(const LeagueBrowserCup*)b;return x->date-y->date;}
static void league_browser_insert_leader(LeagueBrowserLeader*out,size_t*count,const LeagueBrowserLeader*item){size_t i,j;
    for(i=0;i<*count&&out[i].value>=item->value;++i){}if(i>=LEAGUE_BROWSER_LEADER_CAPACITY)return;
    if(*count<LEAGUE_BROWSER_LEADER_CAPACITY)++*count;for(j=*count-1;j>i;--j)out[j]=out[j-1];out[i]=*item;}
static int league_browser_is_database_league(int root,const FceModel*model,const ClubBrowserRow*catalog,size_t count){size_t i,j;
    for(i=0;i<model->node_count;++i){const FceCompNode*n=model->nodes+i;if(n->type!=3||n->id!=root)continue;
        for(j=0;j<count;++j)if(catalog[j].league==n->id||catalog[j].league==n->asset)return 1;return 0;}return 0;}
static void native_leagues_browser_refresh(void){
    int league=0,nation=-1,root=-1,stage=-1,date=native_view.date;size_t catalog_count=0,standing_count=0,i,j,k;unsigned catalog_revision=0;
    ClubBrowserRow*catalog=NULL;LeagueBrowserSnapshot snapshot;LeagueStageCandidate stages[32];size_t stage_count=0;int catalog_ok=0;
    LeagueRawStat*raw=NULL;size_t raw_count=0,unique_count=0;
    if(!leagues_browser_take_data_request(&league))return;memset(&snapshot,0,sizeof(snapshot));memset(stages,0,sizeof(stages));
    catalog_count=clubs_browser_copy_catalog(NULL,0,&catalog_revision);if(catalog_count&&catalog_count<=CLUB_BROWSER_CAPACITY){
        catalog=(ClubBrowserRow*)HeapAlloc(GetProcessHeap(),0,catalog_count*sizeof(*catalog));if(catalog){catalog_ok=clubs_browser_copy_catalog(catalog,catalog_count,&catalog_revision)>=catalog_count;}}
    if(!catalog_ok||!catalog||!native_view.nodes||!native_view.standings)goto done;
    for(i=0;i<catalog_count;++i)if(catalog[i].league==league){nation=catalog[i].nation;lstrcpynA(snapshot.league_name,catalog[i].league_name,sizeof(snapshot.league_name));lstrcpynA(snapshot.nation_name,catalog[i].nation_name,sizeof(snapshot.nation_name));break;}
    if(nation<0)goto done;snapshot.league=league;snapshot.nation=nation;snapshot.date=date;
    /* Match the competition root by its stable database ID or installed
     * league-logo asset ID; never infer a league from a club-name string. */
    for(i=0;i<native_view.node_count;++i){const FceCompNode*n=native_view.nodes+i;if(n->type==3&&(n->id==league||n->asset==league)){root=n->id;break;}}
    if(root>0){
        for(i=0;i<native_view.standing_count;++i){const FceStanding*s=native_view.standings+i;int object;
            if(s->team<=0||fce_model_ancestor(&native_view,s->competition_object,3)!=root||!league_browser_team_in(catalog,catalog_count,league,s->team))continue;
            object=s->competition_object;for(j=0;j<stage_count&&stages[j].stage!=object;++j){}if(j==stage_count&&stage_count<sizeof(stages)/sizeof(stages[0])){stages[j].stage=object;++stage_count;}
            if(j>=stage_count)continue;for(k=0;k<(size_t)stages[j].count&&stages[j].teams[k]!=s->team;++k){}if(k==(size_t)stages[j].count&&stages[j].count<LEAGUE_BROWSER_TABLE_CAPACITY)stages[j].teams[stages[j].count++]=s->team;
        }
        /* Explicitly prefer the largest stage; a direct root table wins ties. */
        {int best=-1,best_count=0;for(i=0;i<stage_count;++i)if(stages[i].count>best_count||(stages[i].count==best_count&&stages[i].stage==root)){best=(int)i;best_count=stages[i].count;}if(best>=0)stage=stages[best].stage;}
        if(stage>0)for(i=0;i<native_view.standing_count&&snapshot.table_count<LEAGUE_BROWSER_TABLE_CAPACITY;++i){const FceStanding*s=native_view.standings+i;const ClubBrowserRow*club;
            if(s->competition_object!=stage||!league_browser_team_in(catalog,catalog_count,league,s->team))continue;
            for(j=0;j<snapshot.table_count&&snapshot.table[j].team!=s->team;++j){}if(j<snapshot.table_count&&snapshot.table[j].played>=(int)s->played)continue;
            club=league_browser_team_row(catalog,catalog_count,league,s->team);if(!club)continue;LeagueBrowserTableRow*r=snapshot.table+j;memset(r,0,sizeof(*r));
            r->team=s->team;r->played=(int)s->played;r->won=(int)(s->home_wins+s->away_wins);r->drawn=(int)(s->home_draws+s->away_draws);r->lost=(int)(s->home_losses+s->away_losses);r->points=r->won*3+r->drawn;lstrcpynA(r->name,club->name,sizeof(r->name));
            if(j==snapshot.table_count)++snapshot.table_count;
        }
        for(i=0;i<native_view.fixture_count;++i){const FceFixture*f=native_view.fixtures+i;if(!f->played_raw||(fce_date_valid(date)&&f->date_raw>date)||native_fixture_root(f)!=root||!native_fixture_stage_matches(f,stage))continue;
            for(j=0;j<snapshot.table_count;++j){LeagueBrowserTableRow*r=snapshot.table+j;if(r->team==f->home){r->goals_for+=f->home_score;r->goals_against+=f->away_score;}else if(r->team==f->away){r->goals_for+=f->away_score;r->goals_against+=f->home_score;}}}
        if(snapshot.table_count>1){qsort(snapshot.table,snapshot.table_count,sizeof(snapshot.table[0]),league_browser_table_order);for(i=0;i<snapshot.table_count;++i)snapshot.table[i].rank=(int)i+1;}
        snapshot.table_available=snapshot.table_count>=3;
        /* A cup is current only when the loaded calendar contains a future
         * fixture for a club belonging to the selected country's catalog. */
        {LeagueBrowserCup candidates[96];size_t cup_count=0;for(i=0;i<native_view.fixture_count&&cup_count<sizeof(candidates)/sizeof(candidates[0]);++i){const FceFixture*f=native_view.fixtures+i;int cup_root=native_fixture_root(f),asset,found=0;
                if(f->played_raw||cup_root<=0||cup_root==root||(fce_date_valid(date)&&f->date_raw<date)||
                   (league_browser_team_nation(catalog,catalog_count,f->home)!=nation&&league_browser_team_nation(catalog,catalog_count,f->away)!=nation)||
                   league_browser_is_database_league(cup_root,&native_view,catalog,catalog_count))continue;
                for(j=0;j<cup_count;++j)if(candidates[j].competition==cup_root){found=1;break;}if(found)continue;
                asset=native_logo(cup_root);candidates[cup_count].competition=cup_root;candidates[cup_count].asset=asset;candidates[cup_count].date=f->date_raw;++cup_count;}
            qsort(candidates,cup_count,sizeof(candidates[0]),league_browser_cup_order);snapshot.cup_count=cup_count<LEAGUE_BROWSER_CUP_CAPACITY?cup_count:LEAGUE_BROWSER_CUP_CAPACITY;
            memcpy(snapshot.cups,candidates,snapshot.cup_count*sizeof(snapshot.cups[0]));snapshot.cups_available=snapshot.cup_count>0;}
        if(native_view.stat_count&&native_view.stat_count<=65536){raw=(LeagueRawStat*)HeapAlloc(GetProcessHeap(),0,native_view.stat_count*sizeof(*raw));if(raw){
            for(i=0;i<native_view.stat_count;++i){const FceStat*s=native_view.stats+i;if(s->player<=0||s->team<=0||!league_browser_team_in(catalog,catalog_count,league,s->team)||fce_model_ancestor(&native_view,s->competition,3)!=root)continue;
                raw[raw_count].player=s->player;raw[raw_count].team=s->team;raw[raw_count].competition=s->competition;raw[raw_count].goals=s->goals;raw[raw_count].assists=s->assists;++raw_count;}
            qsort(raw,raw_count,sizeof(*raw),league_browser_raw_order);
            for(i=0;i<raw_count;){LeagueRawStat current=raw[i];j=i+1;while(j<raw_count&&raw[j].player==current.player&&raw[j].team==current.team&&raw[j].competition==current.competition){if(raw[j].goals>current.goals)current.goals=raw[j].goals;if(raw[j].assists>current.assists)current.assists=raw[j].assists;++j;}raw[unique_count++]=current;i=j;}
            for(i=0;i<unique_count;){size_t end=i;int player=raw[i].player,root_goals=0,root_assists=0,child_goals=0,child_assists=0,best_team=raw[i].team,best_value=-1,has_root=0;LeagueBrowserLeader g,a;
                while(end<unique_count&&raw[end].player==player){if(raw[end].competition==root){has_root=1;root_goals+=raw[end].goals;root_assists+=raw[end].assists;if(raw[end].goals+raw[end].assists>best_value){best_value=raw[end].goals+raw[end].assists;best_team=raw[end].team;}}
                    else{child_goals+=raw[end].goals;child_assists+=raw[end].assists;if(raw[end].goals+raw[end].assists>best_value){best_value=raw[end].goals+raw[end].assists;best_team=raw[end].team;}}++end;}
                memset(&g,0,sizeof(g));g.player=player;g.team=best_team;g.value=has_root?root_goals:child_goals;native_player_label(player,g.name,sizeof(g.name));native_team_name(best_team,g.team_name,sizeof(g.team_name));
                if(g.value>0)league_browser_insert_leader(snapshot.goals,&snapshot.goals_count,&g);
                a=g;a.value=has_root?root_assists:child_assists;if(a.value>0)league_browser_insert_leader(snapshot.assists,&snapshot.assists_count,&a);i=end;}
            snapshot.goals_available=snapshot.goals_count>0;snapshot.assists_available=snapshot.assists_count>0;
        }}
    }
done:
    if(catalog){for(i=0;i<catalog_count;++i)if(catalog[i].league==league){snapshot.league=league;snapshot.nation=catalog[i].nation;lstrcpynA(snapshot.league_name,catalog[i].league_name,sizeof(snapshot.league_name));lstrcpynA(snapshot.nation_name,catalog[i].nation_name,sizeof(snapshot.nation_name));break;}}
    snapshot.date=date;leagues_browser_publish(&snapshot);if(raw)HeapFree(GetProcessHeap(),0,raw);if(catalog)HeapFree(GetProcessHeap(),0,catalog);
}
