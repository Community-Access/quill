@echo off
REM Build quill: QUILL itself -- portable bundle + Windows installer.
REM
REM Options are passed straight through, so these all work:
REM   build-quill          build it, log to local\build-logs
REM   build-quill -NoLog   stream the full build output instead
REM   build-quill -Sign    Authenticode-sign the payload and installers
REM   build-quill -NoCopy  leave artifacts in dist, skip the \installs copy
REM
REM Finished installers and zips are copied to the \installs folder on this
REM drive. All the real work lives in build.ps1 and the per-product scripts it
REM calls; this file only picks the product.
setlocal
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" quill %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" quill %*
)
exit /b %ERRORLEVEL%
