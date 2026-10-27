@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_sites.cpp /Fobuild\ /Febuild\test_sites.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_sites.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD smoke_machine.cpp /Fobuild\ /Febuild\smoke_machine.dll /link /NOLOGO
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_loading.cpp /Fobuild\ /Febuild\test_loading.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_loading.exe
set result=%errorlevel%
popd
exit /b %result%
