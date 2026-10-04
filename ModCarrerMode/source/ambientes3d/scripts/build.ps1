[CmdletBinding()]
param([string]$SourceRoot='', [string]$OutputDirectory='', [string]$OutputName='Ambientes3D.exe')
$ErrorActionPreference='Stop'
$studioRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $SourceRoot) { $SourceRoot=Join-Path $studioRoot '..\career_native' }
$SourceRoot=(Resolve-Path -LiteralPath $SourceRoot).Path
$studioEdition=Join-Path $SourceRoot '..\..\config\edition.ini'
if ((Get-Content -LiteralPath $studioEdition -Raw) -notmatch '(?m)^id=new-experience\s*$') { throw 'Compile com os fontes da New Experience.' }
if (-not $OutputDirectory) { $OutputDirectory=$studioRoot }
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
if($OutputName -notmatch '^Ambientes3D(-[A-Za-z0-9]+)?\.exe$'){throw 'Nome de executavel invalido'}
$studioOutput=Join-Path $OutputDirectory $OutputName
$studioBuild=Join-Path (Join-Path $studioRoot 'build') ([IO.Path]::GetFileNameWithoutExtension($OutputName))
$studioEngine=Join-Path $studioBuild 'engine'
New-Item -ItemType Directory -Path $studioEngine -Force | Out-Null
$studioEncoding=[Text.UTF8Encoding]::new($false)
function Replace-Exact([string]$text,[string]$old,[string]$new) {
    if(-not $text.Contains($old)){throw "O renderizador mudou: trecho esperado não foi encontrado. Reavalie o adaptador antes de compilar: $old"}
    return $text.Replace($old,$new)
}
# Private build adapters only. The Dev/game renderer and recipes remain untouched.
$studioAssets=(Join-Path $SourceRoot 'src\render\assets\fifa_player_assets.h').Replace('\','/')
$studioHeader=[IO.File]::ReadAllText((Join-Path $SourceRoot 'src\render\renderer\fifa_player_renderer.h'))
$studioHeader=Replace-Exact $studioHeader '#include "../assets/fifa_player_assets.h"' ('#include "'+$studioAssets+'"')
$studioHeader=Replace-Exact $studioHeader 'class Renderer {' @'
struct InspectionCamera {Vec3 position={0,155,650};float yaw=0,pitch=0,fov=45;};
class Renderer {
    bool inspection_enabled_=false;
    InspectionCamera inspection_camera_;
'@
$studioHeader=Replace-Exact $studioHeader 'bool blend=false,hair=false,actor=false;' 'bool blend=false,hair=false,actor=false,emissive=false,outdoor=false;'
$studioHeader=Replace-Exact $studioHeader '    ~Renderer(){release_device();}' @'
    bool render_inspection(UINT width,UINT height,const InspectionCamera&,bool isolated=false);
    ~Renderer(){release_device();}
'@
[IO.File]::WriteAllText((Join-Path $studioEngine 'fifa_player_renderer.h'),$studioHeader,$studioEncoding)
$studioRenderer=[IO.File]::ReadAllText((Join-Path $SourceRoot 'src\render\renderer\fifa_player_renderer.cpp'))
$studioRenderer='#include "viewer_training_center.h"'+"`n"+$studioRenderer
$studioRenderer=Replace-Exact $studioRenderer 'Mesh m;m.count=(UINT)p.indices.size();' 'Mesh m;m.emissive=(p.asset.rfind("studio/dressing/",0)==0||p.asset.rfind("studio/room/",0)==0)&&p.color.x>1.05f;m.outdoor=p.name.rfind("CT /",0)==0;m.count=(UINT)p.indices.size();'
$studioRenderer=Replace-Exact $studioRenderer 'c.parameters.w=model_->room==RoomOfficeLineup&&m.surface==3?1.f:0.f;' 'c.parameters.w=(model_->room==RoomDressing||model_->room==RoomPressPair||model_->room==studio::RoomGym||model_->room==studio::RoomTraining)&&m.emissive?2.f:model_->room==RoomOfficeLineup&&m.surface==3?1.f:0.f;if(model_->room==studio::RoomGym||model_->room==studio::RoomTraining)c.parameters.z=m.outdoor?5.f:4.f;'
$studioRenderer=Replace-Exact $studioRenderer 'float4 c=Diffuse.Sample(Linear,i.uv);' 'float4 c=Diffuse.Sample(Linear,i.uv);if(Parameters.z>3.5&&Parameters.w>1.5)return float4(saturate(c.rgb*Tint.rgb),1);if(Parameters.z>1.5&&Parameters.w>1.5)return float4(saturate(Tint.rgb),1);'
# Dressing-room lighting is local to this standalone viewer, never the mod DLL.
$studioRenderer=Replace-Exact $studioRenderer 'if(Parameters.z>0)lit=' @'
if(Parameters.z>4.5){
 lit=.38+.62*saturate(dot(n,normalize(float3(-.40,.65,.80))))*(.18+.82*visibility(i))+.14*saturate(dot(n,normalize(float3(.5,.3,-.6))));
}else if(Parameters.z>3.5){
 float3 mainDelta=float3(0,690,-650)-i.w;
 float main=saturate(dot(n,normalize(mainDelta)))/(1+dot(mainDelta,mainDelta)/650000);
 float fixtures=0;
 [unroll]for(int x=-1;x<=1;x++)[unroll]for(int z=-1;z<=0;z++){
  float3 q=float3(x*800,694,-650+z*800)-i.w;
  fixtures+=saturate(dot(n,normalize(q)))/(1+dot(q,q)/350000)*saturate((694-i.w.y)/15);
 }
 float lower=0;
 [unroll]for(int x=-1;x<=1;x++){
  float3 q=float3(x*550,330,-1460)-i.w;
  lower+=saturate(dot(n,normalize(q)))/(1+dot(q,q)/110000)*saturate((330-i.w.y)/12);
 }
 float daylight=saturate(dot(n,normalize(float3(0,.7,1))))*saturate(1+ i.w.z/2100);
 lit=.32+.16*saturate(-n.y)+.44*main*(.15+.85*visibility(i))+.115*fixtures+.15*lower+.14*daylight;
}else if(Parameters.z>2.5){
 float3 d=float3(0,290,-150)-i.w;
 float keyLight=saturate(dot(n,normalize(d)))/(1+dot(d,d)/220000)*saturate((290-i.w.y)/12);
 float ceiling=0;
 [unroll]for(int x=-1;x<=1;x++)[unroll]for(int z=-1;z<=1;z++){
   float3 q=float3(x*300,311,35+z*385)-i.w;
   ceiling+=saturate(dot(n,normalize(q)))/(1+dot(q,q)/210000)*saturate((311-i.w.y)/8);
 }
 float3 left=float3(-250,290,-150)-i.w,right=float3(250,290,-150)-i.w;
 float front=(saturate(dot(n,normalize(left)))/(1+dot(left,left)/160000)+saturate(dot(n,normalize(right)))/(1+dot(right,right)/160000))*saturate((290-i.w.y)/12);
 [unroll]for(int x=-1;x<=1;x++){
   float3 back=float3(x*300,311,820)-i.w;
   ceiling+=saturate(dot(n,normalize(back)))/(1+dot(back,back)/210000)*saturate((311-i.w.y)/8);
 }
 lit=.39+.28*saturate(-n.y)+.45*keyLight*(.25+.75*visibility(i))+.10*ceiling+.22*front;
}else if(Parameters.z>1.5){
 float3 mainDelta=float3(0,309,115)-i.w;
 float main=saturate(dot(n,normalize(mainDelta)))/(1+dot(mainDelta,mainDelta)/180000);
 float fixtures=0;
 [unroll]for(int x=-1;x<=1;x++)[unroll]for(int z=-1;z<=1;z++){
   if(x==0&&z==0)continue;
   float3 delta=float3(x*320,309,115+z*465)-i.w;
   fixtures+=saturate(dot(n,normalize(delta)))/(1+dot(delta,delta)/180000);
 }
 float lockerLights=0;
 float X=(i.w.x<0?-1:1)*(150+clamp(round((abs(i.w.x)-150)/90),0,3)*90);
 float Z=-343+clamp(round((i.w.z+343)/108),0,7)*108;
 float3 d=float3(X,220,-422)-i.w;
 lockerLights+=saturate(dot(n,normalize(d)))/(1+dot(d,d)/1800);
 d=float3(-467,220,Z)-i.w;
 lockerLights+=saturate(dot(n,normalize(d)))/(1+dot(d,d)/1800);
 d=float3(467,220,Z)-i.w;
 lockerLights+=saturate(dot(n,normalize(d)))/(1+dot(d,d)/1800);
 // Indoor bounce/fill and ceiling fixtures, never the external sunlight key.
 lit=.34+.20*saturate(-n.y)+.62*main*(.10+.90*visibility(i))+.075*fixtures+.15*lockerLights;
}else if(Parameters.z>0)lit=
'@
$studioRenderer=Replace-Exact $studioRenderer '(model_->room!=RoomPhoto&&model_->room!=RoomOfficeLineup&&model_->room!=RoomFullSquadPhoto)?1.f:0.f' '(model_->room!=RoomPhoto&&model_->room!=RoomOfficeLineup&&model_->room!=RoomFullSquadPhoto)?(model_->room==RoomPressPair?3.f:model_->room==RoomDressing?2.f:1.f):0.f'
$studioRenderer=Replace-Exact $studioRenderer 'if(Tint.w>=6)lit=' 'if(Tint.w>=6&&Parameters.z<2.5)lit='
$studioRenderer=Replace-Exact $studioRenderer 'XMMATRIX light_proj=XMMatrixOrthographicRH(light_size,light_size,.1f,light_size*4);' @'
    if(model_->room==RoomDressing){
        light_view=XMMatrixLookAtRH(XMVectorSet(0,309,115,1),XMVectorSet(0,0,115,1),XMVectorSet(0,0,-1,0));
        light_size=1450;
    }
    if(model_->room==RoomPressPair){light_view=XMMatrixLookAtRH(XMVectorSet(0,290,-150,1),XMVectorSet(0,0,-150,1),XMVectorSet(0,0,-1,0));light_size=1450;}
    XMMATRIX light_proj=XMMatrixOrthographicRH(light_size,light_size,.1f,light_size*4);
    if(model_->room==RoomDressing)light_proj=XMMatrixPerspectiveFovRH(XMConvertToRadians(135),1,10.f,1500);
    if(model_->room==RoomPressPair)light_proj=XMMatrixPerspectiveFovRH(XMConvertToRadians(135),1,10.f,1800);
    if(model_->room==studio::RoomGym){light_view=XMMatrixLookAtRH(XMVectorSet(0,690,-650,1),XMVectorSet(0,0,-650,1),XMVectorSet(0,0,-1,0));light_proj=XMMatrixPerspectiveFovRH(XMConvertToRadians(142),1,10.f,5000);}
    if(model_->room==studio::RoomTraining){auto center=XMVectorSet(0,100,6350,1);auto key=XMVector3Normalize(XMVectorSet(-.40f,.65f,.80f,0));light_view=XMMatrixLookAtRH(center+key*18000,center,XMVectorSet(0,1,0,0));light_proj=XMMatrixOrthographicRH(17500,17500,10,60000);}
'@
$studioRenderer=Replace-Exact $studioRenderer 'for(const auto&m:meshes_)if(!m.surface)' 'for(const auto&m:meshes_)if(!m.surface&&!((model_->room==studio::RoomGym||model_->room==studio::RoomTraining)&&m.emissive))'
$studioRenderer=Replace-Exact $studioRenderer 'p.z-.0015' 'p.z-(Parameters.z>1.5?.00018:.0015)'
$studioRenderer=Replace-Exact $studioRenderer 'td.Width=td.Height=1024;' 'td.Width=td.Height=2048;'
$studioRenderer=Replace-Exact $studioRenderer 'shadow_viewport={0,0,1024,1024,0,1}' 'shadow_viewport={0,0,2048,2048,0,1}'
$studioRenderer=Replace-Exact $studioRenderer 'float2(x,y)/1024' 'float2(x,y)*(Parameters.z>1.5?2.6:1)/2048'
$studioRenderer=Replace-Exact $studioRenderer 'd.Format=tex.format==0?DXGI_FORMAT_BC1_UNORM:tex.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;' 'd.Format=tex.format==3?DXGI_FORMAT_R8G8B8A8_UNORM:tex.format==0?DXGI_FORMAT_BC1_UNORM:tex.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;'
$studioRenderer=Replace-Exact $studioRenderer 'D3D11_SUBRESOURCE_DATA data={tex.bytes.data(),((tex.width+3)/4)*(tex.format?16:8),(UINT)tex.bytes.size()};' 'D3D11_SUBRESOURCE_DATA data={tex.bytes.data(),tex.format==3?tex.width*4:((tex.width+3)/4)*(tex.format?16:8),(UINT)tex.bytes.size()};'
$studioRenderer=Replace-Exact $studioRenderer 'if(SUCCEEDED(device_->CreateTexture2D(&d,&data,&t)))device_->CreateShaderResourceView(t,nullptr,&view);' @'
        if(tex.format==3&&(model->room==studio::RoomGym||model->room==studio::RoomTraining)&&tex.width>1&&tex.height>1){
            d.MipLevels=0;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags|=D3D11_BIND_RENDER_TARGET;d.MiscFlags=D3D11_RESOURCE_MISC_GENERATE_MIPS;
            if(SUCCEEDED(device_->CreateTexture2D(&d,nullptr,&t))){ID3D11DeviceContext*ctx=nullptr;device_->GetImmediateContext(&ctx);ctx->UpdateSubresource(t,0,nullptr,tex.bytes.data(),tex.width*4,0);if(SUCCEEDED(device_->CreateShaderResourceView(t,nullptr,&view)))ctx->GenerateMips(view);ctx->Release();}
        }else if(SUCCEEDED(device_->CreateTexture2D(&d,&data,&t)))device_->CreateShaderResourceView(t,nullptr,&view);
'@
$studioRenderer=Replace-Exact $studioRenderer 'XMMATRIX world=model_->room==RoomStadium&&free_stadium_?XMMatrixIdentity():XMMatrixRotationY(yaw);' 'XMMATRIX world=inspection_enabled_||(model_->room==RoomStadium&&free_stadium_)?XMMatrixIdentity():XMMatrixRotationY(yaw);'
$studioRenderer=Replace-Exact $studioRenderer "    /* Pan a photograph's framing, never its models." @'
    if(inspection_enabled_){auto&cam=inspection_camera_;auto&p=cam.position;
        auto eye=XMVectorSet(p.x,p.y,p.z,1);auto direction=XMVectorSet(sinf(cam.yaw)*cosf(cam.pitch),sinf(cam.pitch),-cosf(cam.yaw)*cosf(cam.pitch),0);
        view=XMMatrixLookAtRH(eye,eye+direction,XMVectorSet(0,1,0,0));
        bool training=model_->room==studio::RoomGym||model_->room==studio::RoomTraining;
        proj=XMMatrixPerspectiveFovRH(XMConvertToRadians(cam.fov),aspect,training?20.f:(model_->room==RoomDressing||model_->room==RoomPressPair)?2.f:.1f,training?60000.f:20000.f);
    }
    /* Pan a photograph's framing, never its models.
'@
$studioRenderer+=@'

namespace fifa_player {
bool Renderer::render_inspection(UINT w,UINT h,const InspectionCamera&c,bool isolated){
    if(!std::isfinite(c.position.x)||!std::isfinite(c.position.y)||!std::isfinite(c.position.z)||!std::isfinite(c.yaw)||!std::isfinite(c.pitch)||!std::isfinite(c.fov)||fabsf(c.pitch)>1.5f||c.fov<15||c.fov>100)return false;
    inspection_camera_=c;inspection_enabled_=true;
    bool ok=render(w,h,0,1,false,0,0,isolated);inspection_enabled_=false;return ok;
}}
'@
[IO.File]::WriteAllText((Join-Path $studioEngine 'fifa_player_renderer.cpp'),$studioRenderer,$studioEncoding)
$studioPose=[IO.File]::ReadAllText((Join-Path $SourceRoot 'src\render\poses\fifa_player_pose.cpp'))
$studioPose=Replace-Exact $studioPose '#include "../assets/fifa_player_assets.h"' ('#include "'+$studioAssets+'"'+"`n"+'#include "viewer_pose_hooks.h"')
$studioPose=$studioPose.Replace('#include "viewer_pose_hooks.h"','#include "viewer_animation.h"')
$studioPose=Replace-Exact $studioPose '    for(size_t i=0;i<count;++i)XMStoreFloat4x4(&delta[i],' "    studio::apply_overrides(model,rest,pose);`n    for(size_t i=0;i<count;++i)XMStoreFloat4x4(&delta[i],"
$studioPose=Replace-Exact $studioPose '    for(size_t i=0;i<31;++i)XMStoreFloat4x4(&delta[i],' "    studio::apply_overrides(model,rest,pose);`n    for(size_t i=0;i<31;++i)XMStoreFloat4x4(&delta[i],"
$studioPose=Replace-Exact $studioPose '    for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=feet;' "    feet=studio::animation_floor(model,feet);`n    for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=feet;"
$studioPose=Replace-Exact $studioPose 'if(!std::isfinite(floor))return false;for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=floor;' 'if(!std::isfinite(floor))return false;floor=studio::animation_floor(model,floor);for(auto&p:parts)for(auto&v:p.vertices)v.position.y-=floor;'
$studioPose=Replace-Exact $studioPose '    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=pose_id;' "    studio::capture_bones(model,pose,feet,model.bind_scale);`n    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=pose_id;"
$studioPose=Replace-Exact $studioPose '    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=id;' "    studio::capture_bones(model,pose,floor,1);`n    model.parts=std::move(parts);model.presentation_pose=true;model.presentation_pose_id=id;"
[IO.File]::WriteAllText((Join-Path $studioEngine 'fifa_player_pose.cpp'),$studioPose,$studioEncoding)
# Reuse formation geometry/contacts in a private adapter, adding actor ownership.
$studioAssetSource=[IO.File]::ReadAllText((Join-Path $SourceRoot 'src\render\assets\fifa_player_assets.cpp'))
$studioTeamMarker='Model assemble_team(const std::vector<std::shared_ptr<const Model>>&players,unsigned pose_id) {'
$studioTeamOffset=$studioAssetSource.IndexOf($studioTeamMarker)
if($studioTeamOffset -lt 0){throw 'Formation source changed; adapter cannot be generated'}
$studioTeam=$studioAssetSource.Substring($studioTeamOffset)
$studioTeam=Replace-Exact $studioTeam $studioTeamMarker 'Model assemble_editable_team(const std::vector<std::shared_ptr<const Model>>&players,unsigned pose_id) {'
$studioTeam=Replace-Exact $studioTeam '        const auto&m=posed;' "        posed=edit_team_pose(*source,posed,i>=back,&contacts,pose_id);`n        const auto&m=posed;"
$studioTeam=Replace-Exact $studioTeam '        for(auto p:m->parts) {' "        size_t actor_part_begin=out.parts.size();`n        for(auto p:m->parts) {"
$studioTeam=Replace-Exact $studioTeam '        ++out.player_count;' "        register_team_actor(out,*m,actor_part_begin,x,z);`n        ++out.player_count;"
$studioTeam='#include "viewer_team.h"'+"`n"+'#include <algorithm>'+"`n"+'#include <cmath>'+"`n"+'#include <sstream>'+"`n"+'namespace studio { using namespace fifa_player;'+"`n"+$studioTeam
[IO.File]::WriteAllText((Join-Path $studioEngine 'viewer_team_formation.cpp'),$studioTeam,$studioEncoding)
$studioRooms=[IO.File]::ReadAllText((Join-Path $SourceRoot 'src\render\scenes\fifa_club_room.cpp'))
$studioRooms=Replace-Exact $studioRooms '#include "../assets/fifa_player_assets.h"' ('#include "'+$studioAssets+'"'+"`n"+'#include "viewer_team.h"')
$studioRooms=Replace-Exact $studioRooms '    for(auto p:coach.parts){' "    size_t coach_begin=room.parts.size();`n    for(auto p:coach.parts){"
$studioRooms=Replace-Exact $studioRooms '    room.diagnostic="coach arrival:' "    studio::register_team_actor(room,coach,coach_begin,0,15);`n    room.diagnostic=`"coach arrival:"
$studioRooms=Replace-Exact $studioRooms '                for(auto p:seated.parts){' "                size_t coach_begin=room.parts.size();`n                for(auto p:seated.parts){"
$studioRooms=Replace-Exact $studioRooms '                room.presentation_pose_id=coach_pose;' "                studio::register_team_actor(room,seated,coach_begin,pair?-64.f:0.f,-12);`n                room.presentation_pose_id=coach_pose;"
$studioRooms=Replace-Exact $studioRooms '            for(auto p:seated_player.parts) {' "            size_t player_begin=room.parts.size();`n            for(auto p:seated_player.parts) {"
$studioRooms=Replace-Exact $studioRooms '            room.press_player_id=seated_player.player_id;' "            studio::register_team_actor(room,seated_player,player_begin,64,-12);`n            room.press_player_id=seated_player.player_id;"
$studioRooms=Replace-Exact $studioRooms 'return p.name==part.name&&p.texture==part.texture' 'return studio::room_actor_kind(p.asset)==0&&studio::room_actor_kind(part.asset)==0&&p.name==part.name&&p.texture==part.texture'
$studioRooms=Replace-Exact $studioRooms '    room.parts=std::move(batch);' "    room.parts=std::move(batch);`n    studio::reindex_room_actors(room);"
[IO.File]::WriteAllText((Join-Path $studioEngine 'viewer_rooms.cpp'),$studioRooms,$studioEncoding)
$studioSources=@(
    (Join-Path $studioRoot 'src\viewer_training_center.cpp'),
    (Join-Path $studioRoot 'src\viewer_press_room.cpp'),
    (Join-Path $studioRoot 'src\viewer_dressing_room.cpp'),
    (Join-Path $studioRoot 'src\viewer_cinematics.cpp'),
    (Join-Path $studioRoot 'src\main.cpp'),(Join-Path $studioRoot 'src\viewer_core.cpp'),(Join-Path $studioRoot 'src\viewer_pose_hooks.cpp'),(Join-Path $studioRoot 'src\viewer_animation.cpp'),
    (Join-Path $studioRoot 'src\viewer_team.cpp'),(Join-Path $studioRoot 'src\viewer_validation.cpp'),(Join-Path $studioEngine 'viewer_team_formation.cpp'),(Join-Path $studioRoot 'third_party\ufbx\ufbx.c'),(Join-Path $studioRoot 'third_party\imguizmo\ImGuizmo.cpp'),
    (Join-Path $studioEngine 'fifa_player_renderer.cpp'),(Join-Path $studioEngine 'fifa_player_pose.cpp'),
    (Join-Path $SourceRoot 'src\render\assets\fifa_player_assets.cpp'),(Join-Path $studioEngine 'viewer_rooms.cpp'),
    (Join-Path $SourceRoot 'third_party\miniz\miniz_tinfl.c'),
    (Join-Path $SourceRoot 'third_party\imgui\imgui.cpp'),(Join-Path $SourceRoot 'third_party\imgui\imgui_draw.cpp'),
    (Join-Path $SourceRoot 'third_party\imgui\imgui_tables.cpp'),(Join-Path $SourceRoot 'third_party\imgui\imgui_widgets.cpp'),
    (Join-Path $SourceRoot 'third_party\imgui\backends\imgui_impl_win32.cpp'),(Join-Path $SourceRoot 'third_party\imgui\backends\imgui_impl_dx11.cpp')
)
$studioArgs=@('/nologo','/std:c++17','/utf-8','/EHsc','/W3','/O2','/MP','/MT','/D_CRT_SECURE_NO_WARNINGS','/DUNICODE','/D_UNICODE',
    ('/I"'+$studioEngine+'"'),('/I"'+(Join-Path $studioRoot 'src')+'"'),('/I"'+(Join-Path $studioRoot 'third_party\ufbx')+'"'),('/I"'+(Join-Path $studioRoot 'third_party\imguizmo')+'"'),('/I"'+(Join-Path $SourceRoot 'third_party\imgui')+'"'))
$studioArgs+=$studioSources|ForEach-Object {'"'+$_+'"'}
$studioArgs+=@('/Fe:"'+$studioOutput+'"','/link','/SUBSYSTEM:WINDOWS','d3d11.lib','dxgi.lib','d3dcompiler.lib','windowscodecs.lib','ole32.lib','shell32.lib','shlwapi.lib','xmllite.lib','xinput.lib','dwmapi.lib','imm32.lib','gdi32.lib')
$studioResponse=Join-Path $studioBuild 'compile.rsp'
[IO.File]::WriteAllLines($studioResponse,$studioArgs,$studioEncoding)
$studioVs='C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
Push-Location $studioBuild
try { & $env:ComSpec /d /c ('call "'+$studioVs+'" >nul && cl @"'+$studioResponse+'"'); if($LASTEXITCODE -ne 0){throw "Falha na compilação: $LASTEXITCODE"} }
finally {Pop-Location}
function Get-SourceHash([string]$path) {
    $stream=[IO.File]::OpenRead($path);$sha=[Security.Cryptography.SHA256]::Create()
    try { [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','') }
    finally { $sha.Dispose();$stream.Dispose() }
}
$studioManifest=[ordered]@{edition='new-experience';source=$SourceRoot;viewer=$studioRoot;generatedAt=(Get-Date).ToString('o');files=@();viewerFiles=@()}
foreach($studioFile in @('src\render\assets\fifa_player_assets.cpp','src\render\assets\fifa_player_assets.h','src\render\poses\fifa_player_pose.cpp','src\render\scenes\fifa_club_room.cpp','src\render\renderer\fifa_player_renderer.cpp','src\render\renderer\fifa_player_renderer.h')) {
    $studioManifest.files+=@{path=$studioFile;sha256=(Get-SourceHash (Join-Path $SourceRoot $studioFile))}
}
foreach($studioFile in Get-ChildItem -LiteralPath (Join-Path $studioRoot 'src') -File) {
    $studioManifest.viewerFiles+=@{path=('src/'+$studioFile.Name);sha256=(Get-SourceHash $studioFile.FullName)}
}
[IO.File]::WriteAllText((Join-Path $studioBuild 'engine-origin.json'),($studioManifest|ConvertTo-Json -Depth 5),$studioEncoding)
if ($OutputDirectory -ne $studioRoot) { Copy-Item -LiteralPath $studioOutput -Destination (Join-Path $studioRoot $OutputName) -Force }
Write-Output "Visualizador pronto: $studioOutput"
