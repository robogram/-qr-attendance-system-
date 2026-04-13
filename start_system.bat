@echo off
setlocal

set ROOT_DIR=%~dp0
if "%ROOT_DIR:~-1%"=="\" set ROOT_DIR=%ROOT_DIR:~0,-1%
cd /d "%ROOT_DIR%"

echo ========================================
echo QR Attendance System Start
echo ========================================
echo.

echo [1/5] Starting Flask Camera Server...
start "Flask Camera" /min cmd /c "call venv\Scripts\activate.bat && python flask_qr_attendance_app.py"
timeout /t 3 /nobreak >nul

echo [2/5] Starting Admin App...
start "Admin Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run admin_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

echo [3/5] Starting Teacher App...
start "Teacher Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run teacher_app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

echo [4/5] Starting Parent App...
start "Parent Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run parent_app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true"
timeout /t 2 /nobreak >nul

echo [5/5] Starting Student App...
start "Student Web" /min cmd /c "call venv\Scripts\activate.bat && streamlit run student_app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true"
timeout /t 4 /nobreak >nul

echo.
echo All systems running. Opening Admin Page...
start "" "http://localhost:8501"
echo.
pause