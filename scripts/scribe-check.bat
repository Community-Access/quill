@echo off
rem Check Scribe for Documents in every QUILL app, offline: no network, no credit.
rem Double-click it, or run it from a command prompt. The result is said first.
rem A live run needs Scribe sign-in first: python -m quill.tools.scribe_check --live quick
setlocal
cd /d "%~dp0.."
where python >/dev/null 2>&1
if errorlevel 1 (
  echo Python was not found. Install it, or open a console where python works, then run this again.
  pause
  exit /b 1
)
python -m quill.tools.scribe_check %*
set "rc=%errorlevel%"
echo %cmdcmdline% | find /i "%~0" >nul
if not errorlevel 1 (
  echo.
  if "%rc%"=="0" (echo Scribe check passed. Press any key to close this window.) else (echo Scribe check did not pass. Press any key to close this window.)
  pause >nul
)
exit /b %rc%
