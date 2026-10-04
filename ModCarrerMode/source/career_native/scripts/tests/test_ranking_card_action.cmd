@echo off
setlocal
call "%~dp0..\env.cmd" "tests" "test_ranking_card_action"
if errorlevel 1 exit /b 1
if not exist ranking_card_tests mkdir ranking_card_tests
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /EHsc /O2 /MT /Foranking_card_tests\ /Fe:test_ranking_card_action.exe "%CAREER_ROOT%\tests\core\test_ranking_card_action.cpp" "%CAREER_ROOT%\src\platform\input\ranking_card_action.cpp"
if errorlevel 1 exit /b 1
test_ranking_card_action.exe
if errorlevel 1 exit /b 1
popd
endlocal
