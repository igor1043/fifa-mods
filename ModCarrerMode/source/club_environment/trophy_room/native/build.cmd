@echo off
setlocal
where cl >nul 2>nul
if errorlevel 1 (
  for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do call "%%i\VC\Auxiliary\Build\vcvars64.bat" >nul
)
if not defined TROPHY_ROOM_OUTPUT set "TROPHY_ROOM_OUTPUT=%TEMP%\Server16TrophyRoomBuild"
if not exist "%TROPHY_ROOM_OUTPUT%" mkdir "%TROPHY_ROOM_OUTPUT%"
pushd "%TROPHY_ROOM_OUTPUT%"
cl /nologo /O2 /W3 /EHsc /std:c++17 /MT "%~dp0test_frame_chain.cpp" /Fe:test_frame_chain.exe
if errorlevel 1 exit /b 1
test_frame_chain.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /MT "%~dp0test_gallery_tour.cpp" /Fe:test_gallery_tour.exe
if errorlevel 1 exit /b 1
test_gallery_tour.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0test_trophy_shelf.cpp" /Fe:test_trophy_shelf.exe
if errorlevel 1 exit /b 1
test_trophy_shelf.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0test_gallery_commands.cpp" /Fe:test_gallery_commands.exe /link user32.lib
if errorlevel 1 exit /b 1
test_gallery_commands.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0test_photo_refresh.cpp" /Fe:test_photo_refresh.exe
if errorlevel 1 exit /b 1
test_photo_refresh.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0..\..\..\club_browser\native\test_gallery_scene_profile.cpp" /Fe:test_gallery_scene_profile.exe
if errorlevel 1 exit /b 1
test_gallery_scene_profile.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0..\..\..\common\test_scene_lens.cpp" /Fe:test_scene_lens.exe
if errorlevel 1 exit /b 1
test_scene_lens.exe scene-lens-scripts.lua
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%~dp0test_gallery_postfx.cpp" /Fe:test_gallery_postfx.exe
if errorlevel 1 exit /b 1
test_gallery_postfx.exe gallery-postfx-scripts.lua
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT /LD "%~dp0trophy_room.cpp" /Fe:trophy_room.dll /link /INCREMENTAL:NO user32.lib
set result=%errorlevel%
popd
exit /b %result%
