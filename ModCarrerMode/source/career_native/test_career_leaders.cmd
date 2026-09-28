@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /Fe:test_native_career_leaders.exe ..\native\test_native_career_leaders.c ..\native\fce_model.c ..\native\fce_contracts.c
if errorlevel 1 exit /b 1
test_native_career_leaders.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /Fe:test_global_ranking.exe ..\native\test_global_ranking.c ..\native\global_ranking.c ..\native\fce_model.c ..\native\fce_contracts.c
if errorlevel 1 exit /b 1
test_global_ranking.exe
if errorlevel 1 exit /b 1
popd
endlocal
