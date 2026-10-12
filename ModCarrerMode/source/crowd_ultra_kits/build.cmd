@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
rc /nologo /fobuild\payload.res payload.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD crowd_ultra_kits.cpp build\payload.res /Fobuild\crowd_ultra_kits.obj /Febuild\crowd_ultra_kits.dll /link /NOLOGO /IMPLIB:build\crowd_ultra_kits.lib
if errorlevel 1 exit /b 1
popd
endlocal
