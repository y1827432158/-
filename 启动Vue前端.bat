@echo off
cd /d "%~dp0"
set "LOCAL_PY=%~dp0.venv\Scripts\python.exe"
if exist "%LOCAL_PY%" (
  "%LOCAL_PY%" start_frontend.py
) else (
  py -3 start_frontend.py
)
