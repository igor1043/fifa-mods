#pragma once
#include <cstdint>
#include <string>
#include <sstream>

namespace gallery_postfx {
// A process-scoped comparison request never survives into another FIFA run.
inline unsigned testMode(const std::string& text,unsigned pid){
 std::istringstream in(text);std::string magic,extra;unsigned version=0,owner=0,mode=0;
 if(!(in>>magic>>version>>owner>>mode)||in>>extra||magic!="S16GALLERYTEST"||version!=1||owner!=pid||mode>4)return 0;
 return mode;
}
inline bool bridge(unsigned mode){return mode!=1&&mode!=3;}
inline bool optics(unsigned mode){return mode!=2&&mode!=3;}
struct Lease {
 int state=-1;uint64_t next=0;
 template<class Execute>void update(bool enabled,uint64_t now,Execute execute){
  if(state==int(enabled)&&(!enabled||now<next))return;
  // These effects grade/distort the camera image. Native SSAO and both shadow
  // systems are deliberately outside this lease and retain their own state.
  std::string code="do local as=gSportsRNA;if as then local t=as:GetTable('Settings');S16GalleryPostFX=S16GalleryPostFX or {saved={}};local s=S16GalleryPostFX;s.observed=s.observed or {};local active=";
  code+=enabled?"true":"false";
  code+=";for _,k in ipairs({'PostFX_DOF','PostFX_Rectilinear','PostFX_MotionBlur','PostFX_ColorCubeDepth'}) do if active then if s.saved[k]==nil then s.saved[k]=as:GetInt(t,k) end;if as:GetInt(t,k)~=0 then as:SetInt(t,k,0) end elseif s.saved[k]~=nil then if as:GetInt(t,k)==0 then as:SetInt(t,k,s.saved[k]) end;s.saved[k]=nil end;s.observed[k]=as:GetInt(t,k) end;s.active=active end end";
  if(execute(code.c_str())){state=int(enabled);next=now+500;}
 }
};
}
