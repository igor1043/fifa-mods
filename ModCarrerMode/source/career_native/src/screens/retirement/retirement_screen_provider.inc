/* Runs only on FIFA's existing provider thread after a screen refresh request.
 * Owned rows cross to ImGui; no DB pointer or borrowed result is retained. */
static int retirement_name_compare(const void *a,const void *b) {
    unsigned int x=((const RetirementUiPlayer*)a)->id,y=((const RetirementUiPlayer*)b)->id;
    return x<y?-1:x>y?1:0;
}
#include "../../features/ranking/global_ranking.h"
static void native_retirement_profile_refresh(void) {
    unsigned id=0;int requested_club=0,requested_date=0,club=0,valid=0,captain=0;
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,n=0,i;void*backend=NULL;
    ClubPlayerRow row={0};char name[128]={0};FceGlobalRankedClub*clubs=NULL;size_t club_count=0;
    if(!retirement_profile_take_request(&id,&requested_club,&requested_date))return;
    if(!id||requested_club!=native_club||requested_date!=native_view.date||!native_names||!is_readable_range(native_names,sizeof(void*)))goto done;
    native_name_db_bind();backend=*(void**)native_names;
    if(!backend||!is_readable_range(backend,sizeof(void*)))goto done;
    if(fce_global_ranking_build_all(&native_view,&clubs,&club_count)!=FCE_OK)goto done;
    __try {
        __try {
            void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
            /* players has NO internationalteamid field in FIFA 16. Asking
             * the native integer accessor for it dereferences a null field
             * (confirmed in crash.dmp). Recognize clubs using the owned club
             * catalog instead; national-team links never belong to that set. */
            native_name_db.query_init(query,1,"teamplayerlinks");q=1;native_name_db.where_int(query,"playerid",0,(int)id);
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
            if(n>=0&&n<=32)for(i=0;i<n;++i){size_t j;int team=native_name_db.integer(&result,i,"teamid");
                if(team<=0)continue;
                for(j=0;j<club_count&&clubs[j].team!=team;++j){}if(j==club_count&&team!=native_club)continue;
                if(club&&club!=team){club=-1;break;}club=team;}
        }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}
    }__except(EXCEPTION_EXECUTE_HANDLER){club=0;}
    if(club<0)club=0; /* Ambiguous/free agent: attributes yes, never a borrowed club kit. */
    valid=native_club_player_row(club,(int)id,&row);
    if(valid&&club>0){NativeClubRosterLink links[CLUB_PLAYER_CAPACITY];int ok=0;SIZE_T count,j;
        row.club_colors_valid=native_club_player_identity(club,row.club_colors,&captain);row.captain=captain==(int)id;
        count=native_club_roster_links(club,links,CLUB_PLAYER_CAPACITY,&ok);
        for(j=0;j<count;++j)if(links[j].player==(int)id){row.number=links[j].number;row.squad_position=links[j].position;break;}
        native_team_name(club,name,sizeof(name));native_profile_league_refresh(club);}
