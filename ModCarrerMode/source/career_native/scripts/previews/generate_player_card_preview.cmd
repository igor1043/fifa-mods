@echo off
setlocal
call "%~dp0..\env.cmd" "previews" "generate_player_card_preview"
if errorlevel 1 exit /b 1
if "%~4"=="" (
  echo Uso: generate_player_card_preview.cmd ^<raiz-fifa^> ^<fixture-clube-1.bin^> ^<fixture-clube-2.bin^> ^<pasta-saida-nova^>
  exit /b 2
)
cl /nologo /std:c11 /W3 /O2 /MT /DMINIZ_NO_ZLIB_APIS /DMINIZ_NO_DEFLATE_APIS /DMINIZ_NO_ARCHIVE_APIS /DMINIZ_NO_STDIO /c "%CAREER_ROOT%\third_party\miniz\miniz_tinfl.c"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /W3 /EHsc /O2 /MT /D_CRT_SECURE_NO_WARNINGS /I"%CAREER_ROOT%\third_party\imgui" "%CAREER_ROOT%\tools\previews\generate_player_card_preview.cpp" "%CAREER_ROOT%\src\render\assets\fifa_player_assets.cpp" "%CAREER_ROOT%\src\render\poses\fifa_player_pose.cpp" "%CAREER_ROOT%\src\render\scenes\fifa_club_room.cpp" "%CAREER_ROOT%\src\render\renderer\fifa_player_renderer.cpp" "%CAREER_ROOT%\third_party\imgui\imgui.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_draw.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_tables.cpp" "%CAREER_ROOT%\third_party\imgui\imgui_widgets.cpp" "%CAREER_ROOT%\third_party\imgui\backends\imgui_impl_dx11.cpp" miniz_tinfl.obj /Fe:generate_player_card_preview.exe /link d3d11.lib d3dcompiler.lib dxgi.lib windowscodecs.lib ole32.lib
if errorlevel 1 exit /b 1
generate_player_card_preview.exe "%~1" "%~2" "%~3" "%~4"
if errorlevel 1 exit /b 1
popd
endlocal
