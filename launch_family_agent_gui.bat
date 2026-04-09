@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=E:\DProject\HuffmanCompressor"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%\run_family_agent_gui.py" (
  echo [Error] 找不到项目：%APP_DIR%
  echo 请用记事本打开本 bat，把 APP_DIR 改成你的 HuffmanCompressor 目录。
  pause
  exit /b 1
)

set "KAOYAN_MODE=1"

set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY312%" (
  set "PYTHON=%PY312%"
) else (
  set "PYTHON=python"
)

echo 使用 Python: "%PYTHON%"
"%PYTHON%" -c "import PyQt6" 2>nul
if errorlevel 1 (
  echo [Info] 未检测到 PyQt6，正在回退到 CLI 版本...
  "%PYTHON%" "%APP_DIR%\run_family_agent.py"
  exit /b 0
)

"%PYTHON%" -u "%APP_DIR%\run_family_agent_gui.py"
if errorlevel 1 (
  echo.
  pause
)
endlocal
