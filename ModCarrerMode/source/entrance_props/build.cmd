@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /W4 /WX /O2 /MT test_entrance.cpp /Fobuild\ /Febuild\test_entrance.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_entrance.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT test_crest.cpp /Fobuild\ /Febuild\test_crest.exe /link /NOLOGO
if errorlevel 1 exit /b 1
build\test_crest.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT competition_catalog_test.cpp /Fobuild\ /Febuild\competition_catalog_test.exe /link /NOLOGO
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /MT /LD entrance_props.cpp /Fobuild\ /Febuild\entrance_props.dll /link /NOLOGO
if errorlevel 1 exit /b 1
popd
endlocal
