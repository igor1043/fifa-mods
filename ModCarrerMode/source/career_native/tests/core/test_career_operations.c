#include "../../src/features/finance/career_loan_engine.h"
#include "../../src/features/retirement/retirement_engine.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static int failed;
static void check(int value,const char *text){printf("%s %s\n",value?"PASS":"FAIL",text);if(!value)failed++;}
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint32_t fieldbits(const unsigned char*p,size_t row,uint32_t at,unsigned depth){unsigned i;uint32_t v=0;
    for(i=0;i<depth;++i){size_t bit=row*8+at+i;if(p[bit/8]&(1U<<(bit%8)))v|=1U<<i;}return v;}
static int first_players(const unsigned char*d,size_t n,unsigned int ids[2]){
    size_t cursor=0xA0;unsigned got=0;
    while(cursor+24<n){uint32_t size,count,i;
        if(memcmp(d+cursor,"DB\0\x08\0\0\0\0",8)){cursor++;continue;}
        size=word(d+cursor+8);count=word(d+cursor+16);if(size<28||size>n-cursor||count>4096)return 0;
        for(i=0;i<count;++i){const unsigned char*e=d+cursor+24+i*8;if(!memcmp(e,"CZUM",4)){
            size_t header=cursor+28+(size_t)count*8+word(e+4),row;unsigned f,j,k=0;uint32_t stride,at=0;
            if(header+36>n)return 0;stride=word(d+header+4);f=d[header+24];j=d[header+18]|((unsigned)d[header+19]<<8);
            for(k=0;k<f;++k)if(!memcmp(d+header+36+k*16+8,"ykFq",4))at=word(d+header+36+k*16+4);
            row=header+36+f*16;if(!stride||row+(size_t)stride*j>n)return 0;
            for(k=0;k<j&&got<2;++k)if(!(d[row+(size_t)k*stride+stride-1]&128))ids[got++]=fieldbits(d,row+(size_t)k*stride,at,19);
            return got==2;
        }}cursor+=size;
    }return 0;
}
int main(int argc,char**argv){
    CareerLoanTerms t={1000000,500,6,20260131,20260228,1};CareerLoanSchedule s;uint32_t count=0,amount=0;
    check(career_loan_schedule(&t,&s)&&s.total==1050000&&s.amounts[0]==175000,"principal + total fixed interest / 6 installments");
    check(career_loan_due(&s,20260428,0,&count,&amount)&&count==3&&amount==525000,"catch up three due dates, not wall clock");
    check(career_loan_due(&s,20260428,3,&count,&amount)&&count==0&&amount==0,"paid count prevents repeated installments");
    t.first_due_date=20260131;t.contract_date=20260101;t.principal=100;t.interest_basis_points=1;t.installments=3;
    check(career_loan_schedule(&t,&s)&&s.total==101&&s.due_dates[1]==20260228&&s.due_dates[2]==20260331&&
        s.amounts[0]+s.amounts[1]+s.amounts[2]==101,"integer remainder distribution and anchored month-end");
    t.first_due_date=20240229;t.contract_date=20240131;
    check(career_loan_schedule(&t,&s)&&s.due_dates[1]==20240329,"leap-year due date");
    t.first_due_date=20260230;check(!career_loan_schedule(&t,&s),"invalid date rejected");
    if(argc>1){
        FILE*f=fopen(argv[1],"rb");long length=0;unsigned char *data=NULL,*scratch=NULL;char message[256];
        CareerLoanSnapshot before,after,stale;size_t i;int exact=1;unsigned int ids[2]={0};RetirementApplyResult result;
        if(f&&fseek(f,0,SEEK_END)==0){length=ftell(f);rewind(f);}check(length>0&&length<64*1024*1024,"read-only career fixture opened");
        if(length<=0){if(f)fclose(f);return 1;}data=(unsigned char*)malloc((size_t)length);scratch=(unsigned char*)malloc((size_t)length);
        if(!data||!scratch){if(f)fclose(f);free(data);free(scratch);return 1;}
        if(fread(data,1,(size_t)length,f)!=(size_t)length){fclose(f);free(data);free(scratch);return 1;}fclose(f);
        check(career_loan_read_save(data,(size_t)length,&before,message,sizeof(message)),message);
        printf("snapshot club=%u date=%u transfers=%u wages=%u currency=%u\n",before.club,before.date,before.transfer_budget,before.wage_budget,before.currency);
        memcpy(scratch,data,(size_t)length);
        check(career_loan_patch_budget(scratch,(size_t)length,&before,1000000,&after,message,sizeof(message)),message);
        for(i=0;i<(size_t)length;++i){unsigned char mask=0;unsigned bit;
            if((i>=0x84&&i<0x88)||(i>=before.budget_crc_offset&&i<before.budget_crc_offset+4))mask=255;
            for(bit=0;bit<8;++bit)if(i*8+bit>=before.budget_bit&&i*8+bit<before.budget_bit+31)mask|=(unsigned char)(1U<<bit);
            if(((data[i]^scratch[i])&~mask)!=0){exact=0;break;}}
        check(exact&&after.transfer_budget==before.transfer_budget+1000000&&after.wage_budget==before.wage_budget,
            "only 31 transfer-budget bits + table/container CRCs changed; all other bytes unchanged");
        stale=before;stale.transfer_budget++;
        check(!career_loan_patch_budget(data,(size_t)length,&stale,1,&after,message,sizeof(message)),"stale UI snapshot rejected atomically");
        check(!career_loan_patch_budget(data,(size_t)length,&before,-(int64_t)before.transfer_budget-1,&after,message,sizeof(message)),"negative native budget rejected");
        memcpy(scratch,data,(size_t)length);scratch[0xA0]^=1;
        check(!career_loan_read_save(scratch,(size_t)length,&after,message,sizeof(message)),"corrupt container rejected");
        check(first_players(data,(size_t)length,ids),"read two actual player IDs, no special team");
        memcpy(scratch,data,(size_t)length);
        check(retirement_engine_apply_selection(scratch,(SIZE_T)length,ids,1,1,18,&result)&&result.players_seen==1&&result.players_changed<=1,
            "individual rejuvenation respects ID allow-list, exact-bit proof inside engine");
        printf("selection status=%d seen=%u changed=%u message=%s\n",result.status,result.players_seen,result.players_changed,result.message);
        memcpy(scratch,data,(size_t)length);ids[1]=ids[0];
        check(!retirement_engine_apply_selection(scratch,(SIZE_T)length,ids,2,1,18,&result)&&!memcmp(scratch,data,(size_t)length),
            "duplicate selection rejected; original byte-for-byte preserved");
        memcpy(scratch,data,(size_t)length);ids[0]=300000;
        check(!retirement_engine_apply_selection(scratch,(SIZE_T)length,ids,1,0,18,&result)&&!memcmp(scratch,data,(size_t)length),
            "absent selection rejected; original byte-for-byte preserved");
        memcpy(scratch,data,(size_t)length);
        check(retirement_engine_apply_selection(scratch,(SIZE_T)length,NULL,0,0,18,&result),"global retirement-only selection validates without changing birthdates");
        printf("global status=%d seen=%u changed=%u message=%s\n",result.status,result.players_seen,result.players_changed,result.message);
        free(data);free(scratch);
    }
    printf("%s: %d failures. No save file written.\n",failed?"FAILED":"PASSED",failed);return failed?1:0;
}
