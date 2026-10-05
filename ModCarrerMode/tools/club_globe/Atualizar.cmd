@echo off
setlocal
chcp 65001 >nul
set "FF_PREVIEW_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%FF_PREVIEW_PY%" (
  "%FF_PREVIEW_PY%" -X utf8 "%~dp0build_preview.py"
) else (
  py -X utf8 "%~dp0build_preview.py"
)
if errorlevel 1 (
  echo Nao foi possivel atualizar a previa. Confira o INI, Python e Pillow.
  pause
  exit /b 1
)
powershell.exe -NoProfile -File "%~dp0launch_preview.ps1"
