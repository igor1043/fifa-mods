#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../src/core/fce_model.h"
#include "../../src/screens/player/player_competition_data.h"
static FceModel native_view;
static int native_club=1043,failures;
static unsigned long native_epoch=9;
static PlayerCompetitionInput captured[20];static size_t captured_count;static int captured_club,captured_date;
void player_profile_publish_competitions(const PlayerCompetitionInput*rows,size_t count,int club,int date,unsigned long generation){
    captured_count=count;captured_club=club;captured_date=date;
    if(generation!=9||count>20){++failures;return;}if(count)memcpy(captured,rows,count*sizeof(*rows));}
#include "../../src/screens/player/player_competition_provider.inc"
static void check(int ok,const char*message){if(!ok){++failures;printf("FAIL: %s\n",message);}}
int main(void){FceCompNode nodes[]={{10,-1,3,7,0},{11,10,4,-1,0},{20,-1,3,100,0}};FceStat stats[3]={0};FceFixture fixture={0};
    native_view.nodes=nodes;native_view.node_count=3;native_view.stats=stats;native_view.stat_count=3;native_view.fixtures=&fixture;native_view.fixture_count=1;native_view.date=20260110;
    stats[0]=(FceStat){1,11,1043,7,10,900,3,4,0,0,5,750,3};stats[1]=(FceStat){2,20,99,8,5,450,1,2,0,0,1,350,3};stats[2]=(FceStat){3,99,1043,7,1,90,0,0,0,0,0,70,3};
    fixture.competition_object=10;fixture.home=1043;fixture.away=77;
    native_player_competitions_refresh();check(captured_count==4&&captured_club==1043&&captured_date==20260110,"resolved owned stats and both fixture teams published");
    check(captured[0].root==10&&captured[0].phase==11&&captured[0].asset==7&&captured[0].clean_sheets==5&&captured[0].rating_sum==750,"exact phase, competition asset and optional player fields");
    check(captured[1].club==99&&captured[1].player==8,"foreign team retained for generic profile, not relabeled as career club");
    check(captured[2].player==0&&captured[2].club==1043&&captured[3].club==77,"fixture seeds do not invent player appearances");
    native_view.stat_count=196609;native_view.fixture_count=0;native_player_competitions_refresh();check(captured_count==0&&captured_club==0&&captured_date==0,"oversized snapshot fails closed before dereference");
    printf("Player competition provider: %s (%d failures)\n",failures?"FAIL":"PASS",failures);return failures?1:0;
}
