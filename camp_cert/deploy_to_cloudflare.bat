@echo off
chcp 65001 > nul
echo ========================================================
echo   로보그램 코딩캠프 수료증 앱 - Cloudflare Pages 자동 배포
echo ========================================================
echo.
echo [1/3] 배포 준비 중...
cd /d "%~dp0"

echo [2/3] Cloudflare Pages로 프로젝트 배포를 시작합니다.
echo       (최초 1회 실행 시 웹 브라우저가 열리며 Cloudflare 로그인 창이 뜹니다)
echo.

npx wrangler pages deploy . --project-name=robogram-camp-cert --commit-dirty=true

echo.
echo ========================================================
echo [3/3] 배포가 완료되었습니다!
echo       발급된 *.pages.dev 주소로 즉시 접속 가능합니다.
echo.
echo  * 도메인 연결 방법:
echo    Cloudflare 대시보드 (dash.cloudflare.com) -> Workers & Pages 
echo    -> robogram-camp-cert 프로젝트 -> 'Custom domains' 탭에서
echo    보유하신 도메인(예: cert.robogram.net)을 연결하시면 됩니다.
echo ========================================================
pause
