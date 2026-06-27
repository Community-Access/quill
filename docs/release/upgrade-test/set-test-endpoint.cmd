@echo off
rem Persist the rehearsal updater endpoint for your Windows user so every QUILL
rem launch checks the throwaway test repo (not production). Undo with
rem reset-to-production.cmd. Only redirects discovery; downloads still enforce
rem the HTTPS trusted-host allowlist.
set "URL=https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
setx QUILL_UPDATE_API_URL "%URL%" >nul
echo Persisted QUILL_UPDATE_API_URL for your user:
echo   %URL%
echo.
echo Open a NEW terminal (or use launch-quill.cmd) for it to take effect.
echo Run reset-to-production.cmd when you are finished.
