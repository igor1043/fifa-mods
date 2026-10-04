#include "career_loan_engine.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define LOAN_MAX_BUDGET 2147483520U
#define LOAN_MAX_SIZE (64U*1024U*1024U)
#define LOAN_SENTINEL 0xCDCDCDCDU
typedef struct LoanField {uint32_t bit,depth;int found;} LoanField;
typedef struct LoanTable {
    size_t record,crc_start,crc_offset;
    uint32_t stride; uint16_t count; uint8_t fields;
    size_t descriptors;
} LoanTable;

static uint16_t u16(const unsigned char*p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t u32(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(unsigned char*p,uint32_t v){unsigned i;for(i=0;i<4;++i)p[i]=(unsigned char)(v>>(i*8));}
static int range(size_t p,size_t n,size_t size){return p<=size&&n<=size-p;}
static int error(char*out,size_t cap,const char*text){if(out&&cap)snprintf(out,cap,"%s",text);return 0;}
static uint32_t crc(const unsigned char*p,size_t n,int fifa){
    uint32_t c=0xFFFFFFFFU;size_t i;unsigned j;
    for(i=0;i<n;++i){
        if(fifa){c^=(uint32_t)p[i]<<24;for(j=0;j<8;++j)c=(c&0x80000000U)?(c<<1)^0x04C11DB7U:c<<1;}
        else {c^=p[i];for(j=0;j<8;++j)c=(c>>1)^((c&1)?0xEDB88320U:0);}
    }
    return fifa?c:~c;
}
static unsigned month_days(unsigned y,unsigned m){
    static const unsigned days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};
    if(m<1||m>12)return 0;return days[m]+(m==2&&y%4==0&&(y%100!=0||y%400==0));
}
static int date_valid(uint32_t v){unsigned y=v/10000,m=v/100%100,d=v%100;return y>=2008&&y<=2060&&d>=1&&d<=month_days(y,m);}
static uint32_t add_months(uint32_t date,uint32_t months){
    unsigned y=date/10000,m=date/100%100,d=date%100,serial=y*12+m-1+months;
    y=serial/12;m=serial%12+1;if(d>month_days(y,m))d=month_days(y,m);
    return y*10000+m*100+d;
}
int career_loan_schedule(const CareerLoanTerms*t,CareerLoanSchedule*out){
    CareerLoanSchedule s;uint64_t interest,total;uint32_t i;
    if(!t||!out||!t->principal||t->principal>LOAN_MAX_BUDGET||t->interest_basis_points>10000||
       !t->installments||t->installments>120||!t->interval_months||t->interval_months>12||
       !date_valid(t->contract_date)||!date_valid(t->first_due_date)||t->first_due_date<=t->contract_date)return 0;
    interest=((uint64_t)t->principal*t->interest_basis_points+9999)/10000;
    total=t->principal+interest;if(total>LOAN_MAX_BUDGET)return 0;
    memset(&s,0,sizeof(s));s.total=(uint32_t)total;s.count=t->installments;
    s.installment_base=s.total/s.count;s.extra_unit_installments=s.total%s.count;
    if(!s.installment_base)return 0;
    for(i=0;i<s.count;++i){s.due_dates[i]=add_months(t->first_due_date,i*t->interval_months);
        if(!date_valid(s.due_dates[i]))return 0;
        s.amounts[i]=s.installment_base+(i<s.extra_unit_installments);}
    *out=s;return 1;
}
int career_loan_due(const CareerLoanSchedule*s,uint32_t today,uint32_t paid,uint32_t*count,uint32_t*amount){
    uint64_t sum=0;uint32_t i,all=0,n=0;
    if(!s||!count||!amount||!date_valid(today)||!s->count||s->count>120||paid>s->count)return 0;
    for(i=0;i<s->count;++i){if(!date_valid(s->due_dates[i])||!s->amounts[i]||(i&&s->due_dates[i]<=s->due_dates[i-1]))return 0;
        sum+=s->amounts[i];if(sum>LOAN_MAX_BUDGET)return 0;
        if(i>=paid&&s->due_dates[i]<=today){n++;all+=s->amounts[i];}}
    if(sum!=s->total)return 0;*count=n;*amount=all;return 1;
}
static int field(const unsigned char*d,const LoanTable*t,const char*name,unsigned depth,LoanField*out){
    unsigned i;LoanField f={0};
    for(i=0;i<t->fields;++i){const unsigned char*p=d+t->descriptors+i*16;
        if(memcmp(p+8,name,4))continue;
        if(f.found||u32(p)!=3||u32(p+12)!=depth||u32(p+4)>t->stride*8||depth>t->stride*8-u32(p+4))return 0;
        f.bit=u32(p+4);f.depth=depth;f.found=1;}
    *out=f;return f.found;
}
static uint32_t bits(const unsigned char*d,size_t row,const LoanField*f){
    unsigned i;uint32_t v=0;for(i=0;i<f->depth;++i){size_t b=row*8+f->bit+i;if(d[b/8]&(1U<<(b%8)))v|=1U<<i;}return v;
}
static void write31(unsigned char*d,size_t bit,uint32_t v){
    unsigned i;for(i=0;i<31;++i){unsigned char mask=(unsigned char)(1U<<((bit+i)%8));
        if(v&(1U<<i))d[(bit+i)/8]|=mask;else d[(bit+i)/8]&=(unsigned char)~mask;}
}
static int single_row(const unsigned char*d,const LoanTable*t,size_t*out){
    unsigned i,n=0;for(i=0;i<t->count;++i){size_t row=t->record+(size_t)i*t->stride;
        if(!(d[row+t->stride-1]&0x80)){*out=row;n++;}}
    return n==1;
}
static int find_tables(const unsigned char*d,size_t n,LoanTable*tables,char*msg,size_t cap){
    static const char*names[]={"dqXv","GJUr","mPrV","biWl"};
    size_t cursor=0xA0;unsigned found=0;
    while(range(cursor,24,n)){
        uint32_t size,count,i;size_t base;
        if(memcmp(d+cursor,"DB\0\x08\0\0\0\0",8)){cursor++;continue;}
        size=u32(d+cursor+8);count=u32(d+cursor+16);
        if(size<28||!range(cursor,size,n)||!count||count>4096||24+(size_t)count*8+4>size)
            return error(msg,cap,"Invalid database directory");
        base=24+(size_t)count*8+4;
        for(i=0;i<count;++i){const unsigned char*entry=d+cursor+24+i*8;unsigned k;
            for(k=0;k<4;++k)if(!memcmp(entry,names[k],4)){
                LoanTable t={0};size_t head,records,end;uint32_t compressed,relative=u32(entry+4);
                if((found&(1U<<k))||relative>size-base||!range(base+relative,36,size))return error(msg,cap,"Missing or duplicate finance table");
                head=cursor+base+relative;t.stride=u32(d+head+4);t.count=u16(d+head+18);t.fields=d[head+24];compressed=u32(d+head+12);
                if(!t.stride||t.stride>4096||!t.fields||t.fields>128||compressed)
                    return error(msg,cap,"Unsupported compressed finance table");
                records=head+36+(size_t)t.fields*16;
                if(records<cursor||records-cursor>size||(size_t)t.count*t.stride>size-(records-cursor))return error(msg,cap,"Invalid finance records");
                end=records+(size_t)t.count*t.stride;
                if(end-cursor>size||size-(end-cursor)<4)return error(msg,cap,"Invalid finance checksum range");
                t.record=records;t.descriptors=head+36;t.crc_start=t.descriptors;t.crc_offset=end;
                if(u32(d+end)!=LOAN_SENTINEL&&u32(d+end)!=crc(d+t.crc_start,end-t.crc_start,1))return error(msg,cap,"Invalid finance table checksum");
                tables[k]=t;found|=1U<<k;break;
            }
        }
        cursor+=size;
    }
    return found==15?1:error(msg,cap,"Career finance tables not present");
}
int career_loan_read_save(const void*buffer,size_t n,CareerLoanSnapshot*out,char*msg,size_t cap){
    const unsigned char*d=(const unsigned char*)buffer;LoanTable t[4]={0};size_t rows[4]={0};unsigned i;
    LoanField budget,wage,currency,date,setup,pref,uid,club,manager,mclub;CareerLoanSnapshot s={0};
    if(!d||!out||n<0xA4||n>LOAN_MAX_SIZE)return error(msg,cap,"Invalid save size");
    if(u32(d+0x84)!=crc(d+0xA0,n-0xA0,0))return error(msg,cap,"Invalid container checksum");
    if(!find_tables(d,n,t,msg,cap))return 0;
    for(i=0;i<4;++i)if(!single_row(d,t+i,rows+i))return error(msg,cap,"Ambiguous multiplayer career; no budget selected");
    if(!field(d,t,"SnDr",31,&budget)||!field(d,t,"TAIb",31,&wage)||!field(d,t,"UtVA",2,&currency)||!field(d,t,"nhwa",1,&pref)||
       !field(d,t+1,"aLZZ",19,&date)||!field(d,t+1,"KNVN",19,&setup)||
       !field(d,t+2,"uipx",7,&uid)||!field(d,t+2,"NTyS",18,&club)||
       !field(d,t+3,"uipx",4,&manager)||!field(d,t+3,"NTyS",18,&mclub))return error(msg,cap,"Finance fields differ from installed schema");
    s.manager=bits(d,rows[3],&manager);s.club=bits(d,rows[2],&club);
    if(!s.club||s.club>200001||s.club!=bits(d,rows[3],&mclub)||bits(d,rows[2],&uid)!=s.manager+1||bits(d,rows[0],&pref)!=0)
        return error(msg,cap,"Career manager/club ownership mismatch");
    s.club--;s.date=bits(d,rows[1],&date)+20080101;s.setup_date=bits(d,rows[1],&setup)+20080101;
    s.transfer_budget=bits(d,rows[0],&budget);s.wage_budget=bits(d,rows[0],&wage);s.currency=bits(d,rows[0],&currency);
    if(!date_valid(s.date)||!date_valid(s.setup_date)||s.transfer_budget>LOAN_MAX_BUDGET||s.wage_budget>LOAN_MAX_BUDGET||s.currency>2||
       budget.bit+31>t[0].stride*8-8)return error(msg,cap,"Invalid career finance values");
    /* Do not allow a malformed descriptor to alias salaries/manager/currency. */
    for(i=0;i<t[0].fields;++i){const unsigned char*p=d+t[0].descriptors+i*16;uint32_t at=u32(p+4),depth=u32(p+12);
        if(memcmp(p+8,"SnDr",4)&&depth&&at<budget.bit+31&&budget.bit<(uint64_t)at+depth)return error(msg,cap,"Overlapping budget descriptor");}
    s.budget_bit=rows[0]*8+budget.bit;s.budget_crc_start=t[0].crc_start;s.budget_crc_offset=t[0].crc_offset;s.original_crc=u32(d+0x84);
    *out=s;if(msg&&cap)snprintf(msg,cap,"Finance snapshot validated; read-only");return 1;
}
int career_loan_patch_budget(void*buffer,size_t n,const CareerLoanSnapshot*expected,int64_t delta,CareerLoanSnapshot*out,char*msg,size_t cap){
    CareerLoanSnapshot before,after;unsigned char*copy;int64_t money;
    if(!buffer||!expected||!out||!career_loan_read_save(buffer,n,&before,msg,cap))return 0;
    if(before.club!=expected->club||before.manager!=expected->manager||before.date!=expected->date||
       before.setup_date!=expected->setup_date||before.transfer_budget!=expected->transfer_budget||
       before.wage_budget!=expected->wage_budget||before.currency!=expected->currency||
       before.budget_bit!=expected->budget_bit||before.budget_crc_start!=expected->budget_crc_start||
       before.budget_crc_offset!=expected->budget_crc_offset||before.original_crc!=expected->original_crc)
        return error(msg,cap,"Save changed since snapshot; transaction rejected");
    if(delta<-(int64_t)before.transfer_budget||delta>(int64_t)LOAN_MAX_BUDGET-before.transfer_budget)return error(msg,cap,"Budget underflow/overflow; transaction rejected");
    money=(int64_t)before.transfer_budget+delta;copy=(unsigned char*)malloc(n);if(!copy)return error(msg,cap,"Not enough memory");memcpy(copy,buffer,n);
    write31(copy,before.budget_bit,(uint32_t)money);
    if(u32(copy+before.budget_crc_offset)!=LOAN_SENTINEL)put32(copy+before.budget_crc_offset,crc(copy+before.budget_crc_start,before.budget_crc_offset-before.budget_crc_start,1));
    put32(copy+0x84,crc(copy+0xA0,n-0xA0,0));
    if(!career_loan_read_save(copy,n,&after,msg,cap)||after.transfer_budget!=(uint32_t)money||after.club!=before.club||after.date!=before.date||
       after.setup_date!=before.setup_date||after.manager!=before.manager||after.wage_budget!=before.wage_budget||after.currency!=before.currency){free(copy);return error(msg,cap,"Finance post-validation failed; original unchanged");}
    memcpy(buffer,copy,n);free(copy);*out=after;if(msg&&cap)snprintf(msg,cap,"Budget patch validated in memory; no file written");return 1;
}
