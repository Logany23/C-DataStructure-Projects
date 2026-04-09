@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=E:\DProject\HuffmanCompressor"
cd /d "%APP_DIR%"
set "KAOYAN_MODE=1"

set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY312%" (
  set "PYTHON=%PY312%"
) else (
  set "PYTHON=python"
)

"%PYTHON%" "%APP_DIR%\run_family_agent.py"
endlocal
