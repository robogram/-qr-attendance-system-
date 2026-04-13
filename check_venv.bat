@echo off
echo ========================================
echo ?? 가상환경 체크
echo ========================================

cd C:\Users\User\Downloads\qr_attendance

echo.
echo [1/4] venv 폴더 확인...
if exist venv (
    echo ? venv 폴더 발견!
    goto :activate
) else (
    echo ? venv 폴더 없음
    goto :create
)

:activate
echo.
echo [2/4] 가상환경 활성화 시도...
call venv\Scripts\activate
if %errorlevel% == 0 (
    echo ? 가상환경 활성화 성공!
    goto :check_packages
) else (
    echo ? 활성화 실패 - 재생성 필요
    goto :create
)

:create
echo.
echo [3/4] 가상환경 생성 중...
python -m venv venv
if %errorlevel% == 0 (
    echo ? 가상환경 생성 완료!
    call venv\Scripts\activate
    goto :install_packages
) else (
    echo ? 생성 실패 - Python 설치 확인 필요
    pause
    exit
)

:install_packages
echo.
echo [4/4] 패키지 설치 중...
if exist requirements.txt (
    pip install -r requirements.txt
    echo ? 패키지 설치 완료!
) else (
    echo ?? requirements.txt 없음
)
goto :end

:check_packages
echo.
echo [3/4] 설치된 패키지 확인...
pip list
echo.
echo [4/4] 필요한 패키지 체크...
python -c "import streamlit; print('? Streamlit OK')" 2>nul || echo "? Streamlit 없음"
python -c "import pandas; print('? Pandas OK')" 2>nul || echo "? Pandas 없음"
python -c "import flask; print('? Flask OK')" 2>nul || echo "? Flask 없음"

:end
echo.
echo ========================================
echo ?? 체크 완료!
echo ========================================
pause