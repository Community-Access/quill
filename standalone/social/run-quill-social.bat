@echo off
rem Run QUILL Social from source on Windows.
rem Usage: run-quill-social.bat
setlocal
set QUILLSOCIAL_DATA=%~dp0data
python "%~dp0launcher.py" %*
endlocal
