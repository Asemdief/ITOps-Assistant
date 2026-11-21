@echo off
cd /d "%~dp0"

echo Stopping old process...
taskkill /F /IM ITOps-Assistant.exe 2>nul

echo Cleaning...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /f /q ITOps-Assistant.spec 2>nul

set ICON_ARGS=
if exist icon.ico set ICON_ARGS=--icon icon.ico

set VER_ARGS=
if exist version_info.txt set VER_ARGS=--version-file version_info.txt

echo Building v1.9 (windowed + CustomTkinter)...
python -m PyInstaller --onefile --windowed --noconsole --name "ITOps-Assistant" %ICON_ARGS% %VER_ARGS% --hidden-import=psutil --hidden-import=customtkinter --hidden-import=modules --hidden-import=modules.win_silent --hidden-import=modules.network --hidden-import=modules.inventory --hidden-import=modules.processes --hidden-import=modules.health --hidden-import=modules.root_cause --hidden-import=modules.fix_plan --hidden-import=modules.fix_engine --hidden-import=modules.history --hidden-import=modules.export --hidden-import=modules.paths --collect-all customtkinter gui.py

if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)

echo.
echo DONE: dist\ITOps-Assistant.exe
pause
