@echo off
rem Silently install QUILL 0.8.0 Beta 1 (per-user, no elevation) for the
rem update rehearsal. The installer is in installers\ (gitignored).
setlocal
set "EXE=%~dp0installers\Quill-for-All-Setup-0.8.0 Beta 1.exe"
if not exist "%EXE%" (
  echo ERROR: "%EXE%" not found.
  echo Copy the built Beta 1 installer into the installers\ folder first.
  exit /b 1
)
echo Installing QUILL 0.8.0 Beta 1 silently...
"%EXE%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
echo Exit code %errorlevel%.
endlocal
