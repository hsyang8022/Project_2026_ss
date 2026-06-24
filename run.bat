@echo off
chcp 65001 >nul
REM ============================================================
REM  청출어람 대시보드 - 재실행 (run.bat)
REM  최초 1회 setup.bat 실행 후, 다음부터는 이 파일을 쓰세요.
REM ============================================================
cd /d "%~dp0"
title 청출어람 대시보드 - 실행

if not exist ".venv\Scripts\activate.bat" (
    echo [오류] 가상환경(.venv)이 없습니다. 먼저 setup.bat을 실행하세요.
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo ============================================================
echo   대시보드를 실행합니다. (종료: 이 창에서 Ctrl + C)
echo ============================================================
echo.
python -m streamlit run app.py

pause
