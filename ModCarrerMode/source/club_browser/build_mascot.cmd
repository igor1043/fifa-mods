@echo off
setlocal
if "%~1"=="" exit /b 2
set "MASCOT_OUTPUT=%~f1"
set "MASCOT_SOURCE=%~dp0native"
if not exist "%MASCOT_OUTPUT%" mkdir "%MASCOT_OUTPUT%"
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%MASCOT_OUTPUT%"
cl /nologo /O2 /MT /c "%MASCOT_SOURCE%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT /LD "%MASCOT_SOURCE%\render.cpp" miniz_tinfl.obj /Fe:club_browser.dll /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%MASCOT_SOURCE%\test_scene_publication.cpp" miniz_tinfl.obj /Fe:test_scene_publication.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_scene_publication.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%MASCOT_SOURCE%\test_mascot_view.cpp" miniz_tinfl.obj /Fe:test_mascot_view.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_mascot_view.exe
if errorlevel 1 exit /b 1
popd
