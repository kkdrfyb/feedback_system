@echo off
setlocal
chcp 65001 >nul

where conda >nul 2>&1
if errorlevel 1 (
  echo Conda was not found on PATH. Please install Anaconda/Miniconda first.
  pause
  exit /b 1
)

set "ENV_NAME=feedback-system-dev"
set "ROOT=%~dp0"

echo Starting IFMS with single window...
conda run -n %ENV_NAME% python "%ROOT%run.py"
pause
