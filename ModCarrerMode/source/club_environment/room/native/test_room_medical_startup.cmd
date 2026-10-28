@echo off
setlocal
where cl >nul 2>nul
if errorlevel 1 call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if not defined CLUB_ROOM_OUTPUT set "CLUB_ROOM_OUTPUT=%TEMP%\Server16ClubRoomStartupTest"
if not exist "%CLUB_ROOM_OUTPUT%" mkdir "%CLUB_ROOM_OUTPUT%"
pushd "%CLUB_ROOM_OUTPUT%"
cl /nologo /O2 /W4 /EHsc /std:c++17 /utf-8 /MT /Fe:test_room_medical_startup.exe "%~dp0test_room_medical_startup.cpp"
if errorlevel 1 exit /b 1
test_room_medical_startup.exe
set result=%errorlevel%
popd
exit /b %result%
