@echo off
rem Shared dev launcher for every QuillVille app: find a usable Python, set the
rem dev-build flags, sync dependencies, and run a module from source.
rem
rem   set "QUILL_RUN_MODULE=quill.apps.lite"
rem   set "QUILL_RUN_TAG=run-quill-lite"
rem   call scripts\run_app.cmd %*
rem
rem The root `run-quill-<app>.bat` files are shims over this, the same way
rem `build-<product>.cmd` are shims over `build.ps1`. One copy, because the
rem interesting part -- "which interpreter actually has wx" -- had been written
rem out once per app, and several copies of a search order is several chances
rem for one app to be launched by a Python the others rejected.
rem
rem The module arrives in a variable rather than as %1 on purpose: `shift` moves
rem %1..%9 and leaves `%*` alone, so a positional module name would still be
rem sitting in `%*` and would reach the app as an argument to open.
rem
rem An app with its own data-folder variable (QuillLite's QUILL_LITE_DATA_DIR)
rem sets it in its own shim before calling this. Anything already defined is
rem left alone, so every variable here stays overridable from the caller.
setlocal EnableExtensions EnableDelayedExpansion

if not defined QUILL_RUN_MODULE (
    echo scripts\run_app.cmd needs QUILL_RUN_MODULE, e.g. quill.apps.lite
    exit /b 2
)
if not defined QUILL_RUN_TAG set "QUILL_RUN_TAG=run-app"

set "ROOT=%~dp0..\"
set "PYTHON_EXE="

REM --- Dev data folder + dev-build flag ---
REM QUILL_DATA_DIR is only honored when the dev-build flag is on, and it must
REM live under your home directory. Defaulting it here keeps test data out of
REM the repo and out of your real install, so you can test source changes
REM without rebuilding. Override either var before calling this script.
if not defined QUILL_DEV_BUILD set "QUILL_DEV_BUILD=1"
if not defined QUILL_DATA_DIR set "QUILL_DATA_DIR=%USERPROFILE%\quill-dev-data"

echo [%QUILL_RUN_TAG%] running %QUILL_RUN_MODULE% from source
echo [%QUILL_RUN_TAG%] QUILL_DATA_DIR=%QUILL_DATA_DIR%
if defined QUILL_LITE_DATA_DIR echo [%QUILL_RUN_TAG%] QUILL_LITE_DATA_DIR=%QUILL_LITE_DATA_DIR%

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
    echo No Python interpreter with wxPython was found.
    echo.
    echo Install the UI extras into the Python you develop with, for example:
    echo   pip install -e ".[ui,dev]"
    exit /b 1
)

REM Answers "which Python would this use?" without opening a window. Every
REM launcher gets it for free, which is what makes "it ran the wrong Python"
REM a question somebody can answer rather than guess at.
if /i "%~1"=="--print-python" (
    echo %PYTHON_EXE%
    exit /b 0
)

REM --- Auto-install dependencies when requirements.txt changes ---
REM All the hash/compare/pip logic lives in scripts\_autodeps.py so cmd has
REM nothing to mis-parse. Reinstalls only after a real change (e.g. a git pull).
REM Skip with QUILL_NO_AUTO_DEPS=1.
if exist "%ROOT%scripts\_autodeps.py" "%PYTHON_EXE%" "%ROOT%scripts\_autodeps.py" "%ROOT%"

pushd "%ROOT%"
"%PYTHON_EXE%" -m %QUILL_RUN_MODULE% %*
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
