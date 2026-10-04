#include "../../src/screens/player/player_competition_data.h"
extern "C" {
#include "../../src/core/fce_model.h"
}
#include <cstdio>
#include <cstring>
#include <cmath>
static int failures=0;
static void check(bool value,const char*message){if(!value){++failures;printf("FAIL: %s\n",message);}}
static void i32(unsigned char*b,int offset,int value){memcpy(b+offset,&value,4);}
int main(){using namespace player_competitions;
    std::vector<PlayerCompetitionInput>rows={{7,1043,10,10,13,10,3,4,5,750,3},{7,1043,10,11,13,4,1,1,2,300,3},
        {7,1043,20,21,100,2,1,0,1,140,3},{7,1043,20,22,100,3,2,2,1,240,3},{0,1043,30,30,30,0,0,0,0,0,0},
        {8,1043,10,10,13,20,99,10,10,1800,3},{7,99,10,10,13,90,90,90,90,9000,3}};
    rows.push_back(rows[0]);auto stats=aggregate(rows,7,1043);auto sum=total(stats);
    check(stats.available&&stats.rows.size()==3,"one competition root, retains scheduled competitions");
    check(stats.rows[0].games==10&&stats.rows[0].goals==3&&stats.rows[0].clean_sheets==5,"root wins over stages; exact duplicates counted once");
    check(stats.rows[1].games==5&&stats.rows[1].goals==3&&stats.rows[1].assists==2,"child phases summed when no root total");
    check(sum.games==15&&sum.goals==6&&sum.assists==6&&sum.clean_sheets==7,"total excludes other players/club and root double counting");
    check(fabs(average(sum)-1130./150)<.0001,"average weighted by appearances, never summed or mean of means");
    check(stats.rows[2].games==0&&average(stats.rows[2])<0,"unplayed tournament is zero counts but no fake rating");
    auto missing=rows;missing[2].valid=1;auto no_rating=aggregate(missing,7,1043);check(average(total(no_rating))<0,"missing rating makes total unknown");
    missing=rows;missing[2].valid=2;check(!(total(aggregate(missing,7,1043)).valid&1),"partial clean sheets never shown as complete zero");
    rows.back().goals=99;check(!aggregate(rows,7,1043).available,"conflicting duplicates fail closed");
    unsigned char raw[0x40]={},comp[0x1c]={},standing[0x24]={},fixture[0x23]={};raw[10]=1;i32(raw,0x10,1043);i32(raw,0x14,7);raw[0x18]=10;raw[0x1e]=10;raw[0x1f]=3;raw[0x21]=4;raw[0x1c]=0xee;raw[0x1d]=2;raw[0x27]=5;
    FceRawTable tables[]={{comp,0,sizeof(comp)},{standing,0,sizeof(standing)},{raw,1,sizeof(raw)},{fixture,0,sizeof(fixture)}};FceModel model={};
    check(fce_model_build(tables,20260110,&model)==FCE_OK,"owned raw model decoder");check(model.stat_count==1&&model.stats[0].clean_sheets==5&&model.stats[0].rating_sum==750&&model.stats[0].profile_valid==3,"verified raw clean sheet/rating offsets");fce_model_free(&model);
    tables[2].stride=0x25;check(fce_model_build(tables,20260110,&model)==FCE_OK&&!(model.stats[0].profile_valid&1),"legacy short row never reads clean sheets past stride");fce_model_free(&model);
    unsigned char view[FCE_STAT_VIEW_BYTES]={};i32(view,8,1043);i32(view,12,7);i32(view,0x10,10);i32(view,0x28,750);i32(view,0x3c,5);FceStat decoded={};
    check(fce_decode_stat(view,sizeof(view),&decoded)==FCE_OK&&decoded.clean_sheets==5&&decoded.rating_sum==750&&decoded.profile_valid==3,"FCEI offsets distinct from raw fields");
    i32(view,0x3c,11);i32(view,0x28,1100);check(fce_decode_stat(view,sizeof(view),&decoded)==FCE_OK&&decoded.profile_valid==0,"impossible optional values rejected without corrupting goals");
    printf("Player competitions: %s (%d failures)\n",failures?"FAIL":"PASS",failures);return failures?1:0;
}
