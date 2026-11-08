#include "competitions_footer.h"
#include <cassert>
#include <fstream>
#include <iostream>
int wmain(int argc,wchar_t**argv){
 assert(argc==2);namespace fs=std::filesystem;fs::path root=argv[1];assert(fs::exists(root));
 auto source=root/L"ModCarrerMode/data/club_browser/competition_help";
 auto target=root/L"data/ui/game/screens/career/server16";fs::create_directories(source);fs::create_directories(target);
 for(int mode=0;mode<5;++mode){std::ofstream out(source/(L"mode_"+std::to_wstring(mode)+L".big"));out<<mode;}
 assert(clubcomp::helpMode(false,true,true,true)==0);
 assert(clubcomp::helpMode(true,false,false,false)==1);
 assert(clubcomp::helpMode(true,true,true,true)==2);
 assert(clubcomp::helpMode(true,false,true,true)==3);
 assert(clubcomp::helpMode(true,false,false,true)==4);
 clubcomp::FooterPublication pub;
 for(int mode=0;mode<5;++mode){assert(pub.publish(root,mode,10000+mode));assert(!pub.publish(root,mode,10000+mode));
  for(int slot=0;slot<2;++slot){int value=-1;std::ifstream in(target/(L"competitionhelp"+std::to_wstring(slot)+L".big"));in>>value;assert(value==mode);}}
 assert(!pub.publish(root,9,20000));pub.reset();assert(pub.publish(root,1,20001));
 fs::remove(source/L"mode_2.big");assert(!pub.publish(root,2,21000));assert(pub.last==1);assert(!pub.publish(root,2,21500));
 std::cout<<"FIFA footer metadata: five real modes, fixed two-file publication, no repeated writes, failed publication retries OK\n";
}
