@echo off
setlocal
call "%~dp0..\..\..\career_native\scripts\env.cmd" "build" "trophy_room_bridge"
if errorlevel 1 exit /b 1
if not exist dinput8_active_chain_resource.res copy /Y "%CAREER_ROOT%\build\production\dinput8_active_chain_resource.res" . >nul
cl /nologo /std:c11 /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c "%CAREER_ROOT%\src\host\dinput8_wrapper.c"
if errorlevel 1 exit /b 1
link /nologo /DLL /MAP:dinput8.map /MAPINFO:EXPORTS /OUT:dinput8.dll /DEF:"%CAREER_ROOT%\src\host\dinput8_wrapper.def" dinput8_wrapper.obj stadium_thumbnail.obj swiss_delta.obj league_query_batches.obj tournament_list_compat.obj fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj dinput8_active_chain_resource.res kernel32.lib user32.lib gdi32.lib psapi.lib bcrypt.lib ole32.lib windowscodecs.lib
set result=%errorlevel%
popd
exit /b %result%
