#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../../src/core/fce_model.h"

static uint8_t nodes[8][80],standing[2][0x24],fixture[1][0x23];
static void word(uint8_t *p,int at,int v){p[at]=(uint8_t)v;p[at+1]=(uint8_t)(v>>8);}
static void number(uint8_t *p,int at,int v){memcpy(p+at,&v,4);}
static void node(int row,int id,int parent,int kind,const char *name){
    nodes[row][10]=1;word(nodes[row],0x10,id);nodes[row][0x12]=(uint8_t)kind;word(nodes[row],0x14,parent);
    strcpy((char *)nodes[row]+0x1c,name);
}
static void reset(void){
    memset(nodes,0,sizeof(nodes));memset(standing,0,sizeof(standing));memset(fixture,0,sizeof(fixture));
    node(0,10,-1,3,"TrophyName_Abbr15_1003");node(1,11,10,4,"FCE_Semi_Finals");node(2,12,11,5,"");
    node(3,13,10,4,"FCE_Final");node(4,14,13,5,"");
    node(5,20,-1,3,"TrophyName_Abbr15_1007");node(6,21,20,4,"FCE_Final");node(7,22,21,5,"");
    standing[0][10]=standing[1][10]=1;word(standing[0],8,100);word(standing[1],8,200);
    word(standing[0],0x10,14);word(standing[1],0x10,14);
    number(standing[0],0x14,1043);number(standing[1],0x14,567);
    fixture[0][10]=1;word(fixture[0],0x10,10);number(fixture[0],0x14,20261017);word(fixture[0],0x18,1600);
    word(fixture[0],0x1a,100);word(fixture[0],0x1e,200);fixture[0][0x1c]=2;fixture[0][0x22]=1;
}
static int stage(void){
    FceRawTable tables[4]={{nodes[0],8,sizeof(nodes[0])},{standing[0],2,sizeof(standing[0])},{NULL,0,0x25},{fixture[0],1,sizeof(fixture[0])}};
    FceModel model;int result;
    assert(fce_model_build(tables,20261230,&model)==FCE_OK);assert(model.fixture_count==1);
    result=model.fixtures[0].stage;assert(fce_model_ancestor(&model,model.fixtures[0].competition_object,3)==10);
    fce_model_free(&model);return result;
}
int main(void){
    reset();assert(stage()==13);number(fixture[0],0x14,20271017);assert(stage()==13);
    reset();word(standing[1],0x10,12);assert(stage()==10);
    reset();word(standing[0],0x10,22);word(standing[1],0x10,22);assert(stage()==10);
    reset();word(fixture[0],0x10,11);assert(stage()==11);
    reset();word(standing[0],0x10,10);word(standing[1],0x10,10);assert(stage()==10);
    puts("PASS: fixture phase follows matching native standing slots within its own competition, including unsaved seasons.");
    return 0;
}
