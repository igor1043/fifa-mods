@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "xi_build=%~1"
if not defined xi_build set "xi_build=%~dp0build"
if not exist "%xi_build%" mkdir "%xi_build%"
pushd "%xi_build%"
cl /nologo /O2 /Gy /W3 /EHsc /std:c++17 /utf-8 /MT /D_CRT_SECURE_NO_WARNINGS /c "%~dp0engine\src\render\assets\fifa_player_assets.cpp" "%~dp0engine\src\render\poses\fifa_player_pose.cpp" "%~dp0engine\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /O2 /Gy /W3 /EHsc /std:c++17 /utf-8 /MT /D_CRT_SECURE_NO_WARNINGS "%~dp0generate_lineup.cpp" fifa_player_assets.obj fifa_player_pose.obj miniz_tinfl.obj /Fe:generate_lineup.exe /link /OPT:REF shlwapi.lib xmllite.lib user32.lib gdi32.lib ole32.lib
if errorlevel 1 exit /b 1
popd
endlocal
