@echo off
rem Show the current/persisted rehearsal override and whether QUILL is installed.
echo === QUILL update-rehearsal status ===
echo QUILL_UPDATE_API_URL (this session): "%QUILL_UPDATE_API_URL%"
set "PERSISTED="
for /f "tokens=2,*" %%a in ('reg query HKCU\Environment /v QUILL_UPDATE_API_URL 2^>nul ^| findstr /i QUILL_UPDATE_API_URL') do set "PERSISTED=%%b"
if defined PERSISTED (echo QUILL_UPDATE_API_URL (persisted^): %PERSISTED%) else (echo QUILL_UPDATE_API_URL (persisted^): ^<not set^>)
set "APP=%LOCALAPPDATA%\Programs\QUILL for All\quill.exe"
if exist "%APP%" (echo Installed: "%APP%") else (echo Installed: NO)
