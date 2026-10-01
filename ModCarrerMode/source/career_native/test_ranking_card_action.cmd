@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0build"
if errorlevel 1 exit /b 1
if not exist ranking_card_tests mkdir ranking_card_tests
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /Foranking_card_tests\ /Fe:test_ranking_card_action.exe ..\native\test_ranking_card_action.cpp ..\native\integration\ranking_card_action.cpp
if errorlevel 1 exit /b 1
test_ranking_card_action.exe
if errorlevel 1 exit /b 1
popd
endlocal
