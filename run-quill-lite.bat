@echo off
rem QUILL Lite, from this checkout rather than from an installed build.
rem
rem This is the one to reach for after editing quill\apps\lite*.py and seeing
rem nothing change: standalone\quilllite\dist\ holds a FROZEN build carrying its
rem own copy of the quill package, so a source edit cannot reach it and neither
rem can a commit. This runs the source.
rem
rem QUILL Lite keeps its state in QUILL_LITE_DATA_DIR, not QUILL_DATA_DIR --
rem two products, two folders, which is the whole point of the product
rem (quill\core\lite\paths.py). A dev run gets its own, so testing a change
rem cannot rewrite the settings, recent files or recovered work of a real
rem QUILL Lite install. Point QUILL_LITE_DATA_DIR at %LOCALAPPDATA%\QuillLite
rem yourself to test against the real one.
setlocal EnableExtensions
if not defined QUILL_LITE_DATA_DIR set "QUILL_LITE_DATA_DIR=%USERPROFILE%\quill-dev-data\QuillLite"
set "QUILL_RUN_MODULE=quill.apps.lite"
set "QUILL_RUN_TAG=run-quill-lite"
call "%~dp0scripts\run_app.cmd" %*
exit /b %ERRORLEVEL%
