@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c11 /W4 /WX /O2 /MT test_kickoff_spacing.c /Fobuild\ /Febuild\test_kickoff_spacing.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_kickoff_spacing.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD kickoff_modern_v9.c /Fobuild\ /Febuild\kickoff_modern_v9.dll /link /NOLOGO
if errorlevel 1 exit /b 1
popd
endlocal
