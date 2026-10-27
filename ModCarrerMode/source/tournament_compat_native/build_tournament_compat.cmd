@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /LD tournament_compat.c /Fobuild\tournament_compat.obj /Febuild\tournament_compat_native.dll /link /NOLOGO /IMPLIB:build\tournament_compat.lib
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_tournament_compat.c /Fobuild\test_tournament_compat.obj /Febuild\test_tournament_compat.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_tournament_compat.exe "%~dp0..\..\..\dlc\dlc_FootballCompEng\dlc\FootballCompEng\data\compdata\compobj.txt" "%~dp0..\..\..\data\db\fifa_ng_db-meta.xml"
if errorlevel 1 exit /b 1
popd
endlocal
