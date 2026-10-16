@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT test_ball_layout.c /Fobuild\ /Febuild\test_ball_layout.exe /link /NOLOGO
if not "%errorlevel%"=="0" exit /b 1
build\test_ball_layout.exe
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /c multiball_visual.c /Fobuild\multiball_visual.obj
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT /c standball.cpp /Fobuild\standball.obj
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_stands.cpp /Fobuild\ /Febuild\test_stands.exe /link /NOLOGO
if not "%errorlevel%"=="0" exit /b 1
build\test_stands.exe
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /LD build\multiball_visual.obj build\standball.obj /Febuild\multiball_visual.dll /link /NOLOGO
if not "%errorlevel%"=="0" exit /b 1
popd
if /I "%~1"=="--build-only" exit /b 0
if not exist "%~dp0..\..\mods\multiball_visual" mkdir "%~dp0..\..\mods\multiball_visual"
copy /y "%~dp0build\multiball_visual.dll" "%~dp0..\..\mods\multiball_visual\multiball_visual.dll" >nul
if errorlevel 1 exit /b 1
copy /y "%~dp0standball.lua" "%~dp0..\..\mods\multiball_visual\standball.lua" >nul
if errorlevel 1 exit /b 1
if not exist "%~dp0..\..\mods\multiball_visual\standball.ini" copy /y "%~dp0standball.ini" "%~dp0..\..\mods\multiball_visual\standball.ini" >nul
if errorlevel 1 exit /b 1
endlocal
