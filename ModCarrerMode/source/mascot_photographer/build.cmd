@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD mascot_goal_line.cpp /Fobuild\mascot_goal_line.obj /Febuild\mascot_goal_line.dll /link /NOLOGO /IMPLIB:build\mascot_goal_line.lib
if errorlevel 1 exit /b 1
if not exist ..\..\mods\mascot_single mkdir ..\..\mods\mascot_single
copy /y build\mascot_goal_line.dll ..\..\mods\mascot_single\mascot_goal_line.dll >nul
if errorlevel 1 exit /b 1
popd
endlocal
