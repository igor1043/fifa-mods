#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../src/screens/operations/career_operations.h"
#include "../../src/features/ranking/global_ranking.h"
/* The REAL provider body runs against a strict owned fake DB. No FIFA process,
 * borrowed game memory or DATA writes. The old invalid players field fails. */
static int failures,native_club=1043,requested=1,requested_club=1043,requested_date=20260110;
static int link_teams[4]={1043,1337},links=2,queries,results,where_id,published_valid,captured_club,loaded;
static unsigned requested_player=227275;
static ClubPlayerRow captured;
static FceModel native_view;
static void check(int ok,const char*message){if(!ok){++failures;printf("FAIL: %s\n",message);}}
static char table[64];
static void*mock_query(void*p,int kind,const char*name){(void)kind;strcpy_s(table,sizeof(table),name);++queries;return p;}
static void mock_where(void*q,const char*field,int op,int id){(void)q;(void)op;check(!strcmp(field,"playerid"),"profile where uses real playerid");where_id=id;}
static void*mock_result(void*p){++results;return p;}
static int mock_count(void*p){(void)p;return !strcmp(table,"teamplayerlinks")?links:1;}
static int mock_integer(void*p,int row,const char*field){(void)p;
    if(!strcmp(table,"teamplayerlinks")&&!strcmp(field,"teamid")&&row>=0&&row<links)return link_teams[row];
    printf("FAIL: unknown native field %s.%s\n",table,field);++failures;return 0;}
static const char*mock_string(void*p,int row,const char*field){(void)p;(void)row;(void)field;return "Fixture";}
static void mock_result_free(void*p){(void)p;--results;}
static void mock_query_free(void*p){(void)p;--queries;}
static void mock_execute(void*b,void*q,void*r){(void)b;(void)q;(void)r;check(!strcmp(table,"teamplayerlinks"),"profile membership never queries a nonexistent players column");}
static void*mock_vtable[2]={NULL,mock_execute};static void*mock_object[1]={mock_vtable};static void*mock_backend=mock_object;static void*native_names=&mock_backend;
static struct {void*(*query_init)(void*,int,const char*);void(*where_int)(void*,const char*,int,int);void*(*result_init)(void*);int(*count)(void*);int(*integer)(void*,int,const char*);const char*(*string)(void*,int,const char*);void(*result_free)(void*);void(*query_free)(void*);}native_name_db={mock_query,mock_where,mock_result,mock_count,mock_integer,mock_string,mock_result_free,mock_query_free};
static void native_name_db_bind(void){}
static int is_readable_range(const void*p,SIZE_T n){return p&&n;}
BOOL retirement_profile_take_request(unsigned*id,int*club,int*date){if(!requested)return FALSE;requested=0;*id=requested_player;*club=requested_club;*date=requested_date;return TRUE;}
void retirement_profile_publish(const ClubPlayerRow*row,const char*name,int club,int date,int valid){(void)name;(void)club;(void)date;captured=*row;published_valid=valid;}
BOOL retirement_screen_take_refresh(void){return FALSE;}
void retirement_screen_publish(const RetirementUiPlayer*p,size_t n,int club,int date,int valid){(void)p;(void)n;(void)club;(void)date;(void)valid;}
FceResult fce_global_ranking_build_all(const FceModel*m,FceGlobalRankedClub**out,size_t*count){(void)m;*count=2;*out=calloc(2,sizeof(**out));(*out)[0].team=1043;(*out)[1].team=112893;return FCE_OK;}
void fce_global_ranking_free(void*p){free(p);}
static int native_club_player_row(int club,int id,ClubPlayerRow*out){++loaded;memset(out,0,sizeof(*out));out->team_id=club;out->player_id=id;strcpy_s(out->name,128,"Jogador da consulta");out->overall=80;captured_club=club;return 1;}
typedef struct NativeClubRosterLink {int player,position,number;}NativeClubRosterLink;
static SIZE_T native_club_roster_links(int club,NativeClubRosterLink*out,SIZE_T cap,int*valid){(void)club;(void)cap;*valid=1;out[0].player=(int)requested_player;out[0].position=3;out[0].number=21;return 1;}
static int native_club_player_identity(int club,unsigned int*colors,int*captain){(void)club;colors[0]=0xff0000;colors[1]=0;colors[2]=0xffffff;*captain=0;return 1;}
static void native_team_name(int club,char*out,size_t n){snprintf(out,n,"Clube %d",club);}
static void native_profile_league_refresh(int club){(void)club;}
static int native_squad_player_age(int birth,int date){(void)birth;(void)date;return 30;}
static void mock_resolver(int*key,void*names,char*out,int size){(void)key;(void)names;strcpy_s(out,size,"Fixture");}
static void(*g_resolve_player_name)(int*,void*,char*,int)=mock_resolver;
#include "../../src/screens/retirement/retirement_screen_provider.inc"
static void request(void){requested=1;published_valid=-1;loaded=0;native_retirement_profile_refresh();check(queries==0&&results==0,"all native query/result lifetimes end before publish");}
int main(void){native_view.date=20260110;
    request();check(published_valid==1&&captured_club==1043&&captured.player_id==227275&&captured.number==21,"own club exact ID/kit/shirt, excludes national link");
    link_teams[0]=112893;request();check(published_valid==1&&captured_club==112893,"foreign club exact kit, never career club fallback");
    link_teams[1]=1043;request();check(published_valid==1&&captured_club==0,"ambiguous club keeps attributes without borrowed kit");
    links=0;request();check(published_valid==1&&captured_club==0,"free agent profile has no borrowed club");
    links=1;link_teams[0]=1337;request();check(published_valid==1&&captured_club==0,"national-only link cannot become club kit");
    requested_club=999;request();check(published_valid==0&&loaded==0,"wrong career request never queries player");requested_club=native_club;
    requested_date=20260111;request();check(published_valid==0&&loaded==0,"wrong date request never queries player");requested_date=native_view.date;
    links=33;request();check(published_valid==1&&captured_club==0,"out-of-bounds links do not index result");
    printf("Retirement native profile provider: %s (%d failures)\n",failures?"FAIL":"PASS",failures);return failures?1:0;
}
