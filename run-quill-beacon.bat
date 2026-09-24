@echo off
rem QuillBeacon, from this checkout rather than from an installed build.
rem
rem A shim over scripts\run_app.cmd, which holds the interpreter search and the
rem dev-build flags for every app -- the same shape as build-<product>.cmd over
rem build.ps1. See run-quill-lite.bat for why running from source is not the
rem same thing as running what sits in standalone\<app>\dist.
setlocal EnableExtensions
set "QUILL_RUN_MODULE=quill.apps.beacon"
set "QUILL_RUN_TAG=run-quill-beacon"
call "%~dp0scripts\run_app.cmd" %*
exit /b %ERRORLEVEL%
