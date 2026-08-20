@echo off
REM Build any QuillVille product from the repo root: build <product>
REM
REM   build list                     what can be built
REM   build radio                    Quill Radio, every artifact
REM   build radio -SkipSharedRuntime reuse the shared runtime already built
REM   build all                      the runtime, its installer, and every app
REM
REM All this does is run build.ps1 under PowerShell 7 (pwsh) when it is
REM installed, or Windows PowerShell otherwise, so the same command works from
REM cmd.exe, PowerShell, and a shortcut. All arguments are passed through.
setlocal
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
)
exit /b %ERRORLEVEL%
