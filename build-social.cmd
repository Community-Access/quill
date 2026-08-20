@echo off
REM Build social: Quill Social.
REM
REM Options are passed straight through, so these all work:
REM   build-social          build it, log to local\build-logs
REM   build-social -NoLog   stream the full build output instead
REM   build-social -Sign    Authenticode-sign the payload and installers
REM   build-social -NoCopy  leave artifacts in dist, skip the \installs copy
REM
REM Finished installers and zips are copied to the \installs folder on this
REM drive. All the real work lives in build.ps1 and the per-product scripts it
REM calls; this file only picks the product.
setlocal
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" social %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" social %*
)
exit /b %ERRORLEVEL%
