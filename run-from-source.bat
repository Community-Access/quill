@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "PYTHON_EXE="

REM --- Dev data folder + dev-build flag ---
REM QUILL_DATA_DIR is only honored when the dev-build flag is on, and it must
REM live under your home directory. Defaulting it here keeps test data out of
REM the repo and out of your real install, so you can test source changes
REM without rebuilding. Override either var before calling this script.
if not defined QUILL_DEV_BUILD set "QUILL_DEV_BUILD=1"
if not defined QUILL_DATA_DIR set "QUILL_DATA_DIR=%USERPROFILE%\quill-dev-data"

REM Point at an installed QUILL so a source run can discover bundled engine
REM assets that are not in the source tree (whisper.cpp, DECtalk, Piper under
REM tools\speech\). Search the common install locations and use the first that
REM has the engine folder. Override by setting QUILL_APP_ROOT yourself.
if not defined QUILL_APP_ROOT (
    for %%R in ("C:\quill" "%LOCALAPPDATA%\Programs\Quill" "%ProgramFiles%\Quill") do (
        if not defined QUILL_APP_ROOT if exist "%%~R\tools\speech" set "QUILL_APP_ROOT=%%~R"
    )
)

echo [run-from-source] QUILL_DATA_DIR=%QUILL_DATA_DIR%
if defined QUILL_APP_ROOT echo [run-from-source] QUILL_APP_ROOT=%QUILL_APP_ROOT%

if defined QUILL_PYTHON call :UsePythonIfHasWx "%QUILL_PYTHON%"
if not defined PYTHON_EXE if defined VIRTUAL_ENV call :UsePythonIfHasWx "%VIRTUAL_ENV%\Scripts\python.exe"
if not defined PYTHON_EXE if defined CONDA_PREFIX call :UsePythonIfHasWx "%CONDA_PREFIX%\python.exe"
if not defined PYTHON_EXE call :UsePythonIfHasWx "%ROOT%.venv\Scripts\python.exe"
if not defined PYTHON_EXE call :UsePythonIfHasWx "%ROOT%venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        if not defined PYTHON_EXE call :UsePythonIfHasWx "%%I"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('where py.exe 2^>nul') do (
        if not defined PYTHON_EXE call :UsePythonIfHasWx "%%I"
    )
)

if not defined PYTHON_EXE (
    echo No Python interpreter was found.
    echo.
    echo Create or activate a development environment first, for example:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev,ui]"
    exit /b 1
)

if /i "%~1"=="--print-python" (
    echo %PYTHON_EXE%
    exit /b 0
)

REM --- Auto-install dependencies when requirements.txt changes ---
REM All the hash/compare/pip logic lives in scripts\_autodeps.py so cmd has
REM nothing to mis-parse. Reinstalls only after a real change (e.g. a git pull).
REM Skip with QUILL_NO_AUTO_DEPS=1.
if exist "%ROOT%scripts\_autodeps.py" "%PYTHON_EXE%" "%ROOT%scripts\_autodeps.py" "%ROOT%"

REM --new-window forces Quill to open its own window instead of forwarding to a
REM single-instance "primary". A leftover instance.lock from a force-killed run
REM could otherwise make this exit silently with no window. The dev launcher
REM should always actually open Quill.
pushd "%ROOT%"
"%PYTHON_EXE%" -m quill --new-window %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

:UsePythonIfHasWx
set "CANDIDATE=%~1"
if not exist "%CANDIDATE%" exit /b 0
"%CANDIDATE%" -c "import wx" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYTHON_EXE=%CANDIDATE%"
exit /b 0