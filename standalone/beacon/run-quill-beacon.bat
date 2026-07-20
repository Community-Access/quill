@echo off
rem Run QuillBeacon from source on Windows.
rem Usage: run-quill-beacon.bat
setlocal
set QUILLBEACON_DATA=%~dp0data
python "%~dp0launcher.py" %*
endlocal