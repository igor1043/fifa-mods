@echo off
setlocal
where cl >nul 2>nul
if errorlevel 1 (
  for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do call "%%i\VC\Auxiliary\Build\vcvars64.bat" >nul
)
if not defined CLUB_ROOM_OUTPUT set "CLUB_ROOM_OUTPUT=%TEMP%\Server16ClubRoomBuild"
if not exist "%CLUB_ROOM_OUTPUT%" mkdir "%CLUB_ROOM_OUTPUT%"
pushd "%CLUB_ROOM_OUTPUT%"
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT /LD "%~dp0native_dressing_room_20261022.cpp" /Fe:native_dressing_room.dll /link /INCREMENTAL:NO user32.lib
set result=%errorlevel%
popd
exit /b %result%
