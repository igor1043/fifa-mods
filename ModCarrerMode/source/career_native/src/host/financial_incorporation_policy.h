#ifndef SERVER16_FINANCIAL_INCORPORATION_POLICY_H
#define SERVER16_FINANCIAL_INCORPORATION_POLICY_H
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
enum { FINANCIAL_IDLE,FINANCIAL_CHOOSING,FINANCIAL_ARMED,FINANCIAL_APPLIED,FINANCIAL_REJECTED };
typedef struct {int phase,amount;unsigned generation,epoch,club;uint64_t armed;} FinancialIncorporation;
static int financial_amount_valid(int amount) {
    static const int values[]={0,10000,20000,40000,80000,1000000,5000000,10000000,50000000,100000000,200000000,500000000};
    unsigned i;for(i=0;i<sizeof(values)/sizeof(values[0]);++i)if(values[i]==amount)return 1;return 0;
}
static int financial_wire(const char *wire,int *action,int *amount) {
    const char *p;char *end,canonical[80];long n;
    if(!wire||strlen(wire)>=sizeof(canonical)||strncmp(wire,"S16FUND1|",9))return 0;
    p=wire+9;
    if(!strncmp(p,"BEGIN|",6)){*action=0;p+=6;}
    else if(!strncmp(p,"ARM|",4)){*action=1;p+=4;}
    else if(!strncmp(p,"CANCEL|",7)){*action=2;p+=7;}else return 0;
    errno=0;n=strtol(p,&end,10);
    if(errno||n<0||n>500000000||strcmp(end,"|END")||!financial_amount_valid((int)n)||(*action!=1&&n))return 0;
    snprintf(canonical,sizeof(canonical),"S16FUND1|%s|%ld|END",*action==0?"BEGIN":*action==1?"ARM":"CANCEL",n);
    if(strcmp(canonical,wire))return 0;*amount=(int)n;return 1;
}
static void financial_begin(FinancialIncorporation *s) {
    unsigned generation=s->generation+1;memset(s,0,sizeof(*s));s->generation=generation?generation:1;s->phase=FINANCIAL_CHOOSING;
}
static int financial_arm(FinancialIncorporation *s,int amount,uint64_t tick,unsigned epoch) {
    if(s->phase!=FINANCIAL_CHOOSING||!financial_amount_valid(amount))return 0;
    s->amount=amount;s->epoch=epoch;s->armed=tick;s->phase=amount?FINANCIAL_ARMED:FINANCIAL_IDLE;return 1;
}
static int financial_creation_calendar(FinancialIncorporation *s,int current,int season_start,int today) {
    if(s->phase!=FINANCIAL_ARMED)return 0;
    /* startdate is the native season reference, not the date a career was
     * created. For example, a new Brazilian career can have Jan 1 / Jan 9.
     * Freshness comes from the scoped Setup request and its navigation life.
     * Reading DATA is normal while generating a new save, not a load signal. */
    return current==today&&current>=20080101&&current<=20601231
        &&season_start>=20080101&&season_start<=20601231;
}
static int financial_mirrors_match(int live_money,int live_season,int db_money,int db_season) {
    return live_money==db_money&&live_season==db_season;
}
static int financial_plan(int transfer,int seasonal,int amount,int *after,int *season_after) {
    const int limit=2147483520;
    if(!financial_amount_valid(amount)||amount==0||transfer<0||seasonal<0||transfer>limit-amount||seasonal>limit-amount)return 0;
    *after=transfer+amount;*season_after=seasonal+amount;return 1;
}
typedef struct {
    void *context;
    int (*scope)(void *);
    int (*write)(void *,int,int,int,int);
    int (*read)(void *,int *,int *);
} FinancialBudgetOps;
static int financial_commit(FinancialIncorporation *s,FinancialBudgetOps ops,int before,int season_before,int *after,int *season_after) {
    int actual,season_actual;
    if(s->phase!=FINANCIAL_ARMED)return 0;
    if(!financial_plan(before,season_before,s->amount,after,season_after)){s->phase=FINANCIAL_REJECTED;return -1;}
    if(!ops.scope(ops.context))return 0;
    s->phase=FINANCIAL_REJECTED;
    if(!ops.write(ops.context,before,season_before,*after,*season_after))return -2;
    if(!ops.scope(ops.context)||!ops.read(ops.context,&actual,&season_actual))return -3;
    if(actual!=*after||season_actual!=*season_after)return -4;
    s->phase=FINANCIAL_APPLIED;return 1;
}
#endif
