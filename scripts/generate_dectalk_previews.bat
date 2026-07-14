@echo off
REM Regenerate the 9 DECtalk voice previews with the bundled QUILL phrase.
REM
REM DECtalk synthesis is driven through DECtalk.dll (the real synthesis runtime),
REM not the graphical speak.exe sample. Double-click or invoke from a terminal;
REM the script anchors itself to the repo root via %~dp0..

setlocal
cd /d "%~dp0.."

set "PHRASE=scripts\phrase.txt"
set "DECTALK_DLL=%CD%\tools\speech\dectalk\AMD64\DECtalk.dll"

if not exist "%PHRASE%" (
    echo ERROR: phrase file not found: %PHRASE%
    endlocal & exit /b 2
)
if not exist "%DECTALK_DLL%" (
    echo ERROR: DECtalk.dll not found: %DECTALK_DLL%
    endlocal & exit /b 2
)

echo Phrase file : %PHRASE%
echo DECtalk DLL : %DECTALK_DLL%
echo.
echo Regenerating DECtalk previews...
echo.

python scripts\gen_voice_previews.py "%PHRASE%" --engines dectalk --overwrite --dectalk-exe "%DECTALK_DLL%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo SUCCESS: DECtalk previews regenerated with the new phrase.
) else (
    echo FAILURE: one or more DECtalk voices did not generate ^(exit %RC%^).
    echo See the per-voice ERROR lines above for the cause.
)

echo.
pause
endlocal & exit /b %RC%
