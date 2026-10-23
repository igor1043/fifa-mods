@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
ml64 /nologo /c /Fobuild\subson_friendly_thunks.obj subson_friendly_thunks.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /LD /D_CRT_SECURE_NO_WARNINGS subson_bridge.c subson_friendly.c subson_career.c patch_memory.c build\subson_friendly_thunks.obj /Fobuild\ /Febuild\subson_bridge.dll /link /NOLOGO /Brepro /IMPLIB:build\subson_bridge.lib bcrypt.lib
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT bridge_probe.c /Fobuild\bridge_probe.obj /Febuild\bridge_probe.exe /link /NOLOGO
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DSUBSON_FRIENDLY_TEST test_friendly.c subson_friendly.c patch_memory.c build\subson_friendly_thunks.obj /Fobuild\ /Febuild\test_friendly.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_friendly.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS test_career.c subson_career.c patch_memory.c build\subson_friendly_thunks.obj /Fobuild\ /Febuild\test_career.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_career.exe
if errorlevel 1 exit /b 1
popd
endlocal
