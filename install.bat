@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ===================================================
echo   Quill Installation and Setup Script
echo ===================================================
echo.

set "ROOT=%~dp0"
cd /d "%ROOT%"

:: 1. Check Python installation and find a version >= 3.12
set "PYTHON_CMD="

:: Try 'python' first (picks up any active virtual environment)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :found_python
)

:: Try 'py' launcher
py -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :found_python
)

:: Try specific py launcher versions
for %%v in (3.14 3.13 3.12) do (
    py -%%v -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -%%v"
        goto :found_python
    )
)

:: Try 'python3'
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :found_python
)

:: Try explicit python version commands
for %%v in (3.14 3.13 3.12) do (
    python%%v -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python%%v"
        goto :found_python
    )
)

echo [ERROR] No Python interpreter version 3.12 or newer was found.
echo Please install Python 3.12 or newer (e.g. Python 3.14).
pause
exit /b 1

:found_python
for /f %%i in ('%PYTHON_CMD% -c "import sys; print(sys.version.split()[0])"') do set "PY_VER=%%i"
echo [INFO] Found compatible Python version !PY_VER! (using '%PYTHON_CMD%')

:: 2. Check for API Keys in Environment
echo [INFO] Checking environment variables for API keys...
set "API_KEY_FOUND=0"
if defined GOOGLE_API_KEY (
    echo [INFO] Found GOOGLE_API_KEY in environment.
    set "API_KEY_FOUND=1"
)
if defined GEMINI_API_KEY (
    echo [INFO] Found GEMINI_API_KEY in environment.
    set "API_KEY_FOUND=1"
)
if "!API_KEY_FOUND!"=="0" (
    echo [WARNING] Neither GOOGLE_API_KEY nor GEMINI_API_KEY was found in your environment.
    echo           If you plan to use Google Gemini AI features, please set one of them
    echo           in your Windows System/User Environment Variables.
)

:: 3. Determine Virtual Environment Path
set "VENV_DIR=%ROOT%.venv"
if not exist "%ROOT%.venv" (
    echo [INFO] Creating new, isolated virtual environment at %VENV_DIR% using !PYTHON_CMD!...
    !PYTHON_CMD! -m venv "%ROOT%.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Using existing local virtual environment at %VENV_DIR%
)

set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

:: 4. Upgrade pip and install package
echo [INFO] Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip

echo [INFO] Installing Quill with [ui,dev] dependencies in editable mode...
"%PIP_EXE%" install -e ".[ui,dev]"
if errorlevel 1 (
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo [INFO] Quill dependencies successfully installed.

:: 5. Create launch-quill.bat
echo [INFO] Creating launch-quill.bat...
(
echo @echo off
echo setlocal EnableExtensions EnableDelayedExpansion
echo set "ROOT=%%~dp0"
echo set "PYTHON_EXE="
echo if exist "%%ROOT%%..\..\env_quill\Scripts\pythonw.exe" (
echo     set "PYTHON_EXE=%%ROOT%%..\..\env_quill\Scripts\pythonw.exe"
echo ^) else if exist "%%ROOT%%.venv\Scripts\pythonw.exe" (
echo     set "PYTHON_EXE=%%ROOT%%.venv\Scripts\pythonw.exe"
echo ^) else if exist "%%ROOT%%venv\Scripts\pythonw.exe" (
echo     set "PYTHON_EXE=%%ROOT%%venv\Scripts\pythonw.exe"
echo ^)
echo if not defined PYTHON_EXE (
echo     echo [ERROR] Could not find pythonw.exe in virtual environments.
echo     echo Please run install.bat first to set up the environment.
echo     pause
echo     exit /b 1
echo ^)
echo start "" "%%PYTHON_EXE%%" -m quill --new-window %%*
echo exit /b 0
) > "%ROOT%launch-quill.bat"

:: 6. Create Desktop shortcut
echo [INFO] Creating Desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'Quill.lnk')); $Shortcut.TargetPath = '%ROOT%launch-quill.bat'; $Shortcut.WorkingDirectory = '%ROOT%'; $Shortcut.Description = 'Launch Quill Editor'; $Shortcut.Save()"
if errorlevel 1 (
    echo [WARNING] Failed to create Desktop shortcut. You can launch Quill using launch-quill.bat.
) else (
    echo [INFO] Desktop shortcut 'Quill' created successfully.
)

echo.
echo ===================================================
echo   Installation complete!
echo   You can launch Quill using the Desktop shortcut
echo   or run: launch-quill.bat
echo ===================================================
echo.
pause
exit /b 0
