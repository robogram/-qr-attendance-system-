# 📗 로보그램 QR 출석 시스템: 기술 복구 교과서 (Recovery Textbook)

이 문서는 과거 수차례 반복되었던 **배포 장애**와 **UI 가독성 문제**를 근본적으로 해결하고, 향후 신입 개발자나 관리자가 시스템을 즉시 복구할 수 있도록 작성된 가이드입니다.

---

## 🛠️ 문제 1: 배포 채널 차단 (Git History Issue)

### 🚨 문제 현상
*   코드를 수정하고 GitHub에 올렸으나, 실제 사이트(Hugging Face)에는 반영되지 않음.
*   GitHub Actions 로그에서 **"Your push was rejected because it contains binary files"** 에러 발생.

### 💡 원인 분석
*   이미 삭제한 백업 파일(`old_*.py`)이라도 Git의 과거 역사(History) 어딘가에 남아있으면 Hugging Face 서버는 이를 거부합니다. 단순 삭제(Delete)만으로는 부족하며, 기록 자체를 세척(Purge)해야 합니다.

### ✅ 복구 명령어 (반드시 순서대로 실행)
1. **역사 기록 세척**: 모든 커밋에서 문제의 파일 흔적을 지웁니다.
   ```powershell
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch old_student_app.py old_teacher_app.py" --prune-empty --tag-name-filter cat -- --all
   ```
2. **강제 업데이트**: 수정한 기록을 서버에 강제로 덮어씁니다.
   ```powershell
   git push origin main --force
   ```

---

## 🎨 문제 2: 입력창 글자 안 보임 (UI Contrast Issue)

### 🚨 문제 현상
*   아이디/비밀번호 입력란의 배경과 글자색이 구분되지 않아 사용자가 로그인할 수 없음.

### 💡 원인 분석
*   Streamlit의 다크 모드/라이트 모드 설정이 브라우저마다 다르며, 일반적인 CSS는 이 시스템 설정을 이기지 못할 때가 많습니다.

### ✅ 복구 솔루션 (전역 강제 주입)
*   `streamlit_app.py`의 최상단(페이지 설정 직후)에 아래 코드를 고정하십시오. `!important`가 핵심입니다.
```python
st.markdown("""
<style>
    /* 모든 텍스트/비밀번호 입력창에 대해 흰색 배경과 검정 글씨를 강제합니다. */
    input[type="text"], input[type="password"], [data-baseweb="input"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)
```

---

## 🖼️ 문제 3: 마스코트 이미지 깨짐 (Image Loading Issue)

### 🚨 문제 현상
*   로그인 페이지의 캐릭터 이미지가 엑스박스(X)로 나오거나 매우 느리게 뜸.

### 💡 원인 분석
*   이미지를 텍스트(Base64)로 변환해 저장하는 방식은 코드가 수만 줄로 길어져 배포 중 데이터 손실이 발생하기 쉽습니다.

### ✅ 복구 솔루션 (정적 경로 방식)
*   항상 `static` 폴더를 유지하고 아래 표준 로딩 방식을 사용하십시오.
```python
# 가장 빠르고 확실한 로딩 방식
st.image("static/mascot_small.png", width=140)
```

---

## 🚀 최종 체크리스트 (점검 교과서)

1.  **불필요한 파일 삭제**: `old_`, `backup_` 등 임시 파일을 생성하지 마십시오. 배포 서버의 용량 및 정책 위반의 주범입니다.
2.  **강제 동기화**: 배포 후에도 화면이 그대로라면 Hugging Face 설정에서 **"Factory rebuild"**를 누르십시오.
3.  **브라우저 캐시**: `Ctrl + Shift + R`을 눌러 강력 새로고침을 생활화하십시오.

---
> **최종 검수**: 2026-04-18
> **주의**: 이 가이드를 벗어난 CSS 수정은 UI 가독성 장애를 재발시킬 수 있습니다.
