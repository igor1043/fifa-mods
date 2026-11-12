#include <assert.h>
#include <stdio.h>
#include "../../src/host/financial_incorporation_policy.h"
typedef struct {int money,season,writes,valid,ack,write_ok;} Budget;
static int scope(void *p){return ((Budget *)p)->valid;}
static int read_budget(void *p,int *money,int *season){Budget *b=(Budget *)p;*money=b->money;*season=b->season;return b->ack;}
static int write_budget(void *p,int before,int season_before,int after,int season_after){
    Budget *b=(Budget *)p;++b->writes;
    if(!b->write_ok||b->money!=before||b->season!=season_before)return 0;
    b->money=after;b->season=season_after;return 1;
}
typedef struct {int money,season,live_money,live_season,sync,writes;} Mirrors;
static int mirrors_scope(void *p){(void)p;return 1;}
static int mirrors_read(void *p,int *money,int *season){
    Mirrors *m=(Mirrors *)p;*money=m->money;*season=m->season;
    return financial_mirrors_match(m->live_money,m->live_season,m->money,m->season);
}
static int mirrors_write(void *p,int before,int season_before,int after,int season_after){
    Mirrors *m=(Mirrors *)p;
    if(!financial_mirrors_match(m->live_money,m->live_season,before,season_before))return 0;
    ++m->writes;m->money=after;m->season=season_after;
    if(m->sync){m->live_money=after;m->live_season=season_after;}return 1;
}
static void test_active_budget_mirrors(void){
    FinancialIncorporation s={0};int after,season;
    Mirrors m={28000000,28000000,28000000,28000000,0,0};
    FinancialBudgetOps ops={&m,mirrors_scope,mirrors_write,mirrors_read};
    financial_begin(&s);assert(financial_arm(&s,100000000,100,1));
    /* Regression: a successful SQL UPDATE must not report success if FIFA's
     * spending budget is still 28M. */
    assert(financial_commit(&s,ops,28000000,28000000,&after,&season)==-3);
    assert(m.money==128000000&&m.live_money==28000000&&s.phase!=FINANCIAL_APPLIED);
    m.money=m.season=m.live_money=m.live_season=28000000;m.sync=1;
    financial_begin(&s);assert(financial_arm(&s,200000000,200,2));
    assert(financial_commit(&s,ops,28000000,28000000,&after,&season)==1);
    assert(m.money==228000000&&m.live_money==228000000&&m.live_season==228000000);
    assert(financial_commit(&s,ops,228000000,228000000,&after,&season)==0);
    m.money=m.season=m.live_money=m.live_season=28000000;
    financial_begin(&s);assert(financial_arm(&s,500000000,300,3));
    assert(financial_commit(&s,ops,28000000,28000000,&after,&season)==1);
    assert(m.money==528000000&&m.live_money==528000000&&m.live_season==528000000);
    assert(!financial_plan(1800000000,1800000000,500000000,&after,&season));
}
int main(void) {
    FinancialIncorporation s={0};int action,amount,after,season;
    Budget budget={20000000,18000000,0,1,1,1};FinancialBudgetOps ops={&budget,scope,write_budget,read_budget};
    assert(financial_wire("S16FUND1|BEGIN|0|END",&action,&amount)&&action==0&&amount==0);
    assert(financial_wire("S16FUND1|ARM|10000000|END",&action,&amount)&&action==1&&amount==10000000);
    assert(!financial_wire("S16FUND1|ARM|+10000000|END",&action,&amount));
    assert(!financial_wire("S16FUND1|ARM|010000000|END",&action,&amount));
    assert(!financial_wire("S16FUND1|ARM|2147483648|END",&action,&amount));
    assert(!financial_wire("S16FUND1|ARM|25000001|END",&action,&amount));
    assert(!financial_wire("S16FUND1|CANCEL|1000000|END",&action,&amount));
    assert(!financial_wire("S16FUND1|ARM|1000000|ENDjunk",&action,&amount));
    assert(!financial_arm(&s,1000000,10,2));
    financial_begin(&s);assert(s.phase==FINANCIAL_CHOOSING&&s.generation==1);
    assert(financial_arm(&s,10000000,100,4)&&s.phase==FINANCIAL_ARMED&&s.epoch==4);
    assert(!financial_arm(&s,10000000,101,4));
    assert(financial_plan(20000000,18000000,s.amount,&after,&season)&&after==30000000&&season==28000000);
    assert(!financial_plan(2147000000,0,1000000,&after,&season));
    assert(!financial_plan(-1,0,1000000,&after,&season));
    assert(!financial_plan(0,0,0,&after,&season));
    s.phase=FINANCIAL_APPLIED;assert(!financial_arm(&s,10000000,200,4));
    financial_begin(&s);assert(s.generation==2&&s.phase==FINANCIAL_CHOOSING&&s.amount==0);
    assert(financial_arm(&s,0,300,8)&&s.phase==FINANCIAL_IDLE);
    financial_begin(&s);assert(financial_arm(&s,10000000,400,9));
    budget.valid=0;assert(financial_commit(&s,ops,20000000,18000000,&after,&season)==0&&budget.writes==0);
    budget.valid=1;assert(financial_commit(&s,ops,20000000,18000000,&after,&season)==1);
    assert(budget.money==30000000&&budget.season==28000000&&budget.writes==1);
    assert(financial_commit(&s,ops,30000000,28000000,&after,&season)==0&&budget.writes==1);
    financial_begin(&s);assert(financial_arm(&s,1000000,500,10));budget.ack=0;
    assert(financial_commit(&s,ops,30000000,28000000,&after,&season)==-3);
    assert(budget.money==31000000&&budget.writes==2&&s.phase==FINANCIAL_REJECTED);
    assert(financial_commit(&s,ops,31000000,29000000,&after,&season)==0&&budget.writes==2);
    financial_begin(&s);assert(financial_arm(&s,1000000,600,11));budget.ack=1;budget.write_ok=0;
    assert(financial_commit(&s,ops,31000000,29000000,&after,&season)==-2);
    assert(financial_commit(&s,ops,31000000,29000000,&after,&season)==0&&budget.writes==3);
    /* Real regression: new save at Jan 1, native season reference at Jan 9. */
    financial_begin(&s);assert(financial_arm(&s,100000000,700,12));
    assert(financial_creation_calendar(&s,20260101,20260109,20260101)==1);
    assert(financial_creation_calendar(&s,20260701,20260630,20260701)==1);
    assert(financial_creation_calendar(&s,20260101,20260109,20260102)==0);
    assert(financial_creation_calendar(&s,20260101,0,20260101)==0);
    assert(s.phase==FINANCIAL_ARMED);
    budget.money=28000000;budget.season=28000000;budget.write_ok=1;
    assert(financial_commit(&s,ops,28000000,28000000,&after,&season)==1);
    assert(after==128000000&&season==128000000);
    assert(financial_commit(&s,ops,128000000,128000000,&after,&season)==0);
    financial_begin(&s);assert(financial_arm(&s,100000000,800,13));
    /* Back/load navigation cancels the creation token. File reads do not:
     * FIFA itself reads DATA while constructing a fresh career. */
    s.phase=FINANCIAL_IDLE;
    assert(financial_creation_calendar(&s,20260101,20260109,20260101)==0);
    assert(financial_commit(&s,ops,128000000,128000000,&after,&season)==0);
    assert(financial_wire("S16FUND1|ARM|200000000|END",&action,&amount)&&amount==200000000);
    assert(financial_wire("S16FUND1|ARM|500000000|END",&action,&amount)&&amount==500000000);
    assert(!financial_wire("S16FUND1|ARM|1000000000|END",&action,&amount));
    test_active_budget_mirrors();
    puts("PASS financial start: allowed values, canonical requests, fresh creation, one arm, default disabled and overflow bounds");return 0;
}
