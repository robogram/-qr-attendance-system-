# -*- coding: utf-8 -*-
import os
import winshell
from win32com.client import Dispatch

# 1. Start Script Content (Robust Version)
# - Handles trailing backslashes
# - Uses CP949 for Windows CMD compatibility
# - Simplified start commands
bat_content = r'''@echo off
setlocal
chcp 65001 >nul

:: %~dp0 ends with \, remove it for safe quoting
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

cd /d "%ROOT_DIR%"

echo ========================================
echo [ 로보그램 QR 출석 시스템 시작 ]
echo   위치: %ROOT_DIR%
echo ========================================
echo.

:: Check venv
if not exist "venv\Scripts\activate.bat" (
    echo [오류] venv 환경을 찾을 수 없습니다. 설치를 확인해주세요.
    pause
    exit /b
)

:: 1. Flask Camera
echo [1/5] 📸 Flask 카메라 서버 시작...
start "[Flask] Camera" /min cmd /c "call venv\Scripts\activate.bat && python flask_qr_attendance_app.py"
timeout /t 3 /nobreak >nul

:: 2. Admin App
echo [2/5] 👨‍💼 관리자 앱 시작...
start "[Admin] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run admin_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 3. Teacher App
echo [3/5] 👩‍🏫 선생님 앱 시작...
start "[Teacher] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run teacher_app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 4. Parent App
echo [4/5] 👨‍👩‍👧‍👦 학부모 앱 시작...
start "[Parent] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run parent_app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

:: 5. Student App
echo [5/5] 👦 학생 앱 시작...
start "[Student] Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run student_app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true"
timeout /t 4 /nobreak >nul

echo.
echo ========================================
echo 모든 시스템이 시작되었습니다.
echo ========================================
echo.
echo 🌐 접속 주소:
echo    - 관리자: http://localhost:8501
echo    - 선생님: http://localhost:8502
echo.
echo 💡 관리자 페이지를 자동으로 엽니다...
start "" "http://localhost:8501"

echo.
echo 이 창을 닫아도 서버는 백그라운드에서 계속 실행됩니다.
pause
'''

def setup():
    current_dir = os.getcwd()
    bat_path = os.path.join(current_dir, "start_system.bat")
    icon_path = os.path.join(current_dir, "icons", "attendance_icon.ico")
    
    # Write .bat file (CP949)
    try:
        with open(bat_path, 'w', encoding='cp949') as f:
            f.write(bat_content)
        print(f"✅ 배치 파일 생성 완료: {bat_path}")
    except Exception as e:
        print(f"❌ 배치 파일 생성 실패: {e}")
        return

    # Create Desktop Shortcut
    try:
        desktop = winshell.desktop()
        shell = Dispatch('WScript.Shell')
        shortcut_path = os.path.join(desktop, "로보그램 QR 출석 시스템.lnk")
        
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = bat_path
        shortcut.WorkingDirectory = current_dir
        if os.path.exists(icon_path):
            shortcut.IconLocation = icon_path
        shortcut.save()
        print(f"✅ 바탕화면 바로가기 생성 완료: {shortcut_path}")
    except Exception as e:
        print(f"❌ 바로가기 생성 실패: {e}")

if __name__ == "__main__":
    setup()
