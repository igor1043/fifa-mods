@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_policies.cpp /Fobuild\test_policies.obj /Febuild\test_policies.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_policies.exe
exit /b %errorlevel%
