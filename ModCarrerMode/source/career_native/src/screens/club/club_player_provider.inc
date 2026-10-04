/* Read-only capture on the existing FIFA provider thread. No native object or
 * database result crosses into the renderer/asset worker, and no save is edited. */
static int native_club_player_row(int club,int player,ClubPlayerRow *out) {
    unsigned __int64 query[7]={0},result=0;
    int query_ready=0,result_ready=0,found=0;size_t i;
    void *backend;
    static const struct {const char *name;size_t offset;} appearance[]={
        {"headtypecode",offsetof(ClubPlayerRow,head_type)},
        {"headclasscode",offsetof(ClubPlayerRow,head_class)},
        {"hairtypecode",offsetof(ClubPlayerRow,hair_type)},
        {"haircolorcode",offsetof(ClubPlayerRow,hair_color)},
        {"skintonecode",offsetof(ClubPlayerRow,skin_tone)},
        {"skintypecode",offsetof(ClubPlayerRow,skin_type)},
        {"facialhairtypecode",offsetof(ClubPlayerRow,facial_hair_type)},
        {"facialhaircolorcode",offsetof(ClubPlayerRow,facial_hair_color)},
        {"shoetypecode",offsetof(ClubPlayerRow,shoe_type)},
        {"shoedesigncode",offsetof(ClubPlayerRow,shoe_design)},
        {"gender",offsetof(ClubPlayerRow,gender)},
        {"height",offsetof(ClubPlayerRow,height)},
        {"weight",offsetof(ClubPlayerRow,weight)},
        {"bodytypecode",offsetof(ClubPlayerRow,body_type)},
        {"eyecolorcode",offsetof(ClubPlayerRow,eye_color)},
        {"eyebrowcode",offsetof(ClubPlayerRow,eyebrow)},
        {"sideburnscode",offsetof(ClubPlayerRow,sideburns)},
        {"jerseysleevelengthcode",offsetof(ClubPlayerRow,sleeve_length)},
        {"jerseyfit",offsetof(ClubPlayerRow,jersey_fit)},
        {"jerseystylecode",offsetof(ClubPlayerRow,jersey_style)},
        {"socklengthcode",offsetof(ClubPlayerRow,sock_length)},
        {"shortstyle",offsetof(ClubPlayerRow,short_style)},
        {"gkglovetypecode",offsetof(ClubPlayerRow,glove_type)}
    };
    if(!out || player<=0 || !native_names || !is_readable_range(native_names,sizeof(void *)))return 0;
    native_name_db_bind();backend=*(void **)native_names;
    if(!backend || !is_readable_range(backend,sizeof(void *)))return 0;
    memset(out,0,sizeof(*out));out->player_id=player;out->team_id=club;out->squad_position=-1;
    out->birthdate_raw=out->join_team_date_raw=out->career_date=out->retiring=out->weekly_wage=-1;
    out->position=out->age=out->overall=-1;
    for(i=0;i<3;++i)out->secondary_positions[i]=-1;
    for(i=0;i<CLUB_PLAYER_ATTRIBUTE_COUNT;++i)out->attributes[i]=-1;
    __try {
        __try {
            void (*execute)(void *,void *,void *)=
                (void (*)(void *,void *,void *))(*(void ***)backend)[1];
            native_name_db.query_init(query,1,"players");query_ready=1;
            native_name_db.where_int(query,"playerid",0,player);
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1) {
                int birthdate=native_name_db.integer(&result,0,"birthdate");
                out->age=native_squad_player_age(birthdate,native_view.date);
                out->birthdate_raw=birthdate>=0&&birthdate<=1048575?birthdate:-1;
                out->join_team_date_raw=native_name_db.integer(&result,0,"playerjointeamdate");
                if(out->join_team_date_raw<0||out->join_team_date_raw>1048575)out->join_team_date_raw=-1;
                out->retiring=native_name_db.integer(&result,0,"isretiring");
                if(out->retiring!=0&&out->retiring!=1)out->retiring=-1;
                out->career_data_valid=1;
                out->career_date=fce_date_valid(native_view.date)?native_view.date:-1;
                player_profile_publish_birthdate(player,birthdate,native_view.date);
                out->position=native_name_db.integer(&result,0,"preferredposition1");
                out->secondary_positions[0]=native_name_db.integer(&result,0,"preferredposition2");
                out->secondary_positions[1]=native_name_db.integer(&result,0,"preferredposition3");
                out->secondary_positions[2]=native_name_db.integer(&result,0,"preferredposition4");
                out->secondary_positions_valid=1;
                out->overall=native_name_db.integer(&result,0,"overallrating");
                player_profile_publish_nationality(player,native_name_db.integer(&result,0,"nationality"));
                player_profile_publish_foot(player,native_name_db.integer(&result,0,"preferredfoot"));
                for(i=0;i<sizeof(appearance)/sizeof(appearance[0]);++i)
                    *(int *)((char *)out+appearance[i].offset)=native_name_db.integer(&result,0,appearance[i].name);
                for(i=0;i<CLUB_PLAYER_ATTRIBUTE_COUNT;++i)
                    out->attributes[i]=native_name_db.integer(&result,0,club_player_attribute_field(i));
                found=1;
            }
        } __finally {
            if(result_ready)native_name_db.result_free(&result);
            if(query_ready)native_name_db.query_free(query);
        }
    } __except(EXCEPTION_EXECUTE_HANDLER) {found=0;}
    if(found)native_player_label(player,out->name,sizeof(out->name));
    return found;
}
/* Capture one unambiguous current-club wage per player. Contract negotiations
 * can leave multiple rows for the same player/team; in that case we suppress
 * the figure rather than treating an offer or demand as the signed wage. */
