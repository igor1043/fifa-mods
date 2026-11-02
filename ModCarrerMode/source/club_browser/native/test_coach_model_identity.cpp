#include <cassert>
#include <iostream>
#include "render.cpp"
int main(){
 auto temp=std::filesystem::temp_directory_path()/(L"coach-identity-"+std::to_wstring(GetCurrentProcessId()));std::filesystem::create_directories(temp);
 clublineup::View worker;worker.configure(temp);worker.child=OpenProcess(SYNCHRONIZE,FALSE,GetCurrentProcessId());assert(worker.running());clubcoach::View view;view.request(worker,1629,1043);
 auto ready=[&](const std::string&actor,const std::string&hash){std::ofstream profile(worker.folder/L"coach.tsv",std::ios::binary);profile<<"S16COACH1\t1629\tGremio\nF\tname\tCoach\nS\ttotal\t0\t0\t0\t0\t0\t0\t0\nS\thome\t0\t0\t0\t0\t0\t0\t0\nS\taway\t0\t0\t0\t0\t0\t0\t0\n";profile.close();std::ofstream out(worker.folder/L"status.tsv",std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<worker.sequence<<"\nclub=1629\nstatus=ready\nkind=coach\ncareer=1043\nprofile_revision=same\nactor="<<actor<<"\nhash="<<hash<<"\nplayer=100001629\nrenderer=native\nheight=180\npages=1\nbindings=0";for(int i=1;i<96;++i)out<<",0";out<<"\n";worker.lastPoll=0;};
 ready("1",std::string(64,'a'));view.poll(worker,nullptr);assert(view.ready&&view.submitted==worker.sequence);auto old=worker.sequence;
 // Same profile revision: an independently completed model must still refresh.
 ready("1",std::string(64,'b'));clubscene::requested=true;view.poll(worker,nullptr);assert(worker.sequence>old&&!clubscene::requested&&!view.submitted);
 ready("1",std::string(64,'b'));view.poll(worker,nullptr);assert(view.submitted==worker.sequence);old=worker.sequence;
 ready("0","");clubscene::requested=true;view.poll(worker,nullptr);assert(worker.sequence>old&&!clubscene::requested&&!view.submitted);
 ready("0","");view.poll(worker,nullptr);assert(view.ready&&!view.submitted&&!clubscene::requested);
 worker.stop();std::filesystem::remove_all(temp);clubscene::pending.reset();std::cout<<"PASS coach identity change and missing model hide predecessor without reusing native object\n";
}
