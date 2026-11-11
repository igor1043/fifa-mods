#include <cassert>
#include <iostream>
#include "render.cpp"
static DWORD WINAPI noPad(DWORD,XINPUT_STATE* state){*state={};return ERROR_SUCCESS;}
int wmain(int argc,wchar_t**argv){
 assert(argc==2);readPad=noPad;
 managerface::ValueRect rect;assert(rect.parse("row:487,284,390,24"));
 for(const char*bad:{"row:0,0,1281,20","row:487,710,390,24","row:-1,1,20,20","row:1,1,20,91","row:1,1,20,20junk"})assert(!rect.parse(bad));
 assert(rect.x==487&&rect.y==284&&rect.w==390&&rect.h==24);
 managerface::Camera a,b;
 for(int i=0;i<60;++i)a.update(1,1,.4f,0,1.f/60);
 for(int i=0;i<30;++i)b.update(1,1,.4f,0,1.f/30);
 assert(std::abs(a.angle-b.angle)<.0001f&&std::abs(a.pan-b.pan)<.0001f&&std::abs(a.zoom-b.zoom)<.0001f);
 assert(a.pan>0&&a.zoom>1);for(int i=0;i<200;++i)a.update(0,-1,-1,0,.06f);
 assert(a.pan==-.45f&&a.zoom==.65f);a.update(0,0,0,120,.016f);assert(a.zoom>.65f);
 managerFace.game=argv[1];managerFace.choices={{0,"","Padrão do FIFA",""},{383,"COACH-ABEL","Abel Ferreira","minifaces/abel.png"},{1,"COACH-TITE","Tite","minifaces/tite.png"}};
 managerFace.command("begin");assert(managerFace.preferenceName()==L"Padrão do FIFA");
 managerFace.command("open");managerFace.select(1);managerFace.command("confirm");assert(managerFace.preferenceName()==L"Abel Ferreira");
 managerFace.command("open");managerFace.select(2);managerFace.command("cancel");assert(managerFace.preferenceName()==L"Abel Ferreira");
 managerFace.command("open");managerFace.select(2);managerFace.command("confirm");assert(managerFace.preferenceName()==L"Tite");
 managerFace.command("row:487,284,390,24");assert(managerFace.valueRect.valid);managerFace.command("row_focus");assert(managerFace.valueHighlighted);managerFace.command("row_hide");assert(!managerFace.valueRect.valid);
 managerFace.command("open");clubscene::playerPan=.4f;clubscene::playerZoom=2;clubscene::playerAngle=1;managerFace.command("center");assert(clubscene::playerPan==0&&clubscene::playerZoom==1&&clubscene::playerAngle==0);
 managerFace.command("cancel");std::cout<<"PASS native face value, confirmation/cancellation, native row bounds and frame-independent camera controls\n";
 // A still-loading old animation may never block the native rendering thread.
 std::promise<std::shared_ptr<clubanim::Clip>> pending;managerFace.clip=pending.get_future();
 auto start=GetTickCount64();managerFace.poll(nullptr);assert(GetTickCount64()-start<100);assert(managerFace.clip.valid());pending.set_value(nullptr);
 managerFace.selected=0;managerFace.requested=0;managerFace.poll(nullptr);assert(!managerFace.clip.valid());
 managerFace.select(1);assert(managerFace.requested==-1);managerFace.poll(nullptr);assert(managerFace.requested==-1);
 assert(managerFace.photos.size()==managerFace.choices.size()&&managerFace.badges.size()==managerFace.choices.size());
 std::cout<<"PASS nonblocking animation handoff, rapid-list debounce and per-coach artwork slots\n";
}
