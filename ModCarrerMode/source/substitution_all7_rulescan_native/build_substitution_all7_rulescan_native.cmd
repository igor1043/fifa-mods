@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD /D_CRT_SECURE_NO_WARNINGS substitution_all7_rulescan_native.c /Fesubstitution_all7_rulescan_native.dll /link /NOLOGO
if errorlevel 1 exit /b 1
popd
endlocal
