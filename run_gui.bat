@echo off
cd /d "%~dp0"
REM Use pythonw = no black CMD window
where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
  start "" pythonw gui.py
  exit /b 0
)
REM Fallback: py launcher windowless
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  start "" pyw gui.py
  exit /b 0
)
echo pythonw not found. Install Python and retry.
pause
