#pragma once
#include "../finance/career_loan_engine.h"
#include <windows.h>
#include <string>
#include <vector>
#include <cstdint>
namespace career_ops {
enum Kind {Retirement=1,LoanCredit=2,LoanCollect=3};
struct Request {
    uint32_t magic=0x314F4346,version=1,kind=0,club=0,manager=0,setup=0,career_date=0;
    uint32_t parent=0,reset_age=0,target_age=18,id_count=0;
    uint64_t parent_created=0,requested_at=0;
    CareerLoanTerms terms={};
    char data[1024]={};
    uint32_t ids[60000]={};
};
struct Ledger {
    uint32_t magic=0x314C4346,version=1,club=0,manager=0,setup=0,paid=0,last_date=0;
    CareerLoanTerms terms={};
    uint32_t credited=0,events=0;
    unsigned char before[121][32]={},after[121][32]={};
};
bool read_save(const std::string&,std::vector<unsigned char>&,CareerLoanSnapshot&,std::string&);
bool write_request(const std::string&,const Request&,std::string&);
bool read_request(const std::string&,Request&,std::string&);
std::string ledger_path(const std::string&mod,const std::string&data,uint32_t setup,uint32_t manager);
bool read_ledger(const std::string&,Ledger&,std::string&);
bool exists(const std::string&);
bool run_request(const std::string&request_path,const std::string&mod,std::string&message);
bool save_path_valid(const char*);
uint64_t file_time_now();
#ifdef CAREER_OPS_IO_TEST
extern bool test_crash_after_data;
#endif
}
