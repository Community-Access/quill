@echo off
REM Build runtime-installer: QuillVille-Runtime-Setup.exe. Build it on a FRESH runtime:
REM   an app build stages 306 MB of ffmpeg/mpv into the runtime dist, and
REM   this installer packs whatever is sitting there.
REM
REM Options are passed straight through, so these all work:
REM   build-runtime-installer          build it, log to local\build-logs
REM   build-runtime-installer -NoLog   stream the full build output instead
REM   build-runtime-installer -Sign    Authenticode-sign the payload and installers
REM   build-runtime-installer -NoCopy  leave artifacts in dist, skip the \installs copy
REM
REM Finished installers and zips are copied to the \installs folder on this
REM drive. All the real work lives in build.ps1 and the per-product scripts it
REM calls; this file only picks the product.
setlocal
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" runtime-installer %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" runtime-installer %*
)
exit /b %ERRORLEVEL%
