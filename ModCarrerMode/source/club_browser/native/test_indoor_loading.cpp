// Headless WARP rendering of the actual HUD, without launching or driving FIFA.
#include "render.cpp"
#include <cassert>
#include <iostream>
int wmain(int argc,wchar_t** argv){
 assert(argc==3);CoInitializeEx(nullptr,COINIT_MULTITHREADED);
 art.game=argv[1];root=art.game/L"ModCarrerMode/data/club_browser";
 logPath=fs::path(argv[2])/L"loading-test.log";
 auto font=art.game/L"data/ui/fonts/eahelveticaneueconbol-mod.ttf";AddFontResourceExW(font.c_str(),FR_PRIVATE,nullptr);
 ComPtr<ID3D11Device> dev;ComPtr<ID3D11DeviceContext> context;
 assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&dev,nullptr,&context)));
 assert(renderer.init(dev.Get(),root.wstring()));
 gameImage(dev.Get(),renderer.clubIcon,art,{"data/ui/imgAssets/crest/light/l1043.dds"});assert(renderer.clubIcon.view);
 for(int variant:{0,1,2,3}){
  const bool trophy=variant==1,background=variant>=2;
  D3D11_TEXTURE2D_DESC d{};d.Width=2560;d.Height=1080;d.MipLevels=d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_R8G8B8A8_UNORM;d.BindFlags=D3D11_BIND_RENDER_TARGET;
  ComPtr<ID3D11Texture2D> color,copy;ComPtr<ID3D11RenderTargetView> target;
  assert(SUCCEEDED(dev->CreateTexture2D(&d,nullptr,&color))&&SUCCEEDED(dev->CreateRenderTargetView(color.Get(),nullptr,&target)));
  d.BindFlags=0;d.Usage=D3D11_USAGE_STAGING;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;assert(SUCCEEDED(dev->CreateTexture2D(&d,nullptr,&copy)));
  const float gray[]={.1f,.1f,.1f,1};context->ClearRenderTargetView(target.Get(),gray);
  scene_loading::Status s;s.club=1043;s.visible=1;s.loaded=25;s.total=100;s.elapsedMs=10000;
  if(variant==0)s.variant=scene_loading::RoomPreparation|(4<<8);
  if(variant==2){s.total=s.loaded=0;s.variant=scene_loading::RoomPreparation|(1<<8);} // before resource publication
  {clubgfx::UiPass pass(context.Get(),renderer.uiPipeline);renderer.begin(context.Get(),target.Get(),2560,1080);renderer.normal(context.Get());if(background)drawRoomBackgroundLoading(context.Get(),s);else drawIndoorLoading(context.Get(),s,L"Flamengo",trophy);}
  context->CopyResource(copy.Get(),color.Get());D3D11_MAPPED_SUBRESOURCE map{};assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&map)));
  unsigned marked=0,gold=0;std::ofstream out(fs::path(argv[2])/(variant==2?L"background-pending.rgba":variant==3?L"background-loading.rgba":trophy?L"trophy-loading.rgba":L"room-loading.rgba"),std::ios::binary);
  for(unsigned y=0;y<1080;++y){const auto*row=static_cast<unsigned char*>(map.pData)+y*map.RowPitch;
   for(unsigned x=0;x<2560;++x){const auto*p=row+x*4;if(!background&&y<998&&(x<100||x>2460))assert(p[0]<30&&p[1]<30&&p[2]<30);
    if(y>1010)assert(p[0]<30&&p[1]<30&&p[2]<30);
    if(p[0]<250||p[1]<250||p[2]<250)++marked;
    if(std::abs(int(p[0])-185)<3&&std::abs(int(p[1])-162)<3&&std::abs(int(p[2])-116)<3)++gold;
   }out.write(reinterpret_cast<const char*>(row),2560*4);
  }context->Unmap(copy.Get(),0);assert(marked>10000&&gold>50);
 }
 renderer.clear();std::cout<<"PASS indoor HUD: native crisp labels, real club crest, gold ETA, white ultrawide margins, restored graphics state\n";
}
