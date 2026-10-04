/* Writes ONLY to an explicitly supplied isolated fixture under J:\mods\backup.
 * The original career is copied by the caller and is never passed to run_request. */
#include "../../src/features/operations/career_operations_io.h"
#include <cstdio>
#include <memory>
#include <cstring>
#include <algorithm>
static int failed;
static void check(bool ok,const char*s){printf("%s %s\n",ok?"PASS":"FAIL",s);if(!ok)++failed;}
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put(unsigned char*p,uint32_t x){for(int i=0;i<4;++i)p[i]=(unsigned char)(x>>(i*8));}
static uint32_t crc(const unsigned char*p,size_t n,bool fifa){uint32_t c=~0U;for(size_t i=0;i<n;++i){if(fifa){c^=(uint32_t)p[i]<<24;for(int j=0;j<8;++j)c=(c&0x80000000U)?(c<<1)^0x04C11DB7U:c<<1;}
    else{c^=p[i];for(int j=0;j<8;++j)c=(c>>1)^((c&1)?0xEDB88320U:0);}}return fifa?c:~c;}
static bool fixture_date(std::vector<unsigned char>&data,uint32_t date){size_t cursor=160;
    while(cursor+24<data.size()){if(memcmp(data.data()+cursor,"DB\0\x08\0\0\0\0",8)){++cursor;continue;}
        uint32_t size=word(data.data()+cursor+8),n=word(data.data()+cursor+16);if(size>data.size()-cursor||n>4096)return false;
        for(uint32_t i=0;i<n;++i){const unsigned char*e=data.data()+cursor+24+i*8;if(memcmp(e,"GJUr",4))continue;
            size_t header=cursor+28+(size_t)n*8+word(e+4);unsigned fields=data[header+24];uint32_t stride=word(data.data()+header+4);
            size_t records=header+36+fields*16;for(unsigned j=0;j<fields;++j){const unsigned char*f=data.data()+header+36+j*16;if(memcmp(f+8,"aLZZ",4))continue;
                size_t bit=records*8+word(f+4);unsigned raw=date-20080101;
                for(unsigned k=0;k<19;++k){unsigned char mask=(unsigned char)(1U<<((bit+k)%8));if(raw&(1U<<k))data[(bit+k)/8]|=mask;else data[(bit+k)/8]&=(unsigned char)~mask;}
                size_t checksum=records+stride;if(word(data.data()+checksum)!=0xCDCDCDCDU)put(data.data()+checksum,crc(data.data()+header+36,checksum-header-36,true));
                put(data.data()+0x84,crc(data.data()+160,data.size()-160,false));return true;}}
        cursor+=size;
    }return false;
}
static bool write_fixture(const std::string&path,const std::vector<unsigned char>&data){if(path.rfind("J:\\mods\\backup\\CareerOps-Test-",0)!=0)return false;
    FILE*f=fopen(path.c_str(),"wb");if(!f)return false;bool ok=fwrite(data.data(),1,data.size(),f)==data.size();fclose(f);return ok;}
