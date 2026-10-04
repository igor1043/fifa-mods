#include "player_competition_data.h"
/* Only the already-owned FCE model. No speculative database fields or queries.
 * Resolve roots before publication; render/asset workers never borrow nodes. */
static void native_player_competitions_refresh(void){
    size_t cap,count=0,i;
    PlayerCompetitionInput*rows;
    if(native_view.stat_count>65536||native_view.fixture_count>65536||native_view.node_count>65536||
       (native_view.stat_count&&!native_view.stats)||(native_view.fixture_count&&!native_view.fixtures)||(native_view.node_count&&!native_view.nodes)){
        player_profile_publish_competitions(NULL,0,0,0,native_epoch);return;}
    cap=native_view.stat_count+native_view.fixture_count*2;
    if(cap>196608){player_profile_publish_competitions(NULL,0,0,0,native_epoch);return;}
    rows=calloc(cap?cap:1,sizeof(*rows));
    if(!rows){player_profile_publish_competitions(NULL,0,0,0,native_epoch);return;}
    for(i=0;i<native_view.stat_count;++i){const FceStat*s=native_view.stats+i;FceCompetition c;
        if(s->stats_id<0||s->team<=0||s->player<=0||s->competition<=0||fce_resolve_competition(native_view.nodes,native_view.node_count,s->competition,&c)!=FCE_OK)continue;
        rows[count++]=(PlayerCompetitionInput){s->player,s->team,c.competition,s->competition,c.asset,s->appearances,s->goals,s->assists,s->clean_sheets,s->rating_sum,s->profile_valid};
    }
    for(i=0;i<native_view.fixture_count;++i){const FceFixture*f=native_view.fixtures+i;FceCompetition c;
        if(fce_resolve_competition(native_view.nodes,native_view.node_count,f->competition_object,&c)!=FCE_OK)continue;
        rows[count++]=(PlayerCompetitionInput){0,f->home,c.competition,c.competition,c.asset,0,0,0,0,0,0};
        rows[count++]=(PlayerCompetitionInput){0,f->away,c.competition,c.competition,c.asset,0,0,0,0,0,0};
    }
    player_profile_publish_competitions(rows,count,native_club,native_view.date,native_epoch);free(rows);
}
