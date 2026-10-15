# 🌐 Cloudflare Pages 도메인 호스팅 및 배포 가이드

본 수료증 발급 시스템은 **Cloudflare Pages**와 **Pages Functions**를 완벽하게 지원하도록 구성되었습니다.  
별도의 24시간 파이썬 백엔드 서버 없이도 전 세계 초고속 글로벌 CDN 및 무료 SSL(HTTPS) 인증서가 적용된 도메인으로 배포할 수 있습니다.

---

## 🚀 방법 1. 원클릭 터미널 배포 (가장 빠르고 간편한 방법)

프로젝트 폴더 내에 생성된 [`deploy_to_cloudflare.bat`](file:///E:/AI%20%EA%B0%9C%EB%B0%9C%20%ED%98%91%EC%97%85/%EC%9E%91%EC%97%85%EB%AC%BC/qr_attendance/%EC%BD%94%EB%94%A9%EC%BA%A0%ED%94%84%EC%9A%A9%20%EC%88%98%EB%A3%8C%EC%A6%9D%EC%95%B1%EB%A7%8C%EB%93%A4%EA%B8%B0/deploy_to_cloudflare.bat)을 더블 클릭하거나, 터미널(PowerShell)에서 아래 명령어를 실행합니다:

```bash
cd "E:\AI 개발 협업\작업물\qr_attendance\코딩캠프용 수료증앱만들기"
npx wrangler pages deploy . --project-name=robogram-camp-cert
```

1. **최초 1회 인증**: 실행 시 브라우저가 열리며 Cloudflare 로그인 및 권한 승인 창(`Allow`)이 표시됩니다.
2. **배포 완료**: 수 초 내에 정적 파일과 Functions API가 업로드되며, `https://robogram-camp-cert.pages.dev` 형태의 고유 URL이 즉시 발급됩니다.

---

## 🔄 방법 2. GitHub 연동 자동 배포 (Git Push 시 자동 업데이트)

1. **Cloudflare 대시보드** ([dash.cloudflare.com](https://dash.cloudflare.com/))에 로그인합니다.
2. 좌측 메뉴에서 **Workers & Pages** -> **Create application** -> **Pages** -> **Connect to Git**을 선택합니다.
3. GitHub 계정을 연동하고 `-qr-attendance-system-` 저장소를 선택합니다.
4. 빌드 설정을 아래와 같이 입력합니다:
   - **Framework preset**: `None`
   - **Root directory**: `코딩캠프용 수료증앱만들기`
   - **Build command**: (비워둠)
   - **Build output directory**: (비워둠 또는 `.`)
5. **[Save and Deploy]** 버튼을 누르면 1분 내에 배포가 완료됩니다.

---

## 🏷️ 보유 도메인 연결 (Custom Domain)

발급된 `*.pages.dev` 주소 대신 보유하신 도메인(예: `cert.robogram.net`)으로 연결하는 방법:

1. Cloudflare 대시보드 -> **Workers & Pages**로 이동합니다.
2. 생성된 `robogram-camp-cert` 프로젝트를 클릭합니다.
3. 상단 **Custom domains (커스텀 도메인)** 탭을 클릭합니다.
4. **[Set up a custom domain]** 버튼을 누르고 연결할 도메인 주소(예: `cert.robogram.net`)를 입력합니다.
5. Cloudflare DNS를 이미 사용 중이시라면 CNAME 레코드가 1초 만에 자동 생성되며, **무료 SSL 보안인증서(HTTPS)**가 즉시 활성화됩니다!

---

## 💾 관리자 데이터 영구 저장을 위한 Cloudflare KV 바인딩 (선택 사항)

> **안내**: 바인딩을 하지 않더라도 현재 등록된 한국반도체마이스터고 40명 학생 데이터와 기본 수료증 발급은 100% 정상 작동합니다.  
> 향후 웹 관리자 페이지에서 학생 명단을 추가/수정하거나 직인을 바꾼 내용이 Cloudflare 클라우드에 영구 보존되길 원하시면 아래 설정을 1회 진행해주세요:

1. Cloudflare 대시보드 -> **Workers & Pages** -> **KV** 메뉴로 이동합니다.
2. **[Create namespace]** 클릭 -> 이름: `CAMP_DATA_KV` 입력 후 생성.
3. `robogram-camp-cert` Pages 프로젝트로 이동 -> **Settings** -> **Functions** 클릭.
4. **KV namespace bindings** 항목에서 **[Add binding]** 클릭:
   - **Variable name**: `CAMP_KV` (반드시 대문자로 정확히 입력)
   - **KV namespace**: 방금 생성한 `CAMP_DATA_KV` 선택 후 저장.
5. 이제 관리자 페이지에서 수정한 모든 정보(학교, 학생, 직인)가 Cloudflare 글로벌 엣지 DB에 실시간 저장됩니다.
