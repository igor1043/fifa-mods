@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
rc /nologo /fo dinput8_active_chain_resource.res dinput8_active_chain_resource.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c ..\native\fce_contracts.c ..\native\fce_model.c ..\native\fce_runtime.c ..\native\crowd_runtime.c
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c ..\native\integration\dinput8_wrapper.c
if errorlevel 1 exit /b 1
link /nologo /DLL /MAP:dinput8_my_team_height_fix.map /MAPINFO:EXPORTS /OUT:dinput8.dll /DEF:..\native\integration\dinput8_wrapper.def dinput8_wrapper.obj fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj dinput8_active_chain_resource.res kernel32.lib user32.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
popd
endlocal
