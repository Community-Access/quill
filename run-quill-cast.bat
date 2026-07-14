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

echo [run-quill-cast] QUILL_DATA_DIR=%QUILL_DATA_DIR%

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

REM --- Auto-install dependencies when requirements.txt changes ---
if exist "%ROOT%scripts\_autodeps.py" "%PYTHON_EXE%" "%ROOT%scripts\_autodeps.py" "%ROOT%"

pushd "%ROOT%"
"%PYTHON_EXE%" -m quill.apps.podcasts %*
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
