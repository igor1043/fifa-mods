@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD flamengo_pyro_v2.cpp /Fobuild\ /Febuild\flamengo_pyro_v5.dll /link /NOLOGO user32.lib
set result=%errorlevel%
popd
exit /b %result%
