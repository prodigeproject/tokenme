@echo off
REM tokenme launcher — Windows CMD
set "HERE=%~dp0.."
set "PYTHONPATH=%HERE%;%PYTHONPATH%"
python -m tokenme %*
