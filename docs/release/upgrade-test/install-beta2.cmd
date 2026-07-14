@echo off
rem Silently install QUILL 0.8.1 Beta 1 (per-user, no elevation). Use to reset
rem state or to test the Beta 2 installer on its own.
setlocal
set "EXE=%~dp0installers\Quill-for-All-Setup-0.8.1 Beta 1.exe"
if not exist "%EXE%" (
  echo ERROR: "%EXE%" not found.
  echo Copy the built Beta 2 installer into the installers\ folder first.
  exit /b 1
)
echo Installing QUILL 0.8.1 Beta 1 silently...
"%EXE%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
echo Exit code %errorlevel%.
endlocal
