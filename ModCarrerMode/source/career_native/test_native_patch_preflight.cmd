@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W3 /O2 /MT /Fe:test_native_patch_preflight.exe ..\native\test_native_patch_preflight.c fce_contracts.obj fce_model.obj fce_runtime.obj crowd_runtime.obj retirement_engine.obj global_ranking.obj ranking_overlay.obj ranking_card_action.obj ranking_input_gate.obj mod_overlay_screens.obj mod_xinput_gate.obj imgui.obj imgui_draw.obj imgui_tables.obj imgui_widgets.obj imgui_impl_win32.obj imgui_impl_dx11.obj /link kernel32.lib user32.lib gdi32.lib dwmapi.lib d3d11.lib dxgi.lib psapi.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_native_patch_preflight.exe
if errorlevel 1 exit /b 1
popd
endlocal
