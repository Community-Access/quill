@echo off
rem Dev launcher for testing. Prefers this repo's venv, then the QUILL
rem checkout's venv (which has quill installed editable), then PATH python.
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
) else if exist "S:\QUILL\.venv\Scripts\python.exe" (
    set "PY=S:\QUILL\.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
"%PY%" -m quill.apps.radio %*
