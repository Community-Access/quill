@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "LAUNCHER="

call :try_launcher "%ROOT%dist\windows\portable\run-quill.cmd"
if defined LAUNCHER goto :found

call :try_launcher "%ROOT%windows-distribution\portable\run-quill.cmd"
if defined LAUNCHER goto :found

call :try_launcher "%ROOT%release-dist-0.1-final\portable\run-quill.cmd"
if defined LAUNCHER goto :found

call :try_launcher "%ROOT%release-dist-0.1-r2\portable\run-quill.cmd"
if defined LAUNCHER goto :found

for /f "delims=" %%D in ('dir "%ROOT%release-dist-*" /b /ad /o-d /t:w 2^>nul') do (
    call :try_launcher "%ROOT%%%D\portable\run-quill.cmd"
    if defined LAUNCHER goto :found
)

echo No portable Quill build was found under %ROOT%
echo.
echo Expected one of these launchers:
echo   dist\windows\portable\run-quill.cmd
echo   windows-distribution\portable\run-quill.cmd
echo   release-dist-0.1-final\portable\run-quill.cmd
echo   release-dist-0.1-r2\portable\run-quill.cmd
echo   release-dist-*\portable\run-quill.cmd
exit /b 1

:found
if /i "%~1"=="--print" (
    echo %LAUNCHER%
    exit /b 0
)

echo Launching Quill from:
echo   %LAUNCHER%
echo.
pushd "%ROOT%"
call "%LAUNCHER%"
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

:try_launcher
if exist "%~1" set "LAUNCHER=%~1"
exit /b 0