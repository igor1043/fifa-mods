#define NOMINMAX
#include "career_operations_io.h"
#include "../../platform/mod_paths.h"
#include "../retirement/retirement_engine.h"
#include <bcrypt.h>
#include <tlhelp32.h>
#include <algorithm>
#include <memory>
#include <cstring>
#include <cstdio>
#include <cctype>
namespace career_ops {
#ifdef CAREER_OPS_IO_TEST
bool test_crash_after_data=false;
#endif
namespace {
const size_t max_bytes=64*1024*1024;
std::wstring wide(const std::string&s){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.c_str(),-1,nullptr,0);
    if(!n)return {};std::wstring w(n,L'\0');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.c_str(),-1,&w[0],n);w.pop_back();return w;}
bool read_handle(HANDLE h,std::vector<unsigned char>&out){LARGE_INTEGER n={};out.clear();
    if(!GetFileSizeEx(h,&n)||n.QuadPart<=0||n.QuadPart>(LONGLONG)max_bytes)return false;
    out.resize((size_t)n.QuadPart);size_t at=0;
    while(at<out.size()){DWORD got=0;if(!ReadFile(h,out.data()+at,(DWORD)std::min(size_t(1048576),out.size()-at),&got,nullptr)||!got){out.clear();return false;}at+=got;}return true;}
