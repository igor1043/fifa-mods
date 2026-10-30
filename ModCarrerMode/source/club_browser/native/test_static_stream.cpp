#include <cassert>
#include <iostream>
#include "render.cpp"

static void gpu(const std::filesystem::path&path){
 auto clip=clubanim::load(path,0);assert(clip&&clip->constant&&clip->count==2);assert(!clubanim::load(path,123));
 ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;assert(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)));
 auto&t=clip->tracks[0];auto bytes=t.expandedInitial;D3D11_BUFFER_DESC desc{};desc.ByteWidth=UINT(bytes.size());desc.BindFlags=D3D11_BIND_VERTEX_BUFFER;desc.Usage=D3D11_USAGE_IMMUTABLE;D3D11_SUBRESOURCE_DATA init{bytes.data(),0,0};ID3D11Buffer*source=nullptr;assert(SUCCEEDED(d->CreateBuffer(&desc,&init,&source)));
 auto read=[&](ID3D11Buffer*b){D3D11_BUFFER_DESC desc{};b->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ID3D11Buffer*stage=nullptr;assert(SUCCEEDED(d->CreateBuffer(&desc,nullptr,&stage)));c->CopyResource(stage,b);D3D11_MAPPED_SUBRESOURCE m{};assert(SUCCEEDED(c->Map(stage,0,D3D11_MAP_READ,0,&m)));std::vector<unsigned char>out((unsigned char*)m.pData,(unsigned char*)m.pData+desc.ByteWidth);c->Unmap(stage,0);stage->Release();return out;};
 auto bind=[&](){UINT stride=28,offset=0;c->IASetVertexBuffers(0,1,&source,&stride,&offset);};
 auto bound=[&](){ID3D11Buffer*b=nullptr;UINT stride,offset;c->IAGetVertexBuffers(0,1,&b,&stride,&offset);if(b)b->Release();return b;};
 clubanim::enabled=true;clubanim::activate(clip);clubanim::setVisible(true);
 for(unsigned frame=0;frame<600;++frame){
  clubanim::prepareNativeDraw(c,1000+frame*17);bind();assert(bound()!=source&&clip->captured==1);
  if(frame%60==0){assert(read(bound())==bytes);assert(read(source)==bytes);auto h=clubanim::original(c);assert(clubanim::replace(h.table+18,(void*)&clubanim::bindVertices,(void*)h.bind));}
 }
 assert(read(bound())==bytes&&read(source)==bytes);assert(clip->updates>=600);
 clubanim::setVisible(false);bind();assert(bound()==source);clubanim::stop();UINT stride=28,offset=0;ID3D11Buffer*none=nullptr;c->IASetVertexBuffers(0,1,&none,&stride,&offset);source->Release();clip.reset();c->Release();d->Release();
}

int wmain(int argc,wchar_t**argv){
 _set_error_mode(_OUT_TO_STDERR);assert(argc==3);gpu(argv[1]);gpu(argv[2]);
 // Async preparation uses the same request/session validation as the roster.
 auto temp=std::filesystem::temp_directory_path()/(L"static-stream-"+std::to_wstring(GetCurrentProcessId()));auto hash=std::string(64,'b');auto path=temp/L"data/sceneassets/server16_club_xi"/std::to_wstring(GetCurrentProcessId())/hash;std::filesystem::create_directories(path);std::filesystem::copy_file(argv[1],path/L"animation.bin",std::filesystem::copy_options::overwrite_existing);
 clublineup::View worker;worker.configure(temp);worker.child=OpenProcess(SYNCHRONIZE,FALSE,GetCurrentProcessId());worker.career=111046;std::string bindings="0";for(int i=1;i<96;++i)bindings+=",0";
 auto ready=[&](bool mascot){std::ofstream out(worker.folder/L"status.tsv",std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<worker.sequence<<"\nclub="<<worker.club<<"\nstatus=ready\ncareer=111046\nrenderer=native\nhash="<<hash<<"\npages=1\nbindings="<<bindings<<"\nstable_stream=1\n"<<(mascot?"kind=mascot\nactor=1\nheight=180\n":"players=11\n");};
 worker.request(1043);ready(false);for(int i=0;i<5000&&worker.status!="ready";++i){worker.poll(nullptr);Sleep(1);}assert(worker.status=="ready");assert(clubscene::pending&&clubscene::pending->club==1043&&clubscene::pending->career==111046&&clubscene::pending->animation&&clubscene::pending->animation->constant);
 clubmascot::View mascot;mascot.enter(worker,1629,111046);ready(true);for(int i=0;i<5000&&!mascot.submitted;++i){mascot.poll(worker,nullptr);Sleep(1);}assert(mascot.submitted&&clubscene::pending->club==1629&&clubscene::pending->career==111046&&clubscene::pending->animation&&clubscene::pending->animation->constant);
 mascot.enter(worker,567,111046);{std::ofstream out(worker.folder/L"status.tsv",std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\nseq="<<worker.sequence<<"\nclub=567\nstatus=ready\nkind=mascot\ncareer=111046\nactor=0\n";}mascot.poll(worker,nullptr);assert(mascot.ready&&!mascot.submitted&&!clubscene::requested);
 worker.stop();clubscene::pending.reset();assert(temp.is_absolute()&&std::filesystem::equivalent(temp.parent_path(),std::filesystem::temp_directory_path()));std::filesystem::remove_all(temp);
 std::cout<<"PASS static scenes: mascot and XI use persistent DISCARD buffers across 1200 GPU frames; pose/UV/normal bytes unchanged; native dispatch rearmed; async club/session checks; missing mascot hides model\n";
}
