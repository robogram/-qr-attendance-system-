# -*- coding: utf-8 -*-
import os

content = r'''@echo off
chcp 65001 >nul
setlocal

:: 현재 폴더 경로 설정 (공백 포함 경로 대응)
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo ========================================
echo [ 로보그램 QR 출석 시스템 전체 시작 ]
echo   (위치: %BASE_DIR%)
echo ========================================
echo.

:: 1. Flask 카메라 서버
echo [1/5] 📸 Flask 카메라 서버 시작...
start "[Flask] Camera 5000" /min cmd /c "cd /d "%BASE_DIR%" && call venv\Scripts\activate && python flask_qr_attendance_app.py"
timeout /t 3 /nobreak >nul

:: 2. 관리자 앱
echo [2/5] 👨‍💼 관리자 앱 시작...
start "[Admin] Web 8501" /min cmd /c "cd /d "%BASE_DIR%" && call venv\Scripts\activate && streamlit run admin_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 3. 선생님 앱
echo [3/5] 👩‍🏫 선생님 앱 시작...
start "[Teacher] Web 8502" /min cmd /c "cd /d "%BASE_DIR%" && call venv\Scripts\activate && streamlit run teacher_app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 4. 학부모 앱
echo [4/5] 👨‍👩‍👧‍👦 학부모 앱 시작...
start "[Parent] Web 8503" /min cmd /c "cd /d "%BASE_DIR%" && call venv\Scripts\activate && streamlit run parent_app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 5. 학생 앱
echo [5/5] 👦 학생 앱 시작...
start "[Student] Web 8504" /min cmd /c "cd /d "%BASE_DIR%" && call venv\Scripts\activate && streamlit run student_app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true"
timeout /t 4 /nobreak >nul

echo.
echo ========================================
echo [ 모든 시스템 시작 완료! ]
echo ========================================
echo.
echo 🌐 접속 주소:
echo    - 관리자: http://localhost:8501
echo    - 선생님: http://localhost:8502
echo    - 학부모: http://localhost:8503
echo    - 학생:   http://localhost:8504
echo.
echo 💡 관리자 페이지를 엽니다...
start "" "http://localhost:8501"

timeout /t 5 /nobreak >nul
echo 이 창을 닫아도 서버는 백그라운드에서 계속 실행됩니다.
pause
'''

bat_path = r'e:\다운로드\qr_attendance\start_system.bat'
try:
    with open(bat_path, 'w', encoding='cp949') as f:
        f.write(content)
    print(f"Successfully wrote {bat_path} in CP949 encoding.")
except Exception as e:
    print(f"Error: {e}")
