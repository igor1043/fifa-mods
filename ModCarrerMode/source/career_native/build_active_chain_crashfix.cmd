@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
rc /nologo /fo dinput8_active_chain_resource.res dinput8_active_chain_resource.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c ..\native\fce_contracts.c ..\native\fce_model.c ..\native\fce_runtime.c ..\native\crowd_runtime.c ..\native\retirement_engine.c ..\native\global_ranking.c
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /D_CRT_SECURE_NO_WARNINGS /c ..\native\integration\dinput8_wrapper.c
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DIMGUI_IMPL_WIN32_DISABLE_GAMEPAD /I..\third_party\imgui /c ..\native\integration\ranking_overlay.cpp ..\native\integration\ranking_card_action.cpp ..\native\integration\ranking_input_gate.cpp ..\native\integration\mod_overlay_screens.cpp ..\native\integration\mod_xinput_gate.cpp ..\third_party\imgui\imgui.cpp ..\third_party\imgui\imgui_draw.cpp ..\third_party\imgui\imgui_tables.cpp ..\third_party\imgui\imgui_widgets.cpp ..\third_party\imgui\backends\imgui_impl_win32.cpp ..\third_party\imgui\backends\imgui_impl_dx11.cpp
if errorlevel 1 exit /b 1
link /nologo /DLL /MAP:dinput8_my_team_height_fix.map /MAPINFO:EXPORTS /OUT:dinput8.dll /DEF:..\native\integration\dinput8_wrapper.def dinput8_wrapper.obj fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj global_ranking.obj ranking_overlay.obj ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj dinput8_active_chain_resource.res kernel32.lib user32.lib gdi32.lib dwmapi.lib d3d11.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
copy /Y dinput8.dll "%~dp0..\..\..\dinput8.dll" >nul
if errorlevel 1 exit /b 1
popd
endlocal
