@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_competition.cpp /Fobuild\ /Febuild\test_competition.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_competition.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD var_cabin.cpp /Fobuild\ /Febuild\var_cabin.dll /link /NOLOGO
if errorlevel 1 exit /b 1
popd
exit /b 0
