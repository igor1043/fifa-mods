@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD /D_CRT_SECURE_NO_WARNINGS /I "..\substitution_all7_rulescan_native" skip_server_shutdown_notice.c /Feskip_server_shutdown_notice.dll /link /NOLOGO user32.lib
if errorlevel 1 exit /b 1
popd
endlocal
