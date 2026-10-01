@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /I..\third_party\imgui /Fe:test_ranking_controller_capture.exe ..\native\test_ranking_controller_capture.cpp ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj /link user32.lib gdi32.lib dwmapi.lib d3d11.lib dxgi.lib psapi.lib
if errorlevel 1 exit /b 1
test_ranking_controller_capture.exe
if errorlevel 1 exit /b 1
popd
endlocal
