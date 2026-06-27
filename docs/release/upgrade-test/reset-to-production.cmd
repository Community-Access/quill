@echo off
rem Remove the rehearsal override so QUILL uses the PRODUCTION update endpoint
rem (Community-Access/quill) again. Run this when rehearsal testing is done.
setx QUILL_UPDATE_API_URL "" >nul
reg delete HKCU\Environment /v QUILL_UPDATE_API_URL /f >nul 2>&1
set "QUILL_UPDATE_API_URL="
echo Cleared QUILL_UPDATE_API_URL.
echo Open a NEW terminal to confirm it is gone (echo %%QUILL_UPDATE_API_URL%%).
echo QUILL will now check the production update endpoint.
