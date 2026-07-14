@echo off
rem Persist the rehearsal updater endpoint for your Windows user so every QUILL
rem launch checks the throwaway test repo (not production). Undo with
rem reset-to-production.cmd. Only redirects discovery; downloads still enforce
rem the HTTPS trusted-host allowlist.
setlocal
set "URL=https://api.github.com/repos/Community-Access/quill-update-selftest/releases"
rem Strip any stray double-quotes before persisting. setx can store a value with
rem embedded quotes, and a quoted URL reaches urllib as "https... -- failing the
rem update check with 'unknown url type: "https'. A real URL never contains a ".
set URL=%URL:"=%
setx QUILL_UPDATE_API_URL "%URL%" >nul
echo Persisted QUILL_UPDATE_API_URL for your user:
echo   %URL%
echo.
echo Open a NEW terminal (or use launch-quill.cmd) for it to take effect.
echo Run reset-to-production.cmd when you are finished.
endlocal
