@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1

if not exist "%~dp0build" mkdir "%~dp0build"
pushd "%~dp0build"
cl /nologo /std:c11 /O2 /W4 /D_CRT_SECURE_NO_WARNINGS /Fe:easfc_hide_plugin_safe_test.exe ..\test_easfc_hide_plugin_safe.c
set "EASFC_TEST_BUILD_RC=%ERRORLEVEL%"
popd
exit /b %EASFC_TEST_BUILD_RC%
