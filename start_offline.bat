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
set "DIST=%ROOT%frontend\dist"

if not exist "%DIST%\index.html" (
  echo Frontend dist not found at %DIST%.
  echo Please build frontend on an online machine and copy dist to %DIST%.
  pause
  exit /b 1
)

set "IFMS_SKIP_FRONTEND=1"

echo Starting IFMS (offline mode, single window)...
conda run -n %ENV_NAME% python "%ROOT%run.py"
pause
