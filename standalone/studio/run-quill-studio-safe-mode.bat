@echo off
rem Dev launcher for testing in Safe Mode.
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0..\..\.venv\Scripts\python.exe" (
    set "PY=%~dp0..\..\.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
"%PY%" -m quill.apps.studio --safe-mode %*