done:
    row.player_id=(int)id;
    retirement_profile_publish(&row,name,requested_club,requested_date,valid);fce_global_ranking_free(clubs);
}
static void native_retirement_refresh(void) {
    RetirementUiPlayer *rows=NULL,*edited=NULL;unsigned char *club_ids=NULL,*club_teams=NULL;int *player_clubs=NULL;
    FceGlobalRankedClub *clubs=NULL;size_t club_count=0,j;
    unsigned __int64 query[7]={0},result=0;int query_ready=0,result_ready=0,valid=0,n=0,i;
    SIZE_T count=0,edited_count=0;void *backend;
    native_retirement_profile_refresh();
    if(!retirement_screen_take_refresh())return;
    if(native_club<=0||!native_names||!is_readable_range(native_names,sizeof(void*)))goto finish;
    native_name_db_bind();backend=*(void**)native_names;
    if(!backend||!is_readable_range(backend,sizeof(void*)))goto finish;
    club_ids=(unsigned char*)calloc(1U<<19U,1);if(!club_ids)goto finish;
    player_clubs=(int*)calloc(1U<<19U,sizeof(int));club_teams=(unsigned char*)calloc(200001,1);if(!player_clubs||!club_teams)goto finish;
    if(fce_global_ranking_build_all(&native_view,&clubs,&club_count)==FCE_OK)for(j=0;j<club_count;++j)if(clubs[j].team>0&&clubs[j].team<=200000)club_teams[clubs[j].team]=1;
    if(native_club>0&&native_club<=200000)club_teams[native_club]=1;
    __try {
        __try {
            void (*execute)(void*,void*,void*)=(void (*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"teamplayerlinks");query_ready=1;
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            n=native_name_db.count(&result);if(n<0||n>250000) __leave;
            for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"playerid"),team=native_name_db.integer(&result,i,"teamid");
                if(id<=0||id>=(1<<19)||team<=0||team>200000||!club_teams[team])continue;
                if(team==native_club)club_ids[id]=1;
                if(!player_clubs[id])player_clubs[id]=team;else if(player_clubs[id]!=team)player_clubs[id]=-1;}
            native_name_db.result_free(&result);result_ready=0;native_name_db.query_free(query);query_ready=0;
            native_name_db.query_init(query,1,"editedplayernames");query_ready=1;
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            n=native_name_db.count(&result);if(n<0||n>60000) __leave;
            if(n){edited=(RetirementUiPlayer*)calloc((size_t)n,sizeof(*edited));if(!edited)__leave;}
            for(i=0;i<n;++i){static const char*fields[]={"commonname","playerjerseyname","surname","firstname"};unsigned j;
                int id=native_name_db.integer(&result,i,"playerid");if(id<=0||id>=(1<<19))continue;
                edited[edited_count].id=(unsigned)id;
                for(j=0;j<4;++j){const char*name=native_name_db.string(&result,i,fields[j]);if(name&&*name){lstrcpynA(edited[edited_count].name,name,128);break;}}
                ++edited_count;
            }
            if(edited_count)qsort(edited,edited_count,sizeof(*edited),retirement_name_compare);
            native_name_db.result_free(&result);result_ready=0;native_name_db.query_free(query);query_ready=0;
            native_name_db.query_init(query,1,"players");query_ready=1;
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            n=native_name_db.count(&result);if(n<=0||n>60000)__leave;
            rows=(RetirementUiPlayer*)calloc((size_t)n,sizeof(*rows));if(!rows)__leave;
            for(i=0;i<n;++i){RetirementUiPlayer key={0},*name;int id=native_name_db.integer(&result,i,"playerid");unsigned j;
                static const char*fields[]={"commonnameid","playerjerseynameid","lastnameid","firstnameid"};
                if(id<=0||id>=(1<<19)||native_name_db.integer(&result,i,"isretiring")!=1)continue;
                rows[count].id=(unsigned)id;rows[count].in_club=club_ids[id]?1:0;
                rows[count].team_id=player_clubs[id]>0?player_clubs[id]:0;
                rows[count].retiring=native_name_db.integer(&result,i,"isretiring");
                rows[count].age=native_squad_player_age(native_name_db.integer(&result,i,"birthdate"),native_view.date);
                key.id=(unsigned)id;name=edited_count?(RetirementUiPlayer*)bsearch(&key,edited,edited_count,sizeof(*edited),retirement_name_compare):NULL;
                if(name&&name->name[0])lstrcpynA(rows[count].name,name->name,128);
                for(j=0;j<4&&!rows[count].name[0];++j){int name_id=native_name_db.integer(&result,i,fields[j]);
                    if(name_id>0){int item[2]={0,name_id};g_resolve_player_name(item,native_names,rows[count].name,128);rows[count].name[127]=0;}}
                if(!rows[count].name[0])snprintf(rows[count].name,128,"Jogador %u",rows[count].id);++count;
            }valid=1;
        } __finally {if(result_ready)native_name_db.result_free(&result);if(query_ready)native_name_db.query_free(query);}
    } __except(EXCEPTION_EXECUTE_HANDLER){valid=0;count=0;}
finish:
    /* Resolve club labels only after freeing the active DB query/result. */
    if(valid)for(j=0;j<count;++j)if(rows[j].team_id>0){size_t k;
        for(k=0;k<j&&rows[k].team_id!=rows[j].team_id;++k){}
        if(k<j)lstrcpynA(rows[j].club_name,rows[k].club_name,128);else native_team_name(rows[j].team_id,rows[j].club_name,128);}
    retirement_screen_publish(rows,count,native_club,native_view.date,valid);
    free(rows);free(edited);free(club_ids);free(player_clubs);free(club_teams);fce_global_ranking_free(clubs);
}