int main(int argc,char**argv){if(argc!=3||strncmp(argv[1],"J:\\mods\\backup\\CareerOps-Test-",28)||strncmp(argv[2],"J:\\mods\\backup\\CareerOps-Test-",28)){puts("Only isolated backup fixture arguments accepted");return 2;}
    std::string path=argv[1],mod=argv[2],message,request=mod+"\\runtime\\operations\\test.bin";
    CreateDirectoryA((mod+"\\runtime").c_str(),nullptr);CreateDirectoryA((mod+"\\runtime\\operations").c_str(),nullptr);
    std::vector<unsigned char>data;CareerLoanSnapshot initial={};if(!career_ops::read_save(path,data,initial,message)){puts(message.c_str());return 1;}
    /* A real, already-exited parent with a still-held kernel handle. No live
     * FIFA or current test process is killed, impersonated, or waited forever. */
    char command[]="cmd.exe /c exit 0";STARTUPINFOA start={};PROCESS_INFORMATION process={};start.cb=sizeof(start);start.dwFlags=STARTF_USESHOWWINDOW;start.wShowWindow=SW_HIDE;
    if(!CreateProcessA(nullptr,command,nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&start,&process))return 1;
    WaitForSingleObject(process.hProcess,10000);CloseHandle(process.hThread);FILETIME created,exited,kernel,user;ULARGE_INTEGER time;
    GetProcessTimes(process.hProcess,&created,&exited,&kernel,&user);time.LowPart=created.dwLowDateTime;time.HighPart=created.dwHighDateTime;
    auto r=std::make_unique<career_ops::Request>();r->parent=process.dwProcessId;r->parent_created=time.QuadPart;r->club=initial.club;r->manager=initial.manager;r->setup=initial.setup_date;
    r->career_date=initial.date;r->kind=career_ops::LoanCredit;r->terms={1000000,500,6,initial.date,20260211,1};strcpy_s(r->data,path.c_str());
    r->requested_at=career_ops::file_time_now()+600000000ULL;auto original=data;
    check(career_ops::write_request(request,*r,message)&&!career_ops::run_request(request,mod,message),"request requires saving after confirmation; old saved DATA blocked");
    check(career_ops::read_save(path,data,initial,message)&&data==original,"unsaved request leaves every fixture byte unchanged");r->requested_at=0;
    check(career_ops::write_request(request,*r,message),"bounded request + SHA256 persisted in isolated fixture");
    career_ops::test_crash_after_data=true;
    check(!career_ops::run_request(request,mod,message)&&message.find("SIMULATED")!=message.npos,"simulate interruption after DATA but before ledger commit");
    puts(message.c_str());
    career_ops::test_crash_after_data=false;
    check(career_ops::run_request(request,mod,message),"journal recovers ledger without repeating principal");
    puts(message.c_str());
    CareerLoanSnapshot now={};career_ops::read_save(path,data,now,message);
    check(now.transfer_budget==initial.transfer_budget+1000000&&now.wage_budget==initial.wage_budget,"credit applied exactly once, salary preserved");
    check(!career_ops::run_request(request,mod,message),"second principal credit rejected");
    std::string ledger_path=career_ops::ledger_path(mod,path,initial.setup_date,initial.manager);career_ops::Ledger ledger;
    check(career_ops::read_ledger(ledger_path,ledger,message)&&ledger.credited==1&&ledger.paid==0,"committed contract attached to this slot + club + career");
    check(fixture_date(data,20260411)&&write_fixture(path,data),"advance only isolated fixture to three monthly due dates");
    r->kind=career_ops::LoanCollect;career_ops::write_request(request,*r,message);
    check(career_ops::run_request(request,mod,message),"collect three installments in one transaction");
    puts(message.c_str());
    career_ops::read_save(path,data,now,message);career_ops::read_ledger(ledger_path,ledger,message);
    check(now.transfer_budget==initial.transfer_budget+1000000-525000&&ledger.paid==3,"exact amount and paid counter persisted");
    check(career_ops::run_request(request,mod,message),"same career date has no additional installment");
    CareerLoanSnapshot repeated={};career_ops::read_save(path,data,repeated,message);
    check(repeated.transfer_budget==now.transfer_budget,"repeated date did not debit money twice");
    check(fixture_date(data,20260611),"advance isolated fixture to another two due dates");
    CareerLoanSnapshot low={};char detail[256]={};
    check(career_loan_read_save(data.data(),data.size(),&low,detail,sizeof(detail))&&
        career_loan_patch_budget(data.data(),data.size(),&low,100000-(int64_t)low.transfer_budget,&low,detail,sizeof(detail))&&write_fixture(path,data),
        "isolated fixture has insufficient positive transfer budget, CRCs valid");
    auto unchanged=data;
    check(career_ops::run_request(request,mod,message),"insufficient funds leave installments pending without negative budget");
    check(career_ops::read_save(path,data,now,message)&&data==unchanged&&career_ops::read_ledger(ledger_path,ledger,message)&&ledger.paid==3,
        "pending debt changes neither save bytes nor paid count");
    check(fixture_date(data,20260211)&&write_fixture(path,data),"rewind only isolated fixture calendar");unchanged=data;
    check(!career_ops::run_request(request,mod,message),"calendar rewind rejected for reconciliation");
    check(career_ops::read_save(path,data,now,message)&&data==unchanged,"rewind rejection preserves every save byte");
    r->club++;career_ops::write_request(request,*r,message);
    check(!career_ops::run_request(request,mod,message),"different club rejected, never charges another club");
    CloseHandle(process.hProcess);printf("%s: %d failures; only fixture copies were modified.\n",failed?"FAILED":"PASSED",failed);return failed?1:0;
}
