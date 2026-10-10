@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT test_ball_layout.c /Fobuild\ /Febuild\test_ball_layout.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_ball_layout.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD multiball_visual.c /Fobuild\ /Febuild\multiball_visual_v3.dll /link /NOLOGO
if errorlevel 1 exit /b 1
popd
endlocal
