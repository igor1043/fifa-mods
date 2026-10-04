#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "fifa_player_renderer.h"
#include <d3dcompiler.h>
#include <DirectXMath.h>
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
using namespace DirectX;
namespace fifa_player {
template<class T> static void drop(T *&p){if(p)p->Release();p=nullptr;}
struct GpuVertex {float x,y,z,nx,ny,nz,u,v;};
struct Constants {XMFLOAT4X4 wvp,world,light_wvp;XMFLOAT4 color,parameters;};
static const char shader[]=R"(
cbuffer Settings:register(b0){float4x4 WVP;float4x4 World;float4x4 LightWVP;float4 Tint;float4 Parameters;};
struct Input{float3 p:POSITION;float3 n:NORMAL;float2 uv:TEXCOORD0;};
struct Output{float4 p:SV_POSITION;float3 n:NORMAL;float2 uv:TEXCOORD0;float3 w:TEXCOORD1;float4 light:TEXCOORD2;};
Output vertex(Input i){Output o;o.p=mul(float4(i.p,1),WVP);o.n=mul(float4(i.n,0),World).xyz;o.uv=i.uv;o.w=mul(float4(i.p,1),World).xyz;o.light=mul(float4(i.p,1),LightWVP);return o;}
Texture2D Diffuse:register(t0);SamplerState Linear:register(s0);
Texture2D<float> Shadow:register(t1);SamplerComparisonState ShadowCompare:register(s1);
Texture2D HairCoeff:register(t2);
float hairCoverage(float2 uv,float diffuseAlpha){return Parameters.y>0?HairCoeff.Sample(Linear,uv).r:saturate(diffuseAlpha*Parameters.x);}
float visibility(Output i){float3 p=i.light.xyz/i.light.w;float2 uv=p.xy*float2(.5,-.5)+.5;
if(any(uv<0)||any(uv>1)||p.z<0||p.z>1)return 1;
float sum=0;[unroll]for(int y=-1;y<=1;y++)[unroll]for(int x=-1;x<=1;x++)sum+=Shadow.SampleCmpLevelZero(ShadowCompare,uv+float2(x,y)/1024,p.z-.0015);
return sum/9;}
void shadowPixel(Output i){float a=Diffuse.Sample(Linear,i.uv).a;clip((Tint.w>=6?hairCoverage(i.uv,a):a)-.35);}
float4 pixel(Output i):SV_TARGET{
if(Tint.w==2){float radial=dot(i.uv*2-1,i.uv*2-1);clip(1-radial);return float4(.035,.05,.045,.38*pow(saturate(1-radial),2));}
if(Tint.w==3){
 float2 cell=floor(i.w.xz*3);float grain=frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453);
 float mow=.92+.08*step(0,sin(i.w.z*.065));
 /* The office XI sits over a photo that already contains a pitch. Fade only
  * its procedural foreground from that photographic horizon into solid turf. */
 float alpha=Parameters.w>.5?smoothstep(-500,0,i.w.z):1;
 return float4(Tint.rgb*(.78+.22*grain)*mow*(.48+.52*visibility(i)),alpha);}
if(Tint.w==4)return float4(Tint.rgb*(.68+.32*visibility(i)),1);
float4 c=Diffuse.Sample(Linear,i.uv);
if(Tint.w==5){clip(c.a-.005);return float4(c.rgb*.96,c.a);}
if(Tint.w>=6){c.a=hairCoverage(i.uv,c.a);
 if(Tint.w==6)clip(c.a-.8);else {clip(c.a-.015);clip(.8-c.a-.00001);}}
else clip(c.a-(Tint.w>0?.025:.35));
float3 n=normalize(i.n),key=normalize(float3(-.4,.65,.8)),fill=normalize(float3(.65,.2,.7));
float lit=.32+.55*saturate(dot(n,key))*visibility(i)+.13*saturate(dot(n,fill));
if(Parameters.z>0)lit=(.78+.16*saturate(dot(n,float3(0,.8,.6)))+.06*saturate(dot(n,fill)))*(.88+.12*visibility(i));
if(Tint.w>=6)lit=.40+.43*abs(dot(n,key))*visibility(i)+.17*abs(dot(n,fill));
float rim=.07*pow(1-saturate(n.z),3)*saturate(n.y+.3);
float3 light=float3(lit+rim,lit+rim*.95,lit+rim*.88);
return float4(c.rgb*Tint.rgb*light,Tint.w==1||Tint.w==7?c.a:1);}
)";
void Renderer::release_model(){
    for(auto &m:meshes_){drop(m.vertices);drop(m.indices);}meshes_.clear();framing_points_.clear();framing_parts_.clear();fitted_width_=0;
    for(auto &t:textures_)drop(t);textures_.clear();model_.reset();
}
void Renderer::release_device(){
    release_model();drop(commands_);drop(vs_);drop(ps_);drop(shadow_ps_);drop(layout_);drop(constants_);
    drop(sampler_);drop(shadow_sampler_);drop(raster_);drop(depth_state_);drop(strand_depth_);drop(strand_blend_);drop(white_);drop(image_);drop(target_);drop(depth_);drop(shadow_depth_);drop(shadow_image_);
    drop(device_);width_=height_=0;
}
void Renderer::device(ID3D11Device *d){if(d==device_)return;release_device();device_=d;if(d)d->AddRef();}
bool Renderer::initialize(){
    if(vs_)return true;if(!device_)return false;
    ID3DBlob *vb=nullptr,*pb=nullptr,*shadow_blob=nullptr,*errors=nullptr;
    HRESULT hr=D3DCompile(shader,sizeof(shader)-1,"club-player",nullptr,nullptr,"vertex","vs_4_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&vb,&errors);drop(errors);
    if(SUCCEEDED(hr))hr=D3DCompile(shader,sizeof(shader)-1,"club-player",nullptr,nullptr,"pixel","ps_4_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&pb,&errors);drop(errors);
    if(SUCCEEDED(hr))hr=D3DCompile(shader,sizeof(shader)-1,"club-player",nullptr,nullptr,"shadowPixel","ps_4_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&shadow_blob,&errors);drop(errors);
    if(FAILED(hr)){drop(vb);drop(pb);drop(shadow_blob);return false;}
    hr=device_->CreateVertexShader(vb->GetBufferPointer(),vb->GetBufferSize(),nullptr,&vs_);
    if(SUCCEEDED(hr))hr=device_->CreatePixelShader(pb->GetBufferPointer(),pb->GetBufferSize(),nullptr,&ps_);
    if(SUCCEEDED(hr))hr=device_->CreatePixelShader(shadow_blob->GetBufferPointer(),shadow_blob->GetBufferSize(),nullptr,&shadow_ps_);drop(shadow_blob);
    D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},
        {"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0},
        {"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D11_INPUT_PER_VERTEX_DATA,0}};
    if(SUCCEEDED(hr))hr=device_->CreateInputLayout(elements,3,vb->GetBufferPointer(),vb->GetBufferSize(),&layout_);drop(vb);drop(pb);
    D3D11_BUFFER_DESC cb={};cb.ByteWidth=sizeof(Constants);cb.Usage=D3D11_USAGE_DEFAULT;cb.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
    if(SUCCEEDED(hr))hr=device_->CreateBuffer(&cb,nullptr,&constants_);
    D3D11_SAMPLER_DESC sd={};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_WRAP;sd.MaxLOD=D3D11_FLOAT32_MAX;
    if(SUCCEEDED(hr))hr=device_->CreateSamplerState(&sd,&sampler_);
    sd.Filter=D3D11_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT;sd.ComparisonFunc=D3D11_COMPARISON_LESS_EQUAL;
    sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_BORDER;for(float&c:sd.BorderColor)c=1;
    if(SUCCEEDED(hr))hr=device_->CreateSamplerState(&sd,&shadow_sampler_);
    D3D11_RASTERIZER_DESC rd={};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;
    if(SUCCEEDED(hr))hr=device_->CreateRasterizerState(&rd,&raster_);
    D3D11_DEPTH_STENCIL_DESC dd={};dd.DepthEnable=TRUE;dd.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;dd.DepthFunc=D3D11_COMPARISON_LESS;
    if(SUCCEEDED(hr))hr=device_->CreateDepthStencilState(&dd,&depth_state_);
    dd.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;dd.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
    if(SUCCEEDED(hr))hr=device_->CreateDepthStencilState(&dd,&strand_depth_);
    D3D11_BLEND_DESC blend={};auto &rt=blend.RenderTarget[0];rt.BlendEnable=TRUE;
    rt.SrcBlend=D3D11_BLEND_SRC_ALPHA;rt.DestBlend=D3D11_BLEND_INV_SRC_ALPHA;rt.BlendOp=D3D11_BLEND_OP_ADD;
    rt.SrcBlendAlpha=D3D11_BLEND_ONE;rt.DestBlendAlpha=D3D11_BLEND_INV_SRC_ALPHA;rt.BlendOpAlpha=D3D11_BLEND_OP_ADD;
    rt.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;
    if(SUCCEEDED(hr))hr=device_->CreateBlendState(&blend,&strand_blend_);
    if(SUCCEEDED(hr))hr=device_->CreateDeferredContext(0,&commands_);
    uint32_t white=0xffffffff;D3D11_TEXTURE2D_DESC td={};td.Width=td.Height=td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;td.BindFlags=D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA data={&white,4,4};ID3D11Texture2D *texture=nullptr;
    if(SUCCEEDED(hr))hr=device_->CreateTexture2D(&td,&data,&texture);
    if(SUCCEEDED(hr))hr=device_->CreateShaderResourceView(texture,nullptr,&white_);drop(texture);
    td.Width=td.Height=1024;td.Format=DXGI_FORMAT_R32_TYPELESS;td.BindFlags=D3D11_BIND_DEPTH_STENCIL|D3D11_BIND_SHADER_RESOURCE;
    if(SUCCEEDED(hr))hr=device_->CreateTexture2D(&td,nullptr,&texture);
    D3D11_DEPTH_STENCIL_VIEW_DESC shadow_dsv={};shadow_dsv.Format=DXGI_FORMAT_D32_FLOAT;shadow_dsv.ViewDimension=D3D11_DSV_DIMENSION_TEXTURE2D;
    if(SUCCEEDED(hr))hr=device_->CreateDepthStencilView(texture,&shadow_dsv,&shadow_depth_);
    D3D11_SHADER_RESOURCE_VIEW_DESC shadow_srv={};shadow_srv.Format=DXGI_FORMAT_R32_FLOAT;shadow_srv.ViewDimension=D3D11_SRV_DIMENSION_TEXTURE2D;shadow_srv.Texture2D.MipLevels=1;
    if(SUCCEEDED(hr))hr=device_->CreateShaderResourceView(texture,&shadow_srv,&shadow_image_);drop(texture);
    if(FAILED(hr)){ID3D11Device *saved=device_;saved->AddRef();release_device();device_=saved;return false;}
    return true;
}
bool Renderer::target(UINT w,UINT h){
    if(target_&&w==width_&&h==height_)return true;
    drop(image_);drop(target_);drop(depth_);width_=height_=0;
    D3D11_TEXTURE2D_DESC td={};td.Width=w;td.Height=h;td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count=1;td.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D *t=nullptr;HRESULT hr=device_->CreateTexture2D(&td,nullptr,&t);
    if(SUCCEEDED(hr))hr=device_->CreateRenderTargetView(t,nullptr,&target_);
    if(SUCCEEDED(hr))hr=device_->CreateShaderResourceView(t,nullptr,&image_);drop(t);
    td.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;td.BindFlags=D3D11_BIND_DEPTH_STENCIL;
    if(SUCCEEDED(hr))hr=device_->CreateTexture2D(&td,nullptr,&t);
    if(SUCCEEDED(hr))hr=device_->CreateDepthStencilView(t,nullptr,&depth_);drop(t);
    if(FAILED(hr))return false;width_=w;height_=h;return true;
}
bool Renderer::model(std::shared_ptr<const Model> model){
    if(model==model_)return !meshes_.empty();release_model();if(!model||!initialize())return false;
    low_=FLT_MAX;high_=-FLT_MAX;float horizontal=0;stadium_radius_=1;
    for(const auto &tex:model->textures){
        if(tex.bytes.empty()){textures_.push_back(nullptr);continue;}
        D3D11_TEXTURE2D_DESC d={};d.Width=tex.width;d.Height=tex.height;d.MipLevels=d.ArraySize=1;
        d.Format=tex.format==0?DXGI_FORMAT_BC1_UNORM:tex.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;
        d.SampleDesc.Count=1;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;d.Usage=D3D11_USAGE_IMMUTABLE;
        D3D11_SUBRESOURCE_DATA data={tex.bytes.data(),((tex.width+3)/4)*(tex.format?16:8),(UINT)tex.bytes.size()};
        ID3D11Texture2D *t=nullptr;ID3D11ShaderResourceView *view=nullptr;
        if(SUCCEEDED(device_->CreateTexture2D(&d,&data,&t)))device_->CreateShaderResourceView(t,nullptr,&view);
        drop(t);textures_.push_back(view);
    }
    for(const auto &p:model->parts){
        if(p.vertices.empty()||p.indices.empty())continue;
        Vec3 part_min={FLT_MAX,FLT_MAX,FLT_MAX},part_max={-FLT_MAX,-FLT_MAX,-FLT_MAX};
        std::vector<GpuVertex> v(p.vertices.size());
        for(size_t i=0;i<v.size();++i){auto a=p.vertices[i];v[i]={a.position.x,a.position.y,a.position.z,a.normal.x,a.normal.y,a.normal.z,a.u,a.v};
            low_=std::min(low_,a.position.y);high_=std::max(high_,a.position.y);horizontal=std::max(horizontal,std::fabs(a.position.x)*2);
            if(model->room==RoomStadium){horizontal=std::max(horizontal,std::fabs(a.position.z)*2);stadium_radius_=std::max(stadium_radius_,sqrtf(a.position.x*a.position.x+a.position.y*a.position.y+a.position.z*a.position.z));}
            part_min.x=std::min(part_min.x,a.position.x);part_max.x=std::max(part_max.x,a.position.x);
            part_min.y=std::min(part_min.y,a.position.y);part_max.y=std::max(part_max.y,a.position.y);
            part_min.z=std::min(part_min.z,a.position.z);part_max.z=std::max(part_max.z,a.position.z);}
        /* Fit the original vertices, not imaginary corners joining a raised
         * hand to a toe. Cached support planes also keep zoom/pan cheap. */
        framing_parts_.push_back({framing_points_.size(),p.vertices.size(),part_max.y});
        for(const auto&vertex:p.vertices)framing_points_.push_back(vertex.position);
        if(!p.native_normals)for(size_t i=0;i<p.indices.size();i+=3){auto &a=v[p.indices[i]],&b=v[p.indices[i+1]],&c=v[p.indices[i+2]];
            float x1=b.x-a.x,y1=b.y-a.y,z1=b.z-a.z,x2=c.x-a.x,y2=c.y-a.y,z2=c.z-a.z;
            float nx=y1*z2-z1*y2,ny=z1*x2-x1*z2,nz=x1*y2-y1*x2;
            for(size_t j=0;j<3;++j){auto &q=v[p.indices[i+j]];q.nx+=nx;q.ny+=ny;q.nz+=nz;}}
        for(auto &a:v){float len=std::sqrt(a.nx*a.nx+a.ny*a.ny+a.nz*a.nz);if(len>1e-8f){a.nx/=len;a.ny/=len;a.nz/=len;}else a.nz=1;}
        Mesh m;m.count=(UINT)p.indices.size();m.texture=p.texture;m.color=p.color;m.tint=p.tint;m.blend=p.blend;
        m.alpha_scale=p.alpha_scale;
        m.hair_coeff_texture=p.hair_coeff_texture;
        m.hair=p.asset.find("/hair/")!=p.asset.npos;
        m.actor=p.asset.rfind("mod/coach-arrival/source/",0)==0;
        /* A custom RX3 may combine cap and lashes in ONE unnamed submesh.
         * All hair uses a depth-writing coverage core and sorted soft edges,
         * rather than assuming its first submesh is wholly opaque. */
        if(m.hair)m.blend=true;
        for(const auto&a:v){m.center.x+=a.x/v.size();m.center.y+=a.y/v.size();m.center.z+=a.z/v.size();}
        if(m.hair&&m.blend) {
            m.strand_indices=p.indices;
            for(size_t i=0;i<p.indices.size();i+=3){const auto&a=v[p.indices[i]],&b=v[p.indices[i+1]],&c=v[p.indices[i+2]];
                m.strand_centers.push_back({(a.x+b.x+c.x)/3,(a.y+b.y+c.y)/3,(a.z+b.z+c.z)/3});}
        }
        D3D11_BUFFER_DESC bd={};bd.ByteWidth=(UINT)(v.size()*sizeof(GpuVertex));bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA data={v.data(),0,0};HRESULT hr=device_->CreateBuffer(&bd,&data,&m.vertices);
        bd.ByteWidth=(UINT)(p.indices.size()*sizeof(uint32_t));bd.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=p.indices.data();
        if(!m.strand_indices.empty())bd.Usage=D3D11_USAGE_DEFAULT;
        if(SUCCEEDED(hr))hr=device_->CreateBuffer(&bd,&data,&m.indices);
        if(FAILED(hr)){drop(m.vertices);drop(m.indices);release_model();return false;}meshes_.push_back(m);
    }
    if(meshes_.empty()){release_model();return false;}
    /* Renderer-owned scenery: never modifies original RX3s, kits or the DB.
     * Colours and crest belong to this Model's current club, not a fixed team. */
    auto quad=[&](const GpuVertex (&v)[4],int surface,Vec3 color,int texture=-1)->bool {
        const uint32_t indices[6]={0,1,2,0,2,3};Mesh m;m.count=6;m.texture=texture;m.color=color;m.tint={1,1,1};m.blend=surface==2||surface==5;m.surface=surface;
        for(const auto&a:v){m.center.x+=a.x*.25f;m.center.y+=a.y*.25f;m.center.z+=a.z*.25f;}
        D3D11_BUFFER_DESC bd={};bd.ByteWidth=sizeof(v);bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA data={v,0,0};HRESULT hr=device_->CreateBuffer(&bd,&data,&m.vertices);
        bd.ByteWidth=sizeof(indices);bd.BindFlags=D3D11_BIND_INDEX_BUFFER;data.pSysMem=indices;
        if(SUCCEEDED(hr))hr=device_->CreateBuffer(&bd,&data,&m.indices);
        if(FAILED(hr)){drop(m.vertices);drop(m.indices);return false;}meshes_.push_back(m);return true;
    };
    auto stage_quad=[&](float x,float z,float rx,float rz,float y,int surface)->bool {
        GpuVertex v[4]={{x-rx,y,z-rz,0,1,0,0,0},{x+rx,y,z-rz,0,1,0,1,0},
            {x+rx,y,z+rz,0,1,0,1,1},{x-rx,y,z+rz,0,1,0,0,1}};
        return quad(v,surface,{.16f,.38f,.065f});
    };
    auto wall_quad=[&](float x0,float x1,float y0,float y1,float z,Vec3 color,int texture=-1)->bool {
        GpuVertex v[4]={{x0,y1,z,0,0,1,0,0},{x1,y1,z,0,0,1,1,0},
            {x1,y0,z,0,0,1,1,1},{x0,y0,z,0,0,1,0,1}};
        return quad(v,texture<0?4:5,color,texture);
    };
    if(model->room==RoomPhoto||model->room==RoomOfficeLineup||model->room==RoomFullSquadPhoto) {
    float floor_half=std::max(1400.f,horizontal*4.f),wall_half=std::max(550.f,horizontal*2.5f);
    float wall_z=model->room==RoomFullSquadPhoto?-300.f:-105.f,wall_top=high_+250.f;
    /* Extend beyond every viewport edge, including the foreground. Scene
     * bounds still come from players: this must not shrink their framing. */
    if(!stage_quad(0,300,floor_half,800,low_-.35f,3)){release_model();return false;}
    if(model->room==RoomPhoto||model->room==RoomFullSquadPhoto) {
        for(float y=low_;y<wall_top;y+=32.f) {
            int band=int((y-low_)/32.f)%2;
            if(!wall_quad(-wall_half,wall_half,y,std::min(y+32,wall_top),wall_z,model->club_colors[band])){release_model();return false;}
        }
        if(!wall_quad(-wall_half,wall_half,wall_top-4,wall_top,wall_z+.1f,model->club_colors[2])){release_model();return false;}
        if(model->crest_texture>=0&&size_t(model->crest_texture)<textures_.size()&&textures_[model->crest_texture]) {
            const auto&t=model->textures[model->crest_texture];float size=68,rx=size*.5f*t.width/t.height;
            if(!wall_quad(-rx,rx,high_+2,high_+2+size,wall_z+1,{1,1,1},model->crest_texture)){release_model();return false;}
        }
    }
    if(model->formation.empty()) {if(!stage_quad(0,0,27,34,low_-.2f,2)){release_model();return false;}}
    else for(const auto&p:model->formation)if(!stage_quad(p.x,p.z,27,34,low_-.2f,2)){release_model();return false;}
    }
    std::stable_sort(meshes_.begin(),meshes_.end(),[](const Mesh&a,const Mesh&b){return a.blend<b.blend;});
    if(model->room==RoomStadium&&model->stadium_focus_radius>1)stadium_radius_=model->stadium_focus_radius;
    extent_=std::max(high_-low_,horizontal);model_=model;return !meshes_.empty();
}
bool Renderer::render(UINT w,UINT h,float yaw,float zoom,bool portrait,float pan_x,float pan_y,bool profile,float portrait_crop,const CameraFocus*focus,bool transparent_background,float actor_x,float actor_y){
    if(!std::isfinite(yaw)||!std::isfinite(zoom)||!std::isfinite(pan_x)||!std::isfinite(pan_y)||!std::isfinite(actor_x)||!std::isfinite(actor_y))return false;
    if(meshes_.empty()||!initialize()||!w||!h||w>4096||h>4096||!target(w,h))return false;
    profile=profile&&model_&&((model_->room==RoomPhoto&&model_->player_count==1)||model_->room==RoomArtifact);
    const float bg[4]={.105f,.19f,.225f,1},transparent[4]={0,0,0,0},stadium_bg[4]={.94f,.97f,.99f,1};
    commands_->ClearRenderTargetView(target_,model_->room==RoomStadium?stadium_bg:(transparent_background||profile||model_->room==RoomOfficeLineup)?transparent:bg);
    commands_->ClearDepthStencilView(depth_,D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1,0);
    commands_->OMSetRenderTargets(1,&target_,depth_);commands_->OMSetDepthStencilState(depth_state_,0);
    commands_->OMSetBlendState(nullptr,nullptr,0xffffffff);commands_->RSSetState(raster_);
    D3D11_VIEWPORT viewport={0,0,(float)w,(float)h,0,1};commands_->RSSetViewports(1,&viewport);
    commands_->IASetInputLayout(layout_);commands_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    commands_->VSSetShader(vs_,nullptr,0);commands_->PSSetShader(ps_,nullptr,0);
    commands_->GSSetShader(nullptr,nullptr,0);commands_->HSSetShader(nullptr,nullptr,0);commands_->DSSetShader(nullptr,nullptr,0);
    commands_->VSSetConstantBuffers(0,1,&constants_);commands_->PSSetConstantBuffers(0,1,&constants_);commands_->PSSetSamplers(0,1,&sampler_);
    /* Include the crest (not the infinitely extended wall) in default framing. */
    portrait=portrait&&model_&&model_->player_count==1;
    portrait_crop=std::isfinite(portrait_crop)?std::clamp(portrait_crop,0.f,.85f):.50f;
    float scene_low=portrait?low_+(high_-low_)*portrait_crop:low_;
    float aspect=(float)w/h;
    XMMATRIX world=model_->room==RoomStadium&&free_stadium_?XMMatrixIdentity():XMMatrixRotationY(yaw);
    /* Native actor coordinates face +Z. A LH look-at from +Z reverses screen
     * X and mirrors every kit/boot label. Use matching RH view/projection for
     * the scene, without modifying native geometry or UVs. */
    /* A longer photographic lens flattens the apparent size difference
     * between front/back rows; individual inspection keeps its wider lens. */
    const float fov=(model_->room==RoomPress||model_->room==RoomPressPair)?35.f:(model_->room==RoomDressing||model_->room==RoomTrophies)?50.f:model_->player_count>1?22.f:35.f;
    XMMATRIX proj=XMMatrixPerspectiveFovRH(XMConvertToRadians(fov),aspect,.1f,10000.f);
    if(model_->room!=RoomStadium&&(fitted_width_!=w||fitted_height_!=h||fitted_yaw_!=yaw||fitted_portrait_!=portrait||fitted_profile_!=profile||fitted_crop_!=portrait_crop)) {
        /* In this front-facing RH camera the three support constraints are
         * distance >= z+abs(x)*Ax, z+(y-center)*Ay and z-(y-center)*Ay.
         * Their optimum centers the projected scene (crest is farther away
         * than the front row), instead of centering a world-space box. */
        float ay=1.f/tanf(XMConvertToRadians(fov)*.5f)/.93f,ax=ay/aspect;
        float horizontal=0,top=-FLT_MAX,bottom=-FLT_MAX;
        auto include=[&](Vec3 p) {
            horizontal=std::max(horizontal,p.z+fabsf(p.x)*ax);
            top=std::max(top,p.z+p.y*ay);bottom=std::max(bottom,p.z-p.y*ay);
        };
        for(const auto&part:framing_parts_) {
            if(portrait&&part.top<scene_low)continue;
            for(size_t i=part.first;i<part.first+part.count;++i) {
                Vec3 p=framing_points_[i];if(portrait)p.y=std::max(p.y,scene_low);
                XMVECTOR v=XMVector3TransformCoord(XMVectorSet(p.x,p.y,p.z,1),world);
                include({XMVectorGetX(v),XMVectorGetY(v),XMVectorGetZ(v)});
            }
        }
        if(!profile&&(model_->room==RoomPhoto||model_->room==RoomFullSquadPhoto)&&model_->crest_texture>=0&&size_t(model_->crest_texture)<model_->textures.size()) {
            const auto&t=model_->textures[model_->crest_texture];float rx=34.f*t.width/t.height;
            const float wall_z=model_->room==RoomFullSquadPhoto?-300.f:-104.f;
            for(int corner=0;corner<4;++corner)include({corner&1?rx:-rx,high_+2+(corner&2?68.f:0.f),wall_z});
        }
        fitted_center_=(top-bottom)/(2*ay);
        // Opt-in bust cards fit the upper-body vertical range; the full torso's
        // width must not pull the camera back down to the waist. Existing
        // player profiles/team photos retain their complete horizontal fit.
        fitted_distance_=std::max(10.f,portrait&&portrait_crop>.5f?(top+bottom)*.5f:std::max(horizontal,(top+bottom)*.5f));
        fitted_width_=w;fitted_height_=h;fitted_yaw_=yaw;fitted_portrait_=portrait;fitted_profile_=profile;
        fitted_crop_=portrait_crop;
    }
    float center=fitted_center_,distance=fitted_distance_/std::max(.65f,std::min(2.f,zoom));
    /* Interior prototypes have their own camera/light; never change the
     * photographic fit or material treatment of players/coaches. */
    if(model_->room!=RoomPhoto&&model_->room!=RoomOfficeLineup&&model_->room!=RoomFullSquadPhoto&&model_->room!=RoomArtifact&&model_->room!=RoomStadium){
        center=(model_->room==RoomPress||model_->room==RoomPressPair)?121.f:145.f;
        distance=(model_->room==RoomPressPair?std::max(340.f,430.f/aspect):model_->room==RoomPress?220.f:model_->room==RoomTrophies?std::max(540.f,930.f/aspect):std::max(330.f,680.f/aspect))/std::max(.65f,std::min(2.f,zoom));
    }
    float camera_x=0;
    if(focus&&profile&&model_->player_count==1&&model_->room==RoomPhoto&&std::isfinite(focus->height_ratio)&&std::isfinite(focus->horizontal_ratio)&&std::isfinite(focus->span_ratio)){
        float height=std::max(1.f,high_-low_);center=low_+height*std::clamp(focus->height_ratio,.1f,.95f);
        camera_x=height*std::clamp(focus->horizontal_ratio,-.35f,.35f);
        distance=height*std::clamp(focus->span_ratio,.18f,1.f)*.5f/tanf(XMConvertToRadians(fov)*.5f)/std::clamp(zoom,.65f,2.f)+height*.12f;
    }
    XMMATRIX view=XMMatrixIdentity();
    if(model_->room==RoomStadium){
        center=0;distance=stadium_radius_/sinf(XMConvertToRadians(fov)*.5f)*std::max(1.f,1/aspect)*1.08f/std::clamp(zoom,.65f,2.f);
        view=XMMatrixLookAtRH(XMVectorSet(0,distance*.50f,distance*.8660254f,1),XMVectorZero(),XMVectorSet(0,1,0,0));
        if(free_stadium_){auto&p=stadium_camera_.position;float y=stadium_camera_.yaw,t=stadium_camera_.pitch;
            XMVECTOR eye=XMVectorSet(p.x,p.y,p.z,1),direction=XMVectorSet(sinf(y)*cosf(t),sinf(t),-cosf(y)*cosf(t),0);
            view=XMMatrixLookAtRH(eye,eye+direction,XMVectorSet(0,1,0,0));
        }
    }else view=XMMatrixLookAtRH(XMVectorSet(camera_x,center,distance,1),XMVectorSet(camera_x,center,0,1),XMVectorSet(0,1,0,0));
    /* Pan a photograph's framing, never its models. Keep this outside the
     * automatic default fit and outside the shadow camera. */
    proj=proj*XMMatrixTranslation(std::max(-.45f,std::min(.45f,pan_x))*2,
        std::max(-.35f,std::min(.35f,pan_y))*2,0);
    float light_size=extent_*1.5f;
    XMVECTOR light_center=XMVectorSet(0,center,0,1),key=XMVector3Normalize(XMVectorSet(-.4f,.65f,.8f,0));
    XMMATRIX light_view=XMMatrixLookAtRH(light_center+key*light_size*2,light_center,XMVectorSet(0,1,0,0));
    XMMATRIX light_proj=XMMatrixOrthographicRH(light_size,light_size,.1f,light_size*4);
    Constants c;XMStoreFloat4x4(&c.world,XMMatrixTranspose(world));XMStoreFloat4x4(&c.light_wvp,XMMatrixTranspose(world*light_view*light_proj));
    c.wvp=c.light_wvp;c.color={1,1,1,0};c.parameters={1,0,(model_->room!=RoomPhoto&&model_->room!=RoomOfficeLineup&&model_->room!=RoomFullSquadPhoto)?1.f:0.f,0};
    ID3D11ShaderResourceView*empty=nullptr;commands_->PSSetShaderResources(1,1,&empty);
    commands_->OMSetRenderTargets(0,nullptr,shadow_depth_);commands_->ClearDepthStencilView(shadow_depth_,D3D11_CLEAR_DEPTH,1,0);
    D3D11_VIEWPORT shadow_viewport={0,0,1024,1024,0,1};commands_->RSSetViewports(1,&shadow_viewport);commands_->PSSetShader(shadow_ps_,nullptr,0);
    commands_->UpdateSubresource(constants_,0,nullptr,&c,0,0);
    for(const auto&m:meshes_)if(!m.surface) {
        XMMATRIX mesh_world=m.actor?world*XMMatrixTranslation(actor_x,actor_y,0):world;
        XMStoreFloat4x4(&c.world,XMMatrixTranspose(mesh_world));
        XMStoreFloat4x4(&c.light_wvp,XMMatrixTranspose(mesh_world*light_view*light_proj));c.wvp=c.light_wvp;
        c.color.w=m.hair?6.f:0.f;c.parameters.x=m.alpha_scale;
        ID3D11ShaderResourceView*coeff=m.hair_coeff_texture>=0&&size_t(m.hair_coeff_texture)<textures_.size()?textures_[m.hair_coeff_texture]:nullptr;
        c.parameters.y=coeff?1.f:0.f;commands_->PSSetShaderResources(2,1,&coeff);
        commands_->UpdateSubresource(constants_,0,nullptr,&c,0,0);
        ID3D11ShaderResourceView*t=m.texture>=0&&size_t(m.texture)<textures_.size()?textures_[m.texture]:white_;
        if(!t)t=white_;commands_->PSSetShaderResources(0,1,&t);
        UINT stride=sizeof(GpuVertex),offset=0;commands_->IASetVertexBuffers(0,1,&m.vertices,&stride,&offset);
        commands_->IASetIndexBuffer(m.indices,DXGI_FORMAT_R32_UINT,0);commands_->DrawIndexed(m.count,0,0);
    }
    commands_->OMSetRenderTargets(1,&target_,depth_);commands_->RSSetViewports(1,&viewport);commands_->PSSetShader(ps_,nullptr,0);
    commands_->PSSetShaderResources(1,1,&shadow_image_);commands_->PSSetSamplers(1,1,&shadow_sampler_);
    XMStoreFloat4x4(&c.wvp,XMMatrixTranspose(world*view*proj));
    /* Draw transparent strands back to front, including the cards within each
     * hair mesh. Fixed bind-pose ordering loses locks when the camera rotates. */
    auto camera_depth=[&](Vec3 p,bool fixed=false){return -XMVectorGetZ(XMVector3TransformCoord(XMVectorSet(p.x,p.y,p.z,1),fixed?view:world*view));};
    std::vector<size_t>order;std::vector<float>depths;
    for(size_t i=0;i<meshes_.size();++i){order.push_back(i);depths.push_back(camera_depth(meshes_[i].center,meshes_[i].surface>=3));}
    std::stable_sort(order.begin(),order.end(),[&](size_t a,size_t b){const auto&x=meshes_[a],&y=meshes_[b];
        if(x.blend!=y.blend)return x.blend<y.blend;
        return x.blend&&depths[a]>depths[b];});
    /* Opaque scene, then ALL hair cores, then back-to-front soft edges.
     * Core and edge coverage are disjoint so a strand is not alpha-blended
     * over its own opaque pass. No original geometry is discarded. */
    for(int pass=0;pass<3;++pass)for(size_t index:order){const auto&m=meshes_[index];
        if(profile&&m.surface)continue; /* Do not paint grass/wall/crest over the light profile UI. */
        if(pass==0&&(m.hair||m.blend))continue;
        if(pass==1&&!m.hair)continue;
        if(pass==2&&!m.blend)continue;
        /* Keep the photograph backdrop fixed. Rotating it with the actor puts
         * the wall in front of him when inspecting the back of his hair/kit. */
        bool fixed=m.surface>=3;
        XMMATRIX mesh_world=fixed?XMMatrixIdentity():m.actor?world*XMMatrixTranslation(actor_x,actor_y,0):world;
        XMStoreFloat4x4(&c.world,XMMatrixTranspose(mesh_world));
        XMStoreFloat4x4(&c.wvp,XMMatrixTranspose(mesh_world*view*proj));
        XMStoreFloat4x4(&c.light_wvp,XMMatrixTranspose(mesh_world*light_view*light_proj));
        if(pass==2&&!m.strand_indices.empty()) {
            std::vector<size_t>triangles;std::vector<float>triangle_depths;
            for(size_t i=0;i<m.strand_centers.size();++i){triangles.push_back(i);triangle_depths.push_back(camera_depth(m.strand_centers[i]));}
            std::stable_sort(triangles.begin(),triangles.end(),[&](size_t a,size_t b){return triangle_depths[a]>triangle_depths[b];});
            std::vector<uint32_t>indices;indices.reserve(m.strand_indices.size());
            for(size_t tri:triangles)indices.insert(indices.end(),m.strand_indices.begin()+tri*3,m.strand_indices.begin()+tri*3+3);
            commands_->UpdateSubresource(m.indices,0,nullptr,indices.data(),0,0);
        }
        ID3D11ShaderResourceView *t=m.texture>=0&&size_t(m.texture)<textures_.size()?textures_[m.texture]:nullptr;
        float mode=m.surface?(float)m.surface:m.hair?(pass==1?6.f:7.f):m.blend?1.f:0.f;
        c.parameters.x=m.alpha_scale;c.parameters.z=(model_->room!=RoomPhoto&&model_->room!=RoomOfficeLineup&&model_->room!=RoomFullSquadPhoto)?1.f:0.f;
        c.parameters.w=model_->room==RoomOfficeLineup&&m.surface==3?1.f:0.f;
        ID3D11ShaderResourceView*coeff=m.hair_coeff_texture>=0&&size_t(m.hair_coeff_texture)<textures_.size()?textures_[m.hair_coeff_texture]:nullptr;
        c.parameters.y=coeff?1.f:0.f;commands_->PSSetShaderResources(2,1,&coeff);
        c.color=t?XMFLOAT4(m.tint.x,m.tint.y,m.tint.z,mode):XMFLOAT4(m.color.x,m.color.y,m.color.z,mode);if(!t)t=white_;
        commands_->OMSetDepthStencilState(pass==2?strand_depth_:depth_state_,0);
        commands_->OMSetBlendState(pass==2?strand_blend_:nullptr,nullptr,0xffffffff);
        commands_->UpdateSubresource(constants_,0,nullptr,&c,0,0);commands_->PSSetShaderResources(0,1,&t);
        UINT stride=sizeof(GpuVertex),offset=0;commands_->IASetVertexBuffers(0,1,&m.vertices,&stride,&offset);
        commands_->IASetIndexBuffer(m.indices,DXGI_FORMAT_R32_UINT,0);commands_->DrawIndexed(m.count,0,0);
    }
    ID3D11CommandList *list=nullptr;HRESULT hr=commands_->FinishCommandList(FALSE,&list);
    if(FAILED(hr))return false;ID3D11DeviceContext *immediate=nullptr;device_->GetImmediateContext(&immediate);
    /* TRUE restores all pre-existing game pipeline state after this offscreen
     * pass. The new screen reuses Present without adding actor/flow hooks. */
    immediate->ExecuteCommandList(list,TRUE);drop(immediate);drop(list);return true;
}
StadiumCamera Renderer::stadium_orbit_camera(UINT w,UINT h,float yaw,float zoom)const{
    float aspect=w&&h?float(w)/h:1;float distance=stadium_radius_/sinf(XMConvertToRadians(35.f)*.5f)*std::max(1.f,1/aspect)*1.08f/std::clamp(zoom,.65f,2.f);
    return {{-sinf(yaw)*distance*.8660254f,distance*.5f,cosf(yaw)*distance*.8660254f},yaw,-XM_PI/6};
}
bool Renderer::render_stadium(UINT w,UINT h,float yaw,float zoom,const StadiumCamera*camera){
    if(!model_||model_->room!=RoomStadium)return false;
    if(camera){auto&p=camera->position;if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(camera->yaw)||!std::isfinite(camera->pitch)||fabsf(camera->pitch)>1.56f)return false;stadium_camera_=*camera;}
    free_stadium_=camera!=nullptr;bool ok=render(w,h,yaw,zoom);free_stadium_=false;return ok;
}
}
