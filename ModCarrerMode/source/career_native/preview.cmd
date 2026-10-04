@echo off
setlocal
if "%~1"=="" (
    echo Uso: preview.cmd nome_do_script argumentos
    echo Scripts em scripts\previews. Testes visuais em scripts\tests.
    exit /b 0
)
if not exist "%~dp0scripts\previews\%~1.cmd" exit /b 2
call "%~dp0scripts\previews\%~1.cmd" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%
