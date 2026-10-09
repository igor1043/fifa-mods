@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0.."
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT tests\mascot_performance.cpp /Fobuild\mascot_performance.obj /Febuild\mascot_performance.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\mascot_performance.exe
set result=%errorlevel%
popd
exit /b %result%
