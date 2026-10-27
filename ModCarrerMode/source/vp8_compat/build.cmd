@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /W4 /WX /O2 /MT /LD vp8_compat.c /Fobuild\vp8_compat.obj /Febuild\vp8_compat.dll /link /NOLOGO /IMPLIB:build\vp8_compat.lib
set result=%errorlevel%
popd
exit /b %result%
