@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_policies.cpp /Fobuild\test_policies.obj /Febuild\test_policies.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_policies.exe
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_world_position.cpp /Fobuild\test_world_position.obj /Febuild\test_world_position.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_world_position.exe
exit /b %errorlevel%
