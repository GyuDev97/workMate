@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3를 설치한 뒤 다시 실행해 주세요.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js와 npm을 설치한 뒤 다시 실행해 주세요.
  pause
  exit /b 1
)

if "%WORKMATE_PYTHON_ENV%"=="" set "WORKMATE_PYTHON_ENV=%USERPROFILE%\Desktop\python\.venv"
set "PYTHON_BIN=%WORKMATE_PYTHON_ENV%\Scripts\python.exe"
if not exist "%PYTHON_BIN%" (
  echo Python 가상환경을 찾을 수 없습니다: %WORKMATE_PYTHON_ENV%
  echo WORKMATE_PYTHON_ENV 환경 변수로 가상환경 위치를 지정해 주세요.
  pause
  exit /b 1
)

"%PYTHON_BIN%" -c "import fastapi, pypdf, docx, openpyxl" >nul 2>nul
if errorlevel 1 (
  echo 백엔드 의존성을 설치합니다...
  "%PYTHON_BIN%" -m pip install -r backend\requirements.txt
  if errorlevel 1 goto :error
)

if not exist "node_modules" (
  echo 프런트엔드 의존성을 설치합니다...
  call npm install
  if errorlevel 1 goto :error
)

echo WorkMate 백엔드를 시작합니다...
start "WorkMate Backend" /b cmd /c "cd /d \"%CD%\backend\" && \"%PYTHON_BIN%\" -m uvicorn server.main:app --port 8765"

echo WorkMate 데스크톱 앱을 시작합니다...
call npm run dev
goto :end

:error
echo 실행 준비 중 오류가 발생했습니다.
pause

:end
endlocal
