@echo off
setlocal
if "%~5"=="" exit /b 2
call "%~dp0build_club_details_preview.cmd"
if errorlevel 1 exit /b 1
"%~dp0..\..\build\previews\generate_club_details_preview\generate_club_details_preview.exe" "%~1" "%~2" "%~3" "%~4" "%~5"
exit /b %errorlevel%
