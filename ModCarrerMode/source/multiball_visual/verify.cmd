@echo off
setlocal
if "%~1"=="" (
 echo Usage: verify.cmd "root containing data\sceneassets\standball"
 exit /b 1
)
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_native_stands.cpp /Fobuild\ /Febuild\test_native_stands.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_native_stands.exe "%~1"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_scene_selection.cpp /Fobuild\ /Febuild\test_scene_selection.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_scene_selection.exe "%~dp0standball.ini"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT ..\common\test_field_prop_shadow.cpp /Fobuild\ /Febuild\test_field_prop_shadow.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_field_prop_shadow.exe build\field_bind.lua
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT ..\common\test_field_prop_shadow_native.cpp /Fobuild\ /Febuild\test_field_prop_shadow_native.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_field_prop_shadow_native.exe
set result=%errorlevel%
popd
exit /b %result%
