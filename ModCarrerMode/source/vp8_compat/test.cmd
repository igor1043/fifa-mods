@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /W4 /WX /O2 /MT test_vp8_compat.c /Fobuild\test.obj /Febuild\test.exe /link /NOLOGO
if errorlevel 1 exit /b 1
pushd build
test.exe
set result=%errorlevel%
popd
popd
exit /b %result%
