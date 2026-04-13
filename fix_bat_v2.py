# -*- coding: utf-8 -*-
import os

# We will use a more robust way to handle paths and quotes in Batch
content = r'''@echo off
setlocal
chcp 65001 >nul

:: %~dp0 ends with \, we remove it for safer quoting
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

cd /d "%ROOT%"

echo ========================================
echo [ 로보그램 QR 출석 시스템 시작 ]
echo   (위치: %ROOT%)
echo ========================================
echo.

:: 1. Flask Camera
echo [1/5] Flask 카메라 서버 시작...
start "[Flask] Camera" /min cmd /c "call venv\Scripts\activate.bat && python flask_qr_attendance_app.py"
timeout /t 3 /nobreak >nul

:: 2. Admin App
echo [2/5] 관리자 앱 시작...
start "[Admin] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run admin_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 3. Teacher App
echo [3/5] 선생님 앱 시작...
start "[Teacher] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run teacher_app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 4. Parent App
echo [4/5] 학부모 앱 시작...
start "[Parent] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run parent_app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 5. Student App
echo [5/5] 학생 앱 시작...
start "[Student] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run student_app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true"
timeout /t 4 /nobreak >nul

echo.
echo ========================================
echo 모든 시스템이 시작되었습니다.
echo ========================================
echo.

:: Open Admin page
start "" "http://localhost:8501"

echo 이 창을 닫아도 배경에서 서버가 계속 실행됩니다.
pause
'''

bat_path = r'e:\다운로드\qr_attendance\start_system.bat'
try:
    # Use CP949 (Korean ANSI) which is most reliable for Windows Batch files
    with open(bat_path, 'w', encoding='cp949') as f:
        f.write(content)
    print(f"Successfully fixed {bat_path}")
except Exception as e:
    print(f"Error writing batch file: {e}")
