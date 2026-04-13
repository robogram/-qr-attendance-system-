@echo off
setlocal

set ROOT_DIR=%~dp0
if "%ROOT_DIR:~-1%"=="\" set ROOT_DIR=%ROOT_DIR:~0,-1%
cd /d "%ROOT_DIR%"

echo ========================================
11: echo QR Attendance Scanner (LOCAL ONLY)
echo ========================================
echo.

echo [*] Starting Flask Camera Server...
echo [Notice] Dashboards are now hosted in the Cloud.
echo.

call venv\Scripts\activate.bat
python flask_qr_attendance_app.py

pause
