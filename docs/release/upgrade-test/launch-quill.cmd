@echo off
rem Launch the installed QUILL with the rehearsal updater endpoint active for
rem THIS run, so Help > Check for Updates queries the throwaway test repo even
rem if a persisted setx has not yet propagated to already-running programs.
setlocal
set "QUILL_UPDATE_API_URL=https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
set "APP=%LOCALAPPDATA%\Programs\QUILL for All\quill.exe"
if not exist "%APP%" (
  echo ERROR: QUILL not installed at "%APP%".
  echo Run install-beta1.cmd first.
  exit /b 1
)
echo Launching QUILL with the rehearsal updater endpoint:
echo   %QUILL_UPDATE_API_URL%
start "" "%APP%" -m quill
echo.
echo Next, in QUILL:  Help  ^>  Check for Updates
echo Expect "0.8.0 Beta 2 is available" -^> choose Install now.
endlocal
