@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_locomotion.cpp /Fobuild\test_locomotion.obj /Febuild\test_locomotion.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_locomotion.exe %*
exit /b %errorlevel%
