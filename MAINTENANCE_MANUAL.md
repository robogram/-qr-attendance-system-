# 📘 QR 출석 시스템 운영 및 유지보수 매뉴얼 (Maintenance Manual)

이 문서는 QR 출석 시스템 운영 중 반복적으로 발생할 수 있는 UI 및 배포 관련 문제의 근본 원인과 확실한 해결 방법을 기록한 '교과서'입니다. 향후 동일 문제 발생 시 이 매뉴얼을 최우선으로 참조하십시오.

---

## 🚀 1. 배포 오류 해결 (Deployment Troubleshooting)

### 🚨 증상: GitHub 푸시는 성공했으나 Hugging Face 화면에 변화가 없음
**원인**: GitHub Actions에서 Hugging Face로 소스를 전송할 때 '바이너리 파일(Binary Files)' 거부 정책으로 인해 동기화가 중단된 경우입니다.

**확실한 해결책**:
1.  **방해 파일 제거**: 프로젝트 루트에 불필요한 대용량 백업 파일(예: `old_*.py`, `.tmp`, `*.bak`)이 있는지 확인하고 삭제합니다.
2.  **로그 확인**: GitHub 저장소의 `Actions` 탭에서 `Sync to Hugging Face Hub` 워크플로우가 붉은색(실패)인지 확인합니다.
3.  **Hugging Face 강제 재시작**: 배포 성공 후에도 변화가 없다면 HF Space의 `Settings` -> `Factory Reboot` 버튼을 눌러 컨테이너를 재생성합니다.

---

## 🎨 2. UI 가독성 고정 (UI Visibility Fix)

### 🚨 증상: 로그인 입력창의 글자가 안 보이거나 배경이 어두움
**원인**: Streamlit의 내부 테마 엔진(Dark/Light 모드)이 커스텀 CSS보다 우선순위를 가질 때 발생합니다.

**확실한 해결책 (전역 CSS 패턴)**:
`streamlit_app.py` 최상단에 아래 코드를 주입하여 브라우저 환경에 관계없이 흰색 배경을 강제합니다.
```python
st.markdown("""
<style>
    input[type="text"], input[type="password"], [data-baseweb="input"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)
```

---

## 🤖 3. 마스코트 이미지 관리 (Mascot Implementation)

### 🚨 증상: 캐릭터 이미지가 깨져서 나오거나 엑스박스로 표시됨
**원인**: HTML Base64 인코딩 방식은 문자열이 너무 길어 웹에서 처리 오류가 잦으며 경로 의존성이 높습니다.

**확실한 해결책**:
- **반드시** Streamlit의 순수 기능인 `st.image()`를 사용하십시오.
```python
st.image("static/mascot_small.png", width=140)
```
- **이미지 위치**: 항상 `static/mascot_small.png` 경로를 준수하십시오.

---

## 📌 4. 유지보수 체크리스트
1.  **File Cleanup**: 정기적으로 `old_`로 시작하는 백업 파일들을 삭제하여 배포 효율을 높이십시오.
2.  **Global Sync**: `streamlit_app.py`, `user_portal.py`, `staff_portal.py` 세 파일의 CSS 스타일이 일치하는지 확인하십시오.
3.  **Cache Control**: 수정 후에는 반드시 브라우저 강력 새로고침(`Ctrl + F5`)을 수행하십시오.

---
> **최종 업데이트**: 2026-04-18
> **작성자**: Antigravity AI 시스템