static void native_club_player_wages(int club,ClubPlayerRow *rows,size_t count) {
    unsigned __int64 query[7]={0},result=0;int q=0,r=0;void*backend=NULL;
    int matches[CLUB_PLAYER_CAPACITY]={0},wages[CLUB_PLAYER_CAPACITY];size_t i;
    if(!rows||count>CLUB_PLAYER_CAPACITY||club<=0)return;
    for(i=0;i<count;++i){rows[i].weekly_wage=-1;wages[i]=-1;}
    if(!native_names||!is_readable_range(native_names,sizeof(void*)))return;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))return;
    __try {__try {
        void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
        native_name_db.query_init(query,1,"career_playercontract");q=1;
        native_name_db.where_int(query,"teamid",0,club);
        native_name_db.result_init(&result);r=1;execute(backend,query,&result);
        int n=native_name_db.count(&result);
        if(n>=0&&n<=10000)for(int row=0;row<n;++row){
            int id=native_name_db.integer(&result,row,"playerid"),wage=native_name_db.integer(&result,row,"wage");
            if(id<=0||wage<0||wage>1000000000)continue;
            for(i=0;i<count;++i)if(rows[i].player_id==id){++matches[i];wages[i]=wage;break;}
        }
    }__finally {if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){return;}
    for(i=0;i<count;++i)if(matches[i]==1)rows[i].weekly_wage=wages[i];
}
typedef struct NativeClubRosterLink {int player,position,number;} NativeClubRosterLink;
static SIZE_T native_club_roster_links(int club,NativeClubRosterLink *out,SIZE_T capacity,int *valid) {
    unsigned __int64 query[7]={0},result=0;int query_ready=0,result_ready=0,ok=0;SIZE_T count=0;void *backend;
    if(!valid)return 0;
    *valid=0;if(club<=0||!out||!capacity||!native_names||!is_readable_range(native_names,sizeof(void*)))return 0;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))return 0;
    __try {
        __try {
            void (*execute)(void*,void*,void*)=(void (*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"teamplayerlinks");query_ready=1;native_name_db.where_int(query,"teamid",0,club);
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            int n=native_name_db.count(&result);if(n>=0&&n<=512) {
                int i;for(i=0;i<n&&count<capacity;++i) {
                    int player=native_name_db.integer(&result,i,"playerid"),position=native_name_db.integer(&result,i,"position");SIZE_T j;
                    if(player<=0||player>524287)continue;
                    for(j=0;j<count&&out[j].player!=player;++j){}if(j<count)continue;
                    out[count].player=player;out[count].position=position>=0&&position<=33?position:-1;
                    out[count].number=native_name_db.integer(&result,i,"jerseynumber");++count;
                }ok=1;
            }
        } __finally {if(result_ready)native_name_db.result_free(&result);if(query_ready)native_name_db.query_free(query);}
    } __except(EXCEPTION_EXECUTE_HANDLER){count=0;ok=0;}
    *valid=ok;return count;
}
static int native_club_player_identity(int club,unsigned int *colors,int *captain_out) {
    unsigned __int64 query[7]={0},result=0;int query_ready=0,result_ready=0,valid=0;void *backend;
    static const char*fields[9]={"teamcolor1r","teamcolor1g","teamcolor1b",
        "teamcolor2r","teamcolor2g","teamcolor2b","teamcolor3r","teamcolor3g","teamcolor3b"};
    unsigned int value[3]={0};int i,captain=0;
    if(captain_out)*captain_out=0;
    if(!colors||!captain_out||club<=0||!native_names||!is_readable_range(native_names,sizeof(void*)))return 0;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))return 0;
    __try {
        __try {
            void (*execute)(void*,void*,void*)=(void (*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"teams");query_ready=1;native_name_db.where_int(query,"teamid",0,club);
            native_name_db.result_init(&result);result_ready=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1) {
                valid=1;for(i=0;i<9;++i) {int channel=native_name_db.integer(&result,0,fields[i]);
                    if(channel<0||channel>255){valid=0;break;}value[i/3]|=(unsigned int)channel<<(16-(i%3)*8);}
                captain=native_name_db.integer(&result,0,"captainid");
                if(captain<=0||captain>524287)captain=0;
            }
        } __finally {if(result_ready)native_name_db.result_free(&result);if(query_ready)native_name_db.query_free(query);}
    } __except(EXCEPTION_EXECUTE_HANDLER){valid=0;captain=0;}
    *captain_out=captain;
    if(valid)memcpy(colors,value,sizeof(value));return valid;
}
static void native_profile_league_refresh(int club) {
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,league=0,n=0,i,level=0,clubs[512]={0},members=0,matched=0;
    float strength=-1,sum=0;unsigned char seen[512]={0};char name[128]={0};void*backend=NULL;
    if(club<=0||!native_names||!is_readable_range(native_names,sizeof(void*)))return;
    native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*)))return;
    __try {__try {
        void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
        native_name_db.query_init(query,1,"leagueteamlinks");q=1;native_name_db.where_int(query,"teamid",0,club);
        native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
        if(n>=0&&n<=64)for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"leagueid");
            if(native_name_db.integer(&result,i,"secondarytable")||id<=0||id>4096)continue;
            if(league&&league!=id){league=0;break;}league=id;}
        native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
        if(league>0){native_name_db.query_init(query,1,"leagues");q=1;native_name_db.where_int(query,"leagueid",0,league);
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);
            if(native_name_db.count(&result)==1){const char*s=native_name_db.string(&result,0,"leaguename");if(s)lstrcpynA(name,s,sizeof(name));level=native_name_db.integer(&result,0,"level");}
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            if(level>=1&&level<=7){
                native_name_db.query_init(query,1,"leagueteamlinks");q=1;native_name_db.where_int(query,"leagueid",0,league);
                native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
                if(n>0&&n<=512)for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"teamid"),j;
                    if(native_name_db.integer(&result,i,"secondarytable")||id<=0||id>200000)continue;
                    for(j=0;j<members&&clubs[j]!=id;++j){}if(j==members)clubs[members++]=id;}
                native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
                if(members){native_name_db.query_init(query,1,"teams");q=1;native_name_db.result_init(&result);r=1;execute(backend,query,&result);n=native_name_db.count(&result);
                    if(n>0&&n<=10000)for(i=0;i<n;++i){int id=native_name_db.integer(&result,i,"teamid"),j;
                        for(j=0;j<members&&clubs[j]!=id;++j){}if(j<members){int prestige=native_name_db.integer(&result,i,"internationalprestige");
                            if(seen[j]){matched=-1;break;}seen[j]=1;
                            if(prestige<0||prestige>20){matched=-1;break;}sum+=(float)prestige;++matched;}}
                    if(matched==members)strength=100.f*(.60f*(1.f-.70f*(level-1)/6.f)+.40f*sum/(members*20.f));}
            }}
    }__finally{if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
    __except(EXCEPTION_EXECUTE_HANDLER){league=0;name[0]=0;strength=-1;}
    player_profile_publish_league(club,league,name);
    player_profile_publish_league_strength(club,league,strength);
}
static void native_club_players_refresh(void) {
    static int last_club=-1,last_date=0;static DWORD last_tick=0;
    static LONG busy=0;
    ClubPlayerRow rows[CLUB_PLAYER_CAPACITY];NativeClubRosterLink links[CLUB_PLAYER_CAPACITY];int valid=0;
    char name[128]={0};SIZE_T i,count,written=0;DWORD now=GetTickCount();unsigned int colors[3]={0};int has_colors=0,captain=0,force=0;
    if(InterlockedCompareExchange(&busy,1,0))return;
    __try {
        player_profile_publish_career_date(native_view.date);
        force=club_player_screen_take_refresh_request();
        if(sponsor_screen_take_refresh_request())force=1;
        if(!force && last_club==native_club && last_date==native_view.date && (DWORD)(now-last_tick)<10000)return;
        if(native_club<=0 || !native_names) {
            club_player_screen_publish(NULL,0,0,"");sponsor_screen_publish(NULL,0,0,"");last_club=0;last_tick=now;return;
        }
        native_name_db_bind();
        count=native_club_roster_links(native_club,links,CLUB_PLAYER_CAPACITY,&valid);
        for(i=0;i<count;++i)if(native_club_player_row(native_club,links[i].player,rows+written)) {
            rows[written].squad_position=links[i].position;rows[written].number=links[i].number;++written;
        }
        native_club_player_wages(native_club,rows,written);
        if(valid&&written)has_colors=native_club_player_identity(native_club,colors,&captain);
        for(i=0;i<written;++i){rows[i].club_colors_valid=has_colors;memcpy(rows[i].club_colors,colors,sizeof(colors));
            rows[i].captain=captain>0&&rows[i].player_id==captain;}
        native_team_name(native_club,name,sizeof(name));
        if(valid)native_profile_league_refresh(native_club);
        if(valid) {
            club_player_screen_publish(rows,written,native_club,name);
            sponsor_screen_publish(rows,written,native_club,name);
            last_club=native_club;last_date=native_view.date;last_tick=now;
        }else { /* Never show a stale previous club on failure. */
            club_player_screen_publish(NULL,0,native_club,name);
            sponsor_screen_publish(NULL,0,native_club,name);
        }
    } __finally {InterlockedExchange(&busy,0);}
}
