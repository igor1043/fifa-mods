@echo off
setlocal
if "%~1"=="" exit /b 2
set "STADIUM_OUTPUT=%~f1"
set "STADIUM_SOURCE=%~dp0native"
if not exist "%STADIUM_OUTPUT%" mkdir "%STADIUM_OUTPUT%"
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%STADIUM_OUTPUT%"
cl /nologo /O2 /MT /c "%STADIUM_SOURCE%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
for %%T in (test_stadium_view test_choice_focus test_scene_publication test_catalog_metadata) do (
 cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%STADIUM_SOURCE%\%%T.cpp" miniz_tinfl.obj /Fe:%%T.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
 if errorlevel 1 exit /b 1
 %%T.exe
 if errorlevel 1 exit /b 1
)
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%STADIUM_SOURCE%\..\..\common\test_native_scene_vignette.cpp" /Fe:test_native_scene_vignette.exe
if errorlevel 1 exit /b 1
test_native_scene_vignette.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT /LD "%STADIUM_SOURCE%\render.cpp" miniz_tinfl.obj /Fe:club_browser.dll /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
popd