bool read(const std::string&p,std::vector<unsigned char>&out){auto w=wide(p);if(w.empty())return false;
    HANDLE h=CreateFileW(w.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return false;bool ok=read_handle(h,out);CloseHandle(h);return ok;}
bool hash(const void*p,size_t n,unsigned char*out){BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE h=nullptr;bool ok=false;
    if(n>0xFFFFFFFFU||BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
    if(BCryptCreateHash(alg,&h,nullptr,0,nullptr,0,0)>=0){ok=BCryptHashData(h,(PUCHAR)p,(ULONG)n,0)>=0&&BCryptFinishHash(h,out,32,0)>=0;BCryptDestroyHash(h);}BCryptCloseAlgorithmProvider(alg,0);return ok;}
std::string hex(const unsigned char*p,size_t n){static const char chars[]="0123456789abcdef";std::string s;for(size_t i=0;i<n;++i){s+=chars[p[i]>>4];s+=chars[p[i]&15];}return s;}
bool directory(const std::string&p){auto w=wide(p);return !w.empty()&&(CreateDirectoryW(w.c_str(),nullptr)||GetLastError()==ERROR_ALREADY_EXISTS);}
bool raw_write(const std::string&p,const void*data,size_t size,bool fresh=false){auto w=wide(p);if(w.empty()||size>0xFFFFFFFFU)return false;
    HANDLE h=CreateFileW(w.c_str(),GENERIC_WRITE,0,nullptr,fresh?CREATE_NEW:CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;
    DWORD written=0;bool ok=WriteFile(h,data,(DWORD)size,&written,nullptr)&&written==size&&FlushFileBuffers(h);CloseHandle(h);return ok;}
bool atomic(const std::string&p,const void*data,size_t size){std::string temp=p+".ops-"+std::to_string(GetCurrentProcessId())+".tmp";
    if(!raw_write(temp,data,size,true))return false;bool ok=MoveFileExW(wide(temp).c_str(),wide(p).c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
    if(!ok){DWORD error=GetLastError();DeleteFileW(wide(temp).c_str());SetLastError(error);}return ok;}
template<class T> bool write_record(const std::string&p,const T&r){std::vector<unsigned char>v(sizeof(T)+32);memcpy(v.data(),&r,sizeof(T));
    if(!hash(v.data(),sizeof(T),v.data()+sizeof(T)))return false;return atomic(p,v.data(),v.size());}
template<class T> bool read_record(const std::string&p,T&r){std::vector<unsigned char>v;unsigned char expected[32];
    if(!read(p,v)||v.size()!=sizeof(T)+32||!hash(v.data(),sizeof(T),expected)||memcmp(expected,v.data()+sizeof(T),32))return false;
    memcpy(&r,v.data(),sizeof(T));return true;}
bool no_fifa(){HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
    PROCESSENTRY32W p={};p.dwSize=sizeof(p);bool clear=true;if(!Process32FirstW(snapshot,&p))clear=false;
    else do{if(!_wcsicmp(p.szExeFile,L"fifa16.exe")){clear=false;break;}}while(Process32NextW(snapshot,&p));CloseHandle(snapshot);return clear;}
struct Handles {HANDLE parent=nullptr,mutex=nullptr,index=INVALID_HANDLE_VALUE,data=INVALID_HANDLE_VALUE;bool held=false;
    ~Handles(){if(index!=INVALID_HANDLE_VALUE)CloseHandle(index);if(data!=INVALID_HANDLE_VALUE)CloseHandle(data);if(held)ReleaseMutex(mutex);if(mutex)CloseHandle(mutex);if(parent)CloseHandle(parent);}};
struct Journal {uint32_t magic=0x314A4346,base_exists=0;unsigned char base[32]={},before[32]={},after[32]={};Ledger next;};
bool ledger_valid(const Ledger&l){CareerLoanSchedule s;return l.magic==0x314C4346&&l.version==1&&l.club&&l.credited<=1&&l.events<=121&&
    career_loan_schedule(&l.terms,&s)&&l.paid<=s.count&&l.last_date>=l.terms.contract_date&&l.setup>=20080101;}
void log(const std::string&mod,const std::string&text){career_path_logs(mod.c_str());auto w=wide(mod+"\\logs\\career_operations.log");HANDLE h=CreateFileW(w.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return;std::string s=std::to_string(file_time_now())+" "+text+"\r\n";DWORD written=0;WriteFile(h,s.data(),(DWORD)s.size(),&written,nullptr);CloseHandle(h);}
}
uint64_t file_time_now(){FILETIME ft;ULARGE_INTEGER n;GetSystemTimeAsFileTime(&ft);n.LowPart=ft.dwLowDateTime;n.HighPart=ft.dwHighDateTime;return n.QuadPart;}
bool exists(const std::string&p){auto w=wide(p);return !w.empty()&&GetFileAttributesW(w.c_str())!=INVALID_FILE_ATTRIBUTES;}
bool save_path_valid(const char*p){if(!p||strlen(p)>=1024||strstr(p,"..")||strchr(p,'"'))return false;
    std::string s=p;std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return (char)tolower(c);});
    size_t at=s.rfind("\\fifa16\\");if(at==s.npos||s.size()<3||s[1]!=':'||s[2]!='\\')return false;
    at+=8;size_t end=s.find('\\',at);if(end==s.npos||end-at<1||end-at>8||s.substr(end)!="\\data")return false;
    for(size_t i=at;i<end;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return true;}
bool read_save(const std::string&p,std::vector<unsigned char>&data,CareerLoanSnapshot&s,std::string&message){char text[256]={};
    if(!save_path_valid(p.c_str())||!read(p,data)){message="Save indisponível ou caminho não validado.";return false;}
    bool ok=career_loan_read_save(data.data(),data.size(),&s,text,sizeof(text))!=0;message=text;return ok;}
bool write_request(const std::string&p,const Request&r,std::string&m){if(!write_record(p,r)){m="Não foi possível registrar a solicitação.";return false;}return true;}
bool read_request(const std::string&p,Request&r,std::string&m){if(!read_record(p,r)||r.magic!=0x314F4346||r.version!=1||r.kind<1||r.kind>3||
    r.id_count>60000||r.reset_age>1||!r.parent||!r.parent_created||!memchr(r.data,0,sizeof(r.data))||!save_path_valid(r.data)){m="Solicitação corrompida ou incompatível.";return false;}return true;}
std::string ledger_path(const std::string&mod,const std::string&data,uint32_t setup,uint32_t manager){std::string key=data;
    std::transform(key.begin(),key.end(),key.begin(),[](unsigned char c){return (char)tolower(c);});key+="|"+std::to_string(setup)+"|"+std::to_string(manager);
    unsigned char digest[32];if(!hash(key.data(),key.size(),digest))return {};return mod+"\\runtime\\operations\\loan-"+hex(digest,32)+".bin";}
bool read_ledger(const std::string&p,Ledger&l,std::string&m){if(p.empty()||!read_record(p,l)||!ledger_valid(l)){m="Contrato corrompido/incompatível: operação bloqueada.";return false;}return true;}
bool run_request(const std::string&request_path,const std::string&mod,std::string&message){
    auto r=std::make_unique<Request>();if(request_path.compare(0,mod.size()+20,mod+"\\runtime\\operations\\")!=0||!read_request(request_path,*r,message))return false;
    Handles handles;handles.parent=OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,r->parent);
    if(handles.parent){FILETIME created,exited,kernel,user;ULARGE_INTEGER n;
        if(!GetProcessTimes(handles.parent,&created,&exited,&kernel,&user)){message="Identidade do FIFA indisponível.";return false;}
        n.LowPart=created.dwLowDateTime;n.HighPart=created.dwHighDateTime;
        if(n.QuadPart!=r->parent_created){message="PID foi reutilizado; solicitação cancelada.";return false;}
        log(mod,"waiting_game_exit request="+request_path);
        if(WaitForSingleObject(handles.parent,24*60*60*1000)!=WAIT_OBJECT_0){message="Prazo para fechar o FIFA expirou.";return false;}
    }else if(GetLastError()!=ERROR_INVALID_PARAMETER){message="Não foi possível verificar o processo do FIFA.";return false;}
    if(!no_fifa()){message="Existe outro FIFA aberto; operação bloqueada.";return false;}
    unsigned char digest[32];if(!hash(r->data,strlen(r->data),digest))return false;
    handles.mutex=CreateMutexW(nullptr,FALSE,wide("Local\\FifaCareerOps-"+hex(digest,32)).c_str());
    if(!handles.mutex){message="Mutex indisponível.";return false;}
    DWORD wait=WaitForSingleObject(handles.mutex,30000);if(wait!=WAIT_OBJECT_0&&wait!=WAIT_ABANDONED){message="Outra operação está em andamento.";return false;}handles.held=true;
    std::string data_path=r->data,index_path=data_path.substr(0,data_path.size()-4)+"INDEX";
    handles.index=CreateFileW(wide(index_path).c_str(),GENERIC_READ,0,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    handles.data=CreateFileW(wide(data_path).c_str(),GENERIC_READ,FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(handles.index==INVALID_HANDLE_VALUE||handles.data==INVALID_HANDLE_VALUE){message="DATA/INDEX bloqueados; nada alterado.";return false;}
    std::vector<unsigned char>original,index,patched;CareerLoanSnapshot s;char error[256]={};
    if(!read_handle(handles.data,original)||!read_handle(handles.index,index)||
        !career_loan_read_save(original.data(),original.size(),&s,error,sizeof(error))){message=error;return false;}
    if(s.club!=r->club||s.manager!=r->manager||s.setup_date!=r->setup||s.date<r->career_date){message="Carreira/clube/data mudaram; operação bloqueada.";return false;}
    if(r->requested_at){FILETIME ft;ULARGE_INTEGER time;if(!GetFileTime(handles.data,nullptr,nullptr,&ft))return false;
        time.LowPart=ft.dwLowDateTime;time.HighPart=ft.dwHighDateTime;
        if(time.QuadPart<r->requested_at){message="Salve a carreira após confirmar. Nenhum crédito/aposentadoria foi aplicado.";return false;}}
    patched=original;std::string ledger_file=ledger_path(mod,data_path,s.setup_date,s.manager),journal_file=ledger_file+".journal";
    Ledger ledger,next;Journal journal;bool finance=r->kind!=Retirement;
    if(!hash(original.data(),original.size(),digest))return false;
    if(finance&&exists(journal_file)){
        if(!read_record(journal_file,journal)||journal.magic!=0x314A4346||!ledger_valid(journal.next)){message="Journal financeiro inválido: restauração manual necessária.";return false;}
        if(journal.next.club!=s.club||journal.next.manager!=s.manager||journal.next.setup!=s.setup_date){message="Journal pertence a outra carreira; bloqueado.";return false;}
        if(exists(ledger_file)){Ledger current;unsigned char current_hash[32],next_hash[32];
            if(!read_ledger(ledger_file,current,message)||!hash(&current,sizeof(current),current_hash)||!hash(&journal.next,sizeof(journal.next),next_hash)||
                (memcmp(current_hash,journal.base,32)&&memcmp(current_hash,next_hash,32))){message="Contrato/journal divergentes; recuperação bloqueada.";return false;}}
        else if(journal.base_exists){message="Contrato original ausente; recuperação bloqueada.";return false;}
        if(!memcmp(digest,journal.after,32)){
            if(!write_record(ledger_file,journal.next)){message="DATA já aplicado; journal preservado para recuperar contrato.";return false;}
            DeleteFileW(wide(journal_file).c_str());message="Transação anterior recuperada sem repetir crédito/parcela.";log(mod,message);return true;
        }
        if(memcmp(digest,journal.before,32)){message="Save mudou durante recuperação: operação bloqueada, journal preservado.";return false;}
        /* Before-image still exists: no money was applied. Safe to recompute. */
    }
    if(finance){
        if(exists(ledger_file)){if(!read_ledger(ledger_file,ledger,message))return false;
            if(r->kind==LoanCredit){message="Este save já possui contrato. Crédito duplicado bloqueado.";return false;}}
        else if(r->kind==LoanCollect){message="Nenhum contrato ativo.";return true;}
        else {ledger.club=s.club;ledger.manager=s.manager;ledger.setup=s.setup_date;ledger.terms=r->terms;ledger.last_date=r->terms.contract_date;}
        if(ledger.club!=s.club||ledger.manager!=s.manager||ledger.setup!=s.setup_date||s.date<ledger.last_date){message="Contrato pertence a outro clube ou save voltou no tempo; cobrança bloqueada.";return false;}
        for(uint32_t i=0;i<ledger.events;++i)if(!memcmp(digest,ledger.before[i],32)){message="Backup anterior a uma transação foi restaurado; reconcilie o contrato antes de continuar.";return false;}
        next=ledger;CareerLoanSchedule schedule;uint32_t due=0,money=0;int64_t delta=0;
        if(!career_loan_schedule(&ledger.terms,&schedule)){message="Condições inválidas.";return false;}
        if(!ledger.credited){
            if(!career_loan_due(&schedule,s.date,0,&due,&money))return false;
            delta=(int64_t)ledger.terms.principal-money;next.credited=1;next.paid=due;
        }
        else {if(!career_loan_due(&schedule,s.date,ledger.paid,&due,&money))return false;
            if(!due){message="Nenhuma parcela vencida.";return true;}
            if(money>s.transfer_budget){message="Orçamento insuficiente: parcelas seguem pendentes, sem saldo negativo.";return true;}
            delta=-(int64_t)money;next.paid+=due;}
        next.last_date=s.date;
        CareerLoanSnapshot after;
        if(!career_loan_patch_budget(patched.data(),patched.size(),&s,delta,&after,error,sizeof(error))){message=error;return false;}
        if(next.events>=121){message="Limite de transações atingido.";return false;}
        if(!hash(original.data(),original.size(),next.before[next.events])||!hash(patched.data(),patched.size(),next.after[next.events]))return false;
        ++next.events;journal.base_exists=exists(ledger_file)?1U:0U;
        if(!hash(&ledger,sizeof(ledger),journal.base)||!hash(patched.data(),patched.size(),journal.after))return false;
        memcpy(journal.before,digest,32);journal.next=next;
    }else {
        RetirementApplyResult result={};
        if(!retirement_engine_apply_selection(patched.data(),patched.size(),r->id_count?r->ids:nullptr,r->id_count,r->reset_age,(int)r->target_age,&result)){message=result.message;return false;}
        if(!result.players_changed){message="Seleção já estava correta; nada precisava ser alterado.";return true;}
    }
    /* Backups are outside game/Dev/save folders, before journal or DATA writes. */
    const std::string backups="J:\\mods\\backup\\CareerOperations";
    if(!exists("J:\\mods\\backup")||!directory(backups)){message="Pasta J:\\mods\\backup indisponível; escrita bloqueada.";return false;}
    std::string backup=backups+"\\"+std::to_string(file_time_now())+"-"+std::to_string(GetCurrentProcessId());
    if(!directory(backup)||!raw_write(backup+"\\DATA",original.data(),original.size(),true)||!raw_write(backup+"\\INDEX",index.data(),index.size(),true)){
        message="Backup DATA/INDEX falhou; save preservado.";return false;}
    if(finance&&!write_record(journal_file,journal)){message="Journal não pôde ser gravado; save preservado.";return false;}
    /* Windows rejects replacing our own locked destination (ERROR_ACCESS_DENIED).
     * Release DATA only after validation+backup+journal; retain the exclusive
     * INDEX handle and per-career mutex through the rename and verification.
     * The verified parent has exited, and another FIFA is rejected below. */
    CloseHandle(handles.data);handles.data=INVALID_HANDLE_VALUE;
    if(!no_fifa()||!atomic(data_path,patched.data(),patched.size())){message="Escrita atômica bloqueada (Windows "+std::to_string(GetLastError())+"); backup preservado.";return false;}
    std::vector<unsigned char>verify;unsigned char expected[32],actual[32];hash(patched.data(),patched.size(),expected);
    if(!read(data_path,verify)||!hash(verify.data(),verify.size(),actual)||memcmp(expected,actual,32)){
        bool restored=atomic(data_path,original.data(),original.size());message=restored?"Pós-validação falhou; DATA original restaurado.":"Pós-validação falhou; restaure DATA/INDEX do backup.";return false;}
#ifdef CAREER_OPS_IO_TEST
    if(finance&&test_crash_after_data){message="SIMULATED crash after DATA and before ledger commit";return false;}
#endif
    if(finance){if(!write_record(ledger_file,next)){message="Save aplicado; contrato pendente de recuperação pelo journal. Não apagar journal.";return false;}
        DeleteFileW(wide(journal_file).c_str());}
    message=(finance?"Financeiro":"Aposentadoria")+std::string(" aplicado e validado. Backup: ")+backup;
    log(mod,message);return true;
}
}
