@echo off
chcp 65001 >nul
REM ============================================================
REM  청출어람 대시보드 - 최초 설치 및 실행 (setup.bat)
REM  이 파일을 더블클릭하거나 cmd에서 실행하세요.
REM ============================================================
cd /d "%~dp0"
title 청출어람 대시보드 - 설치/실행

echo.
echo ============================================================
echo   청출어람 대시보드 설치를 시작합니다.
echo ============================================================
echo.

REM --- 1) Python 설치 확인 ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo        https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하세요.
    echo        설치 시 "Add python.exe to PATH" 체크를 꼭 하세요.
    echo.
    pause
    exit /b 1
)
echo [확인] Python 설치됨:
python --version
echo.

REM --- 2) 가상환경 생성 (없을 때만) ---
if exist ".venv\Scripts\activate.bat" (
    echo [건너뜀] 가상환경(.venv)이 이미 존재합니다.
) else (
    echo [진행] 가상환경(.venv)을 생성합니다...
    python -m venv .venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
)
echo.

REM --- 3) 가상환경 활성화 ---
call ".venv\Scripts\activate.bat"

REM --- 4) 패키지 설치 ---
echo [진행] 필수 패키지를 설치합니다...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하세요.
    pause
    exit /b 1
)
echo.

REM --- 5) 대시보드 실행 ---
echo ============================================================
echo   설치 완료! 대시보드를 실행합니다.
echo   브라우저가 자동으로 열립니다. (종료: 이 창에서 Ctrl + C)
echo ============================================================
echo.
python -m streamlit run app.py

pause
