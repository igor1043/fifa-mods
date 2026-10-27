@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /LD goal_kick_short_pass.c goal_pass.c core.c layout.c payload.c /Fobuild\ /Febuild\goal_kick_short_pass.dll /link /NOLOGO bcrypt.lib
if errorlevel 1 exit /b 1
popd
if not exist "%~dp0..\..\mods\goal_kick_short_pass" mkdir "%~dp0..\..\mods\goal_kick_short_pass"
copy /y "%~dp0build\goal_kick_short_pass.dll" "%~dp0..\..\mods\goal_kick_short_pass\goal_kick_short_pass.dll" >nul
if errorlevel 1 exit /b 1
copy /y "%~dp0goal_kick_short_pass.ini" "%~dp0..\..\mods\goal_kick_short_pass\goal_kick_short_pass.ini" >nul
if errorlevel 1 exit /b 1
endlocal
