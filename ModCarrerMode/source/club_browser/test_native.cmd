@echo off
setlocal
if "%~1"=="" (
 echo Usage: test_native.cmd "FIFA root" [output directory]
 exit /b 2
)
set "CLUB_SOURCE=%~dp0native"
set "CLUB_DATA=%~dp0..\..\data\club_browser"
set "CLUB_GAME=%~f1"
if "%~2"=="" (set "CLUB_TEST_OUTPUT=%TEMP%\fifa16_club_browser_tests") else (set "CLUB_TEST_OUTPUT=%~f2")
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if not exist "%CLUB_TEST_OUTPUT%" mkdir "%CLUB_TEST_OUTPUT%"
pushd "%CLUB_TEST_OUTPUT%"
if errorlevel 1 exit /b 1
cl /nologo /O2 /MT /c "%CLUB_SOURCE%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_native.cpp" miniz_tinfl.obj /Fe:test_native.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
test_native.exe "%CLUB_DATA%" "%CLUB_GAME%" "%CLUB_TEST_OUTPUT%"
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_worker_process.cpp" miniz_tinfl.obj /Fe:test_worker_process.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib bcrypt.lib
if errorlevel 1 exit /b 1
for %%M in (fixture retry retry-permanent) do (
 test_worker_process.exe --%%M "%CLUB_TEST_OUTPUT%\%%M"
 if errorlevel 1 exit /b 1
)
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_context_restore.cpp" /Fe:test_context_restore.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib windowscodecs.lib
if errorlevel 1 exit /b 1
test_context_restore.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_constant_range_pixels.cpp" /Fe:test_constant_range_pixels.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib windowscodecs.lib
if errorlevel 1 exit /b 1
test_constant_range_pixels.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_scene_publication.cpp" miniz_tinfl.obj /Fe:test_scene_publication.exe /link user32.lib gdi32.lib ole32.lib d3d11.lib d3dcompiler.lib dxgi.lib psapi.lib windowscodecs.lib
if errorlevel 1 exit /b 1
test_scene_publication.exe
if errorlevel 1 exit /b 1
cl /nologo /O2 /W3 /EHsc /std:c++17 /utf-8 /MT "%CLUB_SOURCE%\test_player_animation.cpp" /Fe:test_player_animation.exe /link d3d11.lib dxgi.lib
if errorlevel 1 exit /b 1
test_player_animation.exe
if errorlevel 1 exit /b 1
popd
exit /b 0
