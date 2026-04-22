# 🚀 ROBOGRAM QR Attendance System - Handover Document

이 파일은 프로젝트의 현재 상태, 핵심 기술적 해결책, 그리고 향후 작업 방향을 기록한 문서입니다. **새로운 작업을 시작하기 전 반드시 이 문서를 정독하십시오.**

---

## 1. 프로젝트 현재 상태 (2026-04-20 기준)
전체 포털(관리자, 교사, 학생, 학부모)의 디자인을 프리미엄 **"글래스모피즘(Glassmorphism)"** 스타일로 전환 완료했습니다. 단순히 레이아웃만 바꾼 것이 아니라, 사용자 경험(UX)을 고려한 애니메이션과 피드백 로직이 적용되어 있습니다.

### 핵심 업데이트 사항:
*   **`user_portal.py` (v1.2.2)**: 
    *   로그인 실패 시 **Shake 애니메이션** 및 **빨간색 경고 박스** 노출.
    *   성공 시 전용 **"마스코트 환영 뷰(Success View)"** 렌더링 후 대시보드 진입.
    *   `st.set_page_config` 최상단 배치로 리셋 버그 해결.
*   **`staff_portal.py`**:
    *   관리자용 고도화된 로그인 UI 적용 (대형 마스코트 및 입체적 CSS).
*   **Asset**: 프리미엄 마스코트 이미지(`static/mascot_premium.png`)를 메인 자산으로 사용.

---

## 2. 핵심 기술적 해결 (영업 비밀 및 복구 지침)

### ⚠️ Hugging Face 배포 이슈: Git LFS 및 바이너리 오염 해결
과거 커밋 기록에 남아있던 대용량 바이너리 파일(`mascot_small.png` 등) 때문에 허깅페이스 배포가 차단되는 심각한 문제가 있었습니다. 이를 **Git 히스토리 세척(Purge)**을 통해 해결했습니다.

*   **해결 방법**: `git filter-branch --force --index-filter "git rm --cached --ignore-unmatch static/mascot_small.png" --prune-empty --tag-name-filter cat -- --all` 명령으로 과거 기록을 완전히 지우고 `git push --force`를 수행함.
*   **주의**: 향후 10MB 이상의 파일은 절대 바로 푸시하지 말고, 필요시 Git LFS를 사용하거나 이미지를 최적화하여 업로드해야 합니다.

---

## 3. 시스템 아키텍처 및 로직

*   **인증 시스템**: `auth.py`를 통해 Supabase와 연동. 
    *   **ID**: 학생/학부모 이름
    *   **Password**: 생년월일 6자리 (예: 150305)
*   **디자인 테마**:
    *   배경: 파스텔 톤 그라데이션 (`linear-gradient`)
    *   컨테이너: 투명도 0.7, Blur 15px, 흰색 테두리.
*   **배포 파이프라인**: GitHub Actions(`hf_sync.yml`)를 통해 GitHub -> Hugging Face Hub로 자동 동기화.

---

## 4. 향후 작업 가이드 (Next Steps)

1.  **데이터 무결성 확인**: 현재 Supabase에 학생들의 생년월일 정보가 최신 CSV와 일치하는지 `migrate_csv_to_supabase.py`를 통해 재검토가 필요할 수 있습니다.
2.  **타임존 설정**: 출석 기록 시 한국 시간(KST, 09:30 기준)이 정확히 반영되는지 `student_app.py`와 `parent_app.py`의 `datetime` 로직을 모니터링하십시오.
3.  **추가 기능**: 학생용 "Success View" 이후에 등장하는 대시보드 내부의 표(Table) 디자인도 글래스모피즘 스타일로 통일하는 작업을 제안합니다.

---

## 🤖 다음 AI 어시스턴트에게 주는 메시지
> "이 프로젝트는 Streamlit을 기반으로 하며, 매우 세밀한 CSS 커스터마이징이 적용되어 있습니다. 특히 `user_portal.py`의 `login_screen` 함수 내에 있는 CSS 블록과 세션 상태(`st.session_state`) 관리 로직은 UI의 품질을 결정하는 핵심이므로, 수정 시 기존의 `!important` 속성과 애니메이션 타이밍을 세심하게 살펴보고 작업하십시오."

최종 업데이트일: 2026-04-20
작성자: Antigravity (Powered by Google DeepMind)
