@echo off
REM Build inkwell: Quill Inkwell.
REM
REM Options are passed straight through, so these all work:
REM   build-inkwell          build it, log to local\build-logs
REM   build-inkwell -NoLog   stream the full build output instead
REM   build-inkwell -Sign    Authenticode-sign the payload and installers
REM   build-inkwell -NoCopy  leave artifacts in dist, skip the \installs copy
REM
REM Finished installers and zips are copied to the \installs folder on this
REM drive. All the real work lives in build.ps1 and the per-product scripts it
REM calls; this file only picks the product.
setlocal
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" inkwell %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" inkwell %*
)
exit /b %ERRORLEVEL%
